#!/usr/bin/env python3
"""
Utility per rinominare file video rimuovendo caratteri problematici.
Questo script risolve problemi con file che hanno nomi contenenti caratteri speciali
che possono causare errori durante l'elaborazione con ffmpeg.
"""

import os
import sys
import re
import shutil

def sanitize_filename(filename):
    """
    Rimuove caratteri problematici dal nome del file, mantenendo l'estensione.
    """
    # Separa il nome file dall'estensione
    name, ext = os.path.splitext(filename)
    
    # Rimuovi caratteri speciali, mantieni lettere, numeri, spazi, _ e -
    sanitized = re.sub(r'[^\w\s\-\.]', '_', name)
    
    # Sostituisci spazi multipli con un singolo spazio
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Rimuovi spazi iniziali e finali
    sanitized = sanitized.strip()
    
    # Ricomponi il nome file con l'estensione originale
    return sanitized + ext

def fix_video_filename(video_path, copy=False):
    """
    Rinomina o copia un file video con un nome sanitizzato.
    
    Args:
        video_path: Percorso del file video da rinominare
        copy: Se True, crea una copia invece di rinominare
    
    Returns:
        Il nuovo percorso del file o None se non è stato modificato
    """
    if not os.path.exists(video_path):
        print(f"Errore: file non trovato: {video_path}")
        return None
        
    # Ottieni directory e nome file
    directory = os.path.dirname(video_path)
    filename = os.path.basename(video_path)
    
    # Sanitizza il nome file
    new_filename = sanitize_filename(filename)
    
    # Se il nome file è uguale, non fare nulla
    if new_filename == filename:
        print(f"Il file ha già un nome valido: {video_path}")
        return None
    
    # Costruisci il nuovo percorso
    new_path = os.path.join(directory, new_filename)
    
    # Verifica se esiste già un file con questo nome
    if os.path.exists(new_path):
        base, ext = os.path.splitext(new_filename)
        counter = 1
        while os.path.exists(new_path):
            new_filename = f"{base}_{counter}{ext}"
            new_path = os.path.join(directory, new_filename)
            counter += 1
    
    # Rinomina o copia il file
    try:
        if copy:
            shutil.copy2(video_path, new_path)
            print(f"File copiato: {video_path} -> {new_path}")
        else:
            shutil.move(video_path, new_path)
            print(f"File rinominato: {video_path} -> {new_path}")
        return new_path
    except Exception as e:
        print(f"Errore durante la modifica del nome del file: {e}")
        return None

def main():
    """Funzione principale dello script."""
    # Controlla argomenti
    if len(sys.argv) < 2:
        print("Uso: fix_video_names.py <file_video> [--copy]")
        print("     fix_video_names.py <dir> [--copy] [--recursive]")
        print("\nOpzioni:")
        print("  --copy       Crea copia con nome sicuro invece di rinominare")
        print("  --recursive  Processa tutti i file nelle sottodirectory")
        return
    
    # Analizza argomenti
    path = sys.argv[1]
    copy_mode = "--copy" in sys.argv
    recursive = "--recursive" in sys.argv
    
    # Verifica se il percorso esiste
    if not os.path.exists(path):
        print(f"Errore: percorso non trovato: {path}")
        return
    
    # Se è un file
    if os.path.isfile(path):
        fix_video_filename(path, copy=copy_mode)
        return
    
    # Se è una directory
    if os.path.isdir(path):
        print(f"Elaborazione directory: {path}")
        # Ottieni lista di estensioni video
        video_exts = ['.mp4', '.avi', '.mkv', '.webm', '.mov', '.flv', '.wmv', '.mpg', '.mpeg']
        
        # Funzione per processare una directory
        def process_dir(directory):
            count = 0
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                # Processa sottodirectory se richiesto
                if recursive and os.path.isdir(filepath):
                    count += process_dir(filepath)
                    
                # Processa file video
                if os.path.isfile(filepath) and os.path.splitext(filename)[1].lower() in video_exts:
                    if fix_video_filename(filepath, copy=copy_mode):
                        count += 1
            return count
        
        # Avvia l'elaborazione
        total_fixed = process_dir(path)
        print(f"Elaborazione completata. File modificati: {total_fixed}")

if __name__ == "__main__":
    main()
