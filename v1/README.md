# Caption Forge 2.0

Local-first subtitle studio with a premium browser workspace and a separate processing backend. It transcribes locally using **Medium Whisper**, lets you place captions by dragging/resizing the caption frame, and exports SRT files without sending video to a cloud service.

## Quick start (Windows)

1. Install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/) and select *Add Python to PATH* during installation.
2. Double-click **`start.bat`**.
3. The first launch creates an isolated `.venv`, installs the app, opens the studio, and shows the first-run setup animation.
4. Setup downloads the Medium multilingual Whisper model once (roughly 1.5 GB). The loading screen reports each setup stage, progress, and ETA. Later launches use the cached model. NVIDIA/CUDA is selected automatically when CTranslate2 detects it; if the CUDA model cannot load, Caption Forge records the reason and falls back to CPU.

The local studio runs on `http://127.0.0.1:8787`. Keep the command window open while using it.

## Features

- Native browser video preview for smooth playback rather than decoding every frame in a UI loop.
- Full local Whisper transcription with VAD filtering, language selection, live progress, ETA, caption preview, and SRT download.
- Moveable, resizable subtitle-safe frame stored as responsive percentage coordinates.
- NLE-style canvas toolbar with fit, guides, grid and fullscreen controls.
- Caption list, searchable timeline, editable start/end times, typography, colors, opacity and position presets.
- SRT import and server-backed SRT export.
- Burn the current caption styling permanently into a delivery-ready MP4, rendered locally with the bundled FFmpeg runtime.
- Clear job progress/errors; background transcription keeps the UI interactive.
- Whisper diagnostics in the editor confirm runtime availability, loaded model, device, and FFmpeg status.
- Model manager for Tiny, Base, Small, Medium, Turbo, and Large v3; downloaded models are cached locally.
- A fresh `logs/caption-forge.log` is created on every launch, replacing the previous session log. The editor links to it from the Whisper panel.

## Local rendering

Caption Forge bundles a small FFmpeg runtime through its Python dependencies, so burned-caption MP4 exports work without a separate FFmpeg installation. If a system FFmpeg installation is present, it is used first.

## Project structure

- `server.py` — FastAPI job server, first-run model installer and Faster-Whisper worker.
- `index.html`, `styles.css`, `polish.css`, `model-ui.css`, `app.js` — framework-free responsive frontend.
- `start.bat` — Windows launcher and dependency bootstrapper.
- `assets/icon.ico` — application icon.
- `logs/caption-forge.log` — current session diagnostics; reset automatically at launch.

The previous `movi.py` and `movi2.py` are kept untouched as historical reference; Caption Forge 2.0 does not depend on either.
