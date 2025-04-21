# TermImg - Visualizzatore di Immagini e Video per Terminale

TermImg è un visualizzatore leggero di immagini e video direttamente nel terminale, ottimizzato per funzionare anche su sistemi Linux con librerie MUSL e configurazioni minimali.

## Caratteristiche

- Visualizzazione di immagini in formato ASCII/ANSI colorato
- Supporto per tutti i formati di immagine comuni (JPEG, PNG, GIF, BMP, WebP, ecc.)
- **Supporto per file SVG** tramite convertitori diversi (CairoSVG, Inkscape, librsvg)
- Riproduzione di video con ffmpeg
- Buffering asincrono per riproduzione video fluida
- Sequenze di immagini
- Riconoscimento automatico del tipo di file
- Compatibilità con sistemi minimali (senza numpy)
- Diverse modalità di adattamento (fit, stretch, fill)
- Esportazione dei rendering
- Rilevamento automatico della piattaforma per ottimizzazioni specifiche

## Requisiti

- Python 3.6+
- Pillow (PIL)
- ffmpeg (opzionale, per la riproduzione di video)
- Per SVG (opzionale): CairoSVG, Inkscape, o librsvg

## Installazione

### Metodo semplice

Usare lo script di installazione che verificherà e installerà automaticamente le dipendenze necessarie:

```bash
python install_dependencies.py
```

### Installazione manuale

```bash
# Dipendenza principale
pip install pillow

# Supporto opzionale per SVG
pip install cairosvg

# Opzionale per supporto video (a seconda del sistema operativo)
# Debian/Ubuntu:
apt-get install ffmpeg
# Alpine Linux:
apk add ffmpeg
# Arch Linux:
pacman -S ffmpeg
# Fedora:
dnf install ffmpeg
# macOS:
brew install ffmpeg
# Windows:
# Scaricare l'installer da https://ffmpeg.org/download.html
```

## Utilizzo

### Utilizzo di Base

```bash
# Visualizza un'immagine
python termimg.py immagine.jpg

# Visualizza un'immagine SVG
python termimg.py immagine.svg

# Riproduci un video
python termimg.py video.mp4

# Visualizza tutte le immagini in una cartella
python termimg.py ./cartella_immagini

# Riproduci il video a un FPS specifico
python termimg.py video.mp4 --fps 30
```

### Script Semplificato (run.py)

Per un utilizzo ancora più semplice, è disponibile lo script run.py:

```bash
# Rilevamento automatico immagine/video/svg
python run.py file.jpg    # o file.mp4, file.svg, ecc.

# Riproduzione di una cartella
python run.py ./cartella
```

### Opzioni Principali

- `-m, --mode`: Modalità di adattamento (fit, stretch, fill)
- `-c, --contrast`: Fattore di contrasto (default: 1.1)
- `-b, --brightness`: Fattore di luminosità (default: 1.0)
- `-r, --reload`: Ricarica l'ultima immagine utilizzata
- `--fps`: FPS target per la modalità video (default: 24)
- `--loop`: Riproduce il video in loop invece di fermarsi alla fine
- `-v, --video`: Forza la modalità video
- `-i, --image`: Forza la modalità immagine
- `--start`: Tempo di inizio in secondi (solo per video)
- `--duration`: Durata in secondi (solo per video)
- `--extract-only`: Estrai i frame del video senza visualizzarli
- `--extract-dir`: Directory dove estrarre i frame del video

## Modalità Video

### Riproduzione Video

```bash
# Riproduzione normale
python termimg.py video.mp4

# Riproduzione in loop continuo
python termimg.py video.mp4 --loop

# Riproduzione a partire da un punto specifico
python termimg.py video.mp4 --start 30 --duration 60

# Estrazione dei frame
python termimg.py video.mp4 --extract-only --extract-dir ./frames
```

### Controlli durante la riproduzione

- `q`: Esci dalla riproduzione
- `p` o `spazio`: Pausa/Riprendi

## Modalità Immagine

### Comandi disponibili durante la visualizzazione

- `Invio` o `q`: Chiudi l'immagine
- `r`: Aggiorna la visualizzazione
- `e`: Esporta il rendering corrente come PNG

## Test e Debugging

Sono disponibili script di test per verificare la funzionalità dei vari moduli:

```bash
# Test di tutte le funzionalità
python test_all.py --all

# Test specifici
python test_image.py immagine.jpg
python test_svg.py immagine.svg
```

## Struttura del Progetto

Il progetto è organizzato in moduli per facilitare la manutenzione:

- `core.py`: Funzioni e utilità di base
- `image_processor.py`: Elaborazione delle immagini 
- `terminal_renderer.py`: Visualizzazione nel terminale
- `video_manager.py`: Gestione dei video e delle sequenze
- `svg_renderer.py`: Supporto per file SVG
- `async_video_buffer.py`: Buffering video asincrono
- `platform_detector.py`: Rilevamento e ottimizzazioni per piattaforme
- `input_handler.py`: Gestione input in tempo reale
- `termimg.py`: Script principale
- `run.py`: Script semplificato

## Compatibilità

TermImg è stato progettato per funzionare anche su sistemi Linux con libreria MUSL (Alpine Linux, ecc.) e configurazioni minimali, dove librerie più complesse come NumPy potrebbero non essere disponibili o difficili da installare.

Supporta anche:
- iSH su iOS
- Termux su Android
- WSL su Windows
- Sistemi con risorse limitate

## Limitazioni note

- La qualità della visualizzazione dipende dal supporto del terminale per i colori
- La riproduzione video richiede ffmpeg installato
- La visualizzazione di file SVG richiede un convertitore compatibile
- Alcuni terminali potrebbero mostrare caratteri diversi per i blocchi Unicode utilizzati
