"""Plain video processing endpoints: probe, trim, resize, extract frames."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import OUTPUT_DIR, TMP_DIR, settings
from app.core.jobs import job_manager
from app.core.validation import safe_filename, validate_extension, validate_upload_size
from app.services import video_service as vid

router = APIRouter(prefix="/api/video", tags=["video"])


async def _save_video_upload(file: UploadFile) -> Path:
    ext = validate_extension(file.filename, settings.allowed_video_ext)
    data = await validate_upload_size(file, settings.max_video_mb)
    p = TMP_DIR / f"vid_{uuid.uuid4().hex[:10]}{ext}"
    p.write_bytes(data)
    return p


@router.post("/probe")
async def probe_video(file: UploadFile = File(...)):
    path = await _save_video_upload(file)
    try:
        info = vid.probe(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        path.unlink(missing_ok=True)
    return info


@router.post("/trim")
async def trim_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    start_sec: float = Form(0),
    end_sec: float = Form(...),
):
    path = await _save_video_upload(file)
    job = job_manager.create("video_trim")
    out_name = safe_filename(f"{Path(file.filename).stem}_trimmed.mp4")
    out_path = OUTPUT_DIR / "video_trim" / job.id / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def run():
        try:
            vid.trim(path, out_path, start_sec, end_sec, progress_cb=lambda p, m: job_manager.set_progress(job.id, p, m))
            job_manager.complete(job.id, {"download_url": f"/api/video/trim/{job.id}/download/{out_name}"})
        except Exception as e:  # noqa: BLE001
            job_manager.fail(job.id, str(e))
        finally:
            path.unlink(missing_ok=True)

    background_tasks.add_task(run)
    return {"job_id": job.id}


@router.get("/trim/{job_id}/download/{filename}")
async def download_trim(job_id: str, filename: str):
    path = OUTPUT_DIR / "video_trim" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


@router.post("/resize")
async def resize_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    width: int = Form(...),
    height: int = Form(...),
):
    path = await _save_video_upload(file)
    job = job_manager.create("video_resize")
    out_name = safe_filename(f"{Path(file.filename).stem}_resized.mp4")
    out_path = OUTPUT_DIR / "video_resize" / job.id / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def run():
        try:
            vid.resize_video(path, out_path, width, height, progress_cb=lambda p, m: job_manager.set_progress(job.id, p, m))
            job_manager.complete(job.id, {"download_url": f"/api/video/resize/{job.id}/download/{out_name}"})
        except Exception as e:  # noqa: BLE001
            job_manager.fail(job.id, str(e))
        finally:
            path.unlink(missing_ok=True)

    background_tasks.add_task(run)
    return {"job_id": job.id}


@router.get("/resize/{job_id}/download/{filename}")
async def download_resize(job_id: str, filename: str):
    path = OUTPUT_DIR / "video_resize" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


@router.post("/extract-frames")
async def extract_frames(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    every_n: int = Form(30),
    max_frames: int = Form(60),
):
    path = await _save_video_upload(file)
    job = job_manager.create("frame_extraction")
    out_dir = OUTPUT_DIR / "frames" / job.id

    def run():
        try:
            frames = vid.extract_frames(path, out_dir, every_n, max_frames, progress_cb=lambda p, m: job_manager.set_progress(job.id, p, m))
            urls = [f"/api/video/frames/{job.id}/download/{f.name}" for f in frames]
            job_manager.complete(job.id, {"count": len(frames), "frame_urls": urls})
        except Exception as e:  # noqa: BLE001
            job_manager.fail(job.id, str(e))
        finally:
            path.unlink(missing_ok=True)

    background_tasks.add_task(run)
    return {"job_id": job.id}


@router.get("/frames/{job_id}/download/{filename}")
async def download_frame(job_id: str, filename: str):
    path = OUTPUT_DIR / "frames" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
