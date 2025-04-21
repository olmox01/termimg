#!/usr/bin/env python3
"""
Utility per testare la riproduzione video in vari scenari.
Questo modulo aiuta a verificare il corretto funzionamento della riproduzione 
in modalità diverse e con varie opzioni di rendering.
"""

import os
import sys
import time
import argparse

# Assicura che la directory corrente sia nel path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Importa i moduli necessari
from core import clear_screen, kbhit, getch
from video_manager import VideoManager
from image_processor import ImageProcessor
from terminal_renderer import TerminalRenderer
from complete_video_renderer import CompleteVideoRenderer
import queue

def test_basic_playback(video_path, fps=24.0, duration=None, loop=False):
    """Test di riproduzione base, senza ottimizzazioni avanzate."""
    print(f"Test riproduzione base: {video_path}")
    print(f"FPS target: {fps}")
    
    # Inizializza componenti
    video_manager = VideoManager()
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Ottieni dimensioni terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Estrai i frame
    print("Estrazione frame...")
    frames_dir = video_manager.extract_frames(
        video_path,
        fps=fps,
        start_time=0,
        duration=duration
    )
    
    if not frames_dir:
        print("Estrazione frame fallita.")
        return
        
    # Carica i frame
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(('.jpg', '.png'))])
    if not frame_files:
        print("Nessun frame estratto.")
        return
        
    print(f"Estratti {len(frame_files)} frame.")
    print(f"Avvio riproduzione a {fps} FPS. Premi 'q' per uscire, 'p' per pausa.")
    time.sleep(1)
    clear_screen()
    
    # Variabili per la riproduzione
    frame_count = 0
    start_time = time.time()
    frame_duration = 1.0 / fps
    is_paused = False
    
    # Loop di riproduzione
    while frame_count < len(frame_files):
        # Controllo input utente
        if kbhit():
            key = getch()
            if key == 'q':
                break
            elif key == 'p':
                is_paused = not is_paused
                if not is_paused:
                    # Quando si riprende, regola il tempo di inizio
                    start_time = time.time() - (frame_count * frame_duration)
                
        if is_paused:
            time.sleep(0.1)
            continue
            
        # Calcola il frame da mostrare
        current_time = time.time()
        elapsed = current_time - start_time
        target_frame = int(elapsed * fps)
        
        if target_frame >= len(frame_files):
            if loop:
                # Ricomincia da capo
                frame_count = 0
                start_time = time.time()
                continue
            else:
                # Fine riproduzione
                break
                
        # Se il frame corrente è diverso dall'ultimo mostrato, aggiorna la visualizzazione
        if target_frame != frame_count:
            frame_count = target_frame
            
            # Carica e processa il frame
            frame_path = os.path.join(frames_dir, frame_files[frame_count])
            img = processor.load_image(frame_path)
            processed_img = processor.process_image(img, 1.1, 1.0)
            
            # Ridimensiona per il terminale
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
            
            # Stato riproduzione
            minutes = int(frame_count / fps / 60)
            seconds = int(frame_count / fps) % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            progress = int((frame_count / len(frame_files)) * 100)
            actual_fps = frame_count / max(0.001, elapsed)
            status_text = f"[{progress}% | {time_str} | {actual_fps:.1f} FPS] {os.path.basename(video_path)}"
            
            # Rendering del frame
            renderer.render_video_frame_mobile(pixel_data, term_width, term_height, status_text)
            
        # Calcola quanto attendere per il prossimo frame
        next_frame_time = start_time + ((frame_count + 1) * frame_duration)
        sleep_time = max(0.0, next_frame_time - time.time())
        
        if sleep_time > 0:
            time.sleep(sleep_time)
            
    # Pulizia
    clear_screen()
    print("Riproduzione completata.")

