"""Poll job status for any background task across tools (single source for the UI's progress bars)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.jobs import job_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_public()
