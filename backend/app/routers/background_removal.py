"""rembg-backed background removal endpoints — single + batch."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import OUTPUT_DIR, TMP_DIR, settings
from app.core.jobs import job_manager
from app.core.validation import safe_filename, validate_extension, validate_upload_size
from app.services import bg_removal_service as bg
from app.services import image_service as img

router = APIRouter(prefix="/api/background", tags=["background-removal"])


@router.get("/models")
async def list_models():
    return {"models": [{"id": k, "description": v} for k, v in bg.SUPPORTED_MODELS.items()]}


@router.post("/remove")
async def remove_bg(
    file: UploadFile = File(...),
    model: str = Form("u2net"),
    alpha_matting: bool = Form(False),
    bg_color: str = Form(""),          # "" = transparent, or "r,g,b"
):
    ext = validate_extension(file.filename, settings.allowed_image_ext)
    data = await validate_upload_size(file, settings.max_image_mb)
    tmp_path = TMP_DIR / f"bg_{uuid.uuid4().hex[:10]}{ext}"
    tmp_path.write_bytes(data)

    color = None
    if bg_color.strip():
        try:
            parts = [int(x) for x in bg_color.split(",")]
            color = tuple(parts + [255])[:4]
        except ValueError:
            raise HTTPException(status_code=400, detail="bg_color must be 'r,g,b'")

    try:
        image = img.open_image(tmp_path)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, bg.remove_background, image, model, alpha_matting, color)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Background removal failed: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    out_name = safe_filename(f"{Path(file.filename).stem}_nobg.png")
    out_path = OUTPUT_DIR / "bg_removed" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path, format="PNG")
    return FileResponse(out_path, filename=out_name, media_type="image/png")


@router.post("/batch")
async def remove_bg_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    model: str = Form("u2net"),
):
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=400, detail=f"Max {settings.max_batch_files} files per batch")

    job = job_manager.create("bg_removal_batch")
    loaded = []
    for f in files:
        ext = validate_extension(f.filename, settings.allowed_image_ext)
        data = await validate_upload_size(f, settings.max_image_mb)
        p = TMP_DIR / f"bg_{uuid.uuid4().hex[:10]}{ext}"
        p.write_bytes(data)
        loaded.append((f.filename, p))

    background_tasks.add_task(_run_batch, job.id, loaded, model)
    return {"job_id": job.id}


def _run_batch(job_id: str, loaded: list[tuple[str, Path]], model: str):
    out_dir = OUTPUT_DIR / "bg_removed_batches" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(loaded)
    for i, (filename, path) in enumerate(loaded):
        try:
            image = img.open_image(path)
            out = bg.remove_background(image, model=model)
            out_name = safe_filename(f"{Path(filename).stem}_nobg.png")
            out.save(out_dir / out_name, format="PNG")
            results.append({"filename": filename, "output": out_name, "ok": True})
        except Exception as e:  # noqa: BLE001
            results.append({"filename": filename, "error": str(e), "ok": False})
        finally:
            path.unlink(missing_ok=True)
        job_manager.set_progress(job_id, (i + 1) / total * 100, f"Processed {i + 1}/{total}")
    job_manager.complete(job_id, {"dir": str(out_dir), "files": results})


@router.get("/batch/{job_id}/download/{filename}")
async def download_batch_file(job_id: str, filename: str):
    path = OUTPUT_DIR / "bg_removed_batches" / job_id / safe_filename(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)
