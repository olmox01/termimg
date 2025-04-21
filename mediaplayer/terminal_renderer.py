import os
import sys
import time
import shutil
import tempfile
from PIL import Image, ImageDraw
from core import CHARS, clear_screen, kbhit, getch

class TerminalRenderer:
    def __init__(self):
        self.temp_dir = None
        self.display_active = False
        self.target_width = None
        self.target_height = None
        self.padding_x = None
        self.padding_y = None
        # Inizializza gli attributi per il refresh
        self._last_pixel_data = None
        self._last_term_width = None
        self._last_term_height = None
        
    def create_temp_folder(self):
        """Crea una cartella temporanea per i dati di rendering."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="termimg_")
        return self.temp_dir
    
    def cleanup(self):
        """Rimuove la cartella temporanea."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
        self.display_active = False

    def calculate_intensity(self, pixel):
        """Calcola l'intensità luminosa di un pixel."""
        if isinstance(pixel, tuple) and len(pixel) >= 3:
            r, g, b = pixel[:3]
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return pixel / 255.0
    
    def prepare_pixel_data(self, img, target_width=None, target_height=None, 
                          padding_x=0, padding_y=0, term_width=None, term_height=None):
        """Prepara i dati dei pixel per la visualizzazione semplificata."""
        pixel_data = {}
        
        for y in range(term_height):
            for x in range(term_width):
                img_x = x - padding_x
                img_y = (y - padding_y) * 2
                
                # Controlla se siamo all'interno dell'immagine
                if (padding_x > 0 and (x < padding_x or x >= padding_x + target_width)) or \
                   (padding_y > 0 and (y < padding_y or y >= padding_y + target_height // 2)):
                    continue
                
                if 0 <= img_x < img.width and 0 <= img_y + 1 < img.height:
                    # Pixel di base
                    top_pixel = img.getpixel((img_x, img_y))
                    bottom_pixel = img.getpixel((img_x, img_y + 1))
                    
                    # Calcola l'intensità per la scelta dei caratteri
                    top_intensity = self.calculate_intensity(top_pixel[:3] if len(top_pixel) > 3 else top_pixel)
                    bottom_intensity = self.calculate_intensity(bottom_pixel[:3] if len(bottom_pixel) > 3 else bottom_pixel)
                    
                    # Memorizza i dati per questo pixel
                    pixel_data[(x, y)] = {
                        'top_pixel': top_pixel[:3] if len(top_pixel) > 3 else top_pixel,
                        'bottom_pixel': bottom_pixel[:3] if len(bottom_pixel) > 3 else bottom_pixel,
                        'top_intensity': top_intensity,
                        'bottom_intensity': bottom_intensity
                    }
        
        return pixel_data
    
    def render_image(self, pixel_data, term_width, term_height):
        """Visualizza l'immagine nel terminale con rendering semplice."""
        self.display_active = True
        clear_screen()  # Pulisce lo schermo prima di visualizzare
        
        # Salva i dati per eventuali refresh
        self._last_pixel_data = pixel_data
        self._last_term_width = term_width
        self._last_term_height = term_height
        
        # Rendering semplice - usa il metodo standardizzato
        self._render_simple(pixel_data, term_width, term_height)
        
        # Informazioni di controllo minime - solo comandi necessari
        # Usiamo una posizione fissa in fondo allo schermo per non alterare l'immagine
        sys.stdout.write(f"\033[{term_height};1H\033[0mPremere Invio per chiudere")
        sys.stdout.flush()

    def _render_simple(self, pixel_data, term_width, term_height):
        """Renderizza l'immagine in modalità semplice e veloce senza pulire lo schermo."""
        # Utilizziamo una stringa di output completa invece di stampare linea per linea
        output = []
        
        # Posizionamento iniziale del cursore in alto a sinistra
        output.append("\033[H")  # Equivalente di "\033[1;1H" - muove il cursore in posizione 1,1
        
        for y in range(term_height):
            line = []
            for x in range(term_width):
                if (x, y) in pixel_data:
                    data = pixel_data[(x, y)]
                    top_code = self.rgb_to_ansi(data['top_pixel'])
                    bottom_code = self.rgb_to_ansi(data['bottom_pixel'])
                    line.append(f"\033[38;5;{top_code}m\033[48;5;{bottom_code}m▀")
                else:
                    line.append(" ")
            output.append("".join(line))
            
            # Non andiamo a capo dopo ogni riga ma posizioniamo il cursore
            # all'inizio della riga successiva per evitare di aggiungere righe
            if y < term_height - 1:
                output.append(f"\033[{y+2};1H")
        
        # Stampa tutto il buffer in una volta sola (molto più veloce)
        print("".join(output), end="\033[0m", flush=True)

    # Aggiungiamo un metodo ottimizzato per video che riduce ulteriormente le operazioni
    def render_video_frame(self, pixel_data, term_width, term_height):
        """Renderizza un frame video con ottimizzazioni per la velocità."""
        # Utilizziamo posizionamento diretto del cursore senza pulire lo schermo
        output = ["\033[H"]  # Posiziona il cursore nell'angolo in alto a sinistra
        
        # Generiamo l'immagine completa in un'unica stringa
        for y in range(term_height):
            line = []
            for x in range(term_width):
                if (x, y) in pixel_data:
                    data = pixel_data[(x, y)]
                    top_code = self.rgb_to_ansi(data['top_pixel'])
                    bottom_code = self.rgb_to_ansi(data['bottom_pixel'])
                    line.append(f"\033[38;5;{top_code}m\033[48;5;{bottom_code}m▀")
                else:
                    line.append(" ")
            output.append("".join(line))
            if y < term_height - 1:
                output.append(f"\033[{y+2};1H")
        
        # Output del buffer in una sola operazione
        sys.stdout.write("".join(output) + "\033[0m")
        sys.stdout.flush()

    # Metodo migliorato per dispositivi mobile
    def render_video_frame_mobile(self, pixel_data, term_width, term_height, status_text=None):
        """Renderizza un frame video ottimizzato per dispositivi mobili."""
        # Verifica che pixel_data non sia None
        if pixel_data is None:
            # Se non ci sono dati, stampa solo il messaggio di stato
            if status_text:
                sys.stdout.write(f"\033[H\033[0m{status_text}")
                sys.stdout.flush()
            return
        
        # Ottimizzazione: prepara l'output completo prima di stampare
        output = ["\033[H"]  # Posiziona il cursore nell'angolo in alto a sinistra
        
        # Genera l'immagine in un'unica stringa - ottimizzazione per renderizzazione veloce
        for y in range(term_height-1):  # Lasciamo l'ultima riga per lo stato
            line_chars = []
            last_fg = None
            last_bg = None
            
            for x in range(term_width):
                if (x, y) in pixel_data:
                    data = pixel_data[(x, y)]
                    fg_code = self.rgb_to_ansi(data['top_pixel'])
                    bg_code = self.rgb_to_ansi(data['bottom_pixel'])
                    
                    # Ottimizzazione: applica codici ANSI solo quando cambiano i colori
                    if fg_code != last_fg or bg_code != last_bg:
                        line_chars.append(f"\033[38;5;{fg_code}m\033[48;5;{bg_code}m")
                        last_fg, last_bg = fg_code, bg_code
                    
                    line_chars.append("▀")  # Carattere di rendering
                else:
                    if last_fg is not None:  # Se avevamo applicato colori in precedenza
                        line_chars.append("\033[0m ")  # Reset e spazio
                        last_fg = last_bg = None
                    else:
                        line_chars.append(" ")  # Semplice spazio
            
            # Resetta colori alla fine della riga se necessario
            if last_fg is not None:
                line_chars.append("\033[0m")
                
            output.append("".join(line_chars))
            
            # Posiziona il cursore all'inizio della riga successiva
            if y < term_height - 2:  # Non l'ultima riga
                output.append(f"\033[{y+2};1H")
        
        # Aggiungi la barra di stato in fondo in modo fisso
        if status_text:
            # Posizionati sull'ultima riga con colore neutro
            output.append(f"\033[{term_height};1H\033[0m{status_text:<{term_width}}")
        
        # Output del buffer in una sola operazione (meno I/O = più velocità)
        sys.stdout.write("".join(output))
        sys.stdout.flush()

    def rgb_to_ansi(self, rgb):
        """Converte un colore RGB in codice ANSI a 256 colori."""
        r, g, b = rgb[:3]
        
        # Colori standard 16-231: cubo 6x6x6
        r_idx = int(r / 255 * 5)
        g_idx = int(g / 255 * 5)
        b_idx = int(b / 255 * 5)
        
        if r == g == b:  # Scala di grigi
            if r == 0:
                return 16  # nero
            if r == 255:
                return 231  # bianco
                
            # Scala di grigi 232-255
            gray_idx = int(((r / 255.0) * 23) + 0.5)
            return 232 + gray_idx
                
        return 16 + r_idx * 36 + g_idx * 6 + b_idx

    def wait_for_input(self, processor):
        """Attende l'input dell'utente per chiudere l'immagine."""
        poll_interval = 0.1  # Poll più lento per ridurre uso CPU
        
        while self.display_active:
            if kbhit():
                key = getch()
                # Accetta Invio, 'q' o 'Q' per uscire
                if key in ['\r', '\n', 'q', 'Q']:
                    clear_screen()
                    self.display_active = False
                    return 'close'
                # Supporto per esportazione con 'e'
                elif key in ['e', 'E']:
                    timestamp = int(time.time())
                    filename = f"termimg_export_{timestamp}.png"
                    sys.stdout.write(f"\033[K\033[32mEsportazione: {filename}\033[0m")
                    sys.stdout.flush()
                    self.export_current_rendering(processor, filename)
                # Refresh esplicito con 'r'
                elif key in ['r', 'R']:
                    # Verifica se abbiamo dati salvati prima di tentare un refresh
                    if self._last_pixel_data is not None:
                        clear_screen()
                        self._render_simple(self._last_pixel_data, self._last_term_width, self._last_term_height)
                        sys.stdout.write(f"\033[{self._last_term_height};1H\033[0mPremere Invio per chiudere")
                        sys.stdout.flush()
            
            # Dormiamo per un po' per ridurre l'uso della CPU
            time.sleep(poll_interval)
        
        return 'close'

    def export_current_rendering(self, processor, filename):
        """Esporta il rendering corrente come immagine PNG."""
        term_width, term_height = os.get_terminal_size().columns, os.get_terminal_size().lines - 1
        
        # Crea un'immagine dalle dimensioni appropriate
        scale = 2  # Fattore di scala per l'output
        img_width = term_width * scale
        img_height = term_height * scale * 2  # Carattere del terminale = 2 pixel verticali
        image = Image.new('RGB', (img_width, img_height), color='black')
        
        # Crea un oggetto Draw per disegnare sull'immagine
        draw = ImageDraw.Draw(image)
        
        # Prepara i dati dei pixel
        pixel_data = self.prepare_pixel_data(
            processor.layers['base'], 
            self.target_width, self.target_height, 
            self.padding_x, self.padding_y,
            term_width, term_height
        )
        
        # Disegna ogni carattere come un blocco di colore
        for y in range(term_height):
            for x in range(term_width):
                if (x, y) in pixel_data:
                    data = pixel_data[(x, y)]
                    
                    # Estrai colori
                    top_color = data['top_pixel'][:3]
                    bottom_color = data['bottom_pixel'][:3]
                    
                    # Disegna rettangoli per la parte superiore e inferiore del carattere
                    top_rect = (x * scale, y * scale * 2, (x+1) * scale, (y * 2 + 1) * scale)
                    bottom_rect = (x * scale, (y * 2 + 1) * scale, (x+1) * scale, (y+1) * 2 * scale)
                    
                    draw.rectangle(top_rect, fill=top_color)
                    draw.rectangle(bottom_rect, fill=bottom_color)
        
        # Salva l'immagine
        image.save(filename)
        print(f"Rendering esportato come: {filename}")
        return filename
