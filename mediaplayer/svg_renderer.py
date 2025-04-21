#!/usr/bin/env python3
"""
Modulo per il rendering di immagini SVG nel terminale.
Supporta vari backend (CairoSVG, librsvg, Inkscape).
"""

import os
import sys
import tempfile
import subprocess
import io
import base64
from PIL import Image

# Gestione importazioni SVG con fallback
CAIROSVG_AVAILABLE = False
LIBRSVG_AVAILABLE = False
INKSCAPE_AVAILABLE = False

# Prova a importare CairoSVG
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    pass

# Prova a verificare se librsvg è disponibile
try:
    # Tentativo di rilevamento di rsvg-convert
    subprocess.run(["rsvg-convert", "--version"], 
                  stdout=subprocess.PIPE, 
                  stderr=subprocess.PIPE)
    LIBRSVG_AVAILABLE = True
except:
    pass

# Prova a verificare se Inkscape è disponibile
try:
    # Tentativo di rilevamento di Inkscape
    subprocess.run(["inkscape", "--version"], 
                  stdout=subprocess.PIPE, 
                  stderr=subprocess.PIPE)
    INKSCAPE_AVAILABLE = True
except:
    pass

class SVGRenderer:
    """Classe per il rendering di file SVG utilizzando vari backend."""
    
    def __init__(self):
        """Inizializza il renderer SVG con vari backend."""
        self.backend = self._detect_best_backend()
        print(f"Backend SVG selezionato: {self.backend}")
    
    def _detect_best_backend(self):
        """Determina il backend migliore disponibile."""
        if CAIROSVG_AVAILABLE:
            return "cairosvg"
        elif LIBRSVG_AVAILABLE:
            return "librsvg"
        elif INKSCAPE_AVAILABLE:
            return "inkscape"
        else:
            return "none"
    
    def render_svg(self, svg_path, term_width, term_height, processor, renderer):
        """
        Renderizza un file SVG utilizzando il backend disponibile.
        
        Args:
            svg_path: Percorso del file SVG
            term_width: Larghezza del terminale
            term_height: Altezza del terminale
            processor: Oggetto ImageProcessor
            renderer: Oggetto TerminalRenderer
            
        Returns:
            bool: True se il rendering ha avuto successo
        """
        if self.backend == "none":
            print("Errore: nessun backend SVG disponibile.")
            print("Installa una di queste librerie:")
            print("  - cairosvg (pip install cairosvg)")
            print("  - librsvg (pacchetto del sistema operativo)")
            print("  - inkscape (pacchetto del sistema operativo)")
            return False
        
        # Carica e converte l'SVG in PNG
        png_data = self._convert_svg_to_png(svg_path)
        if not png_data:
            return False
            
        try:
            # Carica l'immagine convertita
            img = Image.open(io.BytesIO(png_data))
            
            # Processa l'immagine
            processed_img = processor.process_image(img, 1.1, 1.0)
            
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
            
            # Rendering dell'immagine
            renderer.render_image(pixel_data, term_width, term_height)
            
            return True
            
        except Exception as e:
            print(f"Errore durante il rendering dell'SVG: {e}")
            return False
    
    def _convert_svg_to_png(self, svg_path):
        """Converte un file SVG in PNG utilizzando il backend selezionato."""
        try:
            if self.backend == "cairosvg":
                if not CAIROSVG_AVAILABLE:
                    raise ImportError("CairoSVG non disponibile")
                    
                # Usa CairoSVG per la conversione diretta
                with open(svg_path, 'rb') as f:
                    svg_data = f.read()
                png_data = cairosvg.svg2png(bytestring=svg_data)
                return png_data
                
            elif self.backend == "librsvg":
                # Usa rsvg-convert
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    output_path = temp_file.name
                
                cmd = ["rsvg-convert", "-o", output_path, svg_path]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if result.returncode != 0:
                    print(f"Errore in librsvg: {result.stderr.decode('utf-8', errors='ignore')}")
                    return None
                
                # Leggi il file PNG generato
                with open(output_path, 'rb') as f:
                    png_data = f.read()
                    
                # Pulisci
                os.unlink(output_path)
                return png_data
                
            elif self.backend == "inkscape":
                # Usa Inkscape
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    output_path = temp_file.name
                
                cmd = ["inkscape", "--export-filename", output_path, svg_path]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if result.returncode != 0:
                    print(f"Errore in Inkscape: {result.stderr.decode('utf-8', errors='ignore')}")
                    return None
                
                # Leggi il file PNG generato
                with open(output_path, 'rb') as f:
                    png_data = f.read()
                    
                # Pulisci
                os.unlink(output_path)
                return png_data
        
        except Exception as e:
            print(f"Errore nella conversione SVG: {e}")
            return None
