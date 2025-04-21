#!/usr/bin/env python3
"""
Modulo per il pre-rendering completo di video prima della riproduzione.
Estrae tutti i frame, li pre-processa e li memorizza per una riproduzione fluida.
"""

import os
import sys
import time
import threading
import queue
import subprocess
from PIL import Image
import tempfile
import shutil

class CompleteVideoRenderer:
    """
    Classe che si occupa di renderizzare completamente un video prima della riproduzione.
    Questo garantisce una riproduzione fluida anche su sistemi con prestazioni limitate.
    """
    
    def __init__(self, video_manager, processor, renderer, buffer_manager=None):
        """
        Inizializza il renderer completo.
        
        Args:
            video_manager: Istanza di VideoManager
            processor: Istanza di ImageProcessor
            renderer: Istanza di TerminalRenderer
            buffer_manager: Opzionale, istanza di AsyncVideoBuffer
        """
        self.video_manager = video_manager
        self.processor = processor
        self.renderer = renderer
        self.buffer_manager = buffer_manager
        
        # Directory per i frame renderizzati
        self.rendered_frames_dir = None
        self.frame_cache = {}  # Cache dei frame già renderizzati
        self.processed_frames = 0
        self.total_frames = 0
        self.progress = 0
        self.is_rendering = False
        self.render_thread = None
        self.is_cancelled = False
        self.render_start_time = 0
        self.estimated_time = 0
        self.frame_times = []  # Per calcolare tempo medio per frame
        self.callback = None
    
    def start_rendering(self, video_path, fps=24.0, term_width=80, term_height=24, 
                      start_time=0, duration=None, contrast=1.1, brightness=1.0,
                      callback=None):
        """
        Avvia il processo di rendering completo del video.
        
        Args:
            video_path: Percorso del file video
            fps: Frame per secondo
            term_width, term_height: Dimensioni del terminale
            start_time, duration: Opzioni di estrazione
            contrast, brightness: Parametri di image processing
            callback: Funzione di callback per aggiornamenti progresso
            
        Returns:
            bool: True se il rendering è avviato con successo
        """
        if self.is_rendering:
            print("Rendering già in corso")
            return False
        
        self.is_cancelled = False
        self.progress = 0
        self.processed_frames = 0
        self.callback = callback
        self.render_start_time = time.time()
        
        # Crea directory temporanea per i frame renderizzati
        try:
            from core import CACHE_DIR
            base_dir = os.path.join(CACHE_DIR, "complete_renders")
        except ImportError:
            base_dir = os.path.join(tempfile.gettempdir(), "termimg", "complete_renders")
        
        os.makedirs(base_dir, exist_ok=True)
        self.rendered_frames_dir = os.path.join(base_dir, f"render_{int(time.time())}")
        os.makedirs(self.rendered_frames_dir, exist_ok=True)
        
        # Avvia thread di rendering
        self.render_thread = threading.Thread(
            target=self._render_video_thread,
            args=(video_path, fps, term_width, term_height, start_time, duration, contrast, brightness),
            daemon=True
        )
        self.is_rendering = True
        self.render_thread.start()
        
        return True
    
    def _render_video_thread(self, video_path, fps, term_width, term_height, start_time, duration, contrast, brightness):
        """Thread worker per il rendering completo."""
        try:
            # Prima estrai tutti i frame del video
            self._update_progress(0, "Estrazione frame...")
            frames_dir = self.video_manager.extract_frames(
                video_path,
                fps=fps,
                start_time=start_time,
                duration=duration,
                callback=lambda p: self._update_progress(p*0.5, "Estrazione frame...")
            )
            
            if not frames_dir or self.is_cancelled:
                self._update_progress(100, "Operazione annullata")
                self.is_rendering = False
                return
            
            # Ottieni lista ordinata di frame
            frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(('.jpg', '.png'))])
            self.total_frames = len(frame_files)
            
            if self.total_frames == 0:
                self._update_progress(100, "Nessun frame estratto")
                self.is_rendering = False
                return
            
            self._update_progress(50, f"Inizio rendering di {self.total_frames} frame...")
            
            # Verifica se possiamo usare il rendering ad alta qualità
            use_high_quality = False
            try:
                from high_quality_renderer import VideoHighQualityRenderer
                # Rileva capacità hardware
                try:
                    from platform_detector import detect_platform
                    platform_info = detect_platform()
                    hardware_capability = "high"
                    if platform_info.get('is_limited_terminal', False):
                        hardware_capability = "low"
                    elif platform_info.get('is_arm', False):
                        hardware_capability = "medium"
                except ImportError:
                    hardware_capability = "high"
                
                # Crea il renderer di alta qualità
                if hasattr(self.renderer, 'hq_renderer'):
                    # Usa il renderer esistente
                    video_hq_renderer = self.renderer.hq_renderer
                    use_high_quality = True
                elif hasattr(self.renderer, 'video_hq_renderer'):
                    # Usa il video renderer esistente
                    video_hq_renderer = self.renderer.video_hq_renderer
                    use_high_quality = True
                else:
                    # Crea un nuovo renderer
                    video_hq_renderer = VideoHighQualityRenderer()
                    self.renderer.hq_renderer = video_hq_renderer
                    use_high_quality = True
                
                # Adatta qualità in base all'hardware
                quality_level = video_hq_renderer.get_optimal_quality_level(hardware_capability)
                self._update_progress(50, f"Configurando rendering in qualità {quality_level}")
                
                # Log informativo sulla qualità
                print(f"Rendering in qualità {quality_level} per hardware {hardware_capability}")
                
            except ImportError:
                use_high_quality = False
                print("Modulo high_quality_renderer non disponibile, usando renderer standard")
            
            # Monitora utilizzo memoria se disponibile
            memory_monitor = None
            try:
                # Importa solo se il modulo esiste
                try:
                    from memory_monitor import MemoryMonitor, estimate_memory_requirements
                    memory_monitor_available = True
                except ImportError:
                    memory_monitor_available = False
                    
                if memory_monitor_available:
                    video_info = self.video_manager.get_video_info(video_path)
                    if video_info:
                        width = video_info.get('width', 640)
                        height = video_info.get('height', 480)
                        memory_required = estimate_memory_requirements(width, height, self.total_frames)
                        print(f"Memoria stimata per rendering completo: {memory_required}MB")
                        
                    memory_monitor = MemoryMonitor()
                    memory_monitor.start_monitoring()
            except Exception as e:
                print(f"Errore nell'inizializzare il monitor di memoria: {e}")
                memory_monitor = None
                
            # Pre-renderizza tutti i frame
            for i, frame_file in enumerate(frame_files):
                if self.is_cancelled:
                    break
                    
                frame_path = os.path.join(frames_dir, frame_file)
                output_path = os.path.join(self.rendered_frames_dir, f"rendered_{i:06d}.dat")
                
                # Salta se il frame è già renderizzato
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    self.processed_frames += 1
                    continue
                
                # Verifica memoria disponibile
                if memory_monitor and not memory_monitor.is_memory_safe():
                    print("Avviso: Memoria insufficiente, riduzione qualità rendering")
                    use_high_quality = False
                
                start_frame_time = time.time()
                
                # Carica e processa l'immagine
                img = self.processor.load_image(frame_path)
                
                # Utilizzo elaborazione ad alta qualità se disponibile
                if use_high_quality:
                    try:
                        # Pre-elabora con alta qualità
                        img = video_hq_renderer.preprocess_video_frame(img, quality_level)
                    except Exception as e:
                        print(f"Errore nell'elaborazione ad alta qualità: {e}")
                        # Fallback all'elaborazione standard
                        processed_img = self.processor.process_image(img, contrast, brightness)
                else:
                    # Elaborazione standard
                    processed_img = self.processor.process_image(img, contrast, brightness)
                
                # Ridimensiona per adattarla al terminale
                resized_img, target_width, target_height, padding_x, padding_y = self.processor.resize_for_terminal(
                    processed_img, term_width, term_height, "fit"
                )
                
                # Prepara i dati per il rendering
                pixel_data = self.renderer.prepare_pixel_data(
                    self.processor.layers['base'],
                    target_width, target_height,
                    padding_x, padding_y,
                    term_width, term_height
                )
                
                # Salva i dati pre-renderizzati
                try:
                    import pickle
                    with open(output_path, 'wb') as f:
                        pickle.dump(pixel_data, f)
                except (ImportError, IOError) as e:
                    print(f"Errore nel salvare il frame renderizzato: {e}")
                
                self.processed_frames += 1
                
                # Calcola tempo stimato rimanente
                frame_time = time.time() - start_frame_time
                self.frame_times.append(frame_time)
                if len(self.frame_times) > 10:
                    self.frame_times.pop(0)
                
                avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                frames_left = self.total_frames - self.processed_frames
                self.estimated_time = avg_frame_time * frames_left
                
                progress = 50 + (self.processed_frames / self.total_frames) * 50
                self._update_progress(progress, f"Rendering frame {self.processed_frames}/{self.total_frames}")
                
                # Rilascia memoria ogni 10 frame
                if i % 10 == 0 and hasattr(self.processor, 'clear_cache'):
                    self.processor.clear_cache()
                    if use_high_quality and hasattr(video_hq_renderer, 'clear_cache'):
                        video_hq_renderer.clear_cache()
            
            # Pulisci la memoria
            if memory_monitor:
                memory_monitor.stop_monitoring()
                try:
                    status = memory_monitor.get_memory_status()
                    print(f"Picco utilizzo memoria: {MemoryMonitor.format_bytes(status['peak_usage'])}")
                except:
                    # Gestione sicura in caso di problemi
                    print("Impossibile ottenere statistiche memoria")
            
            self._update_progress(100, "Rendering completato")
        
        except Exception as e:
            print(f"Errore durante il rendering completo: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_rendering = False
    
    def _update_progress(self, progress, status_text):
        """Aggiorna il progresso e invia callback se disponibile."""
        self.progress = progress
        if self.callback:
            self.callback(progress, status_text, self.estimated_time)
    
    def get_frame(self, frame_num):
        """
        Ottiene un frame specifico dalla cache renderizzata.
        
        Args:
            frame_num: Numero del frame da recuperare
            
        Returns:
            I dati del pixel renderizzato o None se non disponibile
        """
        # Prima verifica nella cache in memoria
        if frame_num in self.frame_cache:
            return self.frame_cache[frame_num]
        
        # Altrimenti carica dal disco
        frame_path = os.path.join(self.rendered_frames_dir, f"rendered_{frame_num:06d}.dat")
        if os.path.exists(frame_path):
            try:
                import pickle
                with open(frame_path, 'rb') as f:
                    data = pickle.load(f)
                    # Memorizza in cache per uso futuro
                    if len(self.frame_cache) > 100:  # Limita dimensione cache
                        old_key = next(iter(self.frame_cache))
                        del self.frame_cache[old_key]
                    self.frame_cache[frame_num] = data
                    return data
            except Exception as e:
                print(f"Errore nel caricare frame renderizzato: {e}")
        
        return None
    
    def cancel_rendering(self):
        """Annulla il processo di rendering."""
        self.is_cancelled = True
        if self.render_thread and self.render_thread.is_alive():
            self.render_thread.join(timeout=2.0)
        self.is_rendering = False
        
    def get_progress(self):
        """Restituisce lo stato corrente del rendering."""
        if not self.is_rendering:
            if self.progress >= 100:
                return 100, "Rendering completato", 0
            else:
                return self.progress, "Rendering interrotto", 0
        
        return self.progress, f"Rendering frame {self.processed_frames}/{self.total_frames}", self.estimated_time
    
    def is_complete(self):
        """Verifica se il rendering è completo."""
        return self.progress >= 100 and not self.is_rendering
    
    def cleanup(self):
        """Pulisce le risorse allocate."""
        try:
            if self.rendered_frames_dir and os.path.exists(self.rendered_frames_dir):
                shutil.rmtree(self.rendered_frames_dir, ignore_errors=True)
        except:
            pass

    def optimize_frame_size(self, width, height, size_factor=1.0):
        """
        Ottimizza le dimensioni del frame in base alle capacità del terminale.
        
        Args:
            width: Larghezza originale
            height: Altezza originale
            size_factor: Fattore di ridimensionamento (1.0 = originale)
            
        Returns:
            tuple: (width, height) ottimizzato
        """
        try:
            # Ottieni dimensioni del terminale
            term_width, term_height = os.get_terminal_size()
            
            # Calcola il rapporto di aspetto
            aspect_ratio = width / height
            
            # Dimensione target basata sul terminale
            target_width = int(term_width * size_factor)
            target_height = int(term_height * size_factor * 2)  # Moltiplica per 2 per compensare la differenza di aspect ratio
            
            # Calcola le dimensioni mantenendo il rapporto di aspetto
            if aspect_ratio > (target_width / target_height):
                # L'immagine è più larga che alta
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                # L'immagine è più alta che larga
                new_height = target_height
                new_width = int(target_height * aspect_ratio)
            
            return new_width, new_height
        except:
            # Fallback: ritorna le dimensioni originali
            return width, height
