#!/usr/bin/env python3
"""
Test semplice per la visualizzazione di file SVG.
Questo script carica e visualizza un SVG utilizzando solo le componenti essenziali.
"""

import os
import sys
import time

# Aggiungi la directory corrente al path per facilitare le importazioni
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import clear_screen, kbhit, getch
from image_processor import ImageProcessor
from terminal_renderer import TerminalRenderer

def main():
    # Controlla i parametri
    if len(sys.argv) < 2:
        print("Uso: python test_svg.py <percorso_svg>")
        return
        
    svg_path = sys.argv[1]
    if not os.path.exists(svg_path):
        print(f"Errore: file {svg_path} non trovato")
        return
    
    print(f"Caricamento SVG: {svg_path}")
    
    try:
        # Importa il renderer SVG
        try:
            from svg_renderer import SVGRenderer
            svg_renderer = SVGRenderer()
        except ImportError:
            print("Errore: Modulo SVGRenderer non trovato. Impossibile visualizzare SVG.")
            return
        
        # Ottieni le dimensioni del terminale
        term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
        
        # Inizializza processore e renderer
        processor = ImageProcessor()
        renderer = TerminalRenderer()
        
        # Renderizza SVG
        if svg_renderer.render_svg(svg_path, term_width, term_height, processor, renderer):
            # Attendi input
            print("SVG visualizzato correttamente. Premi un tasto per uscire.")
            while True:
                if kbhit():
                    key = getch()
                    if key:
                        break
                time.sleep(0.1)
                
            clear_screen()
        else:
            print("Impossibile renderizzare il file SVG.")
            
    except Exception as e:
        print(f"Errore: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
