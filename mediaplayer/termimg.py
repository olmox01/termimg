import os
import sys
import time
import argparse
import atexit
from PIL import Image
import threading
import subprocess
import queue

# Importa i moduli personalizzati
from core import (
    ensure_dirs, clear_screen, clear_refresh_flag, kbhit, getch,
    save_session, load_session, cleanup_old_cache, 
    get_file_type, is_image_file, is_video_file
)
from image_processor import ImageProcessor
from terminal_renderer import TerminalRenderer
from video_manager import VideoManager

# Variabili globali per la gestione dello stato
VIDEO_EXTRACTION_PROGRESS = 0
VIDEO_EXTRACTION_COMPLETED = False
VIDEO_EXTRACTION_STARTED = False

def extract_video_callback(progress):
    """Callback per monitorare il progresso dell'estrazione video."""
    global VIDEO_EXTRACTION_PROGRESS
    VIDEO_EXTRACTION_PROGRESS = progress
    # Aggiorna la visualizzazione del progresso
    print(f"\r\033[KEstrazione video: {progress}%", end="", flush=True)

def is_svg_file(filepath):
    """Verifica se il file è un SVG basandosi sull'estensione."""
    if not os.path.isfile(filepath):
        return False
    extension = os.path.splitext(filepath)[1].lower()
    return extension == '.svg'

