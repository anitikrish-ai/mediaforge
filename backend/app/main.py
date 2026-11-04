"""MediaForge API entrypoint. Wires every service router under one FastAPI app,
plus a background cleanup loop that purges stale temp/output files."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import OUTPUT_DIR, settings
from app.core.storage import cleanup_once
from app.routers import background_removal, detection, download, images, jobs, video, web_extract

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaforge")


async def _cleanup_loop():
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        try:
            removed = cleanup_once()
            if removed:
                logger.info("cleanup: removed %d stale file(s)", removed)
        except Exception:  # noqa: BLE001
            logger.exception("cleanup loop failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router)
app.include_router(background_removal.router)
app.include_router(detection.router)
app.include_router(video.router)
app.include_router(web_extract.router)
app.include_router(download.router)
app.include_router(jobs.router)

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/libraries")
async def libraries():
    """Confirms which of the 7 mandatory libs are importable at runtime — useful for setup verification."""
    results = {}
    for mod, name in [
        ("cv2", "opencv-python"),
        ("supervision", "supervision"),
        ("PIL", "Pillow"),
        ("skimage", "scikit-image"),
        ("rembg", "rembg"),
        ("trafilatura", "trafilatura"),
        ("yt_dlp", "yt-dlp"),
    ]:
        try:
            __import__(mod)
            results[name] = "ok"
        except ImportError as e:
            results[name] = f"missing: {e}"
    return results
