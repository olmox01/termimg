#!/usr/bin/env python3
import os
import sys
import platform
from core import is_image_file, is_video_file

# Importazione con gestione dell'errore
try:
    from termimg import main as termimg_main
except ImportError:
    print("Errore nell'importazione del modulo 'termimg'.")
    print("Assicurati che il modulo esista e sia privo di errori.")
    sys.exit(1)
except SyntaxError as e:
    print(f"Errore di sintassi nel modulo 'termimg': {e}")
    print("Correggi gli errori di sintassi nel file termimg.py prima di continuare.")
    sys.exit(1)

def is_mobile_device():
    """Determina se stiamo eseguendo su un dispositivo mobile o emulatore."""
    try:
        # Usa il rilevatore di piattaforma se disponibile
        from platform_detector import detect_platform
        platform_info = detect_platform()
        return platform_info.get('is_arm', False) or \
               platform_info.get('is_android', False) or \
               platform_info.get('is_ios', False) or \
               platform_info.get('is_termux', False)
    except ImportError:
        # Fallback al metodo tradizionale
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Cerca indizi nel sistema o nelle variabili d'ambiente
        is_termux = 'TERMUX_VERSION' in os.environ
        is_ipad = 'IPAD' in os.environ or 'iOS' in platform.version()
        is_android = 'ANDROID_ROOT' in os.environ or 'com.termux' in os.environ.get('PREFIX', '')
        
        return is_termux or is_ipad or is_android or ('arm' in machine)

def get_optimal_settings():
    """Restituisce impostazioni ottimali in base al dispositivo."""
    settings = {}
    
    try:
        # Usa il rilevamento della piattaforma per impostazioni più precise
        from platform_detector import detect_platform, get_optimal_rendering_settings
        platform_info = detect_platform()
        rendering_settings = get_optimal_rendering_settings()
        
        if platform_info.get('is_limited_terminal', False):
            # Dispositivi a prestazioni limitate (Alpine, iSH, ecc.)
            settings['fps'] = rendering_settings.get('max_fps', 10)
            settings['mode'] = 'fit'
            settings['contrast'] = 1.2
            settings['brightness'] = 1.1
            settings['sync'] = False  # Disabilita sync per migliori prestazioni
            settings['quality'] = 'medium'  # Aumentato da low a medium
            settings['use_prerender'] = rendering_settings.get('use_prerender', True)
        elif is_mobile_device() or platform_info.get('is_arm', False):
            # Dispositivi mobili (Android, iOS, ARM)
            settings['fps'] = rendering_settings.get('max_fps', 15)
            settings['mode'] = 'fit'
            settings['contrast'] = 1.2
            settings['brightness'] = 1.05
            settings['sync'] = True
            settings['quality'] = 'high'  # Aumentato da medium a high
            settings['use_prerender'] = rendering_settings.get('use_prerender', True)
        else:
            # Desktop standard
            settings['fps'] = rendering_settings.get('max_fps', 24)
            settings['mode'] = 'fit'
            settings['contrast'] = 1.1
            settings['brightness'] = 1.0
            settings['sync'] = True
            settings['quality'] = 'ultra'  # Aumentato da high a ultra
            settings['use_prerender'] = rendering_settings.get('use_prerender', False)
        
        # Calibra le impostazioni specifiche per formato file
        # Imposta qualità ultra di default per immagini
        settings['image_quality'] = 'ultra'
        settings['video_quality'] = settings['quality']
        settings['svg_quality'] = 'ultra'  # SVG usa sempre ultra
        
    except ImportError:
        # Fallback se platform_detector non è disponibile
        if is_mobile_device():
            # Ottimizzazioni per dispositivi mobili
            settings['fps'] = 15
            settings['mode'] = 'fit'
            settings['contrast'] = 1.2
            settings['brightness'] = 1.05
            settings['sync'] = True
            settings['quality'] = 'high'  # Aumentato da medium a high
            settings['use_prerender'] = True
        else:
            # Impostazioni desktop
            settings['fps'] = 24
            settings['mode'] = 'fit'
            settings['contrast'] = 1.1
            settings['brightness'] = 1.0
            settings['sync'] = True
            settings['quality'] = 'ultra'  # Aumentato da high a ultra
            settings['use_prerender'] = True  # Attivato di default
            
        # Imposta qualità per tipo di file - sempre ultra per immagini
        settings['image_quality'] = 'ultra'
        settings['video_quality'] = settings['quality']
        settings['svg_quality'] = 'ultra'
    
    return settings

