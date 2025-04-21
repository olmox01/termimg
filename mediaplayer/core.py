import os
import sys
import shutil
import tempfile
import json
import time

# Per gestione input cross-platform
if os.name == 'nt':  # Windows
    import msvcrt
else:  # Linux/Mac
    import select
    import sys
    import tty
    import termios

# Configurazione globale
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".termimg")

# Modifica delle directory temporanee in base al sistema operativo
if os.name == 'nt':  # Windows
    # Prima prova con la directory utente come predefinita
    USER_TOOLS_DIR = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
    USER_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".termimg", "cache")
    
    # Crea le directory dell'utente (queste dovrebbero sempre funzionare)
    try:
        os.makedirs(USER_TOOLS_DIR, exist_ok=True)
        os.makedirs(USER_CACHE_DIR, exist_ok=True)
    except Exception:
        pass
    
    # Prova a usare la directory condivisa se esiste o se abbiamo permessi
    try:
        SHARED_DIR = os.path.join("C:\\Users\\Condivisi\\DOSVideoPlayer")
        TOOLS_DIR = os.path.join(SHARED_DIR, "tools")
        CACHE_DIR = os.path.join(SHARED_DIR, "cache")
        
        # Verifica se la directory esiste già
        if os.path.exists(SHARED_DIR):
            # Se esiste, verificare i permessi di scrittura
            if os.access(SHARED_DIR, os.W_OK):
                # Ok, possiamo usare questa directory
                pass
            else:
                # Usa le directory dell'utente
                TOOLS_DIR = USER_TOOLS_DIR
                CACHE_DIR = USER_CACHE_DIR
        else:
            # La directory non esiste, prova a crearla
            try:
                os.makedirs(TOOLS_DIR, exist_ok=True)
                os.makedirs(CACHE_DIR, exist_ok=True)
            except (PermissionError, OSError):
                # Fallback alle directory dell'utente se non possiamo creare quelle condivise
                TOOLS_DIR = USER_TOOLS_DIR
                CACHE_DIR = USER_CACHE_DIR
    except:
        # In caso di errori, usa le directory dell'utente
        TOOLS_DIR = USER_TOOLS_DIR
        CACHE_DIR = USER_CACHE_DIR
else:  # Linux/Mac
    # Su Linux/Mac, usa /media/termimg se disponibile, altrimenti .termimg nella home
    if os.path.exists('/media') and os.access('/media', os.W_OK):
        CACHE_DIR = "/media/termimg/cache"
    else:
        CACHE_DIR = os.path.join(os.path.expanduser("~"), ".termimg", "cache")
    TOOLS_DIR = None  # Non necessario su Linux
    USER_TOOLS_DIR = None  # Non necessario su Linux

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
REFRESH_LOCK_FILE = os.path.join(CONFIG_DIR, "refresh.lock")

# Caratteri per renderizzazione
CHARS = {
    'basic': {
        'empty': ' ',
        'full': '█',
        'half_top': '▀',
        'half_bottom': '▄',
        'left': '▌',
        'right': '▐',
        'three_quarters': '▓',
        'half': '▒',
        'quarter': '░'
    }
}

# Formati supportati
IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif']
VIDEO_FORMATS = [
    '.mp4', '.avi', '.mkv', '.webm', '.mov', '.flv', '.wmv', '.mpg', '.mpeg',
    '.ts', '.m4v', '.3gp', '.vob', '.ogv', '.asf', '.m2ts', '.mts'
]

def ensure_dirs():
    """Crea le directory necessarie se non esistono."""
    try:
        # Dichiarazione global da mettere all'inizio della funzione
        global CACHE_DIR, TOOLS_DIR
        
        # Crea la directory di configurazione
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Crea le directory di cache
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(os.path.join(CACHE_DIR, "video_frames"), exist_ok=True)
        os.makedirs(os.path.join(CACHE_DIR, "extracted_frames"), exist_ok=True)
        os.makedirs(os.path.join(CACHE_DIR, "temp_renders"), exist_ok=True)
        
        # Su Windows, crea anche le directory per gli strumenti
        if os.name == 'nt' and TOOLS_DIR != USER_TOOLS_DIR:
            try:
                os.makedirs(TOOLS_DIR, exist_ok=True)
            except (PermissionError, OSError):
                # Se fallisce, usa la directory dell'utente
                TOOLS_DIR = USER_TOOLS_DIR
                os.makedirs(TOOLS_DIR, exist_ok=True)
    except PermissionError:
        print(f"AVVISO: Non hai i permessi di scrittura per creare o accedere alle directory necessarie.")
        print(f"Utilizzo directory nella home dell'utente.")
        
        # Utilizza sempre le directory dell'utente in caso di problemi
        backup_dir = os.path.join(os.path.expanduser("~"), ".termimg", "cache")
        tools_dir = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
        
        # Crea le directory di fallback
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(tools_dir, exist_ok=True)
        os.makedirs(os.path.join(backup_dir, "video_frames"), exist_ok=True)
        os.makedirs(os.path.join(backup_dir, "extracted_frames"), exist_ok=True)
        os.makedirs(os.path.join(backup_dir, "temp_renders"), exist_ok=True)
        
        # Aggiorna le variabili globali
        CACHE_DIR = backup_dir
        if os.name == 'nt':
            TOOLS_DIR = tools_dir
            
        print(f"Directory di cache: {CACHE_DIR}")
        if os.name == 'nt':
            print(f"Directory strumenti: {TOOLS_DIR}")
    
    return None  # Non c'è più bisogno di restituire un percorso alternativo

