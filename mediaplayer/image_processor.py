from PIL import Image, ImageOps, ImageEnhance, ImageFilter, UnidentifiedImageError, ImageFile
import os
import sys
import time
from core import CACHE_DIR

class ImageProcessor:
    def __init__(self):
        self.layers = {}
        
    def load_image(self, path):
        """Carica un'immagine dal percorso specificato."""
        try:
            # Attiva il flag per gestire immagini troncate (comune su Alpine/musl)
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            
            # Verifica se il file esiste e ha dimensione > 0
            if not os.path.exists(path):
                print(f"File non trovato: {path}")
                sys.exit(1)
                
            if os.path.getsize(path) <= 0:
                print(f"File immagine vuoto o inaccessibile: {path}")
                sys.exit(1)
            
            # Tenta di aprire l'immagine con metodo robusto
            img = Image.open(path)
            img_rgb = img.convert('RGB')
            
            # Forza il caricamento per verificare che l'immagine sia valida
            img_rgb.load()
            
            return img_rgb
        except UnidentifiedImageError:
            print(f"Formato immagine non supportato: {path}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"File non trovato: {path}")
            sys.exit(1)
        except PermissionError:
            print(f"Permesso negato per l'accesso al file: {path}")
            sys.exit(1)
        except Exception as e:
            print(f"Errore nel caricamento dell'immagine: {e}")
            sys.exit(1)
    
    def enhance_image(self, img, contrast=1.1, brightness=1.0):
        """Applica miglioramenti minimali all'immagine."""
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)
        return img

    def process_image(self, img, contrast=1.1, brightness=1.0):
        """Processo semplificato dell'immagine."""
        # Assicurati che contrast e brightness siano numeri
        try:
            contrast = float(contrast)
            brightness = float(brightness)
        except (ValueError, TypeError):
            # In caso di errore usa i valori predefiniti
            contrast = 1.1
            brightness = 1.0
            
        self.layers['original'] = img
        img = self.enhance_image(img, contrast, brightness)
        self.layers['base'] = img
        return img

    def resize_for_terminal(self, img, term_width, term_height, mode="fit"):
        """Ridimensiona l'immagine per adattarla al terminale in modo ottimizzato."""
        orig_width, orig_height = img.size
        
        # Verifica contro dimensioni nulle o negative
        if orig_width <= 0 or orig_height <= 0:
            print("Avviso: dimensione immagine non valida")
            orig_width = max(1, orig_width)
            orig_height = max(1, orig_height)
            
        # Calcola la massima dimensione possibile in pixel
        max_term_width = term_width
        max_term_height = term_height * 2  # Ogni carattere rappresenta 2 pixel verticali
        
        # Dimensioni minime garantite
        max_term_width = max(1, max_term_width)
        max_term_height = max(1, max_term_height)
        
        # Calcola dimensioni target e padding in base alla modalità
        if mode == "fit":
            # Mantiene l'aspect ratio
            aspect_ratio = orig_width / max(1, orig_height)  # Evita divisione per zero
            
            # Calcola le dimensioni adattate alla finestra mantenendo le proporzioni
            if max_term_width / max_term_height < aspect_ratio:
                # Limitato dalla larghezza
                target_width = max_term_width
                target_height = int(target_width / aspect_ratio)
            else:
                # Limitato dall'altezza
                target_height = max_term_height
                target_width = int(target_height * aspect_ratio)
            
            # Assicura che le dimensioni minime siano rispettate
            target_width = max(1, min(target_width, max_term_width))
            target_height = max(1, min(target_height, max_term_height))
            
            # Calcola padding per centrare l'immagine
            padding_x = max(0, (max_term_width - target_width) // 2)
            padding_y = max(0, (term_height - (target_height // 2)) // 2)
            
        elif mode == "stretch":
            # Riempie tutto lo spazio
            target_width = max_term_width
            target_height = max_term_height
            padding_x = padding_y = 0
            
        else:  # "fill"
            # Riempie mantenendo aspect ratio, può tagliare parti
            aspect_ratio = orig_width / max(1, orig_height)
            h_ratio = max_term_width / max(1, orig_width)
            v_ratio = max_term_height / max(1, orig_height)
            
            ratio = max(h_ratio, v_ratio)
            target_width = min(max_term_width, int(orig_width * ratio))
            target_height = min(max_term_height, int(orig_height * ratio))
            
            # Previene problemi con immagini molto piccole
            if target_width < 1: target_width = 1
            if target_height < 1: target_height = 1
            
            # Crea una copia dell'immagine per evitare di modificare l'originale
            resized_img = img.resize((int(orig_width * ratio), int(orig_height * ratio)), Image.LANCZOS)
            
            # Calcola i punti di crop per centrare l'immagine
            left = (resized_img.width - min(resized_img.width, max_term_width)) // 2
            top = (resized_img.height - min(resized_img.height, max_term_height)) // 2
            
            # Assicura che i valori non superino i limiti dell'immagine
            left = max(0, min(left, resized_img.width - 1))
            top = max(0, min(top, resized_img.height - 1))
            
            right = min(resized_img.width, left + target_width)
            bottom = min(resized_img.height, top + target_height)
            
            # Evita coordinate di crop invalide
            if right <= left:
                right = left + 1
            if bottom <= top:
                bottom = top + 1
                
            img = resized_img.crop((left, top, right, bottom))
            padding_x = padding_y = 0
        
        # Ridimensiona il layer base
        if mode != "fill":
            # Assicura dimensioni minime
            target_width = max(1, target_width)
            target_height = max(1, target_height)
            # Evita ridimensionamenti non necessari per migliori prestazioni
            if self.layers['base'].size != (target_width, target_height):
                base_img = self.layers['base'].copy()
                # Usa LANCZOS per immagini grandi, NEAREST per immagini piccole (più veloce)
                resize_method = Image.LANCZOS if max(target_width, target_height) > 100 else Image.NEAREST
                self.layers['base'] = base_img.resize((target_width, target_height), resize_method)
        else:
            # In modalità fill, il layer base è già stato ridimensionato e ritagliato
            self.layers['base'] = img.copy()
        
        return img, target_width, target_height, padding_x, padding_y
