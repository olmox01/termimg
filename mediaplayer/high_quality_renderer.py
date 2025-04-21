#!/usr/bin/env python3
"""
Modulo per il rendering di immagini e video ad alta qualità.
Fornisce algoritmi avanzati di dithering, correzione colore e ottimizzazioni.
"""

import os
import sys
import time  # Assicuriamoci che time sia importato
import numpy as np
from PIL import Image, ImageEnhance

# Importazione con gestione dell'errore per sklearn
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class HighQualityRenderer:
    """
    Estensione per migliorare la qualità del rendering delle immagini nel terminale.
    Supporta dithering avanzato, ottimizzazioni dei colori e filtri.
    """
    
    def __init__(self):
        """Inizializza il renderer ad alta qualità."""
        # Parametri di qualità
        self.dithering_method = "floyd-steinberg"  # Opzioni: "none", "ordered", "floyd-steinberg"
        self.color_enhancement = 1.2  # Moltiplicatore saturazione colori
        self.edge_enhancement = 1.1   # Moltiplicatore miglioramento bordi
        self.gamma_correction = 1.1   # Fattore correzione gamma
        self.antialiasing = True      # Applica antialiasing durante il ridimensionamento
        
        # Cache per ottimizzare le conversioni di colori
        self.color_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Statistiche rendering
        self.frames_rendered = 0
        self.rendering_time = 0
        
    def apply_dithering(self, image, palette_size=256):
        """
        Applica dithering all'immagine per migliorare la qualità percepita.
        
        Args:
            image: PIL Image da elaborare
            palette_size: Dimensione della palette di colori target
            
        Returns:
            PIL Image con dithering applicato
        """
        if self.dithering_method == "none":
            return image
            
        # Converte in RGB se in un altro formato
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        # Crea una palette ottimizzata
        if palette_size < 256:
            try:
                # Modo 1: Quantizzazione con PIL (più veloce)
                return image.quantize(colors=palette_size, method=1, dither=Image.FLOYDSTEINBERG)
            except:
                pass
                
        # Applica Floyd-Steinberg dithering (implementazione semplificata)
        if self.dithering_method == "floyd-steinberg":
            try:
                import numpy as np
                
                # Converte l'immagine in array numpy
                img_array = np.array(image, dtype=float)
                height, width, channels = img_array.shape
                
                # Fattori di diffusione dell'errore
                for y in range(height-1):
                    for x in range(1, width-1):
                        for c in range(channels):
                            old_val = img_array[y, x, c]
                            new_val = round(old_val / (256 / palette_size)) * (256 / palette_size)
                            img_array[y, x, c] = new_val
                            error = old_val - new_val
                            
                            # Distribuzione dell'errore ai pixel vicini
                            img_array[y, x+1, c] = img_array[y, x+1, c] + error * 7/16
                            img_array[y+1, x-1, c] = img_array[y+1, x-1, c] + error * 3/16
                            img_array[y+1, x, c] = img_array[y+1, x, c] + error * 5/16
                            img_array[y+1, x+1, c] = img_array[y+1, x+1, c] + error * 1/16
                
                # Limita i valori al range 0-255
                img_array = np.clip(img_array, 0, 255)
                
                # Riconverti in PIL Image
                return Image.fromarray(img_array.astype(np.uint8))
            except ImportError:
                # Se numpy non è disponibile, usa il dithering integrato di PIL
                return image.convert("P", palette=Image.ADAPTIVE, colors=palette_size)
        
        # Ordered dithering (implementazione base)
        elif self.dithering_method == "ordered":
            # Matrice di soglie per ordered dithering 4x4
            threshold_map = np.array([
                [0, 8, 2, 10],
                [12, 4, 14, 6],
                [3, 11, 1, 9],
                [15, 7, 13, 5]
            ]) / 16.0
            
            try:
                import numpy as np
                
                # Converte l'immagine in array numpy
                img_array = np.array(image, dtype=float)
                height, width, channels = img_array.shape
                
                # Applica dithering per ciascun canale
                for y in range(height):
                    for x in range(width):
                        for c in range(channels):
                            # Normalizza il valore del pixel
                            normalized = img_array[y, x, c] / 255.0
                            
                            # Applica la soglia dalla mappa
                            threshold = threshold_map[y % 4, x % 4]
                            
                            # Determina il valore finale
                            if normalized >= threshold:
                                img_array[y, x, c] = min(255, round(normalized * 255 + 10))
                            else:
                                img_array[y, x, c] = max(0, round(normalized * 255 - 10))
                
                # Riconverti in PIL Image
                return Image.fromarray(img_array.astype(np.uint8))
            except ImportError:
                # Fallback a dithering PIL
                return image
                
        return image
    
    def enhance_colors(self, image):
        """
        Migliora i colori dell'immagine aumentando contrasto e saturazione.
        
        Args:
            image: PIL Image da elaborare
            
        Returns:
            PIL Image con colori migliorati
        """
        try:
            # Migliora la saturazione
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(self.color_enhancement)
            
            # Migliora il contrasto
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)
            
            # Correzione gamma
            if self.gamma_correction != 1.0:
                from PIL import ImageFilter
                image = image.point(lambda p: int(255 * (p/255) ** (1/self.gamma_correction)))
                
            return image
        except Exception as e:
            print(f"Errore nel miglioramento dei colori: {e}")
            return image
    
    def optimize_terminal_palette(self, colors, target_palette_size=256):
        """
        Ottimizza una lista di colori RGB per il rendering nel terminale.
        
        Args:
            colors: Lista di tuple (R,G,B)
            target_palette_size: Dimensione della palette obiettivo
            
        Returns:
            Lista ottimizzata di colori per il terminale
        """
        # Riutilizza la cache se i colori sono stati già ottimizzati
        cache_key = tuple(map(tuple, colors))
        if cache_key in self.color_cache:
            self.cache_hits += 1
            return self.color_cache[cache_key]
            
        self.cache_misses += 1
        
        try:
            if SKLEARN_AVAILABLE:
                # Converti i colori in un array numpy
                color_array = np.array(colors)
                
                # Usa K-means per trovare i cluster di colori
                kmeans = KMeans(n_clusters=min(target_palette_size, len(colors)), 
                               random_state=0).fit(color_array)
                
                # I centri dei cluster sono i colori ottimizzati
                optimized_colors = kmeans.cluster_centers_.astype(int)
                
                # Mappa i colori originali ai centri dei cluster
                labels = kmeans.labels_
                result = [tuple(optimized_colors[label]) for label in labels]
                
                # Cache risultato
                self.color_cache[cache_key] = result
                return result
            else:
                # Fallback se sklearn non è disponibile
                raise ImportError("sklearn non disponibile")
                
        except ImportError:
            # Se sklearn non è disponibile, usa un metodo più semplice
            # Questa è una semplificazione molto base (non ottimale)
            step = max(1, len(colors) // target_palette_size)
            result = [colors[i] for i in range(0, len(colors), step)]
            
            # Cache risultato
            self.color_cache[cache_key] = result
            return result
    
    def sharpen_image(self, image, factor=1.5):
        """
        Migliora la nitidezza dell'immagine.
        
        Args:
            image: PIL Image da elaborare
            factor: Intensità della nitidezza (1.0 = originale)
            
        Returns:
            PIL Image con nitidezza migliorata
        """
        try:
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(image)
            return enhancer.enhance(factor)
        except:
            return image
            
    def generate_optimized_palette(self):
        """
        Genera una palette di colori ottimizzata per il terminale.
        
        Returns:
            Lista di tuple (R,G,B) ottimizzate per terminale
        """
        # Genera palette di colori per terminale ANSI 256 colori
        palette = []
        
        # Colori standard (0-15)
        standard_colors = [
            (0, 0, 0),       # Nero
            (128, 0, 0),     # Rosso
            (0, 128, 0),     # Verde
            (128, 128, 0),   # Giallo
            (0, 0, 128),     # Blu
            (128, 0, 128),   # Magenta
            (0, 128, 128),   # Ciano
            (192, 192, 192), # Bianco
            (128, 128, 128), # Grigio
            (255, 0, 0),     # Rosso chiaro
            (0, 255, 0),     # Verde chiaro
            (255, 255, 0),   # Giallo chiaro
            (0, 0, 255),     # Blu chiaro
            (255, 0, 255),   # Magenta chiaro
            (0, 255, 255),   # Ciano chiaro
            (255, 255, 255)  # Bianco chiaro
        ]
        palette.extend(standard_colors)
        
        # Colori RGB (16-231)
        for r in range(6):
            for g in range(6):
                for b in range(6):
                    palette.append((r*51, g*51, b*51))
                    
        # Scala di grigi (232-255)
        for i in range(24):
            gray = i*10 + 8
            palette.append((gray, gray, gray))
            
        return palette
        
    def clear_cache(self):
        """Pulisce la cache dei colori."""
        self.color_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

class VideoHighQualityRenderer(HighQualityRenderer):
    """
    Estensione specializzata per il rendering video di alta qualità.
    Ottimizzato per lavorare con il CompleteVideoRenderer.
    """
    
    def __init__(self):
        """Inizializza il renderer video di alta qualità."""
        super().__init__()
        self.video_mode = True
        self.frame_cache = {}  # Cache per i frame pre-elaborati
        self.max_cache_size = 30  # Numero massimo di frame in cache
        self.last_frame_number = -1  # Ultimo frame elaborato
        self.frame_processing_times = []  # Tempi di elaborazione per adattamento dinamico
    
    def preprocess_video_frame(self, frame, quality_level="high"):
        """
        Pre-elabora un frame video per migliorare la qualità.
        
        Args:
            frame: PIL Image frame da migliorare
            quality_level: Livello di qualità desiderato
            
        Returns:
            PIL Image migliorata
        """
        if quality_level == "ultra":
            # Applica tutte le ottimizzazioni di qualità
            frame = self.enhance_colors(frame)
            frame = self.sharpen_image(frame, factor=1.2)
            if self.dithering_method != "none":
                frame = self.apply_dithering(frame, palette_size=256)
        elif quality_level == "high":
            # Applica ottimizzazioni bilanciate per qualità/performance
            frame = self.enhance_colors(frame)
            if self.dithering_method != "none":
                frame = self.apply_dithering(frame, palette_size=216)
        
        return frame
    
    def optimize_for_prerendering(self, frame, cache_key=None):
        """
        Ottimizza un frame per il pre-rendering video.
        Applica cache intelligente per frame simili.
        
        Args:
            frame: PIL Image
            cache_key: Chiave opzionale per la cache (default: frame_number)
        
        Returns:
            PIL Image ottimizzata
        """
        if cache_key is not None and cache_key in self.frame_cache:
            self.cache_hits += 1
            return self.frame_cache[cache_key]
            
        self.cache_misses += 1
        
        # Applica ottimizzazioni
        start_time = time.time()
        enhanced_frame = self.preprocess_video_frame(frame, "high")
        processing_time = time.time() - start_time
        
        # Memorizza i tempi di elaborazione per ottimizzazioni future
        self.frame_processing_times.append(processing_time)
        if len(self.frame_processing_times) > 10:
            self.frame_processing_times.pop(0)
        
        # Memorizza in cache se c'è una chiave
        if cache_key is not None:
            # Gestione dimensione cache (rimuovi vecchie entry se necessario)
            if len(self.frame_cache) >= self.max_cache_size:
                oldest_key = next(iter(self.frame_cache))
                del self.frame_cache[oldest_key]
            
            # Memorizza il frame elaborato
            self.frame_cache[cache_key] = enhanced_frame
        
        return enhanced_frame
    
    def get_optimal_quality_level(self, hardware_capability):
        """
        Determina il livello di qualità ottimale per le capacità hardware.
        
        Args:
            hardware_capability: Stringa che descrive le capacità ('low', 'medium', 'high')
            
        Returns:
            Livello di qualità consigliato ('low', 'medium', 'high', 'ultra')
        """
        if hardware_capability == "low":
            return "low"  # Qualità minima per dispositivi limitati
        elif hardware_capability == "medium":
            return "medium"  # Qualità media per dispositivi mobili
        else:
            # Tenta di determinare se possiamo usare ultra su dispositivi high-end
            try:
                import psutil
                memory_gb = psutil.virtual_memory().total / (1024**3)
                if memory_gb >= 8 and psutil.cpu_count(logical=False) >= 4:
                    return "ultra"
            except:
                pass
            
            return "high"  # Qualità alta è il default per sistemi normali
    
    def adjust_quality_for_performance(self, frame_time, target_fps):
        """
        Regola dinamicamente le impostazioni di qualità in base alle prestazioni.
        
        Args:
            frame_time: Tempo impiegato per elaborare l'ultimo frame
            target_fps: FPS target
            
        Returns:
            Dictonary con nuove impostazioni di qualità
        """
        target_frame_time = 1.0 / target_fps
        ratio = frame_time / target_frame_time
        
        new_settings = {}
        
        if ratio > 1.5:  # Prestazioni molto scarse
            new_settings['dithering_method'] = "none"
            new_settings['color_enhancement'] = 1.0
            new_settings['antialiasing'] = False
        elif ratio > 1.2:  # Prestazioni sotto target
            new_settings['dithering_method'] = "ordered"  # Più veloce
            new_settings['color_enhancement'] = 1.1
        else:  # Prestazioni buone
            # Mantiene le impostazioni correnti
            pass
            
        return new_settings

    # Aggiungo metodi per gestione memoria nel VideoHighQualityRenderer
    def clear_cache(self):
        """Pulisce le cache per liberare memoria."""
        self.frame_cache.clear()
        self.color_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        # Richiedi la garbage collection esplicita
        try:
            import gc
            gc.collect()
        except ImportError:
            pass

    def estimate_memory_usage(self):
        """
        Stima l'utilizzo di memoria corrente delle cache.
        
        Returns:
            int: Memoria stimata in byte
        """
        memory_usage = 0
        
        # Stima cache frame
        for frame in self.frame_cache.values():
            try:
                memory_usage += frame.size[0] * frame.size[1] * len(frame.getbands())
            except:
                # Fallback per frame non-PIL
                memory_usage += 100000  # Supponi 100KB
        
        # Stima cache colori
        memory_usage += len(self.color_cache) * 100  # Circa 100 byte per entry
        
        return memory_usage

def setup_high_quality(renderer):
    """
    Configura un renderer esistente per qualità ultra.
    
    Args:
        renderer: Oggetto TerminalRenderer da configurare
    """
    renderer.dithering_enabled = True
    renderer.subpixel_rendering = True
    renderer.color_correction = True
    renderer.use_half_blocks = True
    
    # Crea un renderer HQ e collegalo 
    hq_renderer = HighQualityRenderer()
    renderer.hq_renderer = hq_renderer
    
    # Estendi il renderer con metodi avanzati
    original_prepare = renderer.prepare_pixel_data
    
    def enhanced_prepare_pixel_data(layers, width, height, padding_x, padding_y, term_width, term_height):
        """Versione migliorata di prepare_pixel_data con qualità superiore."""
        pixel_data = original_prepare(layers, width, height, padding_x, padding_y, term_width, term_height)
        
        try:
            # Esegui ottimizzazioni avanzate dei colori
            unique_colors = set()
            for row in pixel_data:
                for cell in row:
                    if isinstance(cell, tuple) and len(cell) >= 3:
                        unique_colors.add(cell[:3])
                        
            if len(unique_colors) > 256:
                # Troppi colori, esegui ottimizzazione
                color_map = {}
                unique_colors_list = list(unique_colors)
                optimized_colors = hq_renderer.optimize_terminal_palette(unique_colors_list)
                
                for i, original in enumerate(unique_colors_list):
                    color_map[original] = optimized_colors[i]
                    
                # Aggiorna i dati dei pixel
                for y in range(len(pixel_data)):
                    for x in range(len(pixel_data[y])):
                        cell = pixel_data[y][x]
                        if isinstance(cell, tuple) and len(cell) >= 3:
                            # Mantieni l'eventuale canale alfa
                            rgb = cell[:3]
                            alpha = cell[3:]
                            pixel_data[y][x] = color_map.get(rgb, rgb) + alpha
        except Exception as e:
            # Ignora errori e procedi con i dati originali
            pass
            
        return pixel_data
        
    # Sostituisci il metodo originale
    renderer.original_prepare_pixel_data = original_prepare
    renderer.prepare_pixel_data = enhanced_prepare_pixel_data
    
    # Aggiungi metodi per ottimizzazione video se non presenti
    if not hasattr(renderer, 'optimize_video_frame'):
        video_hq_renderer = VideoHighQualityRenderer()
        renderer.video_hq_renderer = video_hq_renderer
        
        def optimize_video_frame(frame, frame_number):
            """Ottimizza un singolo frame video."""
            return video_hq_renderer.optimize_for_prerendering(frame, frame_number)
            
        renderer.optimize_video_frame = optimize_video_frame
    
    return renderer

def auto_configure_quality(renderer, hardware_capability="high", is_video=False):
    """
    Configura automaticamente la qualità ottimale per un renderer.
    
    Args:
        renderer: Oggetto TerminalRenderer da configurare
        hardware_capability: Capacità hardware ('low', 'medium', 'high')
        is_video: True se si tratta di rendering video
        
    Returns:
        Renderer configurato
    """
    # Crea un renderer HQ o Video HQ in base al caso d'uso
    if is_video:
        hq_renderer = VideoHighQualityRenderer()
    else:
        hq_renderer = HighQualityRenderer()
    
    # Collega il renderer HQ al renderer principale
    renderer.hq_renderer = hq_renderer
    
    # Rileva le impostazioni ottimali in base all'hardware
    quality_level = hq_renderer.get_optimal_quality_level(hardware_capability)
    
    # Configura renderer in base al livello di qualità
    if quality_level == "low":
        renderer.dithering_enabled = False
        renderer.subpixel_rendering = False
        renderer.color_correction = False
        renderer.use_half_blocks = hardware_capability != "low"
        
        if is_video:
            hq_renderer.dithering_method = "none"
            hq_renderer.color_enhancement = 1.0
            hq_renderer.antialiasing = False
        
    elif quality_level == "medium":
        renderer.dithering_enabled = True
        renderer.subpixel_rendering = False
        renderer.color_correction = True
        renderer.use_half_blocks = True
        
        if is_video:
            hq_renderer.dithering_method = "ordered"  # Più veloce di floyd-steinberg
            hq_renderer.color_enhancement = 1.1
        
    elif quality_level == "high":
        renderer.dithering_enabled = True
        renderer.subpixel_rendering = True
        renderer.color_correction = True
        renderer.use_half_blocks = True
        
        if is_video:
            hq_renderer.dithering_method = "floyd-steinberg"
            hq_renderer.color_enhancement = 1.2
            
    elif quality_level == "ultra":
        renderer.dithering_enabled = True
        renderer.subpixel_rendering = True
        renderer.color_correction = True
        renderer.use_half_blocks = True
        
        if is_video:
            hq_renderer.dithering_method = "floyd-steinberg"
            hq_renderer.color_enhancement = 1.3
            hq_renderer.edge_enhancement = 1.2
    
    # Estendi il renderer con metodi avanzati di HighQualityRenderer
    original_prepare = renderer.prepare_pixel_data
    
    def enhanced_prepare_pixel_data(layers, width, height, padding_x, padding_y, term_width, term_height):
        """Versione migliorata di prepare_pixel_data con qualità superiore."""
        pixel_data = original_prepare(layers, width, height, padding_x, padding_y, term_width, term_height)
        
        try:
            # Esegui ottimizzazioni avanzate dei colori
            unique_colors = set()
            for row in pixel_data:
                for cell in row:
                    if isinstance(cell, tuple) and len(cell) >= 3:
                        unique_colors.add(cell[:3])
                        
            if len(unique_colors) > 256:
                # Troppi colori, esegui ottimizzazione
                color_map = {}
                unique_colors_list = list(unique_colors)
                optimized_colors = hq_renderer.optimize_terminal_palette(unique_colors_list)
                
                for i, original in enumerate(unique_colors_list):
                    color_map[original] = optimized_colors[i]
                    
                # Aggiorna i dati dei pixel
                for y in range(len(pixel_data)):
                    for x in range(len(pixel_data[y])):
                        cell = pixel_data[y][x]
                        if isinstance(cell, tuple) and len(cell) >= 3:
                            # Mantieni l'eventuale canale alfa
                            rgb = cell[:3]
                            alpha = cell[3:]
                            pixel_data[y][x] = color_map.get(rgb, rgb) + alpha
        except Exception as e:
            # Ignora errori e procedi con i dati originali
            pass
            
        return pixel_data
        
    # Sostituisci il metodo originale
    renderer.original_prepare_pixel_data = original_prepare
    renderer.prepare_pixel_data = enhanced_prepare_pixel_data
    
    return renderer, quality_level
