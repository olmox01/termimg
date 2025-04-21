#!/usr/bin/env python3
"""
Utility per testare e analizzare le prestazioni di riproduzione video.
Utile per diagnosticare problemi di performance e ottimizzare parametri.
"""
import os
import sys
import time
import argparse
import platform  # Importazione aggiunta per risolvere l'errore
import queue
from datetime import datetime

# Aggiungi la directory corrente al path per facilitare le importazioni
script_dir = os.path.dirname(os.path.abspath(__file__))
if (script_dir not in sys.path):
    sys.path.insert(0, script_dir)

try:
    from performance_analyzer import PerformanceAnalyzer
    from async_video_buffer import AsyncVideoBuffer
    from video_manager import VideoManager
    from terminal_renderer import TerminalRenderer
    from image_processor import ImageProcessor
    from core import clear_screen
except ImportError as e:
    print(f"Errore importazione: {e}")
    print("Assicurati di eseguire questo script dalla directory principale del progetto.")
    sys.exit(1)

def main():
    """Testa le prestazioni di riproduzione video."""
    parser = argparse.ArgumentParser(description="Test delle prestazioni di riproduzione video")
    parser.add_argument("video", help="Percorso del file video da testare")
    parser.add_argument("--fps", type=float, default=24.0, help="FPS target (default: 24.0)")
    parser.add_argument("--duration", type=float, default=10.0, help="Durata del test in secondi (default: 10.0)")
    parser.add_argument("--report", action="store_true", help="Genera report dettagliato")
    parser.add_argument("--benchmark", action="store_true", help="Modalità benchmark")
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"Errore: Il file '{args.video}' non esiste.")
        return 1
    
    # Inizializza gli analizzatori
    perf_analyzer = PerformanceAnalyzer(target_fps=args.fps)
    video_manager = VideoManager()
    
    print("=== Test Prestazioni Riproduzione Video ===")
    print(f"File: {args.video}")
    print(f"FPS target: {args.fps}")
    print(f"Durata test: {args.duration} secondi")
    print(f"Hardware rilevato: {perf_analyzer.hardware_capability}")
    print(f"FPS ottimali stimati: {perf_analyzer.get_optimal_fps()}")
    
    # Ottieni info video
    video_info = video_manager.get_video_info(args.video)
    if video_info:
        print("\nInformazioni video:")
        print(f"  Dimensioni: {video_info.get('width', '?')}x{video_info.get('height', '?')}")
        print(f"  FPS originali: {video_info.get('fps', '?')}")
        print(f"  Durata: {video_info.get('duration', '?')} secondi")
    
    # Test del buffer
    print("\nTest buffer video:")
    buffer = AsyncVideoBuffer(max_buffer_size=20)
    
    # Inizio misurazione
    print("\nAvvio test riproduzione...")
    perf_analyzer.start_monitoring()
    
    # Inizializza renderer e processor per simulare la riproduzione reale
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Avvio estrazione
    start_time = time.time()
    buffer.start_extraction(
        args.video,
        fps=args.fps,
        start_time=0,
        duration=min(args.duration * 1.5, video_info.get('duration', 60))
    )
    
    # Attendi preload
    while not buffer.preload_complete and time.time() - start_time < 10:
        progress = buffer.extraction_progress
        print(f"\rPrecaricamento: {progress}%", end="", flush=True)
        time.sleep(0.1)
    
    print("\nInizio test di riproduzione...")
    clear_screen()
    
    # Variabili di simulazione
    frame_count = 0
    frame_skip_count = 0
    test_start = time.time()
    last_frame_time = test_start
    target_fps = args.fps
    frame_duration = 1.0 / target_fps
    
    # Loop principale - simula la riproduzione effettiva
    while time.time() - test_start < args.duration:
        current_time = time.time()
        elapsed = current_time - test_start
        
        # Calcola quanti frame dovrebbero essere stati mostrati
        target_frame = int(elapsed * target_fps)
        frames_behind = target_frame - frame_count
        
        # Salta frame se necessario
        if frames_behind > 1:
            for _ in range(min(frames_behind - 1, 3)):
                try:
                    buffer.get_frame(block=False, timeout=0.01)
                    frame_skip_count += 1
                except queue.Empty:
                    break
        
        # Prendi il frame corrente
        try:
            frame = buffer.get_frame(block=True, timeout=0.1)
            if frame is not None:
                # Simula elaborazione frame
                processed_img = processor.process_image(frame, 1.0, 1.0)
                # Ridimensiona per adattarla al terminale
                resized_img, _, _, _, _ = processor.resize_for_terminal(
                    processed_img, term_width, term_height, "fit"
                )
                # Incrementa contatori
                frame_count += 1
                perf_analyzer.register_frame()
        except queue.Empty:
            continue
    
    # Test completato
    test_elapsed = time.time() - test_start
    perf_analyzer.stop_monitoring()
    buffer.stop()
    clear_screen()
    
    # Analizza risultati
    status = perf_analyzer.get_system_status()
    actual_fps = frame_count / test_elapsed
    fps_ratio = actual_fps / args.fps
    
    # Risultati
    print("\n=== Risultati Test Prestazioni ===")
    print(f"Durata test: {test_elapsed:.2f} secondi")
    print(f"Frame mostrati: {frame_count}")
    print(f"Frame saltati: {frame_skip_count}")
    print(f"FPS target: {args.fps:.1f}")
    print(f"FPS effettivi: {actual_fps:.1f}")
    print(f"Rapporto FPS: {fps_ratio:.2f}")
    
    # Valutazione
    if fps_ratio >= 0.95:
        print("\n✓ OTTIMO: Prestazioni eccellenti, riproduzione fluida a frame rate completo.")
    elif fps_ratio >= 0.85:
        print("\n✓ BUONO: Riproduzione buona, occasionali cali di performance ma accettabile.")
    elif fps_ratio >= 0.7:
        print("\n⚠ SUFFICIENTE: Prestazioni moderate, alcuni frame saltati ma ancora usabile.")
    else:
        print("\n✗ SCARSO: Prestazioni insufficienti, molti frame saltati.")
    
    # Suggerimenti
    print("\nSuggerimenti:")
    if fps_ratio < 0.85:
        print(f"- Riduci FPS target a {round(actual_fps * 0.9)}")
        print("- Usa '--no-sync' per disabilitare la sincronizzazione precisa")
        print("- Riduci la risoluzione del video originale")
    else:
        print("- Il sistema gestisce questo video senza problemi")
    
    # Report dettagliato se richiesto
    if args.report:
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            # Intestazione
            f.write("=== Report Dettagliato Prestazioni ===\n\n")
            
            # Informazioni sistema
            f.write("Informazioni Sistema:\n")
            f.write(f"  Sistema: {platform.system()} {platform.release()}\n")
            f.write(f"  Macchina: {platform.machine()}\n")
            f.write(f"  Capacità hardware: {perf_analyzer.hardware_capability}\n\n")
            
            # Informazioni video
            f.write("Informazioni Video:\n")
            if video_info:
                f.write(f"  Percorso: {args.video}\n")
                f.write(f"  Dimensioni: {video_info.get('width', '?')}x{video_info.get('height', '?')}\n")
                f.write(f"  FPS originali: {video_info.get('fps', '?')}\n")
                f.write(f"  Durata: {video_info.get('duration', '?')} secondi\n\n")
            
            # Risultati test
            f.write("Risultati Test:\n")
            f.write(f"  Durata test: {test_elapsed:.2f} secondi\n")
            f.write(f"  Frame mostrati: {frame_count}\n")
            f.write(f"  Frame saltati: {frame_skip_count}\n")
            f.write(f"  FPS target: {args.fps:.1f}\n")
            f.write(f"  FPS effettivi: {actual_fps:.1f}\n")
            f.write(f"  Rapporto FPS: {fps_ratio:.2f}\n\n")
            
            # Statistiche sistema
            f.write("Utilizzo Risorse:\n")
            f.write(f"  CPU: {status.get('system_stats', {}).get('cpu', 'N/A')}%\n")
            f.write(f"  Memoria: {status.get('system_stats', {}).get('memory', 'N/A')}%\n\n")
            
            # Suggerimenti
            f.write("Parametri Ottimali:\n")
            if fps_ratio < 0.85:
                f.write(f"  FPS consigliati: {round(actual_fps * 0.9)}\n")
                f.write(f"  Pre-rendering: {'Consigliato' if fps_ratio < 0.7 else 'Opzionale'}\n")
                f.write(f"  Sincronizzazione: {'Disabilitata' if fps_ratio < 0.7 else 'Adattiva'}\n")
            else:
                f.write("  Le impostazioni correnti sono ottimali per questo sistema.\n")
            
        print(f"\nReport dettagliato salvato in: {report_file}")
    
    return 0 if fps_ratio >= 0.7 else 1

if __name__ == "__main__":
    sys.exit(main())
