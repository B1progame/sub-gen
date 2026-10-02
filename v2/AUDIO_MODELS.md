# Local audio model research

## Dubbing candidate: Chatterbox Multilingual V3

Resemble AI's upstream project documents its multilingual V3 model as a 0.5B parameter TTS model with 23 language IDs. The API accepts a text string and `language_id`, and can take an audio prompt path for voice conditioning. That makes it a plausible single-model fit for translating existing captions into dubbed speech while preserving cue start times. Upstream's Python install is `pip install chatterbox-tts`; it documents a Linux/Python 3.11 development environment, not a validated Windows GPU package setup. The V2 integration therefore stays optional and is not called production-ready until model load, generation, memory use, and FFmpeg muxing are verified on the target Windows machine.

V2 sends translated or edited caption text to the local Chatterbox Python runtime only after the user starts generation. Its current adapter generates each cue as a clip, places that clip at the cue's start time, then muxes the combined speech into a new MP4/MKV/MOV/WebM. It does not time-stretch dialogue to fit cue ends. The new video replaces source audio with speech only; original music and ambience are not retained, and the source file stays untouched. The UI warns that overlapping or rushed output needs review. Voice-reference audio is optional; use a reference only when authorized to reproduce that voice.

Chatterbox's source repository carries an MIT code license, but the model card/weights and intended usage terms should be checked separately when packaging or distributing weights.

## Speech enhancement candidate: DeepFilterNet

The upstream project provides pretrained speech-enhancement models, a Python package, and a `deepFilter` command-line workflow. Its README lists Windows among supported framework platforms and the code is MIT or Apache 2.0 licensed. It is a good candidate for optional noise reduction before recognition or voice delivery, but the V2 interface does not yet run this model.

## Recognition languages

Faster-Whisper exposes a 100-code language tuple through `faster_whisper.tokenizer._LANGUAGE_CODES`. The V2 `/api/languages` route uses that installed source of truth, with human-readable labels, and fills recognition and local LLM selectors. A full language catalog does not guarantee equal recognition accuracy across every language, model size, or recording condition. Turbo also is a transcription model, not a general translate-to-English mode.

## Source material

- [Chatterbox upstream README](https://github.com/resemble-ai/chatterbox/blob/master/README.md)
- [Chatterbox source license](https://github.com/resemble-ai/chatterbox/blob/master/LICENSE)
- [DeepFilterNet upstream README](https://github.com/Rikorose/DeepFilterNet/blob/main/README.md)
- [Faster-Whisper tokenizer](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/tokenizer.py)
- [OpenAI Whisper language catalog](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py)
