#!/usr/bin/env python3
"""
Modulo per monitorare l'utilizzo della memoria del processo.
Fornisce funzioni per verificare se è sicuro procedere con operazioni ad alta intensità di memoria.
"""

import os
import sys
import time
import threading
import platform

class MemoryMonitor:
    """
    Monitor dell'utilizzo di memoria per verificare limiti e soglie di sicurezza.
    Utile per prevenire out-of-memory durante operazioni intensive.
    """
    
    def __init__(self, warning_threshold_mb=500, critical_threshold_mb=800):
        """
        Inizializza il monitor di memoria.
        
        Args:
            warning_threshold_mb: Soglia di avviso in MB
            critical_threshold_mb: Soglia critica in MB
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # Converti in byte
        self.critical_threshold = critical_threshold_mb * 1024 * 1024  # Converti in byte
        self.monitoring = False
        self.monitor_thread = None
        self.current_usage = 0
        self.peak_usage = 0
        self.last_check_time = 0
        self.check_interval = 1.0  # Controlla ogni secondo
        
        # Determina il metodo più appropriato per la piattaforma
        self.get_memory_usage = self._select_memory_method()
    
    def _select_memory_method(self):
        """Seleziona il metodo più appropriato per misurare l'utilizzo della memoria."""
        system = platform.system().lower()
        
        if system == 'linux':
            return self._get_memory_linux
        elif system == 'darwin':
            return self._get_memory_macos
        elif system == 'windows':
            return self._get_memory_windows
        else:
            return self._get_memory_psutil
    
    def _get_memory_linux(self):
        """Ottiene l'utilizzo della memoria su Linux."""
        try:
            with open(f'/proc/{os.getpid()}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        # VmRSS è la memoria residente in kB
                        return int(line.split()[1]) * 1024  # Converti in byte
            return 0
        except:
            return self._get_memory_psutil()
    
    def _get_memory_macos(self):
        """Ottiene l'utilizzo della memoria su macOS."""
        try:
            import subprocess
            cmd = f"ps -o rss= -p {os.getpid()}"
            output = subprocess.check_output(cmd, shell=True).decode().strip()
            return int(output) * 1024  # Output è in kB, converti in byte
        except:
            return self._get_memory_psutil()
    
    def _get_memory_windows(self):
        """Ottiene l'utilizzo della memoria su Windows."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except:
            try:
                # Fallback con API Windows
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetCurrentProcess()
                memory_info = ctypes.c_ulonglong(0)
                kernel32.GetProcessMemoryInfo(handle, 
                                            ctypes.byref(memory_info), 
                                            ctypes.sizeof(memory_info))
                return memory_info.value
            except:
                return 0
    
    def _get_memory_psutil(self):
        """Ottiene l'utilizzo della memoria usando psutil (fallback)."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except:
            return 0
    
    def start_monitoring(self):
        """Avvia il monitoraggio della memoria in un thread separato."""
        if self.monitoring:
            return False
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_thread, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Ferma il monitoraggio della memoria."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_thread(self):
        """Thread worker per monitorare l'utilizzo della memoria."""
        while self.monitoring:
            try:
                current_usage = self.get_memory_usage()
                self.current_usage = current_usage
                self.peak_usage = max(self.peak_usage, current_usage)
                self.last_check_time = time.time()
                
                # Verifica soglie di avviso
                if current_usage > self.critical_threshold:
                    print(f"AVVISO: Utilizzo memoria critico: {self.format_bytes(current_usage)}")
                    
                # Attendi prima del prossimo controllo
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Errore monitoraggio memoria: {e}")
                time.sleep(5)  # Attendi più a lungo in caso di errore
    
    def check_memory(self):
        """Controlla l'utilizzo corrente della memoria."""
        self.current_usage = self.get_memory_usage()
        self.peak_usage = max(self.peak_usage, self.current_usage)
        self.last_check_time = time.time()
        return self.current_usage
    
    def is_memory_safe(self, additional_mb=0):
        """
        Verifica se l'utilizzo della memoria è in zona sicura.
        
        Args:
            additional_mb: MB addizionali da considerare per l'operazione
            
        Returns:
            bool: True se è sicuro procedere, False altrimenti
        """
        current = self.check_memory()
        additional = additional_mb * 1024 * 1024  # Converti in byte
        projected_usage = current + additional
        
        return projected_usage < self.critical_threshold
    
    def get_memory_status(self):
        """
        Restituisce lo stato corrente della memoria.
        
        Returns:
            dict: Stato corrente della memoria
        """
        return {
            'current_usage': self.current_usage,
            'peak_usage': self.peak_usage,
            'warning_threshold': self.warning_threshold,
            'critical_threshold': self.critical_threshold,
            'is_safe': self.current_usage < self.warning_threshold,
            'is_warning': self.warning_threshold <= self.current_usage < self.critical_threshold,
            'is_critical': self.current_usage >= self.critical_threshold,
            'last_check_time': self.last_check_time
        }
    
    @staticmethod
    def format_bytes(bytes_value):
        """Formatta un valore in byte in una rappresentazione leggibile."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
        return f"{bytes_value:.2f} TB"

def estimate_memory_requirements(frame_width, frame_height, num_frames, bits_per_pixel=24):
    """
    Stima la memoria necessaria per processare un video.
    
    Args:
        frame_width: Larghezza del frame in pixel
        frame_height: Altezza del frame in pixel
        num_frames: Numero di frame da processare
        bits_per_pixel: Profondità di colore in bit per pixel
        
    Returns:
        int: Stima della memoria richiesta in MB
    """
    bytes_per_pixel = bits_per_pixel / 8
    frame_size_bytes = frame_width * frame_height * bytes_per_pixel
    total_bytes = frame_size_bytes * num_frames
    
    # Aggiungi un buffer di sicurezza del 30% per overhead Python e strutture dati
    total_bytes *= 1.3
    
    # Converti in MB
    total_mb = total_bytes / (1024 * 1024)
    
    return int(total_mb)

def get_total_system_memory():
    """
    Ottiene la memoria totale del sistema.
    
    Returns:
        int: Memoria totale in MB o -1 se non è possibile determinarla
    """
    try:
        import psutil
        return psutil.virtual_memory().total // (1024 * 1024)
    except:
        try:
            # Fallback su Linux
            if os.path.exists('/proc/meminfo'):
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            # MemTotal è in kB
                            return int(line.split()[1]) // 1024
        except:
            pass
        
        return -1  # Impossibile determinare

def is_prerender_safe(video_duration, fps, frame_width, frame_height):
    """
    Verifica se è sicuro pre-renderizzare completamente un video.
    
    Args:
        video_duration: Durata del video in secondi
        fps: Frame per secondo
        frame_width: Larghezza del frame in pixel
        frame_height: Altezza del frame in pixel
        
    Returns:
        bool: True se è sicuro pre-renderizzare, False altrimenti
    """
    # Stima il numero di frame
    num_frames = int(video_duration * fps)
    
    # Stima la memoria richiesta
    memory_required = estimate_memory_requirements(frame_width, frame_height, num_frames)
    
    # Ottieni la memoria totale del sistema
    total_memory = get_total_system_memory()
    
    # Se non possiamo determinare la memoria totale, usiamo un valore conservativo
    if total_memory <= 0:
        total_memory = 4096  # Supponiamo 4GB di RAM
    
    # Verifica se c'è abbastanza memoria 
    # Consideriamo sicuro usare fino al 50% della RAM totale
    return memory_required < (total_memory * 0.5)
