#!/usr/bin/env python3
"""
Utility per verificare e riparare l'installazione di ffmpeg.
Questo script controlla la disponibilità di ffmpeg e ffprobe e fornisce assistenza 
per l'installazione se mancanti.
"""
import os
import sys
import subprocess
import platform
import tempfile
import shutil
from urllib.request import urlretrieve

def find_ffmpeg_locations():
    """Cerca ffmpeg in varie posizioni comuni."""
    locations = []
    
    # Directory dell'utente
    user_dir = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
    
    if os.name == 'nt':
        # Percorsi comuni su Windows
        search_paths = [
            user_dir,
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'ffmpeg', 'bin'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'ffmpeg', 'bin'),
            os.path.join('C:\\', 'ffmpeg', 'bin'),
            os.path.join('C:\\Users\\Condivisi\\DOSVideoPlayer\\tools'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')
        ]
        
        # Aggiungi percorsi dalla variabile d'ambiente PATH
        if 'PATH' in os.environ:
            for path_dir in os.environ['PATH'].split(os.pathsep):
                if os.path.exists(path_dir):
                    search_paths.append(path_dir)
        
        # Verifica ciascun percorso
        for path in search_paths:
            ffmpeg_path = os.path.join(path, 'ffmpeg.exe')
            ffprobe_path = os.path.join(path, 'ffprobe.exe')
            
            if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
                locations.append((ffmpeg_path, ffprobe_path))
    else:
        # Percorsi comuni su Linux/macOS
        search_paths = [
            user_dir,
            '/usr/bin',
            '/usr/local/bin',
            '/opt/local/bin',
            '/opt/ffmpeg/bin',
            '/app/bin',  # Percorsi Termux/Android
            os.path.expanduser('~/bin'),
            os.path.dirname(os.path.abspath(__file__))
        ]
        
        # Verifica ciascun percorso
        for path in search_paths:
            ffmpeg_path = os.path.join(path, 'ffmpeg')
            ffprobe_path = os.path.join(path, 'ffprobe')
            
            if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
                locations.append((ffmpeg_path, ffprobe_path))
    
    return locations

def test_ffmpeg(ffmpeg_path):
    """Testa una specifica installazione di ffmpeg."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            # Estrai versione dalle prime righe
            version_info = result.stdout.splitlines()[0]
            return True, version_info
        else:
            return False, f"Errore {result.returncode}: {result.stderr}"
    except Exception as e:
        return False, f"Eccezione: {str(e)}"

def fix_ffmpeg_installation():
    """Tenta di riparare l'installazione di ffmpeg."""
    if os.name != 'nt':
        print("La riparazione automatica è supportata solo su Windows.")
        print("Su Linux/macOS, installa ffmpeg con il gestore pacchetti del sistema.")
        return False
    
    print("Avvio riparazione ffmpeg...")
    
    try:
        # Crea directory utente per ffmpeg
        user_dir = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
        os.makedirs(user_dir, exist_ok=True)
        
        # URL per download
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        
        # Directory temporanea per download
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "ffmpeg.zip")
        
        print(f"Download di ffmpeg da {ffmpeg_url}...")
        urlretrieve(ffmpeg_url, zip_path)
        
        print("Estrazione archivio...")
        from zipfile import ZipFile
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Trova la directory bin nell'archivio estratto
        bin_dir = None
        for root, dirs, files in os.walk(temp_dir):
            if "ffmpeg.exe" in files and "ffprobe.exe" in files:
                bin_dir = root
                break
        
        if not bin_dir:
            print("Errore: impossibile trovare ffmpeg.exe nell'archivio.")
            return False
        
        # Copia i file nella directory dell'utente
        print(f"Installazione in {user_dir}...")
        ffmpeg_dest = os.path.join(user_dir, "ffmpeg.exe")
        ffprobe_dest = os.path.join(user_dir, "ffprobe.exe")
        
        shutil.copy2(os.path.join(bin_dir, "ffmpeg.exe"), ffmpeg_dest)
        shutil.copy2(os.path.join(bin_dir, "ffprobe.exe"), ffprobe_dest)
        
        # Pulisci i file temporanei
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Aggiorna PATH per questa sessione
        os.environ["PATH"] = user_dir + os.pathsep + os.environ.get("PATH", "")
        
        print("✓ Installazione completata con successo!")
        print(f"ffmpeg installato in: {user_dir}")
        
        # Testa l'installazione
        success, version = test_ffmpeg(ffmpeg_dest)
        if success:
            print(f"ffmpeg funziona correttamente: {version}")
            return True
        else:
            print(f"Avviso: ffmpeg è stato installato ma il test ha fallito: {version}")
            return False
            
    except Exception as e:
        print(f"Errore durante la riparazione: {e}")
        print("Riparazione fallita.")
        return False

def main():
    """Funzione principale."""
    print("=== Verifica installazione ffmpeg ===")
    print(f"Sistema: {platform.system()} {platform.release()}")
    print(f"Directory corrente: {os.getcwd()}")
    print()
    
    # Cerca ffmpeg in varie posizioni
    locations = find_ffmpeg_locations()
    
    if not locations:
        print("ffmpeg non trovato nel sistema.")
        
        # Chiedi conferma per riparare
        if os.name == 'nt':
            print("Vuoi scaricare e installare ffmpeg? (s/n)")
            choice = input().lower()
            
            if choice in ('s', 'y', 'si', 'yes'):
                if fix_ffmpeg_installation():
                    print("\nffmpeg ora è installato e funzionante.")
                    sys.exit(0)
                else:
                    print("\nImpossibile installare ffmpeg automaticamente.")
                    print("Scarica ffmpeg manualmente da: https://ffmpeg.org/download.html")
                    sys.exit(1)
        else:
            print("Su Linux/macOS, installa ffmpeg con il gestore pacchetti:")
            print("  • Debian/Ubuntu: sudo apt install ffmpeg")
            print("  • macOS: brew install ffmpeg")
            print("  • Alpine: apk add ffmpeg")
            sys.exit(1)
    else:
        print(f"Trovate {len(locations)} installazioni di ffmpeg:")
        
        for i, (ffmpeg_path, ffprobe_path) in enumerate(locations):
            print(f"\n{i+1}. ffmpeg: {ffmpeg_path}")
            print(f"   ffprobe: {ffprobe_path}")
            
            # Testa questa installazione
            success, result = test_ffmpeg(ffmpeg_path)
            if success:
                print(f"   ✓ Funzionante: {result}")
            else:
                print(f"   ✗ Non funzionante: {result}")
        
        # Verifica se almeno una installazione è funzionante
        working_installations = [(i, loc) for i, loc in enumerate(locations) 
                               if test_ffmpeg(loc[0])[0]]
        
        if working_installations:
            print("\n✓ ffmpeg è disponibile e funzionante.")
            best_installation = working_installations[0][1]
            print(f"Installazione consigliata: {best_installation[0]}")
            sys.exit(0)
        else:
            print("\n✗ Nessuna installazione funzionante trovata.")
            
            if os.name == 'nt':
                print("\nVuoi tentare la riparazione? (s/n)")
                choice = input().lower()
                
                if choice in ('s', 'y', 'si', 'yes'):
                    if fix_ffmpeg_installation():
                        print("\nffmpeg ora è installato e funzionante.")
                        sys.exit(0)
                    else:
                        sys.exit(1)
            sys.exit(1)

if __name__ == "__main__":
    main()
