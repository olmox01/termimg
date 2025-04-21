#!/usr/bin/env python3
"""
Modulo per analizzare le prestazioni di riproduzione video e ottimizzare i parametri.
Monitora FPS, frame saltati e utilizzo risorse per regolare automaticamente la qualità.
"""

import os
import sys
import time
import threading
import platform

class PerformanceAnalyzer:
    """
    Analizzatore di prestazioni per ottimizzare la riproduzione video.
    Regola automaticamente parametri come FPS e qualità in base alle capacità del sistema.
    """
    
    def __init__(self, target_fps=24.0, window_size=30):
        """
        Inizializza l'analizzatore di prestazioni.
        
        Args:
            target_fps: FPS obiettivo
            window_size: Dimensione finestra temporale per le statistiche
        """
        self.target_fps = target_fps
        self.window_size = window_size
        self.frame_times = []
        self.start_time = 0
        self.frames_rendered = 0
        self.skipped_frames = 0
        self.monitoring = False
        self.monitor_thread = None
        self.system_stats = {}
        self.last_update_time = 0
        self.hardware_capability = self._detect_capability()
        self.is_optimized = False
        
    def _detect_capability(self):
        """Rileva le capacità hardware del sistema."""
        try:
            # Cerca di importare il rilevatore di piattaforma
            from platform_detector import detect_platform
            platform_info = detect_platform()
            
            # Sistemi a prestazioni limitate
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
                
            # Default per sistemi desktop standard
            return "high"
        except ImportError:
            # Fallback a controlli base
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            # Controllo per alpine/musl
            is_musl = False
            try:
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    is_musl = 'alpine' in version_info or 'musl' in version_info
            except:
                pass
            
            # Controllo per dispositivi ARM
            is_arm = 'arm' in machine or 'aarch' in machine
            
            if is_musl:
                return "low"
            elif is_arm:
                return "medium"
            else:
                return "high"
                
    def start_monitoring(self):
        """Avvia il monitoraggio delle prestazioni."""
        if self.monitoring:
            return False
            
        self.monitoring = True
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
        # Avvia thread di monitoraggio sistema se possibile
        try:
            import psutil
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()
        except ImportError:
            pass
            
        return True
        
    def stop_monitoring(self):
        """Ferma il monitoraggio delle prestazioni."""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
    def register_frame(self):
        """Registra un frame renderizzato."""
        now = time.time()
        
        # Registra il tempo per il frame
        if self.frames_rendered > 0:
            frame_time = now - self.last_update_time
            self.frame_times.append(frame_time)
            
            # Mantieni la finestra di dimensione limitata
            if len(self.frame_times) > self.window_size:
                self.frame_times.pop(0)
        
        self.last_update_time = now
        self.frames_rendered += 1
        
    def get_current_fps(self):
        """Calcola gli FPS attuali."""
        if not self.frame_times:
            return self.target_fps
            
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        if avg_frame_time > 0:
            return 1.0 / avg_frame_time
        return self.target_fps
        
    def get_optimal_fps(self):
        """Calcola gli FPS ottimali in base alle capacità rilevate."""
        if self.hardware_capability == "low":
            return min(15.0, self.target_fps)
        elif self.hardware_capability == "medium":
            return min(24.0, self.target_fps)
        else:
            return self.target_fps
            
    def get_adaptive_parameters(self):
        """
        Calcola parametri adattivi in base alle prestazioni del sistema.
        
        Returns:
            dict: Parametri ottimizzati (fps, smoothness, skip_ratio)
        """
        current_fps = self.get_current_fps()
        optimal_fps = self.get_optimal_fps()
        
        # Se le prestazioni sono molto sotto il target
        if current_fps < optimal_fps * 0.7:
            # Riduci il target FPS e aumenta lo smoothing
            return {
                'fps': max(12.0, current_fps * 1.1),  # Massimizza un po' oltre il corrente
                'smoothness': 0.8,  # Ridotta fluidità per risparmiare risorse
                'skip_ratio': 0.2  # Salta alcuni frame
            }
        # Se le prestazioni sono leggermente sotto il target
        elif current_fps < optimal_fps * 0.9:
            return {
                'fps': optimal_fps * 0.9,  # Riduci leggermente il target
                'smoothness': 0.9,
                'skip_ratio': 0.1
            }
        else:
            # Prestazioni buone, usa valori standard
            return {
                'fps': optimal_fps,
                'smoothness': 1.0,
                'skip_ratio': 0.0
            }
    
    def _monitor_system(self):
        """Thread per monitorare le risorse di sistema."""
        try:
            import psutil
            
            while self.monitoring:
                # Raccogli statistiche di sistema
                self.system_stats = {
                    'cpu': psutil.cpu_percent(interval=None),
                    'memory': psutil.virtual_memory().percent,
                    'timestamp': time.time()
                }
                
                # Ottimizza in base alle risorse disponibili
                self._optimize_for_resources()
                
                # Attendi prima della prossima misurazione
                time.sleep(2.0)
                
        except Exception as e:
            print(f"Errore nel monitoraggio del sistema: {e}")
            
    def _optimize_for_resources(self):
        """Ottimizza parametri in base alle risorse disponibili."""
        # Attiva ottimizzazioni se CPU o memoria sono sotto pressione
        if self.system_stats.get('cpu', 0) > 80 or self.system_stats.get('memory', 0) > 85:
            self.is_optimized = True
        elif self.system_stats.get('cpu', 0) < 60 and self.system_stats.get('memory', 0) < 70:
            self.is_optimized = False
            
    def get_system_status(self):
        """Restituisce lo stato attuale del sistema e delle prestazioni."""
        elapsed = time.time() - self.start_time
        actual_fps = self.frames_rendered / max(0.001, elapsed) if elapsed > 0 else 0
        
        return {
            'elapsed_time': elapsed,
            'frames_rendered': self.frames_rendered,
            'skipped_frames': self.skipped_frames,
            'target_fps': self.target_fps,
            'actual_fps': actual_fps,
            'fps_ratio': actual_fps / self.target_fps if self.target_fps > 0 else 0,
            'system_stats': self.system_stats,
            'hardware_capability': self.hardware_capability,
            'optimized': self.is_optimized
        }
