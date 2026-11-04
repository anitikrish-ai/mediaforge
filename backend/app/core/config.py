"""App-wide settings. Single source of truth for paths, limits, allowed formats."""
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TMP_DIR = STORAGE_DIR / "tmp"

for d in (UPLOAD_DIR, OUTPUT_DIR, TMP_DIR):
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    app_name: str = "MediaForge"
    max_image_mb: int = 25
    max_video_mb: int = 500
    max_batch_files: int = 20
    job_ttl_seconds: int = 3600          # outputs older than this get purged
    cleanup_interval_seconds: int = 600
    allowed_image_ext: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    allowed_video_ext: set[str] = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "MEDIAFORGE_"


settings = Settings()
