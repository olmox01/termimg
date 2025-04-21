#!/usr/bin/env python3
"""
Utility per analizzare e debuggare problemi con i file video.
Esegue vari test per determinare se un file video può essere riprodotto correttamente.
"""

import os
import sys
import subprocess
import json
import time
import platform
from PIL import Image

def check_ffmpeg():
    """Verifica se ffmpeg è installato e funzionante."""
    print("=== Test ffmpeg ===")
    
    try:
        # Importa funzione per ottenere i percorsi di ffmpeg
        try:
            # Aggiungiamo il percorso attuale al sys.path per facilitare l'importazione
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            
            from core import get_ffmpeg_paths
            ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
            print(f"Percorsi rilevati: ffmpeg={ffmpeg_path}, ffprobe={ffprobe_path}")
        except ImportError as e:
            print(f"Errore importazione: {e}")
            # Tenta di trovare ffmpeg nella directory utente
            user_dir = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
            if os.path.exists(os.path.join(user_dir, "ffmpeg.exe")):
                ffmpeg_path = os.path.join(user_dir, "ffmpeg.exe")
                ffprobe_path = os.path.join(user_dir, "ffprobe.exe")
                print(f"Trovato in directory utente: {ffmpeg_path}")
            else:
                ffmpeg_path, ffprobe_path = "ffmpeg", "ffprobe"
            
        result = subprocess.run([ffmpeg_path, "-version"], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode == 0:
            print("✓ ffmpeg installato")
            print(f"Versione: {result.stdout.splitlines()[0]}")
            print(f"Percorso: {ffmpeg_path}")
            return True
        else:
            print(f"✗ ffmpeg non disponibile o non funzionante (codice: {result.returncode})")
            print(f"Errore: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg non trovato")
        return False
    except Exception as e:
        print(f"✗ Errore durante la verifica di ffmpeg: {e}")
        return False

def analyze_video(video_path):
    """Analizza un file video e restituisce le sue proprietà."""
    print(f"\n=== Analisi del file: {video_path} ===")
    
    # Verifica se il file esiste
    if not os.path.exists(video_path):
        print(f"✗ File non trovato: {video_path}")
        return None
    
    # Verifica che sia un file e non una directory
    if not os.path.isfile(video_path):
        print(f"✗ Non è un file: {video_path}")
        return None
    
    # Verifica dimensione e permessi
    file_size = os.path.getsize(video_path)
    can_read = os.access(video_path, os.R_OK)
    
    print(f"Dimensione: {file_size / (1024*1024):.2f} MB")
    print(f"Permessi lettura: {'Sì' if can_read else 'No'}")
    
    if not can_read:
        print("✗ Impossibile leggere il file! Controlla i permessi.")
        return None
    
    if file_size == 0:
        print("✗ File vuoto!")
        return None
    
    # Usa ffprobe per ottenere informazioni dettagliate
    try:
        # Importa funzione per ottenere i percorsi di ffmpeg
        try:
            from core import get_ffmpeg_paths
            ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
        except ImportError:
            ffmpeg_path, ffprobe_path = "ffmpeg", "ffprobe"
            
        cmd = [
            ffprobe_path, 
            "-v", "quiet", 
            "-print_format", "json", 
            "-show_format", 
            "-show_streams", 
            video_path
        ]
        
        print(f"Esecuzione: {' '.join(cmd)}")
        
        # Su Windows, usa shell=True per gestire meglio i percorsi con spazi
        use_shell = os.name == 'nt'
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            shell=use_shell
        )
        
        if result.returncode != 0:
            print(f"✗ Errore ffprobe: {result.stderr}")
            return None
        
        info = json.loads(result.stdout)
        
        # Estrai informazioni rilevanti
        video_info = {}
        
        # Trova il primo stream video
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                video_info["codec"] = stream.get("codec_name")
                video_info["width"] = stream.get("width")
                video_info["height"] = stream.get("height")
                video_info["bit_depth"] = stream.get("bits_per_raw_sample")
                video_info["pixel_format"] = stream.get("pix_fmt")
                
                # Calcola FPS
                fps_str = stream.get("r_frame_rate")
                if fps_str:
                    try:
                        num, den = map(int, fps_str.split('/'))
                        video_info["fps"] = num / den if den else 0
                    except:
                        video_info["fps"] = "sconosciuto"
                        
                break
                
        # Informazioni sul formato
        format_info = info.get("format", {})
        video_info["format"] = format_info.get("format_name")
        
        if "duration" in format_info:
            try:
                duration = float(format_info["duration"])
                video_info["duration"] = duration
                
                # Stima numero di frame
                if "fps" in video_info and isinstance(video_info["fps"], (int, float)):
                    video_info["estimated_frames"] = int(duration * video_info["fps"])
            except:
                video_info["duration"] = "sconosciuta"
        
        # Mostra le informazioni
        print("\nInformazioni video:")
        print(f"  Formato: {video_info.get('format', 'sconosciuto')}")
        print(f"  Codec: {video_info.get('codec', 'sconosciuto')}")
        print(f"  Risoluzione: {video_info.get('width', '?')}x{video_info.get('height', '?')}")
        print(f"  FPS: {video_info.get('fps', 'sconosciuto')}")
        print(f"  Durata: {video_info.get('duration', 'sconosciuta'):.2f} secondi" 
              if isinstance(video_info.get('duration'), (int, float)) else f"Durata: {video_info.get('duration', 'sconosciuta')}")
        print(f"  Frames stimati: {video_info.get('estimated_frames', 'sconosciuto')}")
        print(f"  Profondità bit: {video_info.get('bit_depth', 'sconosciuta')}")
        print(f"  Formato pixel: {video_info.get('pixel_format', 'sconosciuto')}")
        
        return video_info
        
    except Exception as e:
        print(f"✗ Errore nell'analisi del video: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_frame_extraction(video_path, output_dir=None, num_frames=10):
    """Testa l'estrazione di alcuni frame dal video."""
    print("\n=== Test Estrazione Frame ===")
    
    if output_dir is None:
        # Crea directory temporanea
        import tempfile
        output_dir = tempfile.mkdtemp(prefix="video_test_")
    else:
        os.makedirs(output_dir, exist_ok=True)
        
    print(f"Directory output: {output_dir}")
    
    try:
        # Importa funzione per ottenere i percorsi di ffmpeg
        try:
            from core import get_ffmpeg_paths
            ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
        except ImportError:
            ffmpeg_path, ffprobe_path = "ffmpeg", "ffprobe"
            
        # Estrai i primi frame con ffmpeg
        cmd = [
            ffmpeg_path,
            "-i", video_path,
            "-vframes", str(num_frames),
            "-q:v", "1",  # Qualità immagine
            f"{output_dir}/frame_%04d.jpg"
        ]
        
        print(f"Esecuzione: {' '.join(cmd)}")
        
        # Su Windows, usa shell=True per gestire meglio i percorsi con spazi
        use_shell = os.name == 'nt'
        
        start_time = time.time()
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            shell=use_shell
        )
        extract_time = time.time() - start_time
        
        if result.returncode != 0:
            print(f"✗ Errore nell'estrazione dei frame: {result.stderr.decode()}")
            return False
        
        # Verifica i frame estratti
        frames = [f for f in os.listdir(output_dir) if f.startswith("frame_")]
        frames.sort()
        
        if not frames:
            print("✗ Nessun frame estratto!")
            return False
            
        print(f"✓ Estrazione completata in {extract_time:.2f} secondi")
        print(f"✓ Frame estratti: {len(frames)}")
        
        # Controlla il primo frame
        if frames:
            first_frame = os.path.join(output_dir, frames[0])
            try:
                img = Image.open(first_frame)
                print(f"✓ Primo frame caricato correttamente: {img.format}, {img.size[0]}x{img.size[1]}")
                return True
            except Exception as e:
                print(f"✗ Errore nel caricamento del primo frame: {e}")
                return False
        
        return True
    
    except Exception as e:
        print(f"✗ Errore durante il test di estrazione: {e}")
        return False

def main():
    # Verifica parametri
    if len(sys.argv) < 2:
        print("Uso: debug_video.py <file_video> [directory_output_frame]")
        sys.exit(1)
        
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Mostra informazioni di sistema
    print("=== Informazioni Sistema ===")
    print(f"Sistema operativo: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    
    # Verifica ffmpeg
    if not check_ffmpeg():
        print("\nffmpeg non disponibile. Impossibile analizzare il video.")
        sys.exit(1)
    
    # Analizza il video
    video_info = analyze_video(video_path)
    if not video_info:
        print("\nAnalisi del video fallita.")
        sys.exit(1)
        
    # Testa estrazione frame
    if not test_frame_extraction(video_path, output_dir, num_frames=5):
        print("\nEstrazione frame fallita.")
        sys.exit(1)
    
    print("\n✓ Video analizzato con successo!")
    print("Il video sembra essere compatibile con termimg.")

if __name__ == "__main__":
    main()
