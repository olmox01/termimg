#!/usr/bin/env python3
"""
Script per l'installazione delle dipendenze necessarie per TermImg.
Rileva il sistema operativo e installa i pacchetti richiesti.
"""

import subprocess
import sys
import os
import platform
import tempfile
import shutil
from urllib.request import urlretrieve
from zipfile import ZipFile

def get_python_version():
    """Restituisce la versione di Python in uso."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

def get_system_info():
    """Raccoglie e mostra informazioni sul sistema."""
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    
    print(f"Sistema operativo: {system} {release} ({machine})")
    print(f"Python: {get_python_version()}")
    
    # Verifica se siamo in un ambiente virtuale
    in_venv = sys.prefix != sys.base_prefix
    print(f"Ambiente virtuale: {'Sì' if in_venv else 'No'}")
    
    # Verifica sistema MUSL (Alpine Linux)
    is_musl = False
    if system == "Linux":
        try:
            ldd_output = subprocess.check_output(['ldd', '--version'], stderr=subprocess.STDOUT, text=True)
            is_musl = 'musl' in ldd_output.lower()
        except:
            # Se ldd --version fallisce, potrebbe essere musl
            try:
                with open("/etc/alpine-release") as f:
                    is_musl = True
            except:
                pass
    
    if is_musl:
        print("Rilevata libreria MUSL (probabile Alpine Linux o iSH)")
    
    return system, machine, in_venv, is_musl

def install_package(package):
    """Installa un pacchetto Python con pip e gestisce errori."""
    try:
        # Verifica se il pacchetto è già installato
        try:
            __import__(package.split('==')[0])
            print(f"✓ {package} già installato.")
            return True
        except ImportError:
            pass

        print(f"Installazione di {package}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", package],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"✓ {package} installato con successo.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore durante l'installazione di {package}")
        print(f"  {e}")
        return False

def install_ffmpeg_windows():
    """Scarica e installa ffmpeg su Windows nella directory utente."""
    print("Installazione di ffmpeg per Windows...")
    
    # Usa direttamente la directory dell'utente per evitare problemi di permessi
    target_dir = os.path.join(os.path.expanduser("~"), ".termimg", "tools")
    
    try:
        # Crea la directory di destinazione
        os.makedirs(target_dir, exist_ok=True)
        
        # Verifica che abbiamo i permessi di scrittura
        if not os.access(target_dir, os.W_OK):
            print(f"AVVISO: Non hai i permessi per scrivere in {target_dir}")
            print("Impossibile installare ffmpeg.")
            return False
        
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "ffmpeg.zip")
        extract_dir = os.path.join(temp_dir, "extract")
        
        # Scarica ffmpeg
        print("Download di ffmpeg...")
        urlretrieve(ffmpeg_url, zip_path)
        
        # Estrai archivio
        print("Estrazione dei file...")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Trova il percorso della directory bin
        bin_dir = None
        for root, dirs, files in os.walk(extract_dir):
            if "ffmpeg.exe" in files and "ffprobe.exe" in files:
                bin_dir = root
                break
                
        if not bin_dir:
            print("✗ Impossibile trovare ffmpeg.exe e ffprobe.exe nell'archivio.")
            return False
        
        # Crea directory destinazione
        os.makedirs(target_dir, exist_ok=True)
        
        # Copia i file necessari
        for file in ["ffmpeg.exe", "ffprobe.exe"]:
            src = os.path.join(bin_dir, file)
            dst = os.path.join(target_dir, file)
            shutil.copy2(src, dst)
            
        # Aggiorna PATH per questa sessione
        user_path = os.environ.get("PATH", "").split(os.pathsep)
        if target_dir not in user_path:
            new_path = os.pathsep.join([*user_path, target_dir])
            os.environ["PATH"] = new_path
            
        print(f"✓ ffmpeg installato in: {target_dir}")
        
        # Verifica che l'installazione abbia avuto successo
        try:
            result = subprocess.run([os.path.join(target_dir, "ffmpeg.exe"), "-version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            if result.returncode == 0:
                print("✓ ffmpeg funziona correttamente")
            else:
                print("! ffmpeg potrebbe non funzionare correttamente")
        except:
            print("! Errore nel verificare l'installazione di ffmpeg")
        
        return True
        
    except Exception as e:
        print(f"✗ Errore durante l'installazione di ffmpeg: {e}")
        return False
    finally:
        # Pulizia
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def check_svg_tools():
    """Verifica la disponibilità degli strumenti per il supporto SVG."""
    svg_support = {'cairosvg': False, 'inkscape': False, 'librsvg': False}
    
    # Controlla CairoSVG
    try:
        import cairosvg
        svg_support['cairosvg'] = True
        print("✓ CairoSVG: Installato")
    except ImportError:
        print("! CairoSVG: Non trovato (opzionale per supporto SVG)")
    
    # Controlla Inkscape
    try:
        result = subprocess.run(['inkscape', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            svg_support['inkscape'] = True
            print("✓ Inkscape: Installato")
        else:
            print("! Inkscape: Non trovato (opzionale per supporto SVG)")
    except FileNotFoundError:
        print("! Inkscape: Non trovato (opzionale per supporto SVG)")
    
    # Controlla librsvg (rsvg-convert)
    try:
        result = subprocess.run(['rsvg-convert', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            svg_support['librsvg'] = True
            print("✓ librsvg (rsvg-convert): Installato")
        else:
            print("! librsvg (rsvg-convert): Non trovato (opzionale per supporto SVG)")
    except FileNotFoundError:
        print("! librsvg (rsvg-convert): Non trovato (opzionale per supporto SVG)")
    
    return svg_support

def main():
    """Installa tutte le dipendenze necessarie per il programma."""
    print("=== Script di installazione dipendenze TermImg ===\n")
    
    # Informazioni sul sistema
    system, machine, in_venv, is_musl = get_system_info()
    print()
    
    # Pacchetti Python da installare
    python_packages = [
        "pillow",        # Elaborazione immagini
        "requests"       # Per download opzionali
    ]
    
    # Installa pacchetti Python
    print("Installazione pacchetti Python...")
    for package in python_packages:
        install_package(package)
    
    # Verifica supporto SVG
    print("\nVerifica strumenti SVG...")
    svg_support = check_svg_tools()
    
    if not any(svg_support.values()):
        print("\nNessun supporto SVG trovato. Per aggiungere supporto SVG:")
        
        # Su sistemi MUSL (Alpine), cairosvg potrebbe essere problematico
        if not is_musl:
            print("- Per utilizzare CairoSVG: pip install cairosvg")
        
        if system == "Windows":
            print("- Per utilizzare Inkscape: scaricalo da https://inkscape.org/")
        elif system == "Linux":
            print("- Per utilizzare librsvg: installa il pacchetto")
            print("  • Debian/Ubuntu: sudo apt install librsvg2-bin")
            print("  • Alpine: apk add librsvg")
            print("  • Fedora: sudo dnf install librsvg2-tools")
        print()
    
    # Installa ffmpeg su Windows o mostra istruzioni
    if system == "Windows":
        print("\nVerifica ffmpeg per supporto video...")
        try:
            result = subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                print("✓ ffmpeg già installato")
            else:
                print("! ffmpeg non trovato")
                install_ffmpeg_windows()
        except FileNotFoundError:
            print("! ffmpeg non trovato")
            install_ffmpeg_windows()
    else:
        # Su Linux/Mac mostra istruzioni per installare ffmpeg
        print("\nPer utilizzare le funzionalità video, installa ffmpeg:")
        if system == "Darwin":  # macOS
            print("  brew install ffmpeg")
        elif is_musl:  # Alpine Linux
            print("  apk add ffmpeg")
        elif os.path.exists("/etc/debian_version"):  # Debian/Ubuntu
            print("  sudo apt install ffmpeg")
        elif os.path.exists("/etc/fedora-release"):  # Fedora
            print("  sudo dnf install ffmpeg")
        else:
            print("  Installa ffmpeg tramite il gestore pacchetti del tuo sistema")
    
    print("\n=== Installazione completata ===")
    print("\nPuoi avviare TermImg con:")
    print("python run.py <file_immagine_o_video>")

if __name__ == "__main__":
    main()