def clear_screen():
    """Pulisce lo schermo del terminale."""
    os.system('cls' if os.name == 'nt' else 'clear')

def is_refresh_requested():
    """Verifica se è stato richiesto un refresh."""
    return os.path.exists(REFRESH_LOCK_FILE)

def set_refresh_flag():
    """Imposta il flag di refresh."""
    with open(REFRESH_LOCK_FILE, 'w') as f:
        f.write(str(time.time()))

def clear_refresh_flag():
    """Rimuove il flag di refresh."""
    if os.path.exists(REFRESH_LOCK_FILE):
        os.remove(REFRESH_LOCK_FILE)

def kbhit():
    """Controlla se è stato premuto un tasto senza bloccare l'esecuzione."""
    if os.name == 'nt':  # Windows
        return msvcrt.kbhit()
    else:  # Linux/Mac
        dr, dw, de = select.select([sys.stdin], [], [], 0)
        return dr != []

def getch():
    """Legge un carattere senza visualizzarlo e senza attendere Enter."""
    if os.name == 'nt':  # Windows
        return msvcrt.getch().decode('utf-8', errors='ignore')
    else:  # Linux/Mac
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

def save_session(args):
    """Salva la sessione corrente per riavviare il programma con gli stessi parametri."""
    config = {
        'image_paths': args.file_paths,  # Cambio da args.image_paths a args.file_paths
        'args': vars(args),
        'timestamp': time.time()
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_session():
    """Carica la sessione precedente."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def cleanup_old_cache(max_age=86400):
    """Pulisce i file temporanei più vecchi di max_age secondi."""
    now = time.time()
    for filename in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < now - max_age:
            try:
                os.remove(file_path)
            except:
                pass
    
    # Rimuovi il flag di refresh se esiste
    clear_refresh_flag()

def is_image_file(filepath):
    """Verifica se il file è un'immagine basandosi sull'estensione."""
    if not os.path.isfile(filepath):
        return False
    extension = os.path.splitext(filepath)[1].lower()
    return extension in IMAGE_FORMATS

def is_video_file(filepath):
    """Verifica se il file è un video basandosi sull'estensione."""
    if not os.path.isfile(filepath):
        return False
    extension = os.path.splitext(filepath)[1].lower()
    return extension in VIDEO_FORMATS

def get_file_type(filepath):
    """
    Determina il tipo di file basandosi sull'estensione.
    
    Returns:
        'image', 'video' o None se non riconosciuto
    """
    if is_image_file(filepath):
        return 'image'
    elif is_video_file(filepath):
        return 'video'
    return None

# Funzione per ottenere i percorsi di ffmpeg e ffprobe
def get_ffmpeg_paths():
    """
    Restituisce i percorsi di ffmpeg e ffprobe in base al sistema operativo.
    
    Returns:
        tuple: (ffmpeg_path, ffprobe_path)
    """
    if os.name == 'nt':  # Windows
        # Controlla prima nella directory fallback dell'utente (.termimg/tools)
        ffmpeg_user = os.path.join(USER_TOOLS_DIR, "ffmpeg.exe")
        ffprobe_user = os.path.join(USER_TOOLS_DIR, "ffprobe.exe")
        
        if os.path.exists(ffmpeg_user) and os.path.exists(ffprobe_user):
            return ffmpeg_user, ffprobe_user
            
        # Poi controlla nella directory strumenti condivisa
        ffmpeg_exe = os.path.join(TOOLS_DIR, "ffmpeg.exe")
        ffprobe_exe = os.path.join(TOOLS_DIR, "ffprobe.exe")
        
        if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
            return ffmpeg_exe, ffprobe_exe
    
    # In ogni altro caso, usa il comando diretto (ricerca nel PATH)
    return "ffmpeg", "ffprobe"
