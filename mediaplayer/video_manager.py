import os
import subprocess
import time
import tempfile
import shutil
import glob
import mimetypes
from core import CACHE_DIR, ensure_dirs, get_ffmpeg_paths

# Formati video supportati
SUPPORTED_VIDEO_FORMATS = [
    # Comuni
    '.mp4', '.avi', '.mkv', '.webm', '.mov', '.flv', '.wmv', '.mpg', '.mpeg',
    # Meno comuni ma supportati da ffmpeg
    '.ts', '.m4v', '.3gp', '.vob', '.ogv', '.asf', '.m2ts', '.mts'
]

class VideoManager:
    def __init__(self):
        ensure_dirs()
        self.frame_cache = {}
        self.current_video = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 24.0
        self.extraction_complete = False
        self.extraction_progress = 0
        self.ffmpeg_path, self.ffprobe_path = get_ffmpeg_paths()
        
        # Inizializzazione dei tipi MIME
        mimetypes.init()
        # Aggiungi tipi MIME che potrebbero mancare
        for ext in SUPPORTED_VIDEO_FORMATS:
            if ext not in mimetypes.types_map:
                mimetypes.add_type(f'video/x-{ext[1:]}', ext)
        
    def is_video_file(self, filepath):
        """
        Verifica se il file è un video controllando l'estensione e/o il tipo MIME.
        
        Args:
            filepath: Percorso del file da controllare
            
        Returns:
            True se il file è un video, False altrimenti
        """
        if not os.path.isfile(filepath):
            return False
            
        # Verifica prima per estensione (più veloce)
        extension = os.path.splitext(filepath)[1].lower()
        if extension in SUPPORTED_VIDEO_FORMATS:
            return True
            
        # Poi verifica il tipo MIME (più preciso ma più lento)
        mime_type = mimetypes.guess_type(filepath)[0]
        if mime_type and mime_type.startswith('video/'):
            return True
            
        # Come ultima risorsa, prova a usare ffprobe per verificare
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-v", "quiet", "-show_streams", "-select_streams", "v", filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2
            )
            return result.returncode == 0 and b"codec_type=video" in result.stdout
        except:
            pass
            
        return False
    
    def check_ffmpeg(self):
        """Verifica che ffmpeg sia installato."""
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   timeout=3)
            return result.returncode == 0
        except:
            return False
            
    def extract_frames(self, video_path, output_dir=None, fps=None, start_time=0, duration=None, callback=None):
        """
        Estrae i frame da un video usando ffmpeg, con supporto per callback di progresso.
        
        Args:
            video_path: Percorso del file video
            output_dir: Directory di output (usa una dir temporanea se non specificata)
            fps: Frame per secondo da estrarre (usa il FPS nativo se non specificato)
            start_time: Tempo di inizio in secondi
            duration: Durata in secondi (estrae tutto il video se non specificata)
            callback: Funzione di callback che riceve l'avanzamento (0-100)
            
        Returns:
            Percorso della directory contenente i frame
        """
        if not self.check_ffmpeg():
            print("ERRORE: ffmpeg non trovato. Installalo per usare la funzionalità video.")
            return None
            
        # Crea directory temporanea se non specificata
        if output_dir is None:
            # Usa la sottodirectory dedicata per l'estrazione dei frame
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.join(CACHE_DIR, "extracted_frames", f"video_{video_name}_{int(time.time())}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Ottieni durata totale del video per calcolare il progresso
        video_info = self.get_video_info(video_path)
        
        if not video_info:
            print("AVVISO: Impossibile ottenere informazioni sul video. Utilizzo metodo alternativo.")
            # Tenta un'estrazione base senza conoscere la durata
            return self._extract_frames_basic(video_path, output_dir, fps, start_time, duration, callback)
        
        total_duration = video_info.get('duration', 0) if video_info else 0
        
        if not duration and total_duration > 0:
            duration = total_duration - start_time
        
        # Costruisci il comando ffmpeg
        cmd = [self.ffmpeg_path, "-i", video_path]
        
        # Aggiungi opzioni di inizio e durata se specificate
        if start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        if duration:
            cmd.extend(["-t", str(duration)])
            
        # Imposta FPS se specificato, altrimenti usa quello del video
        if fps:
            self.fps = fps
        elif video_info and 'fps' in video_info:
            self.fps = video_info['fps']
            
        # Aggiungi filtro FPS se specificato
        if fps:
            cmd.extend(["-vf", f"fps={fps}"])
        
        # Aggiungi parametri di output
        cmd.extend([
            "-q:v", "1",  # Alta qualità
            f"{output_dir}/frame_%04d.jpg"
        ])
        
        # Esegui ffmpeg con monitoraggio del progresso
        self.extraction_complete = False
        self.extraction_progress = 0
        
        try:
            # Avvio del processo con pipe per stderr per monitorare il progresso
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitora l'output per il progresso
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                    
                # Cerca informazioni di tempo nell'output
                if "time=" in line and total_duration > 0:
                    time_str = line.split("time=")[1].split(" ")[0]
                    try:
                        # Converti il formato HH:MM:SS.ms in secondi
                        h, m, s = time_str.split(':')
                        current_time = float(h) * 3600 + float(m) * 60 + float(s)
                        progress = min(100, int((current_time / total_duration) * 100))
                        
                        # Aggiorna il progresso
                        self.extraction_progress = progress
                        
                        # Chiama il callback se specificato
                        if callback:
                            callback(progress)
                    except:
                        pass
            
            # Attendi il completamento del processo
            process.wait()
            
            # Verifica se è andato a buon fine
            if process.returncode != 0:
                print(f"Errore nell'estrazione dei frame: codice {process.returncode}")
                self.extraction_complete = False
                return None
                
            # Conta i frame estratti
            frames = sorted(glob.glob(f"{output_dir}/frame_*.jpg"))
            self.total_frames = len(frames)
            self.current_video = output_dir
            self.current_frame = 0
            self.frames = frames  # Salva i frame estratti in ordine
            
            # Segnala completamento
            self.extraction_complete = True
            self.extraction_progress = 100
            
            if callback:
                callback(100)
                
            print(f"Estratti {self.total_frames} frame in {output_dir}")
            return output_dir
        except Exception as e:
            print(f"Errore nell'estrazione dei frame: {e}")
            self.extraction_complete = False
            return None

    def _extract_frames_basic(self, video_path, output_dir, fps, start_time, duration, callback):
        """Metodo di fallback per estrazione frame quando non si può ottenere info video."""
        try:
            # Usa un approccio più semplice che estrae un numero fisso di frame
            max_frames = 500  # Limita il numero di frame
            
            # Costruisci il comando ffmpeg
            cmd = [self.ffmpeg_path, "-y", "-i", video_path]
            
            # Aggiungi opzioni di inizio e durata se specificate
            if start_time > 0:
                cmd.extend(["-ss", str(start_time)])
            if duration:
                cmd.extend(["-t", str(duration)])
                
            # Imposta FPS se specificato
            if fps:
                self.fps = fps
                cmd.extend(["-vf", f"fps={fps}"])
            
            # Limita il numero di frame
            cmd.extend(["-vframes", str(max_frames)])
            
            # Aggiungi parametri di output
            cmd.extend([
                "-q:v", "1",  # Alta qualità
                f"{output_dir}/frame_%04d.jpg"
            ])
            
            print(f"Comando di estrazione: {' '.join(cmd)}")
            
            # Esegui il comando
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.returncode != 0:
                print(f"Errore nell'estrazione dei frame: {process.stderr}")
                return None
                
            # Conta i frame estratti
            frames = sorted(glob.glob(f"{output_dir}/frame_*.jpg"))
            self.total_frames = len(frames)
            if self.total_frames == 0:
                print("Nessun frame estratto!")
                return None
                
            self.current_video = output_dir
            self.current_frame = 0
            self.frames = frames  # Salva i frame estratti in ordine
            self.extraction_complete = True
            self.extraction_progress = 100
            
            if callback:
                callback(100)
                
            print(f"Estratti {self.total_frames} frame in {output_dir}")
            return output_dir
            
        except Exception as e:
            print(f"Errore nell'estrazione di base dei frame: {e}")
            return None
            
    def get_frame(self, frame_number=None):
        """
        Restituisce il frame specificato dal video corrente.
        Se frame_number non è specificato, restituisce il frame corrente
        e incrementa il contatore.
        """
        if not self.current_video:
            print("Errore: Nessun video corrente impostato")
            return None
            
        if frame_number is None:
            frame_number = self.current_frame
            self.current_frame += 1
            
        # Riavvolge alla fine del video
        if frame_number >= self.total_frames:
            frame_number = self.total_frames - 1
            
        # Gestione dei frame oltre la fine del video
        if frame_number < 0 or frame_number >= self.total_frames:
            return None

        # Ottieni il percorso del frame
        frame_path = self.frames[frame_number]
        
        # Usa la cache se il frame è già caricato
        if frame_path in self.frame_cache:
            return self.frame_cache[frame_path]
            
        # Verifica esistenza (senza stampe di debug)
        if not os.path.exists(frame_path) or not os.access(frame_path, os.R_OK):
            return None
        
        # Carica il frame con gestione errori
        try:
            from PIL import Image, ImageFile
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            
            img = Image.open(frame_path)
            img.load()  # Forza il caricamento
            
            # Gestione della cache con LRU (mantieni solo gli ultimi N frame in memoria)
            max_cache_size = 15  # Aumentiamo la cache per prestazioni migliori
            if len(self.frame_cache) > max_cache_size:
                # Rimuovi il frame meno recente
                self.frame_cache.pop(next(iter(self.frame_cache)))
            
            # Memorizza nella cache
            self.frame_cache[frame_path] = img
            return img
        except Exception as e:
            # Prova approccio alternativo in caso di errore
            try:
                img = Image.open(frame_path).convert('RGB')
                img.load()
                self.frame_cache[frame_path] = img
                return img
            except:
                return None
        
    def get_next_frame(self):
        """Restituisce il prossimo frame del video."""
        return self.get_frame()
        
    def get_video_info(self, video_path):
        """Restituisce informazioni su un video utilizzando ffmpeg."""
        if not self.check_ffmpeg():
            return None
            
        try:
            # Debug: mostra il percorso del video che stiamo provando ad analizzare
            print(f"Analisi video: {video_path}")
            
            # Gestione dei percorsi con spazi o caratteri speciali
            # Esegui ffprobe per ottenere informazioni sul video
            cmd = [
                self.ffprobe_path, 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_format", 
                "-show_streams", 
                video_path
            ]
            
            # Debug: mostra il comando che stiamo per eseguire
            print(f"Comando ffprobe: {' '.join(cmd)}")
            
            # Usa shell=True su Windows per gestire meglio i percorsi problematici
            use_shell = os.name == 'nt'
            
            result = subprocess.run(cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                check=False,  # Cambiato da True a False per evitare eccezioni
                                text=True,
                                timeout=10,
                                shell=use_shell)
            
            if result.returncode != 0:
                print(f"Errore ffprobe: {result.stderr}")
                return None
                
            import json
            try:
                info = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"Errore nel parsing JSON: {e}")
                print(f"Output ffprobe: {result.stdout[:100]}...")  # Mostra l'inizio dell'output
                return None
            
            # Estrai informazioni rilevanti
            video_info = {}
            
            # Cerca lo stream video
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_info["width"] = stream.get("width")
                    video_info["height"] = stream.get("height")
                    video_info["codec"] = stream.get("codec_name")
                    
                    # Calcola FPS
                    fps_str = stream.get("r_frame_rate")
                    if fps_str:
                        try:
                            num, den = map(int, fps_str.split('/'))
                            video_info["fps"] = num / den if den else 0
                        except (ValueError, ZeroDivisionError) as e:
                            print(f"Errore nel calcolo FPS: {e}")
                            pass
                            
                    break
                    
            # Durata del video
            format_info = info.get("format", {})
            if "duration" in format_info:
                try:
                    video_info["duration"] = float(format_info["duration"])
                except (ValueError, TypeError) as e:
                    print(f"Errore nel parsing della durata: {e}")
            
            # Debug info - stampa info ottenute
            if not video_info:
                print("Nessuna informazione video trovata nell'output ffprobe")
            else:
                print(f"Info video: {video_info}")
                
            return video_info
        except subprocess.TimeoutExpired:
            print("Timeout nell'esecuzione di ffprobe")
            return None
        except Exception as e:
            print(f"Errore nell'ottenere informazioni video: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def cleanup(self):
        """Pulisce i file temporanei."""
        self.frame_cache.clear()
        if self.current_video and os.path.exists(self.current_video):
            try:
                shutil.rmtree(self.current_video)
                self.current_video = None
            except:
                pass
