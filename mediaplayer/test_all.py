#!/usr/bin/env python3
"""
Test completo per verificare tutte le funzionalità di TermImg.
Include test per SVG, buffering asincrono video e input handler.
"""

import os
import sys
import time
import argparse

def test_dependencies():
    """Verifica la presenza di tutte le dipendenze."""
    print("=== Test Dipendenze ===")
    
    # Verifica PIL
    try:
        from PIL import Image
        print("✓ PIL/Pillow installato")
    except ImportError:
        print("✗ PIL/Pillow non trovato")
    
    # Verifica ffmpeg
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✓ ffmpeg installato")
        else:
            print("✗ ffmpeg non disponibile")
    except:
        print("✗ ffmpeg non disponibile")
    
    # Verifica moduli interni
    modules = [
        "core", "image_processor", "terminal_renderer", "video_manager", 
        "async_video_buffer", "input_handler", "svg_renderer", "platform_detector"
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ Modulo {module} trovato")
        except ImportError:
            print(f"✗ Modulo {module} non trovato")
    
    print()

def test_image():
    """Test funzionalità immagini."""
    print("=== Test Immagini ===")
    
    # Verifica che esista un'immagine test
    test_image = find_test_file([".jpg", ".png", ".gif"])
    
    if not test_image:
        print("✗ Nessuna immagine di test trovata")
        return
    
    print(f"Trovata immagine test: {test_image}")
    
    # Carica e visualizza con subprocess
    try:
        import subprocess
        cmd = [sys.executable, "termimg.py", test_image, "-i"]
        print(f"Esecuzione: {' '.join(cmd)}")
        subprocess.run(cmd)
        print("✓ Test immagine completato")
    except Exception as e:
        print(f"✗ Errore nel test immagine: {e}")
    
    print()

def test_svg():
    """Test funzionalità SVG."""
    print("=== Test SVG ===")
    
    # Verifica che esista un file SVG di test
    test_svg = find_test_file([".svg"])
    
    if not test_svg:
        print("✗ Nessun file SVG di test trovato")
        return
    
    print(f"Trovato SVG test: {test_svg}")
    
    # Verifica convertitori
    try:
        from svg_renderer import SVGRenderer
        renderer = SVGRenderer()
        if renderer.converter:
            print(f"✓ Convertitore SVG trovato: {renderer.converter}")
        else:
            print("✗ Nessun convertitore SVG disponibile")
    except ImportError:
        print("✗ Modulo SVG non disponibile")
    
    # Prova a visualizzare
    try:
        import subprocess
        cmd = [sys.executable, "termimg.py", test_svg, "-i"]
        print(f"Esecuzione: {' '.join(cmd)}")
        subprocess.run(cmd)
        print("✓ Test SVG completato")
    except Exception as e:
        print(f"✗ Errore nel test SVG: {e}")
    
    print()

def test_video():
    """Test funzionalità video."""
    print("=== Test Video ===")
    
    # Verifica che esista un video test
    test_video = find_test_file([".mp4", ".avi", ".mkv", ".mov"])
    
    if not test_video:
        print("✗ Nessun video di test trovato")
        return
    
    print(f"Trovato video test: {test_video}")
    
    # Test estrazione frame
    try:
        from video_manager import VideoManager
        vm = VideoManager()
        if vm.check_ffmpeg():
            print("✓ ffmpeg disponibile")
            
            info = vm.get_video_info(test_video)
            if info:
                print(f"✓ Informazioni video ottenute: {info}")
            
            # Estrai un singolo frame
            frames_dir = vm.extract_frames(test_video, fps=1, duration=0.1)
            if frames_dir and os.path.exists(frames_dir):
                print(f"✓ Frame estratto in: {frames_dir}")
                vm.cleanup()
        else:
            print("✗ ffmpeg non disponibile")
    except Exception as e:
        print(f"✗ Errore nel test di estrazione: {e}")
    
    # Test buffer asincrono
    try:
        from async_video_buffer import AsyncVideoBuffer
        buffer = AsyncVideoBuffer()
        print("✓ Buffer video asincrono disponibile")
        
        # Non avviamo l'estrazione qui poiché potrebbe essere troppo pesante per un test
    except ImportError:
        print("✗ Buffer video asincrono non disponibile")
    
    print()

def test_input_handler():
    """Test input handler."""
    print("=== Test Input Handler ===")
    
    try:
        from input_handler import InputHandler
        handler = InputHandler({
            'quit': lambda k: print(f"Tasto quit premuto: {k}"),
            'pause': lambda k: print(f"Tasto pausa premuto: {k}")
        })
        
        print("✓ Input handler creato")
        print("Premi 'q' per continuare (5 secondi di attesa)...")
        
        handler.start()
        timeout = time.time() + 5
        
        while time.time() < timeout:
            if handler.last_key_pressed == 'q':
                break
            time.sleep(0.1)
            
        handler.stop()
    except Exception as e:
        print(f"✗ Errore nel test input handler: {e}")
    
    print()

def find_test_file(extensions):
    """Cerca un file di test con le estensioni specificate."""
    # Cerca nella directory attuale
    for ext in extensions:
        for file in os.listdir("."):
            if file.lower().endswith(ext):
                return file
    
    # Cerca nella directory dell'utente
    home = os.path.expanduser("~")
    common_dirs = ["Pictures", "Videos", "Downloads", "Desktop", "Documents", "Immagini", "Video", "Documenti", "Scaricati", "工作区"]
    
    for directory in common_dirs:
        path = os.path.join(home, directory)
        if os.path.exists(path):
            for file in os.listdir(path):
                if any(file.lower().endswith(ext) for ext in extensions):
                    return os.path.join(path, file)
    
    return None

def main():
    """Esegue tutti i test o quelli selezionati."""
    parser = argparse.ArgumentParser(description="Test funzionalità TermImg")
    parser.add_argument("--all", action="store_true", help="Esegui tutti i test")
    parser.add_argument("--deps", action="store_true", help="Test dipendenze")
    parser.add_argument("--image", action="store_true", help="Test immagini")
    parser.add_argument("--svg", action="store_true", help="Test SVG")
    parser.add_argument("--video", action="store_true", help="Test video")
    parser.add_argument("--input", action="store_true", help="Test input handler")
    
    args = parser.parse_args()
    
    # Se non è specificato alcun test o è specificato --all, esegui tutti i test
    if not any([args.deps, args.image, args.svg, args.video, args.input]) or args.all:
        test_dependencies()
        test_image()
        test_svg()
        test_video()
        test_input_handler()
    else:
        if args.deps:
            test_dependencies()
        if args.image:
            test_image()
        if args.svg:
            test_svg()
        if args.video:
            test_video()
        if args.input:
            test_input_handler()
    
    print("Test completati!")

if __name__ == "__main__":
    main()
