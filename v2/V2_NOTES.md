# V1 audit and V2 decisions

## V1 code audit

V1 is a local browser editor served from FastAPI. `app.js` owns playback, captions, styling, timeline, exports, and model UI in one large script. `server.py` manages Whisper setup, uploads, background jobs, SRT writing, and FFmpeg burn-in. CSS is split into several files and the main page is compressed onto a single HTML line.

The useful foundation to preserve is local video preview, editable timed captions, Faster-Whisper, VAD, model switching, FFmpeg, and the three-column workbench. The V1 UI already has a caption frame, colors, font, weight, basic timing tools, and SRT import/export.

V1 gaps found in the source:

- Whisper transcription asked for segment times only (`word_timestamps=False`), which prevented word-synced caption effects.
- Preview `paint()` repeatedly appended CSS text to inline styles rather than updating properties.
- The GSAP script and Google Fonts were fetched from public CDNs at run time, so the editor was not fully offline after installation.
- The only dedicated subtitle export was SRT, while the burn-in path was the only video delivery format.
- No translation, reusable subtitle-effect controls, or project-level language variants existed.
- The session logger deletes the previous session log on launch; the V2 copy keeps that behavior, so logs are diagnostic rather than an archive.
- Whisper jobs and model state are in memory and uploaded videos are not yet cleaned up automatically; hardening job persistence and cleanup remains future work.

## Reference project review

`Video-enhancer/REAL-Video-Enhancer` uses a model catalogue/download manager for visual video-restoration models such as RIFE frame interpolation and RealCUGAN upscaling. Those models do not perform speech recognition or subtitle translation, so V2 uses a separate catalog for Whisper and language models.

The subtitle-animation survey informed V2's expanded effect library. The searchable gallery combines ten motion behaviors with nine word treatments (90 combinations), including researched karaoke/highlight, pop, type-on, fade, rise, spring, marker, and underline patterns plus original focus/defocus, wipe, outline-pulse, glass-capsule, slanted-focus, and letter-spread treatments. Typography and placement remain independently editable. Exported ASS supports only the effects the serializer maps; SRT/VTT carry timed text without styling.

## V2 implementation

- Whisper requests word timestamps and groups words using the chosen words-per-beat count; timing and word confidence stay attached to each cue.
- A motion lab exposes font, size, weight, text/panel/highlight/outline colors, opacity, outline thickness, shadow, panel radius, tracking, alignment, casing, line spacing, panel padding, effect type, emphasis, words per beat, and speed. The searchable 90-combination gallery applies the supported live-preview controls.
- Preview animations respect reduced-motion settings. No CDN is required for the editor or its fonts.
- SRT, WebVTT, and styled ASS are available as subtitle files. FFmpeg muxes a selectable ASS track into MKV and a selectable `mov_text` track into MP4. Burn-in remains available as a separate output.
- Argos Translate provides compact local language packs. Optional Ollama integration sends text only to the loopback service and supports local Qwen 3.5 / Gemma 3 models for context-aware, more natural subtitle phrasing. Timing is retained; word timings are cleared when translated text changes.
- The starter LLM model is Qwen 3.5 4B (about 3.4 GB in Ollama's Q4_K_M build); the 9B option is about 6.6 GB. This machine reports an RTX 5060 Ti with 15.9 GB VRAM. GPU allocation from desktop apps and a loaded Whisper model reduces what is free, so 4B is the suggested first run and 9B is an opt-in quality experiment.
- Whisper picks Turbo by default on machines reporting 8–19 GB total NVIDIA VRAM, Medium below that, and Large v3 at 20 GB or more. Users can choose any catalogued model; the reported total is not free VRAM.
- `/api/languages` uses Faster-Whisper's language code catalog to populate recognition and local-LLM language controls; it falls back to an in-app label catalog if Faster-Whisper is unavailable.
- The Audio Lab has an optional local Chatterbox Multilingual V3 dubbing route. It synthesizes each caption with an optional user-selected voice reference and aligns clips at cue start times before muxing to a new video. It rejects unsupported TTS languages and produces an honest missing-runtime error when Chatterbox is not installed. It does not affect V1 or silently install the extra runtime.
- Model research recommends Chatterbox Multilingual V3 as the TTS candidate (23 official language IDs; 0.5B model) and DeepFilterNet as a speech-enhancement candidate. Upstream Chatterbox's documented development environment is Linux/Python 3.11, so Windows + the V2 interpreter/CUDA route is not yet validated. The runtime remains optional and needs a local installation/inference verification pass before release.
- The supplied Caption Forge play-and-caption mark is the V2 PNG/ICO app icon. The V2 interface uses a dark graphite palette, cool blue/cyan focus and restrained blur on navigation, transport, and floating panels, with reduced-transparency/motion fallbacks.

## Remaining scope

- The optional Chatterbox runtime has not been installed or exercised on Windows; validate model loading, sample timing, audio muxing, and GPU/CPU memory behavior before describing local dubbing as production-ready.
- Audio enhancement with DeepFilterNet, speaker diarization/voice assignment, speech-to-speech separation, project save/reopen, human-reviewed translation, cleanup/retention controls, and comprehensive upload limits remain future work.
- The user did not provide a separate reference product URL, so V2 uses the supplied app mark, the requested Liquid Glass direction, source-code analysis, and primary upstream model documentation.

## Research sources

- [OpenAI Whisper language codes](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py)
- [Faster-Whisper language tokens](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/tokenizer.py)
- [Chatterbox Multilingual V3 model notes, language IDs, and generation API](https://github.com/resemble-ai/chatterbox/blob/master/README.md)
- [Chatterbox source license](https://github.com/resemble-ai/chatterbox/blob/master/LICENSE)
- [DeepFilterNet installation, CLI, and license](https://github.com/Rikorose/DeepFilterNet/blob/main/README.md)
- The local sibling Video Enhancer source's FFmpeg subtitle/audio stream selection: `Video/Video-enhancer/REAL-Video-Enhancer/src/GenerateFFMpegCommand.py`.
