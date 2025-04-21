#!/usr/bin/env python3
"""
Modulo per la gestione asincrona dell'input utente durante la riproduzione video.
Permette di gestire i controlli senza bloccare il thread principale.
"""

import os
import sys
import threading
import time

class InputHandler:
    """Gestisce l'input utente in un thread separato."""
    
    def __init__(self, callbacks=None):
        """
        Inizializza l'handler di input.
        
        Args:
            callbacks: Dizionario di callback per vari tipi di input
                       {'quit': funzione, 'pause': funzione, ecc.}
        """
        self.callbacks = callbacks or {}
        self.running = False
        self.thread = None
        
    def start(self):
        """Avvia il thread di gestione input."""
        if self.running:
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._input_thread, daemon=True)
        self.thread.start()
        return True
        
    def stop(self):
        """Ferma il thread di gestione input."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
    def _input_thread(self):
        """Thread worker per monitorare l'input."""
        from core import kbhit, getch
        
        while self.running:
            if kbhit():
                key = getch().lower()
                
                # Gestisci tasti speciali
                if key == 'q' and 'quit' in self.callbacks:
                    self.callbacks['quit'](key)
                elif key in ('p', ' ') and 'pause' in self.callbacks:
                    self.callbacks['pause'](key)
                elif key == '\r' and 'enter' in self.callbacks:
                    self.callbacks['enter'](key)
                elif key in self.callbacks:
                    # Callback diretta per altri tasti
                    self.callbacks[key](key)
                    
            # Dormi brevemente per non sovraccaricare la CPU
            time.sleep(0.05)
            
    def register_callback(self, key, callback):
        """Registra una nuova callback per un tasto specifico."""
        self.callbacks[key] = callback
        
    def remove_callback(self, key):
        """Rimuove una callback."""
        if key in self.callbacks:
            del self.callbacks[key]