def process_svg(args):
    """Processa e visualizza immagini SVG."""
    print(f"Caricamento SVG: {args.file_paths[0]}")
    
    # Importa il renderer SVG
    try:
        from svg_renderer import SVGRenderer
        svg_renderer = SVGRenderer()
    except ImportError:
        print("Errore: Modulo SVGRenderer non trovato. Impossibile visualizzare SVG.")
        return
    
    # Ottieni dimensioni del terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Inizializza processore e renderer
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Setup di alta qualità se richiesto
    quality_level = getattr(args, 'quality', 'auto')
    if quality_level != 'auto':
        try:
            from high_quality_renderer import auto_configure_quality, setup_high_quality
            
            if quality_level == 'ultra':
                renderer = setup_high_quality(renderer)
                print("Rendering SVG in qualità ultra attivato")
            else:
                # Rileva capacità hardware
                try:
                    from platform_detector import detect_platform
                    platform_info = detect_platform()
                    hardware_capability = "high"
                    if platform_info.get('is_limited_terminal', False):
                        hardware_capability = "low"
                    elif platform_info.get('is_arm', False):
                        hardware_capability = "medium"
                except ImportError:
                    hardware_capability = "high"
                    
                # Per SVG possiamo usare qualità superiore
                if hardware_capability == "medium":
                    hardware_capability = "high"
                    
                # Configura automaticamente la qualità
                renderer, actual_quality = auto_configure_quality(
                    renderer, 
                    hardware_capability, 
                    is_video=False
                )
                print(f"Rendering SVG in qualità {actual_quality} attivato")
        except ImportError:
            print("Modulo high_quality_renderer non disponibile, usando renderer standard")
    
    try:
        svg_path = args.file_paths[0]
        if not os.path.exists(svg_path):
            print(f"Errore: file non trovato: {svg_path}")
            return
        
        # Renderizza SVG usando il modulo dedicato
        if svg_renderer.render_svg(svg_path, term_width, term_height, processor, renderer):
            # Attendi input utente
            renderer.wait_for_input(processor)
            
            # Salva sessione
            try:
                save_session(args)
            except Exception as e:
                print(f"Avviso: Impossibile salvare la sessione: {e}")
        else:
            print("Impossibile renderizzare il file SVG.")
    
    except Exception as e:
        print(f"Errore durante la visualizzazione del SVG: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Pulizia
        renderer.cleanup()

def main():
    try:
        # Assicurati che le directory esistano
        ensure_dirs()
        
        # Verifica dipendenze all'avvio
        if "--skip-checks" not in sys.argv:
            if not check_dependencies():
                print("AVVISO: Alcune dipendenze mancano. Il programma potrebbe non funzionare correttamente.")
                print("Provo a continuare comunque...")
        
        # Configura il parser per gli argomenti
        parser = argparse.ArgumentParser(description="Visualizzatore di immagini e video per terminale")
        parser.add_argument("file_paths", nargs="*", help="Percorso delle immagini o video da visualizzare")
        parser.add_argument("-m", "--mode", choices=["fit", "stretch", "fill"], default="fit", 
                          help="Modalità di adattamento: fit (default), stretch, fill")
        parser.add_argument("-c", "--contrast", type=float, default=1.1,
                          help="Fattore di contrasto (default: 1.1)")
        parser.add_argument("-b", "--brightness", type=float, default=1.0,
                          help="Fattore di luminosità (default: 1.0)")
        parser.add_argument("-r", "--reload", action="store_true",
                          help="Ricarica l'ultima immagine utilizzata con le stesse impostazioni")
        parser.add_argument("--fps", type=float, default=24.0,
                          help="FPS target per la modalità video (default: 24)")
        parser.add_argument("-v", "--video", action="store_true",
                          help="Forza la modalità video indipendentemente dal tipo di file")
        parser.add_argument("-i", "--image", action="store_true",
                          help="Forza la modalità immagine indipendentemente dal tipo di file")
        parser.add_argument("--start", type=float, default=0.0,
                          help="Tempo di inizio in secondi (solo per video)")
        parser.add_argument("--duration", type=float, default=None,
                          help="Durata in secondi (solo per video)")
        parser.add_argument("--extract-only", action="store_true",
                          help="Estrai i frame del video senza visualizzarli")
        parser.add_argument("--extract-dir", type=str, default=None,
                          help="Directory dove estrarre i frame del video")
        parser.add_argument("--skip-checks", action="store_true",
                          help="Salta la verifica delle dipendenze")
        parser.add_argument("--version", action="store_true",
                          help="Mostra la versione del programma")
        parser.add_argument("--loop", action="store_true",
                          help="Riproduce il video in loop (default: false)")
        parser.add_argument("--sync", action="store_true",
                          help="Sincronizza precisamente la riproduzione video con l'originale")
        parser.add_argument("--no-sync", action="store_true",
                          help="Disabilita la sincronizzazione precisa (utile per dispositivi con prestazioni limitate)")
        parser.add_argument("--quality", choices=["low", "medium", "high", "ultra", "auto"],
                          default="auto", help="Livello di qualità del rendering")
        parser.add_argument("--pre-render", action="store_true",
                          help="Pre-renderizza completamente i video prima della riproduzione")
        parser.add_argument("--no-prerender", action="store_true",
                          help="Disabilita pre-rendering automatico")
        args = parser.parse_args()
        
        # Aggiungi il controllo della versione
        if args.version:
            print("TermImg versione 1.0.0")
            print("Supporto per immagini e video nel terminale")
            print("Compatibile con sistemi Linux MUSL e configurazioni minimali")
            sys.exit(0)
        
        # Assicurati che le directory esistano
        backup_dir = ensure_dirs()
        
        # Se è stata creata una directory di backup per mancanza di permessi, aggiorna CACHE_DIR
        if backup_dir:
            global CACHE_DIR
            CACHE_DIR = backup_dir
        
        # Registra la pulizia alla chiusura
        atexit.register(cleanup_old_cache)
        
        # Gestisci il ricaricamento dell'ultima sessione
        if args.reload:
            session = load_session()
            if session:
                if 'image_paths' in session:
                    args.file_paths = session['image_paths']
                if 'args' in session:  # Correzione: rimozione dell'apostrofo in eccesso
                    for key, value in session['args'].items():
                        if key not in ['file_paths', 'reload']:
                            setattr(args, key, value)
                    print(f"Sessione precedente caricata: {args.file_paths}")
            else:
                print("Nessuna sessione precedente trovata.")
        
        # Verifica che sia stato specificato almeno un file
        if not args.file_paths:
            print("Specificare almeno un file da visualizzare.")
            parser.print_help()
            sys.exit(1)
        
        # Determina il tipo di file (immagine o video)
        file_path = args.file_paths[0]
        if args.video:
            # Forza modalità video
            process_video(args)
        elif args.image:
            # Forza modalità immagine
            if is_svg_file(file_path):
                process_svg(args)
            else:
                process_images(args)
        else:
            # Autodetection basata sul tipo di file
            if os.path.isdir(file_path) or len(args.file_paths) > 1:
                # Se è una directory o più file, trattali come una sequenza di immagini/video
                process_video(args)
            else:
                # Rileva il tipo di file
                video_manager = VideoManager()
                
                # Prima verifica con il VideoManager che è più accurato per i video
                if video_manager.is_video_file(file_path):
                    process_video(args)
                elif is_svg_file(file_path):
                    process_svg(args)
                elif is_image_file(file_path):
                    process_images(args)
                else:
                    # Se il tipo non è riconoscibile, prova a trattarlo come immagine
                    process_images(args)
    except PermissionError as e:
        print(f"Errore di permessi: {e}")
        print("Esegui il programma con privilegi adeguati o usa --user-dir per forzare l'uso della directory utente.")
        sys.exit(1)
    except Exception as e:
        print(f"Errore durante l'inizializzazione: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def process_images(args):
    """Processa e visualizza immagini statiche."""
    print(f"Caricamento immagine: {args.file_paths[0]}")
    
    # Ottieni dimensioni del terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    # Inizializza processore e renderer
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Setup di alta qualità se richiesto
    quality_level = getattr(args, 'quality', 'auto')
    if quality_level != 'auto':
        try:
            from high_quality_renderer import auto_configure_quality, setup_high_quality
            
            if quality_level == 'ultra':
                renderer = setup_high_quality(renderer)
                print("Rendering in qualità ultra attivato")
            else:
                # Rileva capacità hardware
                try:
                    from platform_detector import detect_platform
                    platform_info = detect_platform()
                    hardware_capability = "high"
                    if platform_info.get('is_limited_terminal', False):
                        hardware_capability = "low"
                    elif platform_info.get('is_arm', False):
                        hardware_capability = "medium"
                except ImportError:
                    hardware_capability = "high"
                    
                # Configura automaticamente la qualità
                renderer, actual_quality = auto_configure_quality(
                    renderer, 
                    hardware_capability, 
                    is_video=False
                )
                print(f"Rendering in qualità {actual_quality} attivato")
        except ImportError:
            print("Modulo high_quality_renderer non disponibile, usando renderer standard")
    
    try:
        # Carica l'immagine
        img_path = args.file_paths[0]
        if not os.path.exists(img_path):
            print(f"Errore: file non trovato: {img_path}")
            return
            
        img = processor.load_image(img_path)
        
        # Processa l'immagine con contrasto e luminosità
        contrast = getattr(args, 'contrast', 1.1)
        brightness = getattr(args, 'brightness', 1.0)
        processed_img = processor.process_image(img, contrast, brightness)
        
        # Ridimensiona per adattarla al terminale
        mode = getattr(args, 'mode', "fit")
        resized_img, target_width, target_height, padding_x, padding_y = processor.resize_for_terminal(
            processed_img, term_width, term_height, mode
        )
        
        # Salva dimensioni nel renderer
        renderer.target_width = target_width
        renderer.target_height = target_height
        renderer.padding_x = padding_x
        renderer.padding_y = padding_y
        
        # Prepara i dati per il rendering una volta sola
        pixel_data = renderer.prepare_pixel_data(
            processor.layers['base'],
            target_width, target_height, 
            padding_x, padding_y,
            term_width, term_height
        )
        
        # Rendering dell'immagine - i dati saranno salvati dentro render_image
        renderer.render_image(pixel_data, term_width, term_height)
        
        # Attendi input utente
        renderer.wait_for_input(processor)
                
        # Salva la sessione per futuri ricaricamenti
        save_session(args)
        
    except Exception as e:
        print(f"Errore durante la visualizzazione dell'immagine: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Pulizia
        renderer.cleanup()

def extract_video_frames_async(video_manager, video_path, output_dir, fps, start_time, duration):
    """Estrae i frame di un video in un thread separato."""
    global VIDEO_EXTRACTION_STARTED, VIDEO_EXTRACTION_COMPLETED
    
    VIDEO_EXTRACTION_STARTED = True
    VIDEO_EXTRACTION_COMPLETED = False
    
    try:
        frames_dir = video_manager.extract_frames(
            video_path, 
            output_dir=output_dir,
            fps=fps,
            start_time=start_time,
            duration=duration,
            callback=extract_video_callback
        )
        VIDEO_EXTRACTION_COMPLETED = True
        return frames_dir
    except Exception as e:
        print(f"\nErrore durante l'estrazione: {e}")
        VIDEO_EXTRACTION_COMPLETED = False
        return None

def show_extraction_progress():
    """Mostra una barra di progresso per l'estrazione del video."""
    global VIDEO_EXTRACTION_PROGRESS, VIDEO_EXTRACTION_COMPLETED
    
    start_time = time.time()
    spin_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spin_idx = 0
    
    while not VIDEO_EXTRACTION_COMPLETED:
        elapsed = time.time() - start_time
        spinner = spin_chars[spin_idx % len(spin_chars)]
        spin_idx += 1
        
        # Crea una barra di progresso grafica
        progress_bar_width = 30
        filled_length = int(progress_bar_width * VIDEO_EXTRACTION_PROGRESS / 100)
        bar = '█' * filled_length + '░' * (progress_bar_width - filled_length)
        
        print(f"\r\033[K{spinner} Estrazione video: [{bar}] {VIDEO_EXTRACTION_PROGRESS}% - {elapsed:.1f}s", 
              end="", flush=True)
        time.sleep(0.1)
    
    # Stampa il completamento
    if VIDEO_EXTRACTION_PROGRESS >= 100:
        print(f"\r\033[K✓ Estrazione completata in {elapsed:.1f}s!                           ")
    else:
        print(f"\r\033[K✗ Estrazione interrotta dopo {elapsed:.1f}s                          ")

def process_video(args):
    """Processa e visualizza video o sequenze di immagini."""
    global VIDEO_EXTRACTION_PROGRESS, VIDEO_EXTRACTION_COMPLETED, VIDEO_EXTRACTION_STARTED
    
    # Prima di tutto, verifica che tutte le dipendenze necessarie siano installate
    if not verify_video_dependencies():
        print("Alcune dipendenze necessarie per la riproduzione video non sono disponibili.")
        print("Esegui 'python install_dependencies.py' per installarle.")
        return
    
    # Inizializza il video manager
    video_manager = VideoManager()
    
    # Modalità di rendering completo prima della riproduzione
    pre_render_complete = args.pre_render if hasattr(args, 'pre_render') and args.pre_render else False
    
    # Inizializza variabili di controllo del buffer
    empty_buffer_count = 0
    max_empty_buffer = 30  # Numero massimo di tentativi prima di uscire con buffer vuoto
    complete_renderer = None  # Inizializzazione di complete_renderer
    
    # Inizializza il buffer asincrono se disponibile
    async_buffer = None
    use_async_buffer = False
    
    try:
        from async_video_buffer import AsyncVideoBuffer
        use_async_buffer = True
        async_buffer = AsyncVideoBuffer(max_buffer_size=30, preload_frames=10)  # Buffer aumentato per prestazioni migliori
        print("Buffer video asincrono disponibile")
    except ImportError:
        use_async_buffer = False
        async_buffer = None
        print("Buffer video asincrono non disponibile")
    
    # Rileva se siamo su una piattaforma limitata
    try:
        from platform_detector import detect_platform
        platform_info = detect_platform()
        
        # Adatta FPS se siamo su una piattaforma limitata
        if platform_info.get('is_limited_terminal', False) and args.fps > platform_info.get('max_fps', 24):
            orig_fps = args.fps
            args.fps = platform_info.get('max_fps', 12)
            print(f"Piattaforma limitata rilevata. FPS ridotti a {args.fps} (erano {orig_fps}).")
    except ImportError:
        platform_info = {'is_limited_terminal': False}
    
    # Inizializza l'handler di input
    input_handler = None
    use_input_handler = False
    try:
        from input_handler import InputHandler
        use_input_handler = True
    except ImportError:
        use_input_handler = False

    # Inizializza processore e renderer per i frame
    processor = ImageProcessor()
    renderer = TerminalRenderer()
    
    # Setup di alta qualità se richiesto
    quality_level = getattr(args, 'quality', 'auto')
    if quality_level != 'auto':
        try:
            from high_quality_renderer import auto_configure_quality, setup_high_quality
            
            if quality_level == 'ultra':
                renderer = setup_high_quality(renderer)
                print("Rendering in qualità ultra attivato")
            else:
                # Rileva capacità hardware
                hardware_capability = "high"
                if platform_info.get('is_limited_terminal', False):
                    hardware_capability = "low"
                elif platform_info.get('is_arm', False):
                    hardware_capability = "medium"
                    
                # Configura automaticamente la qualità
                renderer, actual_quality = auto_configure_quality(
                    renderer, 
                    hardware_capability, 
                    is_video=True
                )
                print(f"Rendering in qualità {actual_quality} attivato")
        except ImportError:
            print("Modulo high_quality_renderer non disponibile, usando renderer standard")
    
    # Ottieni dimensioni del terminale
    term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
    
    try:
        video_path = args.file_paths[0]
        
        # Verifica se il video esiste
        if not os.path.exists(video_path):
            print(f"Il file '{video_path}' non esiste.")
            return
        
        # Per file con nome problematico, mostra il nome completo per debug
        if any(c in video_path for c in ' &()[]{}\'",;<>?|'):
            print(f"Nota: Il percorso del file contiene caratteri speciali: {video_path}")
            print("Se riscontri problemi, prova a rinominare il file rimuovendo caratteri speciali")
        
        # Inizializza l'analizzatore di prestazioni
        try:
            from performance_analyzer import PerformanceAnalyzer
            performance_analyzer = PerformanceAnalyzer(target_fps=args.fps)
            perf_enabled = True
        except ImportError:
            performance_analyzer = None
            perf_enabled = False
            
        # Determina le capacità hardware
        hardware_capability = "high"  # Default
        if perf_enabled:
            hardware_capability = performance_analyzer.hardware_capability
            if hardware_capability != "high" and args.fps > 20:
                print(f"Hardware {hardware_capability} rilevato. Ottimizzazione prestazioni attivata.")
                
        # Variabili che potrebbero essere usate nei callback
        paused = False
        frame_count = 0
        frame_skip_count = 0  # Conteggio frame saltati
        target_frame = 0      # Frame che dovremmo visualizzare in base al tempo
        start_time = time.time()
        last_frame_time = start_time  # Tempo dell'ultimo frame visualizzato
        drift_correction = 0  # Correzione per la deriva temporale
        sync_enabled = not args.no_sync  # Sincronizzazione abilitata di default, a meno che --no-sync sia specificato
        sync_interval = 30  # Intervallo di correzione della sincronizzazione (in frame)
        
        # Configurazione basata su capacità hardware
        smart_sync = hardware_capability != "high"  # Abilita smart sync su hardware non high-end
        adaptive_fps = hardware_capability != "high"  # Abilita FPS adattivi su hardware non high-end
        
        # Configura l'handler di input se disponibile
        if use_input_handler:
            # Prepara le callback
            callbacks = {}
            
            def quit_callback(key):
                # Segnala richiesta di uscita
                nonlocal paused
                paused = True
                clear_screen()
                print("Uscita...")
                sys.exit(0)
                
            def pause_callback(key):
                nonlocal paused, start_time, frame_count
                paused = not paused
                # Se riprendiamo, aggiorna il tempo di inizio
                if not paused:
                    start_time = time.time() - (frame_count / args.fps)
            
            callbacks['quit'] = quit_callback
            callbacks['pause'] = pause_callback
            callbacks['enter'] = quit_callback  # Invio = uscita
            
            input_handler = InputHandler(callbacks)
            input_handler.start()
                    
        # Determina se usare la modalità di pre-rendering completo
        use_complete_renderer = False
        if pre_render_complete or (platform_info.get('is_limited_terminal', False) and not args.no_prerender):
            try:
                from complete_video_renderer import CompleteVideoRenderer
                print("Modalità di pre-rendering completo disponibile")
                use_complete_renderer = True
                
                # Crea oggetto renderer completo
                complete_renderer = CompleteVideoRenderer(video_manager, processor, renderer)
            except ImportError:
                print("Modulo per pre-rendering completo non disponibile")
                use_complete_renderer = False
        
        # Se stiamo usando il buffer asincrono e il video è un file singolo
        if use_async_buffer and os.path.isfile(video_path) and not os.path.isdir(video_path):
            # Ottieni informazioni sul video
            video_info = video_manager.get_video_info(video_path)
            if not video_info:
                print(f"Impossibile ottenere informazioni sul video: {video_path}")
                print("Provo a procedere comunque con l'estrazione dei frame...")
                # Qui invece di uscire, continuiamo lo stesso
                # Usiamo valori predefiniti per frame rate e durata
                video_info = {"fps": args.fps, "duration": 0, "total_frames": 0}
            
            # Se richiesta solo l'estrazione
            if args.extract_only:
                output_dir = args.extract_dir if args.extract_dir else None
                print(f"Estrazione frame verso: {output_dir or 'directory temporanea'}")
                frames_dir = video_manager.extract_frames(
                    video_path, 
                    output_dir=output_dir,
                    fps=args.fps,
                    start_time=args.start,
                    duration=args.duration,
                    callback=extract_video_callback
                )
                if frames_dir:
                    print(f"Frame estratti in: {frames_dir}")
                return
            
            # Avvia il processo di buffering
            print("Avvio buffering video asincrono...")
            
            # Avvia l'estrazione asincrona
            success = async_buffer.start_extraction(
                video_path,
                fps=args.fps,
                start_time=args.start,
                duration=args.duration,
                callback=extract_video_callback
            )
            
            if not success:
                print("Errore nell'avvio dell'estrazione asincrona, provo con il metodo standard")
                # Estrazione diretta con VideoManager
                frames_dir = video_manager.extract_frames(
                    video_path, 
                    fps=args.fps,
                    start_time=args.start,
                    duration=args.duration,
                    callback=extract_video_callback
                )
                
                if not frames_dir:
                    print("Impossibile estrarre frame dal video. Uscita.")
                    return
                
                # Configura video_manager per la riproduzione
                print(f"Riproduco con metodo standard da: {frames_dir}")
                # Continua con il metodo standard di riproduzione
                # ...
                return
            
            # Avvia riproduzione
            print(f"Avvio riproduzione a {args.fps} FPS (p=pausa, q=esci, s=sync, a=adattivo)")
            time.sleep(0.5)  # Attendi un attimo per iniziare l'estrazione
            clear_screen()
            frame_duration = 1.0 / args.fps  # Durata teorica di un frame in secondi
            frame_buffer = None  # Buffer per il frame corrente
            rendered_frame_data = None  # Dati del frame renderizzato
            total_frames = video_info.get('total_frames', 1000)  # Valore predefinito se non disponibile
            video_duration = video_info.get('duration', 0)  # Durata del video in secondi
            
            # Aggiungi una soglia per rilevare quando siamo significativamente in ritardo
            fps_threshold = args.fps * 0.7  # 70% dell'FPS target è la soglia minima accettabile
            
            # Avvia il monitoraggio delle prestazioni
            if perf_enabled:
                performance_analyzer.start_monitoring()
            
            # Avvia pre-rendering per ottimizzare la riproduzione
            if use_async_buffer and smart_sync:
                print("Avvio pre-rendering intelligente...")
                async_buffer.start_pre_rendering(processor, renderer, term_width, term_height)
            
            # Variabili per regolazione adattiva FPS
            performance_history = []
            adaptive_window = 10  # Finestra di campionamento
            max_auto_adjust = 0.2  # Massima regolazione automatica (20%)
            smooth_factor = 1.0   # Fattore di fluidità della riproduzione
            
            while True:
                if not paused:
                    # Gestisci i frame
                    try:
                        # Calcola il tempo corrente dal punto di vista della riproduzione
                        current_time = time.time()
                        elapsed_since_start = current_time - start_time
                        
                        # Calcola quale frame dovremmo mostrare in base al tempo trascorso
                        target_frame = int(elapsed_since_start * args.fps)
                        
                        # Se siamo in ritardo, salta i frame necessari
                        frames_to_skip = target_frame - frame_count
                        
                        if smart_sync and frames_to_skip > 1:
                            # Prova a usare un frame pre-renderizzato per recuperare
                            if rendered_frame_data is None:
                                # Prova a ottenere un frame già renderizzato
                                rendered = async_buffer.get_rendered_frame(block=False)
                                if rendered:
                                    rendered_frame_data, raw_frame = rendered
                                    
                                    # Se serve saltare più di un frame, salta alcuni frame renderizzati
                                    if frames_to_skip > 2:
                                        skipped = async_buffer.skip_rendered_frames(min(frames_to_skip - 1, 3))
                                        if skipped > 0:
                                            frame_skip_count += skipped
                            
                        # Se non abbiamo un frame renderizzato, prova a ottenere un frame normale
                        if rendered_frame_data is None:
                            # Siamo in ritardo e non abbiamo frame renderizzati? Salta alcuni frame
                            if frames_to_skip > 1:
                                # Limita il numero di frame da saltare in una volta
                                max_skip = min(frames_to_skip - 1, 5)
                                for _ in range(max_skip):
                                    try:
                                        _ = async_buffer.get_frame(block=False, timeout=0.01)
                                        frame_skip_count += 1
                                    except queue.Empty:
                                        break
                                
                            # Ottieni un nuovo frame normale
                            frame = async_buffer.get_frame(block=True, timeout=0.1)
                            
                            if frame:
                                # Abbiamo un frame, resetta il contatore di buffer vuoto
                                empty_buffer_count = 0
                                
                                # Processa il nuovo frame
                                processed_img = processor.process_image(frame, args.contrast, args.brightness)
                                
                                # Ridimensiona per adattarla al terminale (mantieni proporzioni)
                                resized_img, target_width, target_height, padding_x, padding_y = processor.resize_for_terminal(
                                    processed_img, term_width, term_height, "fit"
                                )
                                
                                # Prepara i dati per il rendering
                                frame_buffer = renderer.prepare_pixel_data(
                                    processor.layers['base'],
                                    target_width, target_height, 
                                    padding_x, padding_y,
                                    term_width, term_height
                                )
                                
                                # Aggiorna il contatore dei frame
                                frame_count += 1
                        else:
                            # Abbiamo un frame renderizzato, usalo
                            frame_buffer = rendered_frame_data
                            frame_count += 1
                            rendered_frame_data = None  # Reset per il prossimo ciclo
                        
                        # Prepara un testo di stato conciso per la riproduzione
                        progress = int((frame_count / max(1, total_frames)) * 100)
                        
                        # Calcola il tempo di riproduzione corrente (in secondi)
                        current_time = frame_count / args.fps
                        
                        # Formatta il tempo come MM:SS
                        minutes = int(current_time // 60)
                        seconds = int(current_time % 60)
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        
                        # Aggiungi la durata totale se disponibile
                        if video_duration > 0:
                            total_minutes = int(video_duration // 60)
                            total_seconds = int(video_duration % 60)
                            time_str += f"/{total_minutes:02d}:{total_seconds:02d}"
                        
                        # Calcola gli FPS effettivi
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            actual_fps = round(frame_count / elapsed, 1)
                            
                            # Aggiorna l'analizzatore di performance
                            if perf_enabled:
                                performance_analyzer.register_frame()
                                if frame_skip_count > 0:
                                    performance_analyzer.skipped_frames = frame_skip_count
                            
                            # Aggiorna la cronologia delle prestazioni
                            if len(performance_history) >= adaptive_window:
                                performance_history.pop(0)
                            performance_history.append(actual_fps)
                            
                            # Regola il fattore di fluidità in base alle prestazioni
                            if adaptive_fps and len(performance_history) >= 3:
                                avg_fps = sum(performance_history) / len(performance_history)
                                smooth_factor = async_buffer.analyze_playback_timing(args.fps, avg_fps)
                            
                            # Aggiungi informazioni sui frame saltati nella barra di stato
                            skipped_info = f" -SK:{frame_skip_count}" if frame_skip_count > 0 else ""
                            
                            # Aggiungi info sulla modalità di sincronizzazione
                            sync_mode = "S+" if sync_enabled and smart_sync else \
                                        "S" if sync_enabled else "NS"
                            
                            # Aggiungi info sul fattore di fluidità se adattivo è attivo
                            adapt_info = f" A:{smooth_factor:.1f}" if adaptive_fps else ""
                            
                            # Ottieni parametri adattivi dalla libreria di analisi
                            if perf_enabled and adaptive_fps:
                                params = performance_analyzer.get_adaptive_parameters()
                                smooth_factor = params['smoothness']
                                
                                if params['fps'] < args.fps * 0.9:
                                    # Segnala che stiamo usando FPS ridotti
                                    adapt_info = f" A:{smooth_factor:.1f}"
                                else:
                                    adapt_info = ""
                        else:
                            actual_fps = args.fps
                            skipped_info = ""
                            sync_mode = "S" if sync_enabled else "NS"
                            adapt_info = ""
                            
                        # Stato completo con tempo e FPS
                        status_text = f"[{progress}% | {time_str} | {actual_fps:.1f} FPS{skipped_info} | {sync_mode}{adapt_info}] {os.path.basename(video_path)}"
                        
                        # Verifica che frame_buffer non sia None prima del rendering
                        if frame_buffer:
                            # Rendering dell'immagine con metodo ottimizzato per dispositivi mobili
                            renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)

                            # Calcola il tempo target per il prossimo frame con correzione della deriva
                            target_frame_time = start_time + ((frame_count) / args.fps) + drift_correction
                            current_time = time.time()
                            
                            # Regola la sincronizzazione periodicamente
                            if sync_enabled and frame_count % sync_interval == 0:
                                # Calcola il tempo ideale e reale trascorso
                                ideal_time_elapsed = frame_count / args.fps
                                actual_time_elapsed = current_time - start_time
                                drift = actual_time_elapsed - ideal_time_elapsed
                                
                                if abs(drift) > 0.05:  # Solo se la deriva è significativa
                                    if smart_sync:
                                        # Con smart_sync, adatta la strategia in base alle prestazioni
                                        if actual_fps < fps_threshold and drift > 0.5:
                                            # Sistema sovraccaricato, affidati più al salto di frame
                                            drift_correction = 0  # Elimina correzione, sfavorisce timing
                                        else:
                                            # Sistema in grado di gestire la correzione
                                            max_correction = 0.5  # Massima correzione ammissibile
                                            correction = -drift * 0.1  # Applica gradualmente
                                            drift_correction += max(min(correction, max_correction), -max_correction)
                                    else:
                                        # Approccio classico
                                        max_correction = 0.5
                                        correction = -drift * 0.1
                                        drift_correction += max(min(correction, max_correction), -max_correction)
                                    
                                    # Debug sulla sincronizzazione quando c'è una deriva significativa
                                    if abs(drift) > 0.5:
                                        skip_info = f" (frames saltati: {frame_skip_count})" if frame_skip_count > 0 else ""
                                        adaptive_info = f" (adattivo: {smooth_factor:.2f})" if adaptive_fps else ""
                                        print(f"\r\033[KSincronizzazione: deriva={drift:.3f}s corr={drift_correction:.3f}s{skip_info}{adaptive_info}", end="")
                            
                            # Calcola il tempo di sleep necessario
                            sleep_time = max(0, target_frame_time - current_time)
                            
                            # Se il modo adattivo è attivo, regola il tempo di sleep
                            if adaptive_fps and smooth_factor != 1.0:
                                sleep_time *= smooth_factor
                            
                            # Controllo input migliorato
                            check_interval = max(1, min(int(args.fps / 4), 10))
                            if frame_count % check_interval == 0:
                                if kbhit():
                                    key = getch()
                                    if key == 'q':  # Uscita
                                        clear_screen()
                                        return
                                    elif key == 'p' or key == ' ':  # Pausa
                                        paused = not paused
                                        if paused:
                                            status_text = f"[PAUSA {progress}% | {time_str}] {os.path.basename(video_path)}"
                                            renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
                                    elif key == 's':  # Attiva/disattiva sincronizzazione
                                        sync_enabled = not sync_enabled
                                        message = "attivata" if sync_enabled else "disattivata"
                                        print(f"\r\033[KSincronizzazione {message}", end="")
                                        time.sleep(0.5)
                                    elif key == 'a':  # Attiva/disattiva modalità adattiva
                                        adaptive_fps = not adaptive_fps
                                        message = "attivata" if adaptive_fps else "disattivata"
                                        print(f"\r\033[KModalità adattiva {message}", end="")
                                        time.sleep(0.5)
                                    elif key == '+':  # Aumenta FPS target
                                        args.fps = min(args.fps + 2, 60)
                                        frame_duration = 1.0 / args.fps
                                        print(f"\r\033[KFPS target: {args.fps}", end="")
                                        time.sleep(0.5)
                                    elif key == '-':  # Diminuisci FPS target
                                        args.fps = max(args.fps - 2, 5)
                                        frame_duration = 1.0 / args.fps
                                        print(f"\r\033[KFPS target: {args.fps}", end="")
                                        time.sleep(0.5)
                            
                            # Dormi senza polling intensivo
                            if sleep_time > 0:
                                time.sleep(sleep_time)
                                
                            last_frame_time = time.time()
                            
                    except queue.Empty:
                        # Nessun nuovo frame disponibile, ma l'estrazione potrebbe essere ancora in corso
                        empty_buffer_count += 1
                        
                        if empty_buffer_count > max_empty_buffer and async_buffer.extraction_complete:
                            # Se abbiamo provato molte volte e l'estrazione è completa, usciamo
                            break
                        
                        # Aggiungiamo un piccolo ritardo per non sovraccaricare la CPU
                        time.sleep(0.05)
                        continue
                
                else:  # Modalità pausa
                    # In pausa, attendi solo l'input
                    # Mostra indicatore di pausa
                    progress = int((frame_count / max(1, total_frames)) * 100)
                    
                    # Calcola il tempo di riproduzione corrente
                    current_time = frame_count / args.fps
                    minutes = int(current_time // 60)
                    seconds = int(current_time % 60)
                    time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    # Aggiungi la durata totale se disponibile
                    if video_duration > 0:
                        total_minutes = int(video_duration // 60)
                        total_seconds = int(video_duration % 60)
                        time_str += f"/{total_minutes:02d}:{total_seconds:02d}"
                    
                    # Stato in pausa con tempo
                    status_text = f"[PAUSA {progress}% | {time_str}] {os.path.basename(video_path)}"
                    
                    # Usa il renderer completo se disponibile
                    if complete_renderer and complete_renderer.is_complete():
                        # Usa l'ultimo frame disponibile per mostrare stato di pausa
                        frame_buffer = complete_renderer.get_frame(frame_count)
                        if frame_buffer:
                            minutes = int(frame_count / args.fps / 60)
                            seconds = int(frame_count / args.fps) % 60
                            time_str = f"{minutes:02d}:{seconds:02d}"
                            status_text = f"[PAUSA {int((frame_count/total_frames)*100)}% | {time_str}] {os.path.basename(video_path)}"
                            renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
                    
                    # Verifica che frame_buffer non sia None prima del rendering
                    elif frame_buffer:
                        renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
                    else:
                        # Fallback se frame_buffer è None
                        sys.stdout.write(f"\r{status_text}")
                        sys.stdout.flush()
                    
                    # Gestione input durante la pausa
                    if kbhit():
                        key = getch()
                        if key == 'q':
                            clear_screen()
                            print("Riproduzione terminata.")
                            return
                        elif key == 'p' or key == ' ':
                            paused = False
                            # Aggiorna il tempo di partenza quando si riprende
                            start_time = time.time() - (frame_count / args.fps)
                    
                    time.sleep(0.1)  # Breve pausa per evitare di consumare troppa CPU
    
    except KeyboardInterrupt:
        print("\nRiproduzione interrotta dall'utente.")
    finally:
        # Cleanup delle risorse
        if perf_enabled:
            performance_analyzer.stop_monitoring()
        
        # Se abbiamo usato il complete renderer, pulizia
        if complete_renderer:
            complete_renderer.cleanup()
            
        video_manager.cleanup()
        renderer.cleanup()
        clear_screen()

    # Se è richiesto il pre-rendering completo e abbiamo il modulo
    if use_complete_renderer:
        # Configura e avvia il display di progresso
        try:
            from progress_display import ProgressDisplay
            progress_display = ProgressDisplay()
            progress_display.start("Preparazione video...")
        except ImportError:
            progress_display = None
            print("Preparazione video per riproduzione fluida...")
        
        # Callback per aggiornare la visualizzazione del progresso
        def progress_callback(progress, status, eta):
            if progress_display:
                progress_display.update(progress, status, eta)
            else:
                # Fallback semplice
                bar_length = 30
                filled = int(bar_length * progress / 100)
                bar = "#" * filled + "-" * (bar_length - filled)
                eta_str = f"ETA: {int(eta)}s" if eta > 0 else ""
                print(f"\r[{bar}] {progress:.1f}% {status} {eta_str}", end="")
        
        # Avvia il rendering completo
        started = complete_renderer.start_rendering(
            video_path, 
            fps=args.fps,
            term_width=term_width,
            term_height=term_height,
            start_time=args.start,
            duration=args.duration,
            contrast=args.contrast, 
            brightness=args.brightness,
            callback=progress_callback
        )
        
        if not started:
            print("\nImpossibile avviare il pre-rendering completo, torno alla modalità standard")
            use_complete_renderer = False
        else:
            # Attendi il completamento del rendering
            while not complete_renderer.is_complete() and complete_renderer.is_rendering:
                progress, status, eta = complete_renderer.get_progress()
                
                # Controlla input utente per annullamento
                if kbhit():
                    key = getch()
                    if key == 'q':
                        complete_renderer.cancel_rendering()
                        print("\nRendering annullato.")
                        return
                
                time.sleep(0.1)
            
            if progress_display:
                progress_display.stop("Pre-rendering completato!")
            else:
                print("\nPre-rendering completato!")
            
            # Ora riproduci il video dai frame pre-renderizzati
            print(f"Avvio riproduzione ad alta qualità (p=pausa, q=esci)")
            time.sleep(1)
            clear_screen()
            
            # Imposta variabili per la riproduzione
            paused = False
            frame_count = 0
            frame_time = 0
            start_time = time.time()
            frame_duration = 1.0 / args.fps
            total_frames = int(args.duration * args.fps) if args.duration else complete_renderer.total_frames
            
            # Loop di riproduzione dai frame pre-renderizzati
            while frame_count < total_frames:
                if paused:
                    # In pausa, mostra lo stato corrente
                    frame_buffer = complete_renderer.get_frame(frame_count)
                    if frame_buffer:
                        minutes = int(frame_count / args.fps / 60)
                        seconds = int(frame_count / args.fps) % 60
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        progress = int((frame_count / total_frames) * 100)
                        status_text = f"[PAUSA {progress}% | {time_str}] {os.path.basename(video_path)}"
                        renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
                    
                    # Gestisci input utente durante la pausa
                    if kbhit():
                        key = getch()
                        if key == 'q':
                            clear_screen()
                            print("Riproduzione terminata.")
                            return
                        elif key == 'p' or key == ' ':
                            paused = False
                            # Resetta il tempo di inizio quando si riprende
                            start_time = time.time() - (frame_count * frame_duration)
                    
                    time.sleep(0.1)
                else:
                    # Non in pausa, riproduci normalmente
                    current_time = time.time()
                    elapsed = current_time - start_time
                    target_frame = int(elapsed * args.fps)
                    
                    # Verifica limiti
                    if target_frame >= total_frames:
                        if args.loop:
                            # Riparte dall'inizio per loop
                            start_time = time.time()
                            frame_count = 0
                            continue
                        else:
                            # Termina riproduzione
                            break
                    
                    # Ottieni il frame pre-renderizzato
                    frame_buffer = complete_renderer.get_frame(target_frame)
                    if frame_buffer:
                        # Aggiorna contatore
                        frame_count = target_frame
                        
                        # Prepara testo di stato
                        minutes = int(frame_count / args.fps / 60)
                        seconds = int(frame_count / args.fps) % 60
                        time_str = f"{minutes:02d}:{seconds:02d}"
                        progress = int((frame_count / total_frames) * 100)
                        fps_actual = frame_count / max(0.001, elapsed)
                        status_text = f"[{progress}% | {time_str} | {fps_actual:.1f} FPS] {os.path.basename(video_path)}"
                        
                        # Rendering del frame
                        renderer.render_video_frame_mobile(frame_buffer, term_width, term_height, status_text)
                        
                        # Calcola il tempo di wait preciso per sincronizzazione
                        next_frame_time = start_time + ((frame_count + 1) * frame_duration)
                        sleep_time = max(0.0, next_frame_time - time.time())
                        
                        # Gestisci input
                        if frame_count % 5 == 0 and kbhit():
                            key = getch()
                            if key == 'q':
                                clear_screen()
                                print("Riproduzione terminata.")
                                return
                            elif key == 'p' or key == ' ':
                                paused = True
                        
                        # Attendi il tempo giusto per il prossimo frame
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                    else:
                        # Se non troviamo un frame, avanziamo comunque
                        frame_count += 1
            
            # Fine della riproduzione
            clear_screen()
            print("Riproduzione completata.")
            return

def handle_video_input():
    """
    Gestisce l'input utente durante la riproduzione video.
    Ottimizzato per ridurre l'attivazione della tastiera su dispositivi mobili.
    """
    if os.name == 'nt':
        # Windows
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
            if key == 'q':
                return True
            elif key == 'p' or key == ' ':  # Aggiungi supporto per la barra spaziatrice
                return "pause"
    else:
        # Linux/Mac
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1).lower()
            if key == 'q':
                return True
            elif key == 'p' or key == ' ':  # Supporto per barra spaziatrice
                return "pause"
    return False

def is_command_available(command):
    """Controlla se un comando è disponibile nel sistema."""
    try:
        result = subprocess.run(
            ["which" if os.name != "nt" else "where", command],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=False
        )
        return result.returncode == 0
    except:
        return False

def check_dependencies():
    """Verifica le dipendenze necessarie e opzionali."""
    # Verifica PIL/Pillow
    try:
        from PIL import Image
        print("✓ PIL/Pillow: Installato")
    except ImportError:
        print("✗ PIL/Pillow: MANCANTE - Necessario per funzionare!")
        print("  Installa con: pip install pillow")
        return False
    
    # Verifica ffmpeg (opzionale)
    if is_command_available("ffmpeg"):
        print("✓ ffmpeg: Installato (supporto video abilitato)")
    else:
        print("! ffmpeg: Non trovato - Il supporto video non sarà disponibile")
        print("  Per installare ffmpeg:")
        if os.name == "nt":  # Windows
            print("  - Scarica da: https://ffmpeg.org/download.html")
        else:  # Linux/Mac
            print("  - Debian/Ubuntu: sudo apt install ffmpeg")
            print("  - Fedora: sudo dnf install ffmpeg")
            print("  - Arch: sudo pacman -S ffmpeg")
            print("  - Alpine: apk add ffmpeg")
    
    return True

def verify_video_dependencies():
    """
    Verifica che tutte le librerie necessarie per la riproduzione video siano installate.
    
    Returns:
        bool: True se tutte le dipendenze sono soddisfatte, False altrimenti.
    """
    dependencies_ok = True
    
    # Verifica Pillow/PIL
    try:
        from PIL import Image, ImageFile
        print("✓ PIL/Pillow: Disponibile")
    except ImportError:
        print("✗ PIL/Pillow: MANCANTE - Necessaria per la riproduzione video")
        dependencies_ok = False
    
    # Verifica ffmpeg
    try:
        # Usa la funzione get_ffmpeg_paths per ottenere i percorsi corretti
        try:
            from core import get_ffmpeg_paths
            ffmpeg_path, _ = get_ffmpeg_paths()
        except ImportError:
            ffmpeg_path = "ffmpeg"
            
        result = subprocess.run(
            [ffmpeg_path, "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        if result.returncode == 0:
            print("✓ ffmpeg: Disponibile")
        else:
            print("✗ ffmpeg: Installato ma non funzionante")
            dependencies_ok = False
    except FileNotFoundError:
        print("✗ ffmpeg: Non trovato nel PATH")
        print("  • Per istruzioni di installazione, consulta README.md")
        
        # Mostra istruzioni di installazione specifiche per la piattaforma
        if os.name == 'nt':  # Windows
            print("  • Windows: Installa automaticamente con python install_dependencies.py")
            print("  • Gli strumenti verranno installati in C:\\Users\\Condivisi\\DOSVideoPlayer\\tools")
        elif os.path.exists("/etc/debian_version"):  # Debian/Ubuntu/Raspbian
            print("  • Debian/Ubuntu: sudo apt install ffmpeg")
        elif os.path.exists("/etc/alpine-release"):  # Alpine Linux
            print("  • Alpine Linux: apk add ffmpeg")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            print("  • Fedora: sudo dnf install ffmpeg")
        else:
            print("  • Installa ffmpeg tramite il gestore pacchetti del tuo sistema")
            
        dependencies_ok = False
    
    # Verifica moduli opzionali per ottimizzazioni
    try:
        import queue  # Necessario per il buffer asincrono
    except ImportError:
        print("! queue module: Non disponibile (alcune funzionalità potrebbero essere limitate)")
    
    return dependencies_ok

def get_hardware_capability():
    """Determina le capacità hardware del sistema per ottimizzare la riproduzione."""
    try:
        # Prima tenta di usare l'analizzatore di performance
        from performance_analyzer import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        return analyzer.hardware_capability
    except ImportError:
        # Fallback al metodo legacy
        try:
            # Tenta di importare il detector di piattaforma
            from platform_detector import detect_platform
            platform_info = detect_platform()
            
            # Sistemi a basse prestazioni
            if (platform_info.get('is_limited_terminal', False) or 
                platform_info.get('is_alpine', False) or 
                platform_info.get('is_ish', False) or
                platform_info.get('is_termux', False)):
                return "low"
                
            # Sistemi ARM o mobili
            elif platform_info.get('is_arm', False):
                return "medium"
                
            # Sistemi WSL
            elif platform_info.get('is_wsl', False):
                return "medium"
                
            # Default per sistemi standard
            return "high"
        except ImportError:
            # Fallback a controlli base
            import platform
            
            # Controllo per musl/Alpine
            is_musl = False
            try:
                if os.path.exists('/etc/alpine-release'):
                    is_musl = True
            except:
                pass
                
            # Controllo per dispositivi ARM
            is_arm = 'arm' in platform.machine().lower() or 'aarch' in platform.machine().lower()
            
            # Determina capacità
            if is_musl:
                return "low"
            elif is_arm:
                return "medium"
            else:
                return "high"

if __name__ == "__main__":
    main()