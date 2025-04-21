#!/usr/bin/env python3
"""
Script per risolvere problemi di permessi su Windows per la directory DOSVideoPlayer.
Crea la directory condivisa e configura i permessi necessari.
"""

import os
import sys
import ctypes
import subprocess
import winreg

def is_admin():
    """Verifica se lo script è in esecuzione con privilegi amministrativi."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_shared_directory():
    """Crea la directory condivisa per DOSVideoPlayer."""
    shared_dir = "C:\\Users\\Condivisi\\DOSVideoPlayer"
    tools_dir = os.path.join(shared_dir, "tools")
    cache_dir = os.path.join(shared_dir, "cache")
    
    print(f"Creazione directory: {shared_dir}")
    
    # Prima verifica se la directory esiste già
    if os.path.exists(shared_dir):
        print(f"La directory {shared_dir} esiste già.")
        if os.access(shared_dir, os.W_OK):
            print("Hai permessi di scrittura su questa directory.")
            # Crea le sottodirectory
            try:
                os.makedirs(tools_dir, exist_ok=True)
                os.makedirs(cache_dir, exist_ok=True)
                print("✓ Sottodirectory create con successo")
                return True
            except Exception as e:
                print(f"Errore nella creazione delle sottodirectory: {e}")
                return False
        else:
            print("Non hai permessi di scrittura su questa directory.")
            return False
    
    # La directory non esiste, prova a crearla
    try:
        # Prima crea la directory C:\Users\Condivisi
        os.makedirs("C:\\Users\\Condivisi", exist_ok=True)
        # Poi crea la directory principale e le sottodirectory
        os.makedirs(shared_dir, exist_ok=True)
        os.makedirs(tools_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        print("✓ Directory create con successo")
        return True
    except PermissionError:
        print("✗ Permesso negato per creare le directory.")
        print("Questo è normale se non sei amministratore.")
        return False
    except Exception as e:
        print(f"✗ Errore nella creazione delle directory: {e}")
        return False

def set_directory_permissions():
    """Imposta permessi completi sulla directory per tutti gli utenti."""
    shared_dir = "C:\\Users\\Condivisi\\DOSVideoPlayer"
    
    try:
        # Usa icacls per dare permessi completi a tutti gli utenti
        cmd = f'icacls "{shared_dir}" /grant Everyone:(OI)(CI)F /T'
        print(f"Impostazione permessi: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
        print("✓ Permessi impostati correttamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore nell'impostazione dei permessi: {e}")
        return False

def create_fallback_directory():
    """Crea una directory di fallback nella home utente."""
    home_dir = os.path.expanduser("~")
    fallback_dir = os.path.join(home_dir, ".termimg")
    tools_dir = os.path.join(fallback_dir, "tools")
    cache_dir = os.path.join(fallback_dir, "cache")
    
    print(f"Creazione directory di fallback: {fallback_dir}")
    
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        os.makedirs(tools_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        print("✓ Directory di fallback create con successo")
        return True
    except Exception as e:
        print(f"✗ Errore nella creazione della directory di fallback: {e}")
        return False

def main():
    """Funzione principale."""
    print("=== Fix Permessi Windows per DOSVideoPlayer ===")
    
    # Verifica se siamo su Windows
    if os.name != 'nt':
        print("Questo script è solo per sistemi Windows.")
        return 1
    
    # Verifica se siamo amministratori
    admin = is_admin()
    print(f"Esecuzione come amministratore: {'Sì' if admin else 'No'}")
    
    if not admin:
        print("Per risultati migliori, esegui questo script come amministratore.")
        print("Tenterò comunque di creare le directory e impostare i permessi...")
    
    # Crea la directory condivisa
    if not create_shared_directory():
        print("\nImpossibile creare la directory condivisa principale.")
        print("Creazione directory di fallback...")
        if not create_fallback_directory():
            print("✗ Impossibile creare anche la directory di fallback.")
            return 1
        
        print("\nUsare la directory di fallback per ffmpeg:")
        print(f"  {os.path.join(os.path.expanduser('~'), '.termimg', 'tools')}")
        print("\nEseguire:")
        print("  python install_dependencies.py")
        return 1
    
    # Imposta i permessi
    if admin:
        if not set_directory_permissions():
            print("\nImpossibile impostare i permessi corretti.")
            print("L'applicazione potrebbe funzionare, ma alcuni utenti potrebbero avere problemi di accesso.")
    
    print("\n=== Configurazione completata ===")
    print("\nAdesso puoi installare le dipendenze con:")
    print("  python install_dependencies.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
