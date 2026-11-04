"""Secure temp storage: per-job directories + periodic cleanup."""
from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from app.core.config import OUTPUT_DIR, TMP_DIR, UPLOAD_DIR, settings


def new_work_dir() -> Path:
    d = TMP_DIR / uuid.uuid4().hex[:12]
    d.mkdir(parents=True, exist_ok=True)
    return d


def output_path(job_id: str, filename: str) -> Path:
    d = OUTPUT_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d / filename


def cleanup_once(max_age_seconds: int = None) -> int:
    """Delete upload/output/tmp entries older than TTL. Returns count removed."""
    max_age = max_age_seconds or settings.job_ttl_seconds
    now = time.time()
    removed = 0
    for root in (UPLOAD_DIR, OUTPUT_DIR, TMP_DIR):
        if not root.exists():
            continue
        for entry in root.iterdir():
            try:
                age = now - entry.stat().st_mtime
                if age > max_age:
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink(missing_ok=True)
                    removed += 1
            except FileNotFoundError:
                continue
    return removed
