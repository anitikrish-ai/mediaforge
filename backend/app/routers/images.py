"""Image tool endpoints: manipulation (Pillow), enhancement (scikit-image/opencv),
batch processing, all running in a threadpool so the event loop stays free.
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from app.core.config import OUTPUT_DIR, TMP_DIR, settings
from app.core.jobs import job_manager
from app.core.validation import safe_filename, validate_extension, validate_upload_size
from app.services import image_service as img

router = APIRouter(prefix="/api/images", tags=["images"])


def _save_upload(data: bytes, ext: str) -> Path:
    p = TMP_DIR / f"up_{uuid.uuid4().hex[:10]}{ext}"
    p.write_bytes(data)
    return p


async def _load_upload(file: UploadFile) -> tuple[Path, Image.Image]:
    ext = validate_extension(file.filename, settings.allowed_image_ext)
    data = await validate_upload_size(file, settings.max_image_mb)
    path = _save_upload(data, ext)
    return path, img.open_image(path)


def _process_ops(image: Image.Image, ops: list[dict]) -> Image.Image:
    """Apply a pipeline of operations in order. Each op: {"type": ..., **params}."""
    for op in ops:
        t = op.get("type")
        if t == "resize":
            image = img.resize(image, op.get("width"), op.get("height"), op.get("mode", "fit"))
        elif t == "crop":
            image = img.crop(image, op["left"], op["top"], op["right"], op["bottom"])
        elif t == "rotate":
            image = img.rotate(image, op.get("degrees", 90))
        elif t == "flip":
            image = img.flip(image, op.get("horizontal", False), op.get("vertical", False))
        elif t == "auto_contrast":
            image = img.enhance_auto_contrast(image)
        elif t == "sharpen":
            image = img.enhance_sharpen(image, op.get("amount", 1.0))
        elif t == "denoise":
            image = img.denoise(image, op.get("strength", 1.0))
        elif t == "brightness_contrast":
            image = img.adjust_brightness_contrast(image, op.get("brightness", 0), op.get("contrast", 0))
        elif t == "filter":
            image = img.apply_filter(image, op.get("name", "grayscale"))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation '{t}'")
    return image


@router.post("/process")
async def process_image(
    file: UploadFile = File(...),
    ops: str = Form("[]"),            # JSON list of operations, applied in order
    format: str = Form("PNG"),
    quality: int = Form(92),
):
    """Run a pipeline of Pillow/skimage/opencv ops on one image, return the file."""
    try:
        op_list = json.loads(ops)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="`ops` must be valid JSON")

    path, image = await _load_upload(file)
    loop = asyncio.get_event_loop()
    try:
        processed = await loop.run_in_executor(None, _process_ops, image, op_list)
        processed, fmt = img.convert_format(processed, format)
        buf = io.BytesIO()
        save_kwargs = {"quality": quality} if fmt in ("JPEG", "WEBP") else {}
        processed.save(buf, format=fmt, **save_kwargs)
        buf.seek(0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        path.unlink(missing_ok=True)

    ext = fmt.lower().replace("jpeg", "jpg")
    out_name = safe_filename(f"{Path(file.filename).stem}_edited.{ext}")
    out_path = OUTPUT_DIR / "images" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())
    return FileResponse(out_path, filename=out_name, media_type=f"image/{ext}")


@router.post("/batch")
async def process_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    ops: str = Form("[]"),
    format: str = Form("PNG"),
):
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=400, detail=f"Max {settings.max_batch_files} files per batch")
    try:
        op_list = json.loads(ops)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="`ops` must be valid JSON")

    job = job_manager.create("image_batch")

    # Read all uploads up front (UploadFile streams close after the request ends)
    loaded = []
    for f in files:
        path, image = await _load_upload(f)
        loaded.append((f.filename, path, image))

    background_tasks.add_task(_run_batch, job.id, loaded, op_list, format)
    return {"job_id": job.id}


def _run_batch(job_id: str, loaded: list[tuple[str, Path, Image.Image]], ops: list[dict], fmt: str):
    out_dir = OUTPUT_DIR / "batches" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(loaded)
    for i, (filename, path, image) in enumerate(loaded):
        try:
            processed = _process_ops(image, ops)
            processed, out_fmt = img.convert_format(processed, fmt)
            ext = out_fmt.lower().replace("jpeg", "jpg")
            out_name = safe_filename(f"{Path(filename).stem}_edited.{ext}")
            processed.save(out_dir / out_name, format=out_fmt)
            results.append({"filename": filename, "output": out_name, "ok": True})
        except Exception as e:  # noqa: BLE001 keep batch running even if one file fails
            results.append({"filename": filename, "error": str(e), "ok": False})
        finally:
            path.unlink(missing_ok=True)
        job_manager.set_progress(job_id, (i + 1) / total * 100, f"Processed {i + 1}/{total}")
    job_manager.complete(job_id, {"dir": str(out_dir), "files": results})


@router.get("/batch/{job_id}/download/{filename}")
async def download_batch_file(job_id: str, filename: str):
    path = OUTPUT_DIR / "batches" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
