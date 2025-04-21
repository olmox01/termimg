#!/usr/bin/env python3
"""
Utility di test per la qualità dell'immagine.
Permette di confrontare diversi algoritmi di rendering e ottimizzazioni di qualità.
"""

import os
import sys
import time
import argparse

# Aggiungi la directory corrente al path per facilitare le importazioni
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import clear_screen, kbhit, getch
from image_processor import ImageProcessor
from terminal_renderer import TerminalRenderer

def main():
    """Funzione principale per testare la qualità dell'immagine."""
    parser = argparse.ArgumentParser(description="Test per la qualità del rendering delle immagini")
    parser.add_argument("image_path", help="Percorso dell'immagine da testare")
    parser.add_argument("-q", "--quality", choices=["low", "medium", "high", "ultra"], default="high",
                      help="Livello di qualità del rendering (default: high)")
    parser.add_argument("-c", "--contrast", type=float, default=1.1,
                      help="Fattore di contrasto (default: 1.1)")
    parser.add_argument("-b", "--brightness", type=float, default=1.0,
                      help="Fattore di luminosità (default: 1.0)")
    parser.add_argument("-m", "--mode", choices=["fit", "stretch", "fill"], default="fit",
                      help="Modalità di adattamento: fit (default), stretch, fill")
    parser.add_argument("-d", "--dithering", action="store_true",
                      help="Abilita dithering per migliorare la qualità percepita")
    parser.add_argument("--compare", action="store_true",
                      help="Mostra confronto tra diverse qualità")
    args = parser.parse_args()
    
    # Verifica esistenza file
    if not os.path.exists(args.image_path):
        print(f"Errore: Il file '{args.image_path}' non esiste.")
        return 1
    
    print(f"Test qualità immagine: {args.image_path}")
    print(f"Qualità: {args.quality}")
    
    # Ottieni dimensioni del terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Inizializza processore e renderer
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Carica l'immagine
    try:
        img = processor.load_image(args.image_path)
        
        # Modalità di confronto
        if args.compare:
            clear_screen()
            print("Preparazione modalità di confronto...")
            display_comparison(img, processor, renderer, term_width, term_height)
            return 0
        
        # Imposta qualità avanzata se richiesta
        if args.quality == "ultra":
            try:
                from high_quality_renderer import setup_high_quality
                setup_high_quality(renderer)
                print("Modalità qualità ultra attivata")
            except ImportError:
                print("Modulo high_quality_renderer non disponibile, uso qualità alta")
                args.quality = "high"
        
        # Applica contrasto e luminosità
        processed_img = processor.process_image(img, args.contrast, args.brightness)
        
        # Applica dithering se richiesto
        if args.dithering:
            print("Applicazione dithering...")
            processed_img = apply_dithering(processed_img, args.quality)
        
        # Ridimensiona per adattarla al terminale
        resized_img, target_width, target_height, padding_x, padding_y = processor.resize_for_terminal(
            processed_img, term_width, term_height, args.mode
        )
        
        # Configura la qualità del rendering
        configure_quality(renderer, args.quality)
        
        # Salva dimensioni nel renderer
        renderer.target_width = target_width
        renderer.target_height = target_height
        renderer.padding_x = padding_x
        renderer.padding_y = padding_y
        
        # Prepara i dati per il rendering
        pixel_data = renderer.prepare_pixel_data(
            processor.layers['base'],
            target_width, target_height, 
            padding_x, padding_y,
            term_width, term_height
        )
        
        # Rendering dell'immagine
        clear_screen()
        print(f"Rendering immagine in qualità {args.quality}...")
        renderer.render_image(pixel_data, term_width, term_height)
        
        # Attendi input utente
        print("Premi un tasto qualsiasi per uscire...")
        while True:
            if kbhit():
                getch()
                break
            time.sleep(0.1)
        
        clear_screen()
        
    except Exception as e:
        print(f"Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

def configure_quality(renderer, quality_level):
    """Configura il renderer per il livello di qualità specificato."""
    if quality_level == "low":
        renderer.use_dithering = False
        renderer.color_depth = 8
        renderer.use_half_blocks = False
    elif quality_level == "medium":
        renderer.use_dithering = False
        renderer.color_depth = 16
        renderer.use_half_blocks = True
    elif quality_level == "high":
        renderer.use_dithering = True
        renderer.color_depth = 256
        renderer.use_half_blocks = True
    elif quality_level == "ultra":
        renderer.use_dithering = True
        renderer.color_depth = 256
        renderer.use_half_blocks = True
        renderer.subpixel_rendering = True
        renderer.color_correction = True

def apply_dithering(image, quality_level):
    """Applica il dithering all'immagine per migliorare la qualità percepita."""
    # Nota: Questa è una funzione segnaposto. L'implementazione reale richiederebbe
    # algoritmi di dithering come Floyd-Steinberg, ordinate dithering, ecc.
    return image  # Per ora ritorna l'immagine inalterata

def display_comparison(img, processor, renderer, term_width, term_height):
    """Mostra un confronto tra diverse qualità di rendering."""
    qualities = ["low", "medium", "high"]
    
    # Determina la dimensione di ciascun pannello
    panel_height = term_height // len(qualities)
    
    clear_screen()
    
    for i, quality in enumerate(qualities):
        # Configura la qualità
        configure_quality(renderer, quality)
        
        # Processa l'immagine
        processed_img = processor.process_image(img, 1.1, 1.0)
        
        # Ridimensiona per adattarla al pannello
        resized_img, target_width, target_height, padding_x, padding_y = processor.resize_for_terminal(
            processed_img, term_width, panel_height - 2, "fit"
        )
        
        # Salva dimensioni nel renderer
        renderer.target_width = target_width
        renderer.target_height = target_height
        renderer.padding_x = padding_x
        renderer.padding_y = padding_y
        
        # Prepara i dati per il rendering
        pixel_data = renderer.prepare_pixel_data(
            processor.layers['base'],
            target_width, target_height, 
            padding_x, padding_y,
            term_width, panel_height - 2
        )
        
        # Posiziona il cursore alla riga corretta
        print(f"\033[{i * panel_height + 1}H", end="")
        
        # Mostra il titolo del pannello
        print(f"Qualità: {quality.upper()} " + "-" * (term_width - len(quality) - 10))
        
        # Rendering dell'immagine nel pannello
        renderer.render_panel(pixel_data, term_width, panel_height - 2, i * panel_height + 2)
    
    # Posiziona il cursore alla fine
    print(f"\033[{term_height}H", end="")
    print("Premi un tasto qualsiasi per uscire...", end="", flush=True)
    
    # Attendi input utente
    while True:
        if kbhit():
            getch()
            break
        time.sleep(0.1)

if __name__ == "__main__":
    sys.exit(main())