def test_prerendered_playback(video_path, fps=24.0, duration=None, loop=False):
    """Test di riproduzione con pre-rendering completo."""
    print(f"Test riproduzione con pre-rendering completo: {video_path}")
    print(f"FPS target: {fps}")
    
    # Inizializza componenti
    video_manager = VideoManager()
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Ottieni dimensioni terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Crea renderer completo
    complete_renderer = CompleteVideoRenderer(video_manager, processor, renderer)
    
    # Funzione callback per mostrare progresso
    def progress_callback(progress, status, eta):
        bar_width = 30
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        eta_str = f"ETA: {int(eta)}s" if eta > 0 else ""
        print(f"\r[{bar}] {progress:.1f}% {status} {eta_str}", end="")
    
    # Avvia il pre-rendering
    print("Avvio pre-rendering completo...")
    started = complete_renderer.start_rendering(
        video_path,
        fps=fps,
        term_width=term_width,
        term_height=term_height,
        start_time=0,
        duration=duration,
        callback=progress_callback
    )
    
    if not started:
        print("\nAvvio pre-rendering fallito.")
        return
    
    # Attendi il completamento del pre-rendering
    while not complete_renderer.is_complete() and complete_renderer.is_rendering:
        if kbhit():
            key = getch()
            if key == 'q':
                complete_renderer.cancel_rendering()
                print("\nPre-rendering annullato.")
                return
        time.sleep(0.1)
        
    print("\nPre-rendering completato. Avvio riproduzione...")
    time.sleep(1)
    clear_screen()
    
    # Recupera informazioni dai frame pre-renderizzati
    total_frames = complete_renderer.total_frames
    
    # Variabili per la riproduzione
    frame_count = 0
    start_time = time.time()
    frame_duration = 1.0 / fps
    is_paused = False
    
    # Loop di riproduzione
    while frame_count < total_frames:
        # Controllo input utente
        if kbhit():
            key = getch()
            if key == 'q':
                break
            elif key == 'p':
                is_paused = not is_paused
                if not is_paused:
                    # Quando si riprende, regola il tempo di inizio
                    start_time = time.time() - (frame_count * frame_duration)
                    
        if is_paused:
            # In pausa, mostra l'ultimo frame con stato di pausa
            frame_buffer = complete_renderer.get_frame(frame_count)
            if frame_buffer:
                minutes = int(frame_count / fps / 60)
                seconds = int(frame_count / fps) % 60
                time_str = f"{minutes:02d}:{seconds:02d}"
                progress = int((frame_count / total_frames) * 100)
                status_text = f"[PAUSA {progress}% | {time_str}] {os.path.basename(video_path)}"
                renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
            time.sleep(0.1)
            continue
            
        # Calcola il frame da mostrare
        current_time = time.time()
        elapsed = current_time - start_time
        target_frame = int(elapsed * fps)
        
        if target_frame >= total_frames:
            if loop:
                # Ricomincia da capo
                frame_count = 0
                start_time = time.time()
                continue
            else:
                # Fine riproduzione
                break
                
        # Recupera il frame pre-renderizzato
        frame_buffer = complete_renderer.get_frame(target_frame)
        if frame_buffer:
            # Aggiorna contatore
            frame_count = target_frame
            
            # Stato riproduzione
            minutes = int(frame_count / fps / 60)
            seconds = int(frame_count / fps) % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            progress = int((frame_count / total_frames) * 100)
            actual_fps = frame_count / max(0.001, elapsed)
            status_text = f"[{progress}% | {time_str} | {actual_fps:.1f} FPS] {os.path.basename(video_path)}"
            
            # Rendering del frame
            renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
            
        # Calcola quanto attendere per il prossimo frame
        next_frame_time = start_time + ((frame_count + 1) * frame_duration)
        sleep_time = max(0.0, next_frame_time - time.time())
        
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    # Pulizia
    complete_renderer.cleanup()
    clear_screen()
    print("Riproduzione completata.")

def main():
    """Funzione principale."""
    parser = argparse.ArgumentParser(description="Test di riproduzione video")
    parser.add_argument("video_path", help="Percorso del file video da testare")
    parser.add_argument("--fps", type=float, default=24.0, help="FPS target (default: 24.0)")
    parser.add_argument("--duration", type=float, default=None, help="Durata in secondi (default: tutto il video)")
    parser.add_argument("--loop", action="store_true", help="Riproduzione in loop")
    parser.add_argument("--mode", choices=["basic", "prerender"], default="basic", 
                      help="Modalità di test: basic o prerender (default: basic)")
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"Errore: Il file '{args.video_path}' non esiste.")
        return 1
    
    if args.mode == "prerender":
        test_prerendered_playback(args.video_path, args.fps, args.duration, args.loop)
    else:
        test_basic_playback(args.video_path, args.fps, args.duration, args.loop)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
