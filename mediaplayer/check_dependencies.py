#!/usr/bin/env python3
"""
Utility per verificare che tutte le dipendenze necessarie siano installate.
Utile per diagnosticare problemi con TermImg prima dell'esecuzione.
"""

import os
import sys
import subprocess
import platform

def check_system_info():
    """Mostra informazioni sul sistema."""
    print("=== Informazioni di Sistema ===")
    print(f"Sistema operativo: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Architettura: {platform.machine()}")
    
    # Verifica se siamo su un sistema con musl
    is_musl = False
    if platform.system() == "Linux":
        try:
            ldd_output = subprocess.check_output(['ldd', '--version'], stderr=subprocess.STDOUT, text=True)
            is_musl = 'musl' in ldd_output.lower()
        except:
            try:
                # Alpine Linux
                if os.path.exists('/etc/alpine-release'):
                    is_musl = True
            except:
                pass
    
    if is_musl:
        print("Sistema basato su musl rilevato (es. Alpine Linux)")
    
    # Verifica ambiente
    in_venv = sys.prefix != sys.base_prefix
    print(f"Ambiente virtuale: {'Sì' if in_venv else 'No'}")
    
    print()
    return is_musl

def check_python_packages():
    """Verifica i pacchetti Python necessari."""
    print("=== Dipendenze Python ===")
    
    # Lista di pacchetti da verificare
    packages = {
        "PIL": {
            "name": "Pillow/PIL",
            "required": True,
            "module": "PIL"
        },
        "requests": {
            "name": "requests",
            "required": False,
            "module": "requests"
        },
        "cairosvg": {
            "name": "CairoSVG",
            "required": False,
            "module": "cairosvg"
        }
    }
    
    for package_key, package_info in packages.items():
        try:
            __import__(package_info["module"])
            print(f"✓ {package_info['name']}: Installato")
        except ImportError:
            status = "MANCANTE" if package_info["required"] else "Non trovato (opzionale)"
            print(f"{'✗' if package_info['required'] else '!'} {package_info['name']}: {status}")
    
    print()
    return True

def check_external_tools():
    """Verifica gli strumenti esterni necessari."""
    print("=== Strumenti Esterni ===")
    
    # Importa funzione per ottenere i percorsi di ffmpeg
    try:
        from core import get_ffmpeg_paths
        ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
    except ImportError:
        ffmpeg_path, ffprobe_path = "ffmpeg", "ffprobe"
    
    # Lista di comandi da verificare
    commands = [
        {
            "name": "ffmpeg",
            "command": f"{ffmpeg_path} -version",
            "required": True,
            "info": "Necessario per riproduzione video"
        },
        {
            "name": "ffprobe",
            "command": f"{ffprobe_path} -version",
            "required": True,
            "info": "Necessario per metadati video"
        },
        {
            "name": "Inkscape",
            "command": "inkscape --version",
            "required": False,
            "info": "Opzionale per supporto SVG"
        },
        {
            "name": "rsvg-convert",
            "command": "rsvg-convert --version",
            "required": False,
            "info": "Opzionale per supporto SVG"
        }
    ]
    
    all_ok = True
    
    for cmd_info in commands:
        try:
            if " " in cmd_info["command"]:
                # Gestisci comandi con argomenti
                cmd_parts = cmd_info["command"].split()
                process = subprocess.run(
                    cmd_parts,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
            else:
                process = subprocess.run(
                    [cmd_info["command"]], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    shell=True
                )
            
            if process.returncode == 0:
                print(f"✓ {cmd_info['name']}: Installato")
            else:
                status = "Non funzionante" if cmd_info["required"] else "Non funzionante (opzionale)"
                print(f"{'✗' if cmd_info['required'] else '!'} {cmd_info['name']}: {status}")
                if cmd_info["required"]:
                    all_ok = False
        except FileNotFoundError:
            status = "MANCANTE" if cmd_info["required"] else "Non trovato (opzionale)"
            print(f"{'✗' if cmd_info['required'] else '!'} {cmd_info['name']}: {status}")
            if cmd_info["required"]:
                all_ok = False
        except Exception as e:
            print(f"! {cmd_info['name']}: Errore durante la verifica: {e}")
            if cmd_info["required"]:
                all_ok = False
    
    print()
    return all_ok

def show_installation_instructions():
    """Mostra istruzioni di installazione per le dipendenze mancanti."""
    print("=== Istruzioni di Installazione ===")
    print("Per installare tutte le dipendenze necessarie, esegui:")
    print("  python install_dependencies.py")
    print("\nPer installare manualmente:")
    
    # Istruzioni per Pillow
    print("\nPillow/PIL:")
    print("  pip install pillow")
    
    # Istruzioni per ffmpeg
    print("\nffmpeg:")
    system = platform.system()
    if system == "Windows":
        print("  Gli strumenti verranno installati automaticamente in C:\\Users\\Condivisi\\DOSVideoPlayer")
        print("  Esegui: python install_dependencies.py")
    elif system == "Darwin":  # macOS
        print("  brew install ffmpeg")
    elif os.path.exists("/etc/debian_version"):  # Debian/Ubuntu
        print("  sudo apt install ffmpeg")
    elif os.path.exists("/etc/alpine-release"):  # Alpine
        print("  apk add ffmpeg")
    elif os.path.exists("/etc/fedora-release"):  # Fedora
        print("  sudo dnf install ffmpeg")
    else:
        print("  Installa ffmpeg tramite il gestore pacchetti del tuo sistema")
    
    print("\nPer supporto SVG (opzionale), installa uno tra:")
    print("  pip install cairosvg")
    print("  o installa Inkscape o librsvg")
    
    print()

def main():
    """Funzione principale."""
    is_musl = check_system_info()
    python_ok = check_python_packages()
    tools_ok = check_external_tools()
    
    print("=== Riepilogo ===")
    if python_ok and tools_ok:
        print("✓ Tutte le dipendenze necessarie sono installate!")
        print("  TermImg dovrebbe funzionare correttamente.")
    else:
        print("✗ Alcune dipendenze necessarie sono mancanti.")
        show_installation_instructions()
    
    return 0 if (python_ok and tools_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
