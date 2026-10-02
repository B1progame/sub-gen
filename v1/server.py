"""Caption Forge local processing server.

Keeps transcription and rendering on the user's computer.  Jobs run in worker
threads and are exposed as small polling endpoints so the UI never freezes.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI(title="Caption Forge", version="2.0.0")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

lock = threading.Lock()
setup: dict[str, Any] = {"status": "uninitialized", "stage": "Ready to prepare your local studio", "progress": 0, "eta": None, "detail": "The Medium multilingual Whisper model will be downloaded once (about 1.5 GB)."}
jobs: dict[str, dict[str, Any]] = {}
model_cache: dict[str, Any] = {}
model_jobs: dict[str, dict[str, Any]] = {}
MODEL_CATALOGUE = {
    "tiny": {"label": "Tiny", "size": "75 MB", "note": "Fastest draft transcription"},
    "base": {"label": "Base", "size": "145 MB", "note": "Fast, good for clean audio"},
    "small": {"label": "Small", "size": "480 MB", "note": "Balanced speed and accuracy"},
    "medium": {"label": "Medium", "size": "1.5 GB", "note": "Recommended multilingual quality"},
    "large-v3": {"label": "Large v3", "size": "3.1 GB", "note": "Highest accuracy, slower"},
    "turbo": {"label": "Turbo", "size": "1.6 GB", "note": "High quality with faster decoding"},
}

def update(target: dict[str, Any], **values: Any) -> None:
    with lock: target.update(values)

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
        update(job, status="error", progress=0, stage="Download failed", detail=str(exc))

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

def burn_worker(job_id: str, video_path: Path, captions: list[dict[str, Any]], style: dict[str, Any]) -> None:
    job = jobs[job_id]
    try:
        binary = ffmpeg_executable()
        if not binary: raise RuntimeError("Caption rendering requires the bundled FFmpeg runtime. Restart Caption Forge after installation.")
        ass_path = OUTPUTS / f"{job_id}.ass"; output = OUTPUTS / f"{job_id}.mp4"; write_ass(captions, style, ass_path)
        update(job, status="working", progress=10, stage="Preparing burn-in render", eta="calculating…")
        process = subprocess.Popen([binary, "-y", "-i", str(video_path), "-vf", f"ass={ass_path.as_posix()}", "-c:a", "copy", "-movflags", "+faststart", str(output)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            update(job, status="working", progress=min(92, int(job.get("progress", 10)) + 1), stage="Burning captions into video", eta="Rendering locally…")
            time.sleep(1)
        if process.returncode != 0: raise RuntimeError(process.stderr.read()[-1000:])
        update(job, status="done", progress=100, stage="Burned video ready", eta=None, download=f"/api/download/{output.name}")
    except Exception as exc:
        logger.exception("Caption burn job failed: %s", job_id)
        update(job, status="error", stage="Video render stopped", detail="Could not burn captions into this video. Open the session log for details.", eta=None)

def transcription_worker(job_id: str, video_path: Path, language: str | None) -> None:
    job = jobs[job_id]
    try:
        if setup["status"] != "ready": raise RuntimeError("Finish first-run setup before transcribing.")
        update(job, status="working", progress=4, stage="Reading audio track", eta="calculating…")
        model = model_cache["model"]
        update(job, progress=12, stage="Transcribing speech", eta="estimating after first segment")
        segments, info = model.transcribe(str(video_path), language=language or None, vad_filter=True, word_timestamps=False, beam_size=5)
        total = float(info.duration or 1)
        captions = []
        for segment in segments:
            captions.append({"id": len(captions) + 1, "start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip()})
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
def health() -> dict[str, Any]: return {"ok": True, "ffmpeg": ffmpeg_present(), "cuda": _cuda_available(), "cuda_devices": cuda_device_count(), "log_file": str(LOG_FILE), "models": list(model_cache)}

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
    return {"runtime": runtime, "runtime_detail": runtime_detail, "model_loaded": bool(model_cache.get("model")), "active_model": active, "device": setup.get("device"), "cuda": _cuda_available(), "cuda_devices": cuda_device_count(), "ffmpeg": ffmpeg_present(), "ready": runtime and bool(model_cache.get("model"))}

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
def start_setup(model: str = "medium") -> dict[str, Any]:
    if setup["status"] == "working": return setup
    if setup["status"] == "ready": return setup
    thread = threading.Thread(target=setup_worker, args=(model,), daemon=True); thread.start()
    return setup

@app.post("/api/transcribe")
async def transcribe(video: UploadFile = File(...), language: str = "") -> dict[str, str]:
    suffix = Path(video.filename or "video.mp4").suffix or ".mp4"
    job_id = uuid.uuid4().hex
    target = UPLOADS / f"{job_id}{suffix}"
    with target.open("wb") as out:
        while chunk := await video.read(1024 * 1024): out.write(chunk)
    jobs[job_id] = {"status":"queued", "progress":0, "stage":"Queued", "eta":None, "captions":[]}
    threading.Thread(target=transcription_worker, args=(job_id, target, language), daemon=True).start()
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
    job_id = uuid.uuid4().hex; output = OUTPUTS / f"manual-{job_id}.srt"; write_srt(captions, output)
    return {"download": f"/api/download/manual-{job_id}.srt"}

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
