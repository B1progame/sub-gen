# Caption Forge V2

Caption Forge V2 is an offline-first subtitle editor. Video stays on this machine. Optional speech and translation models are downloaded only when selected, then run locally.

## Start on Windows

1. Install Python 3.10 or newer.
2. Double-click `start.bat`.
3. The launcher creates `.venv`, installs dependencies, and opens the local studio at `http://127.0.0.1:8878` (V1 continues to use port 8787).
4. First launch selects a Whisper model from detected NVIDIA VRAM. Model downloads are cached by Faster-Whisper.

For compact offline translation, choose Argos and download the selected language pair once. For more natural, context-aware phrasing, install [Ollama](https://ollama.com/download), leave its local service running, then choose **Natural language · local LLM** and download Qwen 3.5 4B from the translation panel. Caption text goes to the local Ollama service at `127.0.0.1` only. Translation should still be proofread for names, idioms, and context.

## Subtitle and dubbing workspace

- Word timestamps and configurable words-per-beat for speech-generated captions.
- Searchable gallery with 90 combinations of ten entrance/rhythm motions and nine word treatments. Styles include karaoke, pop, type-on, dissolve, lift, spring, focus, defocus, wipe, marker sweep, capsule, outline pulse, and letter-spread emphasis. Word-sync needs Whisper word timestamps; imported captions can use entrance motion.
- Editable font, weight, text and panel colors, opacity, outline, shadow, radius, spacing, alignment, capitalization, line height, panel padding, word emphasis, and effect speed.
- Cinematic, Creator Pop, and Karaoke starting styles.
- Local Argos Translate language pairs with source-text restoration.
- Source language selection is populated from Faster-Whisper's supported language codes; Argos targets are restricted to pairs reported by its local catalog.
- Audio Lab generates a dubbed MP4 from the current caption text, aligned to caption start times, using optional Chatterbox Multilingual V3 and an optional voice reference. Translate the captions first if the target audio should use another language. Listen through for lines that overlap or need timing edits. The exported video replaces source audio with speech only; original music and ambience are not retained. Your input file stays untouched.
- Chatterbox and its weights are optional. The base launcher does not install the audio runtime or download voice weights; the first dubbed export loads weights on demand. V2's Python package and Windows GPU path still need validation on the intended machine. The model is officially documented for 23 languages.

To experiment with the optional runtime, activate the V2 `.venv` and install `chatterbox-tts`, then restart the local studio. Installation and the first voice-model download are separate actions. Chatterbox's upstream Python setup is documented for Linux/Python 3.11, so package and CUDA compatibility on this Windows setup is not guaranteed yet.
- Optional Ollama model catalog and downloader for Qwen 3.5 2B/4B/9B or Gemma 3 4B. Qwen 3.5 4B is about 3.4 GB and recommended for this RTX 5060 Ti 16 GB system; keep VRAM headroom if Whisper is loaded at the same time.
- SRT and WebVTT sidecars, styled ASS sidecars, selectable subtitle tracks in MKV, portable text tracks in MP4, and burned-in MP4 output.
- VRAM-aware Whisper recommendation. RTX cards with at least 8 GB total VRAM default to Turbo; 16 GB cards can also try Large v3 manually, subject to other GPU workloads.

## Transcription models

V2 retains Tiny, Base, Small, Medium, Turbo, and Large v3. The model manager presents their rough download and VRAM classes. Measured free VRAM varies with the editor, video workload, and display processes; leave headroom and use a smaller model if CUDA runs out of memory.

The reachable `/api/health` and `/api/whisper/check` endpoints report detected VRAM when `nvidia-smi` is available. CPU fallback remains available if CUDA model loading fails. Model sizes and VRAM figures are approximate; available memory changes with active desktop apps and other GPU jobs.

## Export behavior

- SRT and WebVTT prioritize broad player/web support.
- ASS carries typography and supported word/entrance effects. Player support for advanced ASS styling varies.
- MKV contains a selectable ASS subtitle stream and keeps rich styling where the player supports it.
- MP4 uses a selectable `mov_text` subtitle stream for compatibility; the MP4 track is plain text. Use ASS sidecar or MKV for styling.
- Burn-in creates a new video and leaves the source untouched.

## Project layout

- `server.py` — local FastAPI services, transcription, translation, and render jobs.
- `subtitle_formats.py` — SRT, WebVTT, and styled ASS serialization.
- Ollama remains a separately installed local runtime; the app communicates with its loopback API and never sends subtitle text to a hosted service.
- `effects.js`, `app.js` — live subtitle customization and editor interactions.
- `effect-catalog.js` — the 90 motion/emphasis combinations.
- `index.html`, `styles.css`, `v2-design.css`, `liquid-glass.css` — editor interface, glass materials and responsive styling.
- `start.bat`, `requirements.txt` — Windows setup.
- `V2_NOTES.md` — V1 audit, model research, and remaining work.
- `DESIGN.md` — V2 visual system and motion rules.
- `assets/gsap.min.js` — locally bundled GSAP core for offline-safe interface motion.
- `THIRD_PARTY_NOTICES.md` — animation runtime attribution and license reference.
- `AUDIO_MODELS.md` — local dubbing and speech-enhancement research.
