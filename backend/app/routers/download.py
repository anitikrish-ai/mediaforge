"""yt-dlp download endpoints: probe formats, then download as background job."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException
from fastapi.responses import FileResponse

from app.core.config import OUTPUT_DIR
from app.core.jobs import job_manager
from app.core.validation import safe_filename, validate_url
from app.services import download_service as dl

router = APIRouter(prefix="/api/download", tags=["download"])


@router.post("/probe")
async def probe(url: str = Form(...)):
    validate_url(url)
    try:
        return dl.probe_formats(url)
    except Exception as e:  # noqa: BLE001 — yt-dlp raises many exception types
        raise HTTPException(status_code=422, detail=f"Could not read URL: {e}")


@router.post("/start")
async def start_download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form("video"),            # "video" | "audio"
    quality: str = Form("best"),
    audio_format: str = Form("mp3"),
):
    validate_url(url)
    if mode not in ("video", "audio"):
        raise HTTPException(status_code=400, detail="mode must be 'video' or 'audio'")

    job = job_manager.create("media_download")
    out_dir = OUTPUT_DIR / "downloads" / job.id

    def run():
        try:
            result = dl.download(
                url, out_dir, mode=mode, quality=quality, audio_format=audio_format,
                progress_cb=lambda p, m: job_manager.set_progress(job.id, p, m),
            )
            fname = Path(result["filepath"]).name
            result["download_url"] = f"/api/download/{job.id}/file/{fname}"
            job_manager.complete(job.id, result)
        except Exception as e:  # noqa: BLE001
            job_manager.fail(job.id, str(e))

    background_tasks.add_task(run)
    return {"job_id": job.id}


@router.get("/{job_id}/file/{filename}")
async def get_file(job_id: str, filename: str):
    path = OUTPUT_DIR / "downloads" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