def is_svg_file(filepath):
    """Verifica se il file è un SVG basandosi sull'estensione."""
    if not os.path.isfile(filepath):
        return False
    extension = os.path.splitext(filepath)[1].lower()
    return extension == '.svg'

def check_video_compatibility(file_path):
    """
    Verifica se tutte le dipendenze necessarie per la riproduzione video sono soddisfatte
    e se il file è supportato.
    
    Args:
        file_path: Percorso del file video da verificare
        
    Returns:
        bool: True se il video può essere riprodotto, False altrimenti
    """
    # Verifica esistenza del file
    if not os.path.exists(file_path):
        print(f"Errore: il file '{file_path}' non esiste.")
        return False
    
    if not os.path.isfile(file_path):
        # Potrebbe essere una directory di immagini, non verificare come video
        return True
    
    # Verifica se il file è un formato video supportato
    if not is_video_file(file_path):
        # Non è un file video, non serve verificare ffmpeg
        return True
    
    # Se è un video, verifica ffmpeg
    try:
        # Importa funzione per ottenere i percorsi di ffmpeg
        try:
            import subprocess  # Aggiungi import mancante
            from core import get_ffmpeg_paths
            ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
        except ImportError:
            ffmpeg_path, ffprobe_path = "ffmpeg", "ffprobe"
            
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        if result.returncode != 0:
            print("ffmpeg non è disponibile o non funziona correttamente.")
            print("La riproduzione di file video richiede ffmpeg.")
            print("Per istruzioni su come installarlo, consulta README.md")
            return False
    except FileNotFoundError:
        print("ffmpeg non è installato.")
        print("La riproduzione di file video richiede ffmpeg.")
        print("Su Windows, esegui: python install_dependencies.py")
        print("Su Linux, installa ffmpeg con il gestore pacchetti.")
        return False
    
    # Verifica che il file sia un video valido e leggibile
    try:
        cmd = [
            ffprobe_path, 
            "-v", "quiet", 
            "-show_streams", 
            "-select_streams", "v", 
            file_path
        ]
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False
        )
        
        if result.returncode != 0:
            print(f"Il file '{file_path}' non sembra essere un video valido o leggibile.")
            return False
    except:
        # Se ffprobe fallisce, prova comunque a procedere
        pass
    
    return True

