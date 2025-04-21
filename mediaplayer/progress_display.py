#!/usr/bin/env python3
"""
Modulo per visualizzare barre di progresso e indicatori di caricamento avanzati.
Fornisce visualizzazioni estetiche per operazioni a lunga durata.
"""

import os
import sys
import time
import threading

class ProgressDisplay:
    """Classe per visualizzare indicatori di progresso avanzati."""
    
    def __init__(self, style="default"):
        """
        Inizializza il display di progresso.
        
        Args:
            style: Stile di visualizzazione ('default', 'fancy', 'simple')
        """
        self.style = style
        self.progress = 0
        self.status = ""
        self.start_time = time.time()
        self.should_stop = False
        self.thread = None
        self.last_update = 0
        self.estimated_time = 0
        self.displayed_rows = 0
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        
        # Animazioni e elementi visuali
        self.animations = {
            "default": self._default_progress,
            "fancy": self._fancy_progress,
            "simple": self._simple_progress,
            "spinner": self._spinner_progress
        }
        
        # Imposta lo stile in base al terminale
        if style == "default":
            # Rileva le capacità del terminale
            if os.name == 'nt':
                # Windows ha supporto limitato per Unicode
                self.style = "simple" 
            else:
                # Rileva se siamo su un terminale minimalista
                if os.environ.get('TERM') == 'dumb':
                    self.style = "simple"
                else:
                    self.style = "fancy"
    
    def start(self, initial_message="Preparazione in corso..."):
        """Avvia la visualizzazione del progresso."""
        self.status = initial_message
        self.start_time = time.time()
        self.should_stop = False
        
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._display_thread, daemon=True)
            self.thread.start()
    
    def update(self, progress, status=None, estimated_time=None):
        """
        Aggiorna il progresso e lo stato.
        
        Args:
            progress: Percentuale di completamento (0-100)
            status: Messaggio di stato opzionale
            estimated_time: Tempo stimato rimanente in secondi
        """
        self.progress = min(100, max(0, progress))
        if status is not None:
            self.status = status
        if estimated_time is not None:
            self.estimated_time = estimated_time
        
        self.last_update = time.time()
    
    def stop(self, final_message=None):
        """
        Ferma la visualizzazione del progresso.
        
        Args:
            final_message: Messaggio finale da visualizzare
        """
        self.should_stop = True
        
        if final_message:
            # Sovrascrivi l'indicatore con il messaggio finale
            progress_width = 50
            elapsed = time.time() - self.start_time
            
            sys.stdout.write("\r\033[K")  # Cancella riga corrente
            sys.stdout.write(f"{final_message} (completato in {elapsed:.1f}s)")
            sys.stdout.write("\n")
            sys.stdout.flush()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
    
    def _display_thread(self):
        """Thread per aggiornare la visualizzazione del progresso."""
        try:
            last_rows = 0
            
            while not self.should_stop:
                # Scegli la funzione di visualizzazione in base allo stile
                display_func = self.animations.get(self.style, self._default_progress)
                
                # Chiama la funzione di visualizzazione
                rows = display_func()
                
                # Aggiorna il numero di righe visualizzate
                self.displayed_rows = rows
                last_rows = rows
                
                # Incrementa l'indice dello spinner
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
                
                # Attendi prima del prossimo aggiornamento
                time.sleep(0.1)
            
            # Pulisci righe alla chiusura
            self._clear_rows(last_rows)
            
        except Exception as e:
            print(f"\nErrore nel thread di visualizzazione: {e}")
    
    def _default_progress(self):
        """Visualizzazione default con spinner e barra di progresso."""
        elapsed = time.time() - self.start_time
        
        # Spinner animato
        spinner = self.spinner_chars[self.spinner_index]
        
        # Barra di progresso
        progress_width = 30
        filled_length = int(progress_width * self.progress / 100)
        bar = '█' * filled_length + '░' * (progress_width - filled_length)
        
        # Tempo stimato
        if self.estimated_time > 0:
            eta_str = f"ETA: {self._format_time(self.estimated_time)}"
        else:
            eta_str = ""
        
        # Formatta la linea di progresso
        progress_line = f"\r\033[K{spinner} [{bar}] {self.progress:.1f}% - {self.status}"
        time_line = f"\r\033[K  Tempo trascorso: {self._format_time(elapsed)} {eta_str}"
        
        # Stampa con pulizia display
        sys.stdout.write(progress_line + "\n" + time_line + "\r")
        sys.stdout.flush()
        
        return 2  # Numero di righe visualizzate
    
    def _fancy_progress(self):
        """Visualizzazione avanzata con elementi grafici migliorati."""
        elapsed = time.time() - self.start_time
        
        # Colori ANSI se supportati
        color_start = "\033[38;5;39m"  # Azzurro
        color_end = "\033[0m"
        title_color = "\033[1;97m"  # Bianco grassetto
        
        # Barra di progresso colorata
        progress_width = 40
        filled_length = int(progress_width * self.progress / 100)
        
        # Sezione completata
        bar_filled = color_start + "█" * filled_length + color_end
        
        # Sezione rimanente
        bar_empty = "░" * (progress_width - filled_length)
        
        # Indicatore completo
        bar = f"[{bar_filled}{bar_empty}]"
        
        # Formatta la linea di progresso
        title = title_color + "Elaborazione" + color_end
        progress_line = f"\r\033[K{title}: {bar} {self.progress:.1f}%"
        status_line = f"\r\033[K  {self.status}"
        
        # Informazioni temporali
        time_info = f"\r\033[K  Tempo: {self._format_time(elapsed)}"
        if self.estimated_time > 0:
            time_info += f" • Rimanente: {self._format_time(self.estimated_time)}"
        
        # Stampa con caratteri fancy
        sys.stdout.write(progress_line + "\n" + status_line + "\n" + time_info + "\r")
        sys.stdout.flush()
        
        return 3  # Numero di righe visualizzate
    
    def _simple_progress(self):
        """Visualizzazione semplice per terminali con supporto limitato."""
        elapsed = time.time() - self.start_time
        
        # Barra di progresso semplice
        progress_width = 40
        filled_length = int(progress_width * self.progress / 100)
        bar = '[' + '#' * filled_length + '-' * (progress_width - filled_length) + ']'
        
        # Formatta la linea di progresso
        progress_line = f"\r{bar} {self.progress:.1f}% - {self.status}"
        time_line = f"\rTempo: {elapsed:.1f}s"
        
        # Visualizza su una singola riga per supporto massimo
        sys.stdout.write(progress_line + "\r")
        sys.stdout.flush()
        
        return 1  # Numero di righe visualizzate
    
    def _spinner_progress(self):
        """Solo spinner con messaggio di stato."""
        spinner = self.spinner_chars[self.spinner_index]
        
        # Formatta la linea di progresso
        progress_line = f"\r\033[K{spinner} {self.status} ({self.progress:.1f}%)"
        
        sys.stdout.write(progress_line + "\r")
        sys.stdout.flush()
        
        return 1  # Numero di righe visualizzate
    
    def _clear_rows(self, rows):
        """Pulisce un numero di righe dallo schermo."""
        for _ in range(rows):
            sys.stdout.write("\033[1A")  # Sposta il cursore su una riga
            sys.stdout.write("\033[K")   # Cancella la riga
        sys.stdout.flush()
    
    def _format_time(self, seconds):
        """Formatta il tempo in formato leggibile."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = seconds % 60
            return f"{minutes}m {int(seconds)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
