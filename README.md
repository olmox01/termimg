![435534796-cc649c27-a35b-4ada-bec0-f56b91928164](https://github.com/user-attachments/assets/f6c3017a-f9cf-4691-bbb6-6de050fff7f4)

---

# TermImg

**TermImg** is a lightweight image and video viewer for the terminal, optimized to work even on Linux systems using MUSL libraries and minimal configurations.

## Features

* Display images in colored ASCII/ANSI
* Supports all common image formats (JPEG, PNG, GIF, BMP, WebP, etc.)
* SVG support via various converters (CairoSVG, Inkscape, librsvg)
* Video playback using ffmpeg
* Asynchronous buffering for smooth video playback
* Image sequence support
* Automatic file type detection
* Compatible with minimal systems (no numpy required)
* Multiple fitting modes: fit, stretch, fill
* Export rendered frames
* Automatic platform detection for specific optimizations

## Requirements

* Python 3.6+
* Pillow (PIL)
* ffmpeg (optional, for video playback)
* For SVG support (optional): CairoSVG, Inkscape, or librsvg

## Installation

### Easy Method

Use the installation script, which automatically checks and installs all required dependencies:

```bash
python install_dependencies.py
```

### Manual Installation

#### Core Dependency

```bash
pip install pillow
```

#### Optional SVG Support

```bash
pip install cairosvg
```

#### Optional Video Support (depending on your OS)

**Debian/Ubuntu:**

```bash
apt-get install ffmpeg
```

**Alpine Linux:**

```bash
apk add ffmpeg
```

**Arch Linux:**

```bash
pacman -S ffmpeg
```

**Fedora:**

```bash
dnf install ffmpeg
```

**macOS:**

```bash
brew install ffmpeg
```

**Windows:**

Download the installer from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

## Usage

### Basic Usage

**View an image:**

```bash
python termimg.py image.jpg
```

**View an SVG image:**

```bash
python termimg.py image.svg
```

**Play a video:**

```bash
python termimg.py video.mp4
```

**View all images in a folder:**

```bash
python termimg.py ./images_folder
```

**Play a video at a specific FPS:**

```bash
python termimg.py video.mp4 --fps 30
```

### Simplified Script (run.py)

For even easier use, a simplified script is available:

**Auto-detect file type (image/video/svg):**

```bash
python run.py file.jpg  # or file.mp4, file.svg, etc.
```

**Play media in a folder:**

```bash
python run.py ./folder
```

## Main Options

* `-m`, `--mode`: Fit mode (`fit`, `stretch`, `fill`)
* `-c`, `--contrast`: Contrast factor (default: 1.1)
* `-b`, `--brightness`: Brightness factor (default: 1.0)
* `-r`, `--reload`: Reload the last used image
* `--fps`: Target FPS for video playback (default: 24)
* `--loop`: Loop the video instead of stopping
* `-v`, `--video`: Force video mode
* `-i`, `--image`: Force image mode
* `--start`: Start time in seconds (video only)
* `--duration`: Duration in seconds (video only)
* `--extract-only`: Extract video frames without displaying
* `--extract-dir`: Directory to extract video frames

## Video Mode

**Normal playback:**

```bash
python termimg.py video.mp4
```

**Looped playback:**

```bash
python termimg.py video.mp4 --loop
```

**Playback from a specific point:**

```bash
python termimg.py video.mp4 --start 30 --duration 60
```

**Extract frames:**

```bash
python termimg.py video.mp4 --extract-only --extract-dir ./frames
```

### Playback Controls

* `q`: Quit playback
* `p` or `space`: Pause/Resume

## Image Mode

### Available Commands During Viewing

* `Enter` or `q`: Close the image
* `r`: Refresh the view
* `e`: Export the current rendering as PNG

## Testing and Debugging

Test scripts are available to verify functionality:

**Test all modules:**

```bash
python test_all.py --all
```

**Specific tests:**

```bash
python test_image.py image.jpg
python test_svg.py image.svg
```

## Project Structure

* `core.py`: Core functions and utilities
* `image_processor.py`: Image processing
* `terminal_renderer.py`: Terminal rendering
* `video_manager.py`: Video and sequence handling
* `svg_renderer.py`: SVG support
* `async_video_buffer.py`: Asynchronous video buffering
* `platform_detector.py`: Platform-specific optimizations
* `input_handler.py`: Real-time input handling
* `termimg.py`: Main script
* `run.py`: Simplified usage script

## Compatibility

**TermImg** is designed to work on systems with MUSL libraries (like Alpine Linux) and minimal setups, where complex libraries like NumPy may be unavailable or hard to install.

Also supports:

* iSH on iOS
* Termux on Android
* WSL on Windows
* Low-resource systems

## Known Limitations

* Rendering quality depends on terminal color support
* ffmpeg is required for video playback
* A compatible SVG converter is required for SVG files
* Some terminals may display different Unicode block characters

---

TermImg è un visualizzatore leggero di immagini e video direttamente nel terminale, ottimizzato per funzionare anche su sistemi Linux con librerie MUSL e configurazioni minimali.

Caratteristiche
Visualizzazione di immagini in formato ASCII/ANSI colorato
Supporto per tutti i formati di immagine comuni (JPEG, PNG, GIF, BMP, WebP, ecc.)
Supporto per file SVG tramite convertitori diversi (CairoSVG, Inkscape, librsvg)
Riproduzione di video con ffmpeg
Buffering asincrono per riproduzione video fluida
Sequenze di immagini
Riconoscimento automatico del tipo di file
Compatibilità con sistemi minimali (senza numpy)
Diverse modalità di adattamento (fit, stretch, fill)
Esportazione dei rendering
Rilevamento automatico della piattaforma per ottimizzazioni specifiche
Requisiti
Python 3.6+
Pillow (PIL)
ffmpeg (opzionale, per la riproduzione di video)
Per SVG (opzionale): CairoSVG, Inkscape, o librsvg
Installazione
Metodo semplice
Usare lo script di installazione che verificherà e installerà automaticamente le dipendenze necessarie:

python install_dependencies.py
Installazione manuale
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
Utilizzo
Utilizzo di Base
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
Script Semplificato (run.py)
Per un utilizzo ancora più semplice, è disponibile lo script run.py:

# Rilevamento automatico immagine/video/svg
python run.py file.jpg    # o file.mp4, file.svg, ecc.

# Riproduzione di una cartella
python run.py ./cartella
Opzioni Principali
-m, --mode: Modalità di adattamento (fit, stretch, fill)
-c, --contrast: Fattore di contrasto (default: 1.1)
-b, --brightness: Fattore di luminosità (default: 1.0)
-r, --reload: Ricarica l'ultima immagine utilizzata
--fps: FPS target per la modalità video (default: 24)
--loop: Riproduce il video in loop invece di fermarsi alla fine
-v, --video: Forza la modalità video
-i, --image: Forza la modalità immagine
--start: Tempo di inizio in secondi (solo per video)
--duration: Durata in secondi (solo per video)
--extract-only: Estrai i frame del video senza visualizzarli
--extract-dir: Directory dove estrarre i frame del video
Modalità Video
Riproduzione Video
# Riproduzione normale
python termimg.py video.mp4

# Riproduzione in loop continuo
python termimg.py video.mp4 --loop

# Riproduzione a partire da un punto specifico
python termimg.py video.mp4 --start 30 --duration 60

# Estrazione dei frame
python termimg.py video.mp4 --extract-only --extract-dir ./frames
Controlli durante la riproduzione
q: Esci dalla riproduzione
p o spazio: Pausa/Riprendi
Modalità Immagine
Comandi disponibili durante la visualizzazione
Invio o q: Chiudi l'immagine
r: Aggiorna la visualizzazione
e: Esporta il rendering corrente come PNG
Test e Debugging
Sono disponibili script di test per verificare la funzionalità dei vari moduli:

# Test di tutte le funzionalità
python test_all.py --all

# Test specifici
python test_image.py immagine.jpg
python test_svg.py immagine.svg
Struttura del Progetto
Il progetto è organizzato in moduli per facilitare la manutenzione:

core.py: Funzioni e utilità di base
image_processor.py: Elaborazione delle immagini
terminal_renderer.py: Visualizzazione nel terminale
video_manager.py: Gestione dei video e delle sequenze
svg_renderer.py: Supporto per file SVG
async_video_buffer.py: Buffering video asincrono
platform_detector.py: Rilevamento e ottimizzazioni per piattaforme
input_handler.py: Gestione input in tempo reale
termimg.py: Script principale
run.py: Script semplificato
Compatibilità
TermImg è stato progettato per funzionare anche su sistemi Linux con libreria MUSL (Alpine Linux, ecc.) e configurazioni minimali, dove librerie più complesse come NumPy potrebbero non essere disponibili o difficili da installare.

Supporta anche:

iSH su iOS
Termux su Android
WSL su Windows
Sistemi con risorse limitate
Limitazioni note
La qualità della visualizzazione dipende dal supporto del terminale per i colori
La riproduzione video richiede ffmpeg installato
La visualizzazione di file SVG richiede un convertitore compatibile
Alcuni terminali potrebbero mostrare caratteri diversi per i blocchi Unicode utilizzati
