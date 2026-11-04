"""Object detection/tracking on single images (sync) and videos (async job)."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import cv2
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import OUTPUT_DIR, TMP_DIR, settings
from app.core.jobs import job_manager
from app.core.validation import safe_filename, validate_extension, validate_upload_size
from app.services import detection_service as det
from app.services import video_service as vid

router = APIRouter(prefix="/api/detect", tags=["detection"])

IMAGE_MODES = {"people": "HOG pedestrian detector", "face": "Haar cascade face detector", "eye": "Haar cascade eye detector"}
VIDEO_MODES = {"motion": "Background-subtraction moving object detector + tracking", "people": "HOG pedestrian detector + tracking", "face": "Haar cascade face detector + tracking"}


@router.get("/modes")
async def modes():
    return {"image_modes": IMAGE_MODES, "video_modes": VIDEO_MODES}


@router.post("/image")
async def detect_image(file: UploadFile = File(...), mode: str = Form("people")):
    if mode not in IMAGE_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {list(IMAGE_MODES)}")
    ext = validate_extension(file.filename, settings.allowed_image_ext)
    data = await validate_upload_size(file, settings.max_image_mb)
    tmp_path = TMP_DIR / f"det_{uuid.uuid4().hex[:10]}{ext}"
    tmp_path.write_bytes(data)

    frame = cv2.imread(str(tmp_path))
    if frame is None:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not decode image.")

    if mode == "people":
        detections = det.detect_people_hog(frame)
    else:
        detections = det.detect_cascade(frame, mode)

    annotated = det.annotate(frame, detections)
    tmp_path.unlink(missing_ok=True)

    out_name = safe_filename(f"{Path(file.filename).stem}_detected.jpg")
    out_path = OUTPUT_DIR / "detections" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

    return {
        "count": len(detections),
        "boxes": detections.xyxy.tolist() if len(detections) else [],
        "confidences": detections.confidence.tolist() if detections.confidence is not None and len(detections) else [],
        "image_url": f"/api/detect/download/{out_name}",
    }


@router.get("/download/{filename}")
async def download_detected(filename: str):
    path = OUTPUT_DIR / "detections" / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


@router.post("/video")
async def detect_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Form("motion"),
    track: bool = Form(True),
):
    if mode not in VIDEO_MODES:
        raise HTTPException(status_code=400, detail=f"mode must be one of {list(VIDEO_MODES)}")
    ext = validate_extension(file.filename, settings.allowed_video_ext)
    data = await validate_upload_size(file, settings.max_video_mb)
    tmp_path = TMP_DIR / f"detv_{uuid.uuid4().hex[:10]}{ext}"
    tmp_path.write_bytes(data)

    job = job_manager.create("video_detection")
    out_name = safe_filename(f"{Path(file.filename).stem}_tracked.mp4")
    out_path = OUTPUT_DIR / "video_detections" / job.id / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    background_tasks.add_task(_run_video_detection, job.id, tmp_path, out_path, mode, track, out_name)
    return {"job_id": job.id}


def _run_video_detection(job_id: str, src: Path, out_path: Path, mode: str, track: bool, out_name: str):
    def cb(pct, msg):
        job_manager.set_progress(job_id, pct, msg)

    try:
        stats = vid.annotate_video_with_detection(src, out_path, mode=mode, track=track, progress_cb=cb)
        stats["download_url"] = f"/api/detect/video/{job_id}/download/{out_name}"
        job_manager.complete(job_id, stats)
    except Exception as e:  # noqa: BLE001
        job_manager.fail(job_id, str(e))
    finally:
        src.unlink(missing_ok=True)


@router.get("/video/{job_id}/download/{filename}")
async def download_video_result(job_id: str, filename: str):
    path = OUTPUT_DIR / "video_detections" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
