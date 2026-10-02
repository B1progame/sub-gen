# Caption Forge product truth

## Product

Caption Forge is an offline-first desktop studio for creating, styling, translating, and exporting subtitles from local video. The user wants the V2 workspace to treat subtitles and dubbing as equally important workflows.

## Audience and scene

Independent video creators and small production teams work with local footage on a Windows desktop. They need to turn speech into reviewable subtitles, adapt those subtitles for other languages, and create dubbed audio while keeping source media on their machine.

## Shipped in V2 today

- FastAPI local server and browser-based editor; uploaded media is processed by the local server.
- Faster-Whisper model catalog, word-timed captions, caption editing and preview.
- Caption styling, seven entrance/rhythm choices, five emphasis choices, and three starter presets.
- Argos Translate and optional loopback Ollama translation.
- SRT, WebVTT and ASS export, selectable subtitle tracks through FFmpeg, and burned-in MP4.

## User-directed work in progress

- Replace the V2 visual identity with a dark graphite Apple Liquid Glass inspired workspace, with cool accents and restrained acrylic surfaces.
- Use the user's supplied play-and-caption mark as the V2 app icon.
- Make the primary workspace serve captioning and dubbing equally.
- Expand the subtitle effect library to at least 80 distinguishable, usable effects, including researched patterns and original designs.
- Expand language availability and add local speech/audio models suitable for denoising and dubbing.

These are goals, not claims that the features are currently available.

## Constraints

- Offline-first: no caption text, video, or audio should be sent to a hosted service by default.
- Keep V1 intact. V2 launches on its own port and remains in its own folder.
- Optional large AI model dependencies must not be installed or downloaded as a side effect of opening the editor.
- Preserve accurate timing when subtitles are translated or dubbed; synthesized audio and subtitle timing need review before export.

## Decisions

- Aesthetic direction: user-selected “Apple liquid design.”
- Workflow hierarchy: subtitles and dubbing have equal priority.
- Target workflow: local transcription, translation, caption styling/export, and local dubbing in one project.

## Open product questions

- Which multilingual local TTS models are practical to support on Windows and the user's GPU without destabilizing the existing Faster-Whisper runtime?
- Speaker matching, diarization, and automatic shot-aware subtitle placement are not present in V2; scope requires implementation decisions.
