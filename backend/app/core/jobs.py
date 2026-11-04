"""In-memory async job manager. Tracks progress of background tasks so the UI
can poll /jobs/{id} for live status. No DB required — jobs live for the process
lifetime and get garbage-collected by the cleanup task alongside their files.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    kind: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0          # 0..100
    message: str = ""
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self):
        self.updated_at = time.time()

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "message": self.message,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, kind: str) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        for k, v in kwargs.items():
            setattr(job, k, v)
        job.touch()

    def set_progress(self, job_id: str, progress: float, message: str = "") -> None:
        self.update(job_id, progress=progress, message=message, status=JobStatus.RUNNING)

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        self.update(job_id, status=JobStatus.DONE, progress=100.0, result=result, message="done")

    def fail(self, job_id: str, error: str) -> None:
        self.update(job_id, status=JobStatus.ERROR, error=error, message="failed")

    def purge_older_than(self, seconds: float) -> list[str]:
        now = time.time()
        stale = [jid for jid, j in self._jobs.items() if now - j.updated_at > seconds]
        for jid in stale:
            del self._jobs[jid]
        return stale


job_manager = JobManager()
