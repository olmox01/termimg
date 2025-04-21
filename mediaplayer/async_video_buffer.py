#!/usr/bin/env python3
"""
Modulo per il buffering video asincrono, ottimizzato per sistemi MUSL.
Usa asyncio e subprocess per estrarre e processare i frame video senza multiprocessing.
"""
import os
import platform
import sys
import time
import threading
import queue
import subprocess
import tempfile
import shutil
import glob  # Aggiunto import mancante per glob.glob
from PIL import Image

# Importa la funzione per ottenere i percorsi di ffmpeg
try:
    from core import get_ffmpeg_paths
except ImportError:
    # Fallback se l'importazione fallisce
    def get_ffmpeg_paths():
        return "ffmpeg", "ffprobe"

class AsyncVideoBuffer:
    """Gestisce il buffering video in modo asincrono senza multiprocessing."""
    
    def __init__(self, max_buffer_size=10, preload_frames=10):
        """Inizializza il buffer video."""
        self.buffer = queue.Queue(maxsize=max_buffer_size)
        self.rendered_buffer = queue.Queue(maxsize=max_buffer_size) # Buffer per frame già renderizzati
        self.is_extracting = False
        self.extraction_complete = False
        self.current_frame = 0
        self.total_frames = 0
        self.extraction_progress = 0
        self.fps = 24.0
        self.stream_process = None
        self.extraction_thread = None
        self.preload_frames = preload_frames  # Numero di frame da precaricare prima di iniziare la riproduzione
        self.preload_complete = False  # Flag per indicare se il precaricamento è completo
        self.ffmpeg_path, self.ffprobe_path = get_ffmpeg_paths()
        self.video_info = {}  # Per memorizzare informazioni sul video
        self.skipped_frames = 0  # Contatore di frame saltati
        self.rendering_thread = None
        self.is_rendering = False
        self.render_complete = False
        self.smoothness_factor = 1.0  # Fattore di fluidità (1.0 = normale)
    
    def start_extraction(self, video_path, fps=24.0, width=None, height=None, 
                         start_time=0, duration=None, callback=None):
        """Avvia il processo di estrazione frame in un thread separato."""
        if self.is_extracting:
            return False
        
        # Verificare che il file esista
        if not os.path.isfile(video_path):
            print(f"Errore: file '{video_path}' non trovato.")
            return False
        
        # Verifica che ffmpeg sia disponibile
        try:
            subprocess.run([self.ffmpeg_path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print(f"Errore: ffmpeg non trovato. Assicurati che sia installato e nel PATH.")
            return False
        
        # Resetta i contatori e i flag
        self.is_extracting = True
        self.extraction_complete = False
        self.preload_complete = False
        self.fps = fps
        self.current_frame = 0
        self.total_frames = 0
        self.extraction_progress = 0
        
        # Svuota il buffer se non vuoto
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break
        
        # Ottieni informazioni sul video come durata e frame rate
        self.video_info = self._get_video_info(video_path)
        
        # Imposta FPS nativi se non specificati diversamente
        if fps is None and self.video_info and 'fps' in self.video_info:
            self.fps = self.video_info['fps']
        else:
            self.fps = fps or 24.0
        
        # Determina se il sistema è a basse prestazioni
        is_low_performance = self._detect_low_performance_system()
        if is_low_performance:
            print("Sistema a basse prestazioni rilevato. Ottimizzazione buffer avviata.")
        
        # Avvia il thread di estrazione
        self.extraction_thread = threading.Thread(
            target=self._extract_frames_thread,
            args=(video_path, fps, width, height, start_time, duration, callback),
            daemon=True
        )
        self.extraction_thread.start()
        
        # Attendi che almeno alcuni frame siano caricati per evitare di iniziare con un buffer vuoto
        preload_timeout = 10  # Timeout in secondi
        start_time = time.time()
        preload_count = 0
        
        print(f"Precaricamento di {self.preload_frames} frame...")
        
        while preload_count < self.preload_frames and time.time() - start_time < preload_timeout:
            if not self.is_extracting:
                break
                
            preload_count = self.buffer.qsize()
            
            if preload_count >= self.preload_frames:
                self.preload_complete = True
                break
                
            time.sleep(0.1)
        
        # Se il timeout è scaduto ma abbiamo almeno un frame, permettiamo comunque di continuare
        if not self.preload_complete and self.buffer.qsize() > 0:
            print(f"Precaricamento parziale completato: {self.buffer.qsize()} frame pronti")
            self.preload_complete = True
        
        return self.preload_complete or self.buffer.qsize() > 0

    def _extract_frames_thread(self, video_path, fps, width, height, start_time, duration, callback):
        """Thread worker per l'estrazione dei frame."""
        try:
            # Debug info
            print(f"Inizio estrazione con fps={fps}, start={start_time}, duration={duration}")
            
            # Prova prima il metodo diretto con ffmpeg
            success = self._extract_with_ffmpeg(video_path, fps, width, height, start_time, duration, callback)
            
            # Se ffmpeg fallisce, prova l'approccio con file temporanei
            if not success:
                print("Estrazione diretta fallita, provo con metodo alternativo...")
                success = self._extract_with_temp_files(video_path, fps, start_time, duration, callback)
            
            # Segnala completamento
            self.extraction_complete = True
            if callback:
                callback(100)
                
        except Exception as e:
            print(f"Errore nell'estrazione: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_extracting = False
            if self.stream_process:
                self.stream_process.terminate()
                self.stream_process = None
    
    def _extract_with_ffmpeg(self, video_path, fps, width, height, start_time, duration, callback):
        """Estrazione diretta con ffmpeg pipe."""
        try:
            # Debug info
            print(f"Inizio estrazione con fps={fps}, start={start_time}, duration={duration}")
            
            # Costruisci il comando ffmpeg
            cmd = [self.ffmpeg_path, "-i", video_path]
            
            # Opzioni di inizio e durata
            if start_time > 0:
                cmd.extend(["-ss", str(start_time)])
            if duration:
                cmd.extend(["-t", str(duration)])
                
            # Ridimensionamento se specificato
            vf_options = []
            if width and height:
                vf_options.append(f"scale={width}:{height}")
                
            # FPS target - usa -vsync cfr per sincronizzazione più precisa
            vf_options.append(f"fps={fps}")
            
            if vf_options:
                cmd.extend(["-vf", ",".join(vf_options)])
                
            # Aggiungi l'opzione vsync cfr per mantenere un frame rate costante
            cmd.extend(["-vsync", "cfr"])
                
            # Formato di output
            cmd.extend([
                "-f", "image2pipe",
                "-pix_fmt", "rgb24",
                "-vcodec", "rawvideo",
                "-"
            ])
            
            # Ottieni informazioni sul video per calcolare la dimensione del frame
            video_info = self._get_video_info(video_path)
            frame_width = width or video_info.get("width", 0)
            frame_height = height or video_info.get("height", 0)
            
            if not frame_width or not frame_height:
                raise ValueError("Impossibile determinare le dimensioni del video")
                
            # Calcola la dimensione del frame in byte
            frame_size = frame_width * frame_height * 3  # RGB = 3 byte per pixel
            
            if video_info and "duration" in video_info:
                total_duration = float(video_info["duration"])
                # Stima il numero totale di frame (approssimato)
                if duration:
                    self.total_frames = int(min(duration, total_duration - start_time) * fps)
                else:
                    self.total_frames = int((total_duration - start_time) * fps)
            
            # Avvia il processo ffmpeg
            print(f"Esecuzione comando ffmpeg: {' '.join(cmd)}")
            self.stream_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10*frame_size
            )
            
            # Estrai frame finché ci sono dati
            frame_count = 0
            start_time = time.time()
            
            while self.is_extracting:
                # Leggi un frame completo
                raw_frame = self.stream_process.stdout.read(frame_size)
                if len(raw_frame) < frame_size:
                    break  # Fine del video
                
                try:
                    # Converti i dati grezzi in un oggetto Image
                    frame = Image.frombytes('RGB', (frame_width, frame_height), raw_frame)
                    
                    # Aggiungi al buffer con timeout minimo
                    try:
                        self.buffer.put(frame, timeout=0.1)
                        frame_count += 1
                        
                        # Aggiorna il progresso
                        if self.total_frames > 0:
                            self.extraction_progress = min(100, int((frame_count / self.total_frames) * 100))
                            if callback:
                                callback(self.extraction_progress)
                    except queue.Full:
                        # Se il buffer è pieno, salta il frame
                        continue
                        
                except Exception as e:
                    print(f"Errore nel processare il frame: {e}")
                    continue
            
            # Segnala completamento
            self.extraction_complete = True
            if callback:
                callback(100)
                
            print(f"Estrazione completata: {frame_count} frame in {time.time() - start_time:.2f}s")
        
        except Exception as e:
            print(f"Errore nell'estrazione: {e}")
        finally:
            self.is_extracting = False
            if self.stream_process:
                self.stream_process.terminate()
                self.stream_process = None
        return True
    
    def _extract_with_temp_files(self, video_path, fps, start_time, duration, callback):
        """Estrazione usando file temporanei."""
        try:
            # Crea directory temporanea per i frame
            from core import CACHE_DIR
            temp_dir = os.path.join(CACHE_DIR, "video_frames", f"temp_{int(time.time())}")
            os.makedirs(temp_dir, exist_ok=True)
            
            print(f"Estrazione frame in: {temp_dir}")
            
            # Definisci il comando ffmpeg
            cmd = [self.ffmpeg_path, "-y", "-i", video_path]
            
            # Aggiungi opzioni di inizio e durata
            if start_time > 0:
                cmd.extend(["-ss", str(start_time)])
            if duration:
                cmd.extend(["-t", str(duration)])
            
            # Filtro fps
            cmd.extend(["-vf", f"fps={fps}"])
            
            # Imposta il pattern di output
            cmd.extend(["-q:v", "2", f"{temp_dir}/frame_%04d.jpg"])
            
            # Esegui ffmpeg
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Thread per leggere l'output di errore e monitorare il progresso
            def read_stderr():
                for line in process.stderr:
                    if "frame=" in line and "fps=" in line:
                        try:
                            # Parse del numero di frame estratti
                            frame_str = line.split("frame=")[1].split()[0].strip()
                            frame_num = int(frame_str)
                            
                            # Aggiorna il progresso
                            self.extraction_progress = min(99, frame_num // 5)
                            if callback:
                                callback(self.extraction_progress)
                        except:
                            pass
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Attendi il completamento dell'estrazione
            process.wait()
            
            # Verifica se l'estrazione è andata a buon fine
            if process.returncode != 0:
                print(f"Errore durante l'estrazione dei frame: {process.returncode}")
                return False
            
            # Elenca i frame estratti
            frame_files = sorted(glob.glob(f"{temp_dir}/frame_*.jpg"))
            if not frame_files:
                print("Nessun frame estratto!")
                return False
            
            print(f"Estratti {len(frame_files)} frame")
            self.total_frames = len(frame_files)
            
            # Carica gradualmente i frame nel buffer
            frame_count = 0
            for frame_path in frame_files:
                try:
                    # Carica l'immagine
                    from PIL import Image
                    img = Image.open(frame_path)
                    
                    # Aggiungi al buffer
                    try:
                        self.buffer.put(img, timeout=0.1)
                        frame_count += 1
                        
                        # Aggiorna il progresso
                        if frame_count % 10 == 0 or frame_count == self.total_frames:
                            progress = min(100, int((frame_count / self.total_frames) * 100))
                            self.extraction_progress = progress
                            if callback:
                                callback(progress)
                                
                            # Segna il precaricamento come completo dopo alcuni frame
                            if not self.preload_complete and frame_count >= self.preload_frames:
                                self.preload_complete = True
                                
                    except queue.Full:
                        # Se il buffer è pieno, attendi che si svuoti
                        time.sleep(0.1)
                        continue
                        
                except Exception as e:
                    print(f"Errore nel processare il frame {frame_path}: {e}")
            
            # Segnala completamento
            self.extraction_complete = True
            self.extraction_progress = 100
            if callback:
                callback(100)
            
            return True
            
        except Exception as e:
            print(f"Errore nel metodo di estrazione alternativo: {e}")
            return False

    def get_frame(self, block=True, timeout=None):
        """Ottiene il prossimo frame dal buffer."""
        try:
            return self.buffer.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
    
    def skip_frames(self, count=1):
        """Salta un numero specifico di frame nel buffer."""
        skipped = 0
        for _ in range(count):
            try:
                self.buffer.get(block=False)
                self.skipped_frames += 1
                skipped += 1
            except queue.Empty:
                break
        return skipped
    
    def get_skipped_frames_count(self):
        """Restituisce il numero di frame saltati finora."""
        return self.skipped_frames
    
    def _get_video_info(self, video_path):
        """Ottiene informazioni sul video tramite ffprobe."""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "error",
                "-show_entries", "stream=width,height,r_frame_rate,duration",
                "-select_streams", "v:0",
                "-of", "csv=s=,:p=0",
                video_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"Errore ffprobe: {result.stderr}")
                return {}
            
            # Parse output CSV: width,height,r_frame_rate,duration
            output = result.stdout.strip().split(',')
            
            if len(output) >= 4:
                try:
                    width = int(output[0])
                    height = int(output[1])
                    
                    # Parse r_frame_rate (formato "num/den")
                    frame_rate_parts = output[2].split('/')
                    if len(frame_rate_parts) == 2:
                        fps = float(frame_rate_parts[0]) / float(frame_rate_parts[1])
                    else:
                        fps = float(output[2])
                    
                    duration = float(output[3])
                    
                    # Calcola il numero totale di frame
                    total_frames = int(duration * fps)
                    
                    return {
                        'width': width,
                        'height': height,
                        'fps': fps,
                        'duration': duration,
                        'total_frames': total_frames
                    }
                except Exception as e:
                    print(f"Errore nel parsing delle informazioni video: {e}")
            
            return {}
        except Exception as e:
            print(f"Errore nell'ottenere informazioni sul video: {e}")
            return {}
    
    def get_video_info(self):
        """Restituisce le informazioni del video attualmente in riproduzione."""
        return self.video_info

    def stop(self):
        """Interrompe il processo di estrazione."""
        self.is_extracting = False
        if self.stream_process:
            try:
                self.stream_process.terminate()
            except:
                pass
        
        # Svuota il buffer
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break

    def _detect_low_performance_system(self):
        """Rileva se il sistema è a basse prestazioni."""
        # Controlla se siamo su musl/Alpine o iSH
        is_musl = False
        is_ish = False
        is_arm = False
        
        # Verifica musl (Alpine Linux)
        try:
            ldd_output = subprocess.check_output(['ldd', '--version'], stderr=subprocess.STDOUT, text=True, errors='ignore')
            is_musl = 'musl' in ldd_output.lower()
        except:
            # Se il comando fallisce, controlla l'esistenza del file di release di Alpine
            try:
                is_musl = os.path.exists('/etc/alpine-release')
            except:
                pass
            
        # Verifica iSH
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                is_ish = 'ish' in version_info
        except:
            pass
            
        # Verifica ARM (dispositivi mobili)
        try:
            machine = platform.machine().lower()
            is_arm = 'arm' in machine or 'aarch' in machine
        except:
            pass
            
        # Carica informazioni di piattaforma se disponibili
        try:
            from platform_detector import detect_platform
            platform_info = detect_platform()
            return platform_info.get('is_limited_terminal', False) or is_musl or is_ish
        except ImportError:
            # Usa i rilevamenti fatti sopra
            return is_musl or is_ish or (is_arm and os.environ.get('ANDROID_DATA', '') != '')
    
    def start_pre_rendering(self, processor, renderer, term_width, term_height):
        """Avvia il pre-rendering dei frame in un thread separato."""
        if self.rendering_thread is not None and self.rendering_thread.is_alive():
            return False  # Thread già attivo
        
        self.is_rendering = True
        self.render_complete = False
        
        self.rendering_thread = threading.Thread(
            target=self._pre_render_frames,
            args=(processor, renderer, term_width, term_height),
            daemon=True
        )
        self.rendering_thread.start()
        return True
        
    def _pre_render_frames(self, processor, renderer, term_width, term_height):
        """Thread worker per il pre-rendering dei frame."""
        rendered_count = 0
        try:
            while self.is_rendering and (not self.extraction_complete or not self.buffer.empty()):
                try:
                    # Prendi un frame dal buffer principale
                    frame = self.buffer.get(block=True, timeout=0.5)
                    
                    if frame:
                        # Processa il frame
                        processed_img = processor.process_image(frame, 1.0, 1.0)
                        
                        # Ridimensiona per adattarla al terminale
                        resized_img, target_width, target_height, padding_x, padding_y = processor.resize_for_terminal(
                            processed_img, term_width, term_height, "fit"
                        )
                        
                        # Prepara i dati per il rendering
                        pixel_data = renderer.prepare_pixel_data(
                            processor.layers['base'],
                            target_width, target_height,
                            padding_x, padding_y,
                            term_width, term_height
                        )
                        
                        # Metti sia i dati renderizzati che il frame originale nel buffer
                        # (il frame originale serve per eventuali processamenti ulteriori)
                        self.rendered_buffer.put((pixel_data, frame), block=False)
                        rendered_count += 1
                        
                        # Reinserisci il frame nel buffer principale per la riproduzione normale
                        self.buffer.put(frame, block=False)
                        
                except queue.Empty:
                    # Se non ci sono più frame da elaborare ma l'estrazione è ancora in corso,
                    # attendi un po'
                    if not self.extraction_complete:
                        time.sleep(0.1)
                    else:
                        break
                    
                except queue.Full:
                    # Se il buffer dei frame renderizzati è pieno, attendi che si svuoti
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Errore nel thread di pre-rendering: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_rendering = False
            self.render_complete = True
            print(f"Pre-rendering completato: {rendered_count} frames")
            
    def get_rendered_frame(self, block=False):
        """
        Ottiene il prossimo frame pre-renderizzato.
        
        Args:
            block: Se True, blocca finché un frame è disponibile
            
        Returns:
            Tuple (pixel_data, raw_frame) o None se non disponibile
        """
        try:
            return self.rendered_buffer.get(block=block)
        except queue.Empty:
            return None
            
    def skip_rendered_frames(self, count=1):
        """
        Salta un numero specifico di frame pre-renderizzati.
        
        Args:
            count: Numero di frame da saltare
            
        Returns:
            int: Numero effettivo di frame saltati
        """
        skipped = 0
        for _ in range(count):
            try:
                self.rendered_buffer.get(block=False)
                skipped += 1
            except queue.Empty:
                break
        return skipped
        
    def analyze_playback_timing(self, target_fps, actual_fps):
        """
        Analizza le prestazioni di riproduzione e calcola un fattore di fluidità ottimale.
        
        Args:
            target_fps: FPS obiettivo
            actual_fps: FPS effettivamente misurati
            
        Returns:
            float: Fattore di fluidità consigliato (1.0 = normale)
        """
        if actual_fps <= 0:
            return 1.0  # Valore predefinito
        
        # Calcola il rapporto tra FPS target e reali
        fps_ratio = actual_fps / target_fps
        
        # Se siamo oltre l'85% del target, va bene così
        if fps_ratio > 0.85:
            return 1.0
        
        # Se siamo tra 60-85%, applica un leggero rallentamento
        elif fps_ratio > 0.6:
            return 0.9
            
        # Sistema sovraccaricato, rallenta notevolmente
        else:
            return 0.7
