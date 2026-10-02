"""Caption Forge local processing server.

Keeps transcription and rendering on the user's computer.  Jobs run in worker
threads and are exposed as small polling endpoints so the UI never freezes.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from subtitle_formats import write_ass as write_styled_ass, write_srt as write_srt_file, write_vtt

# The browser polls setup/job status intentionally; keep that internal traffic
# out of the console so the terminal only shows actionable warnings/errors.
logging.getLogger("uvicorn.access").disabled = True

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UPLOADS, OUTPUTS = DATA / "uploads", DATA / "exports"
LOGS = ROOT / "logs"
for folder in (UPLOADS, OUTPUTS, LOGS): folder.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "caption-forge.log"
try:
    if LOG_FILE.exists(): LOG_FILE.unlink()
except OSError:
    pass
logger = logging.getLogger("captionforge")
logger.setLevel(logging.INFO)
logger.handlers.clear()
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(file_handler)
logger.info("Caption Forge session started")

app = FastAPI(title="Caption Forge", version="2.2.0")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

lock = threading.Lock()
_DUB_LOCK = threading.Lock()
_DUB_MODEL: Any = None
setup: dict[str, Any] = {"status": "uninitialized", "stage": "Ready to prepare your local studio", "progress": 0, "eta": None, "detail": "The Medium multilingual Whisper model will be downloaded once (about 1.5 GB)."}
jobs: dict[str, dict[str, Any]] = {}
model_cache: dict[str, Any] = {}
model_jobs: dict[str, dict[str, Any]] = {}
MODEL_CATALOGUE = {
    "tiny": {"label": "Tiny", "size": "75 MB", "note": "Fastest draft transcription", "vram_gb": 1},
    "base": {"label": "Base", "size": "145 MB", "note": "Fast, good for clean audio", "vram_gb": 1},
    "small": {"label": "Small", "size": "480 MB", "note": "Balanced speed and accuracy", "vram_gb": 2},
    "medium": {"label": "Medium", "size": "1.5 GB", "note": "Recommended multilingual quality", "vram_gb": 5},
    "large-v3": {"label": "Large v3", "size": "3.1 GB", "note": "Highest accuracy, slower", "vram_gb": 10},
    "turbo": {"label": "Turbo", "size": "1.6 GB", "note": "High quality with faster decoding", "vram_gb": 6},
}
OLLAMA_MODELS = {
    "qwen3.5:2b": {"size": "1.9 GB", "vram_gb": 4, "note": "Small multilingual model"},
    "qwen3.5:4b": {"size": "3.4 GB", "vram_gb": 8, "note": "Recommended natural subtitle translation"},
    "qwen3.5:9b": {"size": "6.6 GB", "vram_gb": 20, "note": "Higher quality; leave VRAM headroom"},
    "gemma3:4b": {"size": "3.3 GB", "vram_gb": 8, "note": "Alternative multilingual model"},
}
OLLAMA_URL = "http://127.0.0.1:11434"
WHISPER_LANGUAGE_NAMES = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "as": "Assamese", "az": "Azerbaijani",
    "ba": "Bashkir", "be": "Belarusian", "bg": "Bulgarian", "bn": "Bengali", "bo": "Tibetan",
    "br": "Breton", "bs": "Bosnian", "ca": "Catalan", "cs": "Czech", "cy": "Welsh",
    "da": "Danish", "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "et": "Estonian", "eu": "Basque", "fa": "Persian", "fi": "Finnish", "fo": "Faroese",
    "fr": "French", "gl": "Galician", "gu": "Gujarati", "ha": "Hausa", "haw": "Hawaiian",
    "he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "ht": "Haitian Creole", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian", "ja": "Japanese",
    "jw": "Javanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer", "kn": "Kannada",
    "ko": "Korean", "la": "Latin", "lb": "Luxembourgish", "ln": "Lingala", "lo": "Lao",
    "lt": "Lithuanian", "lv": "Latvian", "mg": "Malagasy", "mi": "Maori", "mk": "Macedonian",
    "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi", "ms": "Malay", "mt": "Maltese",
    "my": "Myanmar", "ne": "Nepali", "nl": "Dutch", "nn": "Norwegian Nynorsk", "no": "Norwegian",
    "oc": "Occitan", "pa": "Punjabi", "pl": "Polish", "ps": "Pashto", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sa": "Sanskrit", "sd": "Sindhi", "si": "Sinhala",
    "sk": "Slovak", "sl": "Slovenian", "sn": "Shona", "so": "Somali", "sq": "Albanian",
    "sr": "Serbian", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil",
    "te": "Telugu", "tg": "Tajik", "th": "Thai", "tk": "Turkmen", "tl": "Tagalog",
    "tr": "Turkish", "tt": "Tatar", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek",
    "vi": "Vietnamese", "yi": "Yiddish", "yo": "Yoruba", "yue": "Cantonese", "zh": "Chinese",
}

def update(target: dict[str, Any], **values: Any) -> None:
    with lock: target.update(values)

def model_download_error(exc: Exception) -> str:
    """Turn common model-fetch failures into a useful, safe UI message."""
    detail = f"{type(exc).__name__}: {exc}".lower()
    if "winerror 10013" in detail or "socket access" in detail:
        return ("Windows denied the outbound connection to Hugging Face (WinError 10013). "
                "Check the firewall, proxy, or network policy for the Python process, then retry. "
                "No model files were downloaded.")
    if any(marker in detail for marker in ("connecterror", "connection refused", "name or service not known", "temporary failure in name resolution", "timed out")):
        return ("Could not connect to Hugging Face to fetch the model. Check your internet or proxy settings, "
                "then retry. No model files were downloaded.")
    return f"Model download failed ({type(exc).__name__}). Open Session log for details, then retry."

def ffmpeg_present() -> bool:
    return ffmpeg_executable() is not None

def ffmpeg_executable() -> str | None:
    system_binary = shutil.which("ffmpeg")
    if system_binary:
        return system_binary
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def cuda_device_count() -> int:
    try:
        import ctranslate2
        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0

def gpu_memory_gb() -> float | None:
    binary = shutil.which("nvidia-smi")
    if not binary:
        return None
    try:
        result = subprocess.run([binary, "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=3, check=True)
        values = [float(line.strip()) / 1024 for line in result.stdout.splitlines() if line.strip()]
        return round(max(values), 1) if values else None
    except Exception:
        return None

def recommended_model() -> str:
    memory = gpu_memory_gb()
    if memory is None: return "medium"
    if memory >= 20: return "large-v3"
    if memory >= 8: return "turbo"
    if memory >= 5: return "medium"
    if memory >= 2: return "small"
    return "base"

def setup_worker(model_name: str) -> None:
    try:
        update(setup, status="working", stage="Checking local acceleration", progress=6, eta="about 3 minutes", detail="Choosing the fastest compatible execution mode.")
        time.sleep(.35)
        update(setup, stage="Preparing the Whisper runtime", progress=18, eta="about 3 minutes", detail="Loading the transcription engine and its audio decoder.")
        from faster_whisper import WhisperModel
        time.sleep(.35)
        update(setup, stage=f"Downloading {model_name.title()} model", progress=38, eta="1–4 minutes", detail="This happens once. Download time depends on your connection.")
        # Loading the model triggers CTranslate2/Hugging Face's cached download.
        device = "cuda" if _cuda_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        try:
            model_cache[model_name] = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception as exc:
            if device != "cuda": raise
            logger.warning("CUDA model load failed; falling back to CPU: %s", exc)
            device, compute = "cpu", "int8"
            model_cache[model_name] = WhisperModel(model_name, device=device, compute_type=compute)
        model_cache["model"] = model_cache[model_name]
        model_cache["name"] = model_name
        logger.info("Whisper model ready: %s (%s/%s)", model_name, device, compute)
        update(setup, status="ready", stage="Studio ready", progress=100, eta=None, detail=f"{model_name.title()} is installed locally using {device.upper()} processing.", device=device, ffmpeg=ffmpeg_present(), model=model_name)
    except Exception as exc:
        logger.exception("Whisper setup failed")
        update(setup, status="error", stage="Setup needs attention", progress=0, eta=None, detail=str(exc))

def model_download_worker(model_name: str) -> None:
    job = model_jobs[model_name]
    try:
        from faster_whisper import WhisperModel
        device = "cuda" if _cuda_available() else "cpu"; compute = "float16" if device == "cuda" else "int8"
        update(job, status="working", progress=12, stage="Preparing download", detail=f"Fetching {MODEL_CATALOGUE[model_name]['size']} of model data")
        try:
            model_cache[model_name] = WhisperModel(model_name, device=device, compute_type=compute)
        except Exception as exc:
            if device != "cuda": raise
            logger.warning("CUDA model download load failed; falling back to CPU: %s", exc)
            device, compute = "cpu", "int8"
            model_cache[model_name] = WhisperModel(model_name, device=device, compute_type=compute)
        model_cache["model"] = model_cache[model_name]
        model_cache["name"] = model_name
        update(setup, model=model_name, device=device)
        update(job, status="ready", progress=100, stage="Model ready", detail=f"{MODEL_CATALOGUE[model_name]['label']} is ready on {device.upper()}", device=device)
        logger.info("Downloaded Whisper model: %s", model_name)
    except Exception as exc:
        logger.exception("Model download failed: %s", model_name)
        update(job, status="error", progress=0, stage="Download failed", detail=model_download_error(exc))

def _cuda_available() -> bool:
    try:
        import ctranslate2
        # CTranslate2 reports compute *types* (float16/int8...), not a literal
        # "cuda" capability.  The previous check therefore always fell back
        # to CPU even when an NVIDIA device was available.
        return cuda_device_count() > 0 and "float16" in ctranslate2.get_supported_compute_types("cuda")
    except Exception:
        return False

def srt_stamp(seconds: float) -> str:
    ms = int(round(seconds * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(captions: list[dict[str, Any]], path: Path) -> None:
    blocks = [f"{i}\n{srt_stamp(float(c['start']))} --> {srt_stamp(float(c['end']))}\n{str(c['text']).strip()}" for i, c in enumerate(captions, 1)]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

def ass_stamp(seconds: float) -> str:
    cs = int(round(max(0, seconds) * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def ass_color(hex_value: str) -> str:
    value = str(hex_value or "#ffffff").lstrip("#")
    if len(value) != 6: value = "ffffff"
    return f"&H00{value[4:6]}{value[2:4]}{value[0:2]}&".upper()

def write_ass(captions: list[dict[str, Any]], style: dict[str, Any], path: Path) -> None:
    font = str(style.get("font", "Inter")).replace(",", " ")
    size = max(18, min(120, int(float(style.get("size", 42)))))
    weight = -1 if int(style.get("weight", 600)) >= 700 else 0
    text_color = ass_color(style.get("color", "#ffffff"))
    panel = ass_color(style.get("bg", "#111827"))
    opacity = max(0, min(100, int(float(style.get("opacity", 72)))))
    alpha = f"{round((100 - opacity) * 255 / 100):02X}"
    panel = panel.replace("&H00", f"&H{alpha}")
    header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
    header += f"Style: Caption,{font},{size},{text_color},{text_color},&H90000000,{panel},{weight},0,0,0,100,100,0,0,3,2,0,2,90,90,84,1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    events=[]
    for c in captions:
        text=str(c.get("text", "")).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")
        events.append(f"Dialogue: 0,{ass_stamp(float(c['start']))},{ass_stamp(float(c['end']))},Caption,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")

def video_look_filters(style: dict[str, Any]) -> list[str]:
    raw = style.get("videoLook")
    if not isinstance(raw, dict):
        return []
    def value(key: str, fallback: float, low: float, high: float) -> float:
        try:
            return max(low, min(high, float(raw.get(key, fallback))))
        except (TypeError, ValueError):
            return fallback
    exposure = value("exposure", 0, -2, 2)
    contrast = value("contrast", 1, .5, 1.5)
    saturation = value("saturation", 1, 0, 2)
    warmth = value("warmth", 0, -100, 100) / 100 * .18
    shadows = value("shadows", 0, -100, 100) / 100 * .18
    midtones = value("midtones", 0, -100, 100) / 100 * .18
    highlights = value("highlights", 0, -100, 100) / 100 * .18
    sharpness = value("sharpness", 0, 0, 100) / 100 * 1.5
    vignette = value("vignette", 0, 0, 100)
    filters: list[str] = []
    if exposure:
        filters.append(f"exposure=exposure={exposure:.3f}")
    if contrast != 1 or saturation != 1:
        filters.append(f"eq=contrast={contrast:.3f}:saturation={saturation:.3f}")
    if any((warmth, shadows, midtones, highlights)):
        red_s = warmth + shadows
        red_m = warmth + midtones
        red_h = warmth + highlights
        filters.append("colorbalance=" + ":".join((
            f"rs={red_s:.3f}", f"bs={-red_s:.3f}",
            f"rm={red_m:.3f}", f"bm={-red_m:.3f}",
            f"rh={red_h:.3f}", f"bh={-red_h:.3f}",
        )))
    if sharpness:
        filters.append(f"unsharp=5:5:{sharpness:.3f}:5:5:0")
    if vignette:
        filters.append(f"vignette=angle=PI*{vignette / 400:.4f}")
    if raw.get("flipX") is True:
        filters.append("hflip")
    if raw.get("flipY") is True:
        filters.append("vflip")
    return filters


def burn_worker(job_id: str, video_path: Path, captions: list[dict[str, Any]], style: dict[str, Any]) -> None:
    job = jobs[job_id]
    try:
        binary = ffmpeg_executable()
        if not binary: raise RuntimeError("Caption rendering requires the bundled FFmpeg runtime. Restart Caption Forge after installation.")
        ass_path = OUTPUTS / f"{job_id}.ass"; output = OUTPUTS / f"{job_id}.mp4"; write_styled_ass(captions, style, ass_path)
        update(job, status="working", progress=10, stage="Preparing burn-in render", eta="calculating…")
        subtitle_filter_path = ass_path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
        render_filters = video_look_filters(style)
        render_filters.append(f"ass=filename='{subtitle_filter_path}'")
        video_filter = ",".join(render_filters)
        with tempfile.TemporaryFile() as error_log:
            process = subprocess.Popen([binary, "-y", "-i", str(video_path), "-vf", video_filter, "-c:a", "copy", "-movflags", "+faststart", str(output)], stdout=subprocess.DEVNULL, stderr=error_log)
            started = time.monotonic()
            while process.poll() is None:
                if time.monotonic() - started > 60 * 60:
                    process.kill()
                    raise TimeoutError("Caption rendering exceeded the one-hour limit")
                update(job, status="working", progress=min(92, int(job.get("progress", 10)) + 1), stage="Burning captions into video", eta="Rendering locally…")
                time.sleep(1)
            if process.returncode != 0:
                error_log.seek(max(0, error_log.tell() - 1200))
                raise RuntimeError(error_log.read().decode("utf-8", errors="replace")[-1000:])
        update(job, status="done", progress=100, stage="Burned video ready", eta=None, download=f"/api/download/{output.name}")
    except Exception as exc:
        logger.exception("Caption burn job failed: %s", job_id)
        update(job, status="error", stage="Video render stopped", detail="Could not burn captions into this video. Open the session log for details.", eta=None)

def transcription_worker(job_id: str, video_path: Path, language: str | None, words_per_beat: int = 5) -> None:
    job = jobs[job_id]
    try:
        if setup["status"] != "ready": raise RuntimeError("Finish first-run setup before transcribing.")
        update(job, status="working", progress=4, stage="Reading audio track", eta="calculating…")
        model = model_cache["model"]
        update(job, progress=12, stage="Transcribing speech", eta="estimating after first segment")
        segments, info = model.transcribe(str(video_path), language=language or None, vad_filter=True, word_timestamps=True, beam_size=5)
        total = float(info.duration or 1)
        captions = []
        for segment in segments:
            words = [{"word": word.word, "start": round(word.start, 3), "end": round(word.end, 3), "probability": round(float(word.probability or 0), 3)} for word in (segment.words or [])]
            if words:
                groups: list[list[dict[str, Any]]] = []
                current: list[dict[str, Any]] = []
                for word in words:
                    current.append(word)
                    token = word["word"].strip()
                    if len(current) >= words_per_beat or (token.endswith((".", "?", "!", ",", ";", ":")) and len(current) >= 2):
                        groups.append(current); current = []
                if current: groups.append(current)
                for group in groups:
                    text = "".join(item["word"] for item in group).strip()
                    if text:
                        captions.append({"id": len(captions) + 1, "start": group[0]["start"], "end": group[-1]["end"], "text": text, "words": group})
            elif segment.text.strip():
                captions.append({"id": len(captions) + 1, "start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip(), "words": []})
            pct = min(96, 12 + int(segment.end / total * 84))
            remaining = max(0, total - segment.end)
            update(job, progress=pct, stage="Transcribing speech", eta=f"{remaining:.0f}s of media remaining", captions=captions)
        srt = OUTPUTS / f"{job_id}.srt"; write_srt(captions, srt)
        update(job, status="done", progress=100, stage="Captions ready", eta=None, captions=captions, download=f"/api/download/{job_id}.srt")
    except Exception as exc:
        logger.exception("Transcription job failed: %s", job_id)
        raw = str(exc).lower()
        if "invalid data" in raw or "processing input" in raw:
            detail = "Caption Forge could not read this video. Try an MP4, MOV, or WebM file with a standard audio track."
        elif "no such file" in raw:
            detail = "The selected video is no longer available. Choose it again and retry."
        else:
            detail = "Transcription stopped unexpectedly. Open the session log for the technical details, then try again."
        update(job, status="error", stage="Transcription stopped", detail=detail, eta=None)

@app.get("/api/health")
def health() -> dict[str, Any]: return {"ok": True, "ffmpeg": ffmpeg_present(), "cuda": _cuda_available(), "cuda_devices": cuda_device_count(), "gpu_vram_gb": gpu_memory_gb(), "log_file": str(LOG_FILE), "models": list(model_cache)}

@app.get("/api/languages")
def speech_languages() -> dict[str, Any]:
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        codes = list(_LANGUAGE_CODES)
    except Exception:
        codes = list(WHISPER_LANGUAGE_NAMES)
    return {"languages": [{"code": code, "name": WHISPER_LANGUAGE_NAMES.get(code, code.upper())} for code in codes]}

@app.get("/api/audio/status")
def audio_status() -> dict[str, Any]:
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: F401
        runtime = True
        detail = "Chatterbox Multilingual is installed. The model loads when you generate a dub."
    except Exception as exc:
        runtime = False
        detail = "Optional Chatterbox runtime is not installed in this Python environment."
        logger.info("Optional TTS runtime unavailable: %s", exc)
    supported = ["ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr", "zh"]
    return {"runtime": runtime, "model_loaded": _DUB_MODEL is not None, "model": "Chatterbox Multilingual V3", "languages": supported, "detail": detail}

def dub_worker(job_id: str, video_path: Path, voice_path: Path | None, captions: list[dict[str, Any]], language: str) -> None:
    job = jobs[job_id]
    audio_path = OUTPUTS / f"{job_id}.wav"
    output = OUTPUTS / f"{job_id}{video_path.suffix.lower()}"
    try:
        import numpy as np
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        global _DUB_MODEL
        update(job, status="working", progress=2, stage="Loading local voice model", eta="First load can take several minutes")
        with _DUB_LOCK:
            if _DUB_MODEL is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                _DUB_MODEL = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
            model = _DUB_MODEL
        sample_rate = int(model.sr)
        total_seconds = max(float(caption["end"]) for caption in captions)
        mix = np.zeros(max(1, int((total_seconds + 0.5) * sample_rate)), dtype=np.float32)
        for index, caption in enumerate(captions):
            text = str(caption.get("text", "")).strip()
            if not text:
                continue
            update(job, status="working", progress=8 + round(index / max(1, len(captions)) * 77), stage=f"Speaking line {index + 1} of {len(captions)}", eta="Generating locally")
            options: dict[str, Any] = {"language_id": language}
            if voice_path is not None:
                options["audio_prompt_path"] = str(voice_path)
            generated = model.generate(text[:1200], **options)
            samples = generated.detach().float().cpu().numpy().reshape(-1)
            peak = float(np.max(np.abs(samples))) if samples.size else 0.0
            if peak > 1e-5:
                samples = samples * (0.72 / peak)
            start = max(0, round(float(caption["start"]) * sample_rate))
            end = min(mix.size, start + samples.size)
            if end > start:
                mix[start:end] += samples[:end - start]
        mix = np.clip(mix, -0.98, 0.98)
        import wave
        pcm = (mix * 32767).astype("<i2", copy=False)
        with wave.open(str(audio_path), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(sample_rate); wav.writeframes(pcm.tobytes())

        binary = ffmpeg_executable()
        if not binary:
            raise RuntimeError("FFmpeg is required to mux the dubbed audio into your video.")
        update(job, progress=90, stage="Muxing dubbed audio into the video", eta="Finalizing locally")
        audio_codec = "libopus" if output.suffix == ".webm" else "aac"
        command = [binary, "-y", "-i", str(video_path), "-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0", "-map", "0:s?", "-c:v", "copy", "-c:a", audio_codec, "-b:a", "160k", "-c:s", "copy", "-metadata:s:a:0", f"language={language}"]
        if output.suffix == ".mp4": command += ["-movflags", "+faststart"]
        command.append(str(output))
        process = subprocess.run(command, capture_output=True, text=True, timeout=60 * 60)
        if process.returncode != 0: raise RuntimeError(process.stderr[-1400:])
        update(job, status="done", progress=100, stage="Dubbed video ready", eta=None, download=f"/api/download/{output.name}", detail="Original video is unchanged. Dub timing follows the caption start times; review the result before delivery.")
    except ImportError as exc:
        logger.exception("Local dubbing runtime is unavailable")
        update(job, status="error", progress=0, stage="Optional voice runtime is missing", detail="Install the optional Chatterbox Multilingual runtime in the V2 Python environment, then restart the local studio. No model was downloaded.", eta=None)
    except Exception as exc:
        logger.exception("Dubbing job failed: %s", job_id)
        update(job, status="error", progress=0, stage="Could not generate the dubbed video", detail=str(exc)[:500], eta=None)
    finally:
        if jobs.get(job_id, {}).get("status") != "done":
            try: output.unlink(missing_ok=True)
            except OSError: pass
        for path in (video_path, voice_path, audio_path):
            if path:
                try: path.unlink(missing_ok=True)
                except OSError: pass

@app.post("/api/dub")
async def dub_video(video: UploadFile = File(...), captions_json: str = "[]", language: str = "en", voice_reference: UploadFile | None = File(default=None)) -> dict[str, str]:
    try:
        captions = json.loads(captions_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Dub caption data is invalid") from exc
    status = audio_status()
    if not status["runtime"]:
        raise HTTPException(503, status["detail"])
    if language not in status["languages"]:
        raise HTTPException(400, "Choose one of the supported Chatterbox languages")
    if not isinstance(captions, list) or not captions or len(captions) > 5000:
        raise HTTPException(400, "Add between 1 and 5,000 captions before generating a dub")
    checked: list[dict[str, Any]] = []
    for item in captions:
        try:
            start, end = float(item["start"]), float(item["end"])
            text = str(item.get("text", "")).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(400, "Each caption needs valid start and end times") from exc
        if start < 0 or end <= start or end - start > 3600 or len(text) > 1200:
            raise HTTPException(400, "Caption timing or text length is outside the supported range")
        checked.append({"start": start, "end": end, "text": text})
    suffix = Path(video.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4", ".mkv", ".mov", ".webm"}:
        raise HTTPException(400, "Choose an MP4, MKV, MOV, or WebM video")
    job_id = f"dub-{uuid.uuid4().hex}"
    video_path = UPLOADS / f"{job_id}{suffix}"
    voice_path: Path | None = None
    try:
        with video_path.open("wb") as out:
            while chunk := await video.read(1024 * 1024): out.write(chunk)
        if voice_reference and voice_reference.filename:
            voice_suffix = Path(voice_reference.filename).suffix.lower()
            if voice_suffix not in {".wav", ".mp3", ".m4a", ".flac", ".ogg"}:
                raise HTTPException(400, "Voice reference must be WAV, MP3, M4A, FLAC, or OGG")
            voice_path = UPLOADS / f"{job_id}-voice{voice_suffix}"
            with voice_path.open("wb") as out:
                while chunk := await voice_reference.read(1024 * 1024): out.write(chunk)
    except Exception:
        video_path.unlink(missing_ok=True)
        if voice_path: voice_path.unlink(missing_ok=True)
        raise
    finally:
        await video.close()
        if voice_reference: await voice_reference.close()
    jobs[job_id] = {"status": "queued", "progress": 0, "stage": "Queued local dubbing", "eta": None}
    threading.Thread(target=dub_worker, args=(job_id, video_path, voice_path, checked, language), daemon=True).start()
    return {"job_id": job_id}

@app.get("/api/log")
def session_log() -> FileResponse:
    return FileResponse(LOG_FILE, filename=LOG_FILE.name, media_type="text/plain")

@app.get("/api/whisper/check")
def whisper_check() -> dict[str, Any]:
    try:
        import faster_whisper  # noqa: F401
        runtime = True; runtime_detail = "Faster-Whisper runtime is importable."
    except Exception as exc:
        runtime = False; runtime_detail = str(exc)
    active = setup.get("model") or model_cache.get("name")
    return {"runtime": runtime, "runtime_detail": runtime_detail, "model_loaded": bool(model_cache.get("model")), "active_model": active, "device": setup.get("device"), "cuda": _cuda_available(), "cuda_devices": cuda_device_count(), "gpu_vram_gb": gpu_memory_gb(), "ffmpeg": ffmpeg_present(), "ready": runtime and bool(model_cache.get("model"))}

@app.get("/api/models")
def models() -> dict[str, Any]:
    return {"active": setup.get("model"), "models": [{"name": name, **meta, "installed": name in model_cache, "downloading": model_jobs.get(name, {}).get("status") == "working"} for name, meta in MODEL_CATALOGUE.items()]}

@app.post("/api/models/download")
def download_model(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    name = str(payload.get("model", "medium"))
    if name not in MODEL_CATALOGUE: raise HTTPException(400, "Unknown Whisper model")
    if name in model_cache: return {"status": "ready", "model": name, **model_jobs.get(name, {})}
    if model_jobs.get(name, {}).get("status") == "working": return {"status": "working", "model": name, **model_jobs[name]}
    model_jobs[name] = {"status": "queued", "progress": 0, "stage": "Queued", "detail": "Waiting for a local worker"}
    threading.Thread(target=model_download_worker, args=(name,), daemon=True).start()
    return {"status": "queued", "model": name, **model_jobs[name]}

@app.get("/api/models/{model_name}/status")
def model_status(model_name: str) -> dict[str, Any]:
    if model_name not in MODEL_CATALOGUE: raise HTTPException(404, "Unknown Whisper model")
    if model_name in model_cache: return {"status": "ready", "progress": 100, "stage": "Model ready", "model": model_name}
    return {"model": model_name, **model_jobs.get(model_name, {"status": "idle", "progress": 0, "stage": "Not installed"})}

@app.get("/api/setup/status")
def setup_status() -> dict[str, Any]: return setup

@app.post("/api/setup/start")
def start_setup(model: str | None = None) -> dict[str, Any]:
    if setup["status"] == "working": return setup
    if setup["status"] == "ready": return setup
    model = model if model in MODEL_CATALOGUE else recommended_model()
    thread = threading.Thread(target=setup_worker, args=(model,), daemon=True); thread.start()
    return setup

@app.post("/api/transcribe")
async def transcribe(video: UploadFile = File(...), language: str = "", words_per_beat: int = 5) -> dict[str, str]:
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    job_id = uuid.uuid4().hex
    target = UPLOADS / f"{job_id}{suffix}"
    with target.open("wb") as out:
        while chunk := await video.read(1024 * 1024): out.write(chunk)
    jobs[job_id] = {"status":"queued", "progress":0, "stage":"Queued", "eta":None, "captions":[]}
    threading.Thread(target=transcription_worker, args=(job_id, target, language, max(1, min(12, words_per_beat))), daemon=True).start()
    return {"job_id": job_id}

@app.post("/api/burn")
async def burn_captions(video: UploadFile = File(...), captions_json: str = "[]", style_json: str = "{}") -> dict[str, str]:
    try:
        captions = json.loads(captions_json); style = json.loads(style_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Caption render data is invalid") from exc
    if not isinstance(captions, list) or not captions: raise HTTPException(400, "Add or import captions before creating a burned video")
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"; job_id = f"burn-{uuid.uuid4().hex}"; target = UPLOADS / f"{job_id}{suffix}"
    with target.open("wb") as out:
        while chunk := await video.read(1024 * 1024): out.write(chunk)
    jobs[job_id] = {"status":"queued", "progress":0, "stage":"Queued burn-in render", "eta":None, "captions":[]}
    threading.Thread(target=burn_worker, args=(job_id, target, captions, style), daemon=True).start()
    return {"job_id": job_id}

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    if job_id not in jobs: raise HTTPException(404, "Unknown job")
    return jobs[job_id]

@app.post("/api/export/srt")
def export_srt(payload: dict[str, Any]) -> dict[str, str]:
    captions = payload.get("captions", [])
    job_id = uuid.uuid4().hex; output = OUTPUTS / f"manual-{job_id}.srt"; write_srt_file(captions, output)
    return {"download": f"/api/download/manual-{job_id}.srt"}

@app.post("/api/export/subtitles")
def export_subtitles(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    captions = payload.get("captions", [])
    style = payload.get("style", {})
    format_name = str(payload.get("format", "srt")).lower()
    if not isinstance(captions, list) or not captions:
        raise HTTPException(400, "Add or import captions before exporting")
    if format_name not in {"srt", "vtt", "ass"}:
        raise HTTPException(400, "Choose SRT, WebVTT, or ASS")
    name = f"captions-{uuid.uuid4().hex}.{format_name}"
    output = OUTPUTS / name
    if format_name == "srt": write_srt_file(captions, output)
    elif format_name == "vtt": write_vtt(captions, output)
    else: write_styled_ass(captions, style, output)
    return {"download": f"/api/download/{name}", "filename": name, "format": format_name}

def mux_worker(job_id: str, video_path: Path, captions: list[dict[str, Any]], style: dict[str, Any], container: str) -> None:
    job = jobs[job_id]
    subtitle_path = OUTPUTS / f"{job_id}.ass"
    output = OUTPUTS / f"{job_id}.{container}"
    try:
        binary = ffmpeg_executable()
        if not binary: raise RuntimeError("Caption tracks require FFmpeg. Restart Caption Forge after installation.")
        write_styled_ass(captions, style, subtitle_path)
        update(job, status="working", progress=14, stage="Adding selectable subtitle track", eta="Muxing locally…")
        subtitle_codec = "ass" if container == "mkv" else "mov_text"
        command = [binary, "-y", "-i", str(video_path), "-i", str(subtitle_path), "-map", "0", "-map", "1:0", "-c", "copy", "-c:s", subtitle_codec, "-metadata:s:s:0", "language=und", "-disposition:s:0", "default", "-movflags", "+faststart", str(output)]
        process = subprocess.run(command, capture_output=True, text=True, timeout=60 * 60)
        if process.returncode != 0: raise RuntimeError(process.stderr[-1200:])
        update(job, status="done", progress=100, stage="Selectable subtitle track ready", eta=None, download=f"/api/download/{output.name}")
    except Exception as exc:
        logger.exception("Subtitle mux job failed: %s", job_id)
        update(job, status="error", progress=0, stage="Could not add subtitle track", detail=str(exc)[:400], eta=None)

@app.post("/api/export/mux")
async def mux_subtitles(video: UploadFile = File(...), captions_json: str = "[]", style_json: str = "{}", container: str = "mkv") -> dict[str, str]:
    if container not in {"mkv", "mp4"}:
        raise HTTPException(400, "Choose MKV or MP4 for a selectable subtitle track")
    try:
        captions, style = json.loads(captions_json), json.loads(style_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Subtitle track data is invalid") from exc
    if not isinstance(captions, list) or not captions:
        raise HTTPException(400, "Add or import captions before exporting")
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    job_id = f"track-{uuid.uuid4().hex}"
    target = UPLOADS / f"{job_id}{suffix}"
    try:
        with target.open("wb") as out:
            while chunk := await video.read(1024 * 1024): out.write(chunk)
    finally:
        await video.close()
    jobs[job_id] = {"status": "queued", "progress": 0, "stage": "Queued subtitle track", "eta": None}
    threading.Thread(target=mux_worker, args=(job_id, target, captions, style, container), daemon=True).start()
    return {"job_id": job_id}

@app.get("/api/translation/languages")
def translation_languages() -> dict[str, Any]:
    try:
        import argostranslate.package as package
        import argostranslate.translate as translate
        installed = [{"from": lang.code, "from_name": lang.name, "to": target.code, "to_name": target.name} for lang in translate.get_installed_languages() for target in lang.translations_from]
        package.update_package_index()
        available = [{"from": item.from_code, "from_name": item.from_name, "to": item.to_code, "to_name": item.to_name} for item in package.get_available_packages()]
        return {"installed": installed, "available": available}
    except ImportError as exc:
        raise HTTPException(503, "Install Argos Translate from requirements.txt to use local translation") from exc
    except Exception as exc:
        logger.exception("Could not load translation language catalog")
        raise HTTPException(503, f"Could not load the local translation catalog: {exc}") from exc

@app.post("/api/translation/install")
def install_translation(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    source, target = str(payload.get("source", "")), str(payload.get("target", ""))
    try:
        import argostranslate.package as package
        package.update_package_index()
        selected = next((item for item in package.get_available_packages() if item.from_code == source and item.to_code == target), None)
        if selected is None: raise HTTPException(404, "That local language pair is not available")
        package.install_from_path(selected.download())
        return {"status": "ready", "source": source, "target": target}
    except HTTPException: raise
    except ImportError as exc: raise HTTPException(503, "Install Argos Translate from requirements.txt first") from exc
    except Exception as exc:
        logger.exception("Translation model installation failed")
        raise HTTPException(502, f"Could not install this language pair: {exc}") from exc

@app.post("/api/translation/translate")
def translate_captions(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    captions = payload.get("captions", [])
    source, target = str(payload.get("source", "")), str(payload.get("target", ""))
    if not isinstance(captions, list) or not captions: raise HTTPException(400, "Add or import captions before translating")
    provider = str(payload.get("provider", "argos"))
    if provider == "ollama":
        model = str(payload.get("model", "qwen3.5:4b"))
        if model not in OLLAMA_MODELS: raise HTTPException(400, "Choose a supported local translation model")
        source_name, target_name = str(payload.get("source_name", source)), str(payload.get("target_name", target))
        request_body = json.dumps({"model": model, "stream": False, "format": "json", "think": False, "keep_alive": "5m", "messages": [
            {"role": "system", "content": f"You translate video subtitles from {source_name} to {target_name}. Write natural, contemporary, idiomatic spoken {target_name}. Preserve intent, humor, register, names, and speaker voice. Keep each line concise enough to read on screen. Return only valid JSON with a 'translations' array, preserving every integer 'index' and translating only its 'text'. Do not merge lines, omit entries, explain, or add commentary."},
            {"role": "user", "content": json.dumps({"captions": [{"index": i, "text": str(caption.get("text", ""))} for i, caption in enumerate(captions)]}, ensure_ascii=False)}
        ]}).encode("utf-8")
        request = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=request_body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60 * 30) as response: model_result = json.loads(response.read().decode("utf-8"))
            translated_data = json.loads(model_result.get("message", {}).get("content", "{}"))
            translated_lines = translated_data.get("translations", [])
            by_index = {int(line["index"]): str(line["text"]) for line in translated_lines}
            if len(by_index) != len(captions) or any(index not in by_index for index in range(len(captions))):
                raise ValueError("The local model did not return every subtitle line")
            translated = [{**caption, "text": by_index[index], "words": []} for index, caption in enumerate(captions)]
            return {"captions": translated, "source": source, "target": target, "provider": provider, "model": model}
        except urllib.error.URLError as exc:
            raise HTTPException(503, "Ollama is unavailable. Start its local service and download a translation model first.") from exc
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(502, f"The local model returned an invalid translation: {exc}") from exc
        except Exception as exc:
            logger.exception("Local language-model translation failed")
            raise HTTPException(502, f"Local translation failed: {exc}") from exc
    if provider != "argos": raise HTTPException(400, "Choose Argos or Ollama local translation")
    try:
        import argostranslate.translate as translate
        languages = translate.get_installed_languages()
        source_language = next((lang for lang in languages if lang.code == source), None)
        target_language = next((lang for lang in languages if lang.code == target), None)
        translator = source_language.get_translation(target_language) if source_language and target_language else None
        if translator is None: raise HTTPException(409, "Install this local translation model first")
        translated = [{**caption, "text": translator.translate(str(caption.get("text", ""))), "words": []} for caption in captions]
        return {"captions": translated, "source": source, "target": target}
    except HTTPException: raise
    except ImportError as exc: raise HTTPException(503, "Install Argos Translate from requirements.txt first") from exc
    except Exception as exc:
        logger.exception("Local subtitle translation failed")
        raise HTTPException(500, f"Local translation failed: {exc}") from exc

def ollama_pull_worker(job_id: str, model: str) -> None:
    job = jobs[job_id]
    try:
        body = json.dumps({"model": model, "stream": True}).encode("utf-8")
        request = urllib.request.Request(f"{OLLAMA_URL}/api/pull", data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=60 * 60) as response:
            for line in response:
                if not line.strip(): continue
                status = json.loads(line.decode("utf-8"))
                total, completed = int(status.get("total", 0)), int(status.get("completed", 0))
                percent = round(completed / total * 100) if total else int(job.get("progress", 1))
                update(job, status="working", progress=min(99, percent), stage=status.get("status", "Downloading model"), detail=f"{completed // 1_000_000} / {max(1, total // 1_000_000)} MB")
        update(job, status="done", progress=100, stage="Translation model ready", eta=None)
    except Exception as exc:
        logger.exception("Ollama language model download failed: %s", model)
        update(job, status="error", progress=0, stage="Model download failed", detail=str(exc)[:300], eta=None)

@app.get("/api/translation/models")
def translation_models() -> dict[str, Any]:
    try:
        request = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=2) as response: data = json.loads(response.read().decode("utf-8"))
        installed = [item.get("name", "") for item in data.get("models", [])]
        return {"available": True, "installed": installed, "catalogue": OLLAMA_MODELS, "gpu_vram_gb": gpu_memory_gb()}
    except Exception:
        return {"available": False, "installed": [], "catalogue": OLLAMA_MODELS, "gpu_vram_gb": gpu_memory_gb()}

@app.post("/api/translation/models/pull")
def pull_translation_model(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    model = str(payload.get("model", ""))
    if model not in OLLAMA_MODELS: raise HTTPException(400, "Choose a model from the local translation catalog")
    job_id = f"model-{uuid.uuid4().hex}"
    jobs[job_id] = {"status": "queued", "progress": 0, "stage": "Queued local model", "eta": None}
    threading.Thread(target=ollama_pull_worker, args=(job_id, model), daemon=True).start()
    return {"job_id": job_id, "model": model}

@app.get("/api/download/{filename}")
def download(filename: str) -> FileResponse:
    file = OUTPUTS / Path(filename).name
    if not file.exists(): raise HTTPException(404, "Export no longer exists")
    return FileResponse(file, filename=file.name)

@app.get("/")
def index() -> FileResponse: return FileResponse(ROOT / "index.html")

@app.get("/{file_path:path}")
def frontend_file(file_path: str) -> FileResponse:
    """Serve the small framework-free frontend without exposing project data."""
    candidate = (ROOT / file_path).resolve()
    if ROOT not in candidate.parents or not candidate.is_file():
        raise HTTPException(404, "Not found")
    if candidate.suffix not in {".html", ".js", ".css", ".ico", ".png", ".svg"}:
        raise HTTPException(404, "Not found")
    return FileResponse(candidate)