def main():
    """
    Script semplificato e ottimizzato per avviare termimg con rilevamento automatico.
    """
    try:
        # Se non ci sono argomenti, mostra una guida veloce
        if len(sys.argv) < 2:
            print("Utilizzo: run.py <file o cartella> [opzioni]")
            print("\nEsempi:")
            print("  run.py immagine.jpg          # Mostra un'immagine")
            print("  run.py immagine.svg          # Visualizza un'immagine SVG")
            print("  run.py video.mp4             # Riproduce un video")
            print("  run.py video.mp4 --loop      # Riproduce un video in loop")
            print("\nVideo: Al termine premi un tasto per uscire (--loop per riprodurre in ciclo)")
            print("Immagini: Premi Invio o Q per chiudere")
            sys.exit(1)
        
        # Ottieni impostazioni ottimali
        settings = get_optimal_settings()
        
        # Ottimizza le opzioni per il dispositivo corrente
        if len(sys.argv) >= 2:
            file_path = sys.argv[1]
            
            # Controllo esplicito dell'esistenza del file
            if not os.path.exists(file_path):
                print(f"Errore: il file '{file_path}' non esiste.")
                sys.exit(1)
            
            # Controlla se è richiesto il loop
            loop_requested = "--loop" in sys.argv
            
            # Controlla se è richiesto --no-sync (disabilitazione sincronizzazione)
            no_sync_requested = "--no-sync" in sys.argv
            
            # Controlla se è richiesto il pre-rendering completo
            pre_render_requested = "--pre-render" in sys.argv
            
            # Verifica per tipo SVG
            file_is_svg = is_svg_file(file_path)
            
            # Se è un file video, verifica compatibilità 
            if is_video_file(file_path) and not check_video_compatibility(file_path):
                print("Impossibile riprodurre il video a causa di dipendenze mancanti.")
                print("Per istruzioni su come installare le dipendenze, esegui:")
                print("  python install_dependencies.py")
                sys.exit(1)
            
            # Rileva il tipo di file per ottimizzazioni specifiche
            file_type = "unknown"
            if is_video_file(file_path):
                file_type = "video"
            elif is_svg_file(file_path):
                file_type = "svg"
            elif is_image_file(file_path):
                file_type = "image"
            elif os.path.isdir(file_path):
                file_type = "directory"
                
            # Controlla se è richiesto l'utilizzo di alta qualità
            quality_requested = False
            quality_level = None
            
            for i, arg in enumerate(sys.argv):
                if arg == "--quality" and i+1 < len(sys.argv):
                    quality_requested = True
                    quality_level = sys.argv[i+1]
            
            # Controlla se è richiesta forzatura alta qualità
            force_high_quality = "--force-hq" in sys.argv
            
            # Se forzata alta qualità, sovrascrivi qualsiasi impostazione
            if force_high_quality and not quality_requested:
                if file_type == "video":
                    quality_level = "high"
                else:
                    quality_level = "ultra"
                quality_requested = True
                print("Forzatura alta qualità attivata")
            
            # Se l'utente non ha già specificato questi parametri
            if not any(arg.startswith('--fps') or arg.startswith('-m') or arg == '-i' or arg == '-v' for arg in sys.argv):
                # Aggiungi opzioni ottimizzate
                if file_type == "video" or file_type == "directory":
                    # Per video: impostazioni ottimizzate
                    sys.argv.extend(['--fps', str(settings['fps']), 
                                   '-m', settings['mode'], 
                                   '--skip-checks'])
                    
                    # Aggiungi pre-rendering se necessario
                    if settings['use_prerender'] and not pre_render_requested and not any(arg == "--no-prerender" for arg in sys.argv):
                        print("Pre-rendering automatico attivato per migliorare la fluidità.")
                        print("Usa --no-prerender per disabilitare.")
                        sys.argv.append('--pre-render')
                    
                    # Aggiungi qualità specifica per il video
                    if not quality_requested:
                        sys.argv.extend(['--quality', settings['video_quality']])
                    elif quality_requested and quality_level:
                        sys.argv.extend(['--quality', quality_level])
                    
                    # Ottimizza per visualizzazione video
                    if '--sync' not in sys.argv and '--no-sync' not in sys.argv:
                        if settings['sync']:
                            sys.argv.append('--sync')
                        else:
                            sys.argv.append('--no-sync')
                
                elif file_type == "image":
                    # Per immagini: impostazioni ottimizzate con qualità ultra
                    sys.argv.extend(['-c', str(settings['contrast']), 
                                   '-b', str(settings['brightness']), 
                                   '-m', settings['mode'],
                                   '-i',  # Forza modalità immagine
                                   '--skip-checks'])
                                   
                    # Aggiungi qualità ultra per le immagini
                    if not quality_requested:
                        sys.argv.extend(['--quality', 'ultra'])
                
                elif file_type == "svg":
                    # Per SVG: impostazioni ottimizzate con qualità ultra
                    sys.argv.extend(['-m', settings['mode'],
                                   '-i',  # Forza modalità immagine
                                   '--skip-checks',
                                   '--quality', 'ultra'])
        
        # Passa il controllo a termimg
        sys.argv[0] = 'termimg.py'
        termimg_main()
    
    except PermissionError as e:
        print(f"Errore di permessi: {e}")
        print("Il programma non può accedere alle directory necessarie.")
        print("Prova a eseguire 'python fix_windows_permissions.py' come amministratore.")
        sys.exit(1)
    except Exception as e:
        print(f"Errore imprevisto: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
