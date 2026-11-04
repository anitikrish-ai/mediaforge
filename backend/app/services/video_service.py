"""Video processing built on OpenCV: frame extraction, trim/resize/speed
transforms, and running the detection/tracking service across every frame to
produce an annotated output video. Progress callback lets routers stream % to
the job manager for the UI's progress bar.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
import supervision as sv

from app.services import detection_service as det

ProgressCB = Callable[[float, str], None]


def probe(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")
    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS) or 0,
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
    }
    info["duration_sec"] = info["frame_count"] / info["fps"] if info["fps"] else 0
    cap.release()
    return info


def extract_frames(path: Path, out_dir: Path, every_n: int = 30, max_frames: int = 200, progress_cb: Optional[ProgressCB] = None) -> list[Path]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    idx = 0
    while cap.isOpened() and len(saved) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % every_n == 0:
            fp = out_dir / f"frame_{idx:06d}.jpg"
            cv2.imwrite(str(fp), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            saved.append(fp)
        idx += 1
        if progress_cb and total:
            progress_cb(min(99, idx / total * 100), f"Extracting frame {idx}/{total}")
    cap.release()
    return saved


def trim(path: Path, out_path: Path, start_sec: float, end_sec: float, progress_cb: Optional[ProgressCB] = None) -> Path:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    start_f, end_f = int(start_sec * fps), int(end_sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    idx = start_f
    total = max(1, end_f - start_f)
    while idx < end_f:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame)
        idx += 1
        if progress_cb:
            progress_cb(min(99, (idx - start_f) / total * 100), f"Trimming {idx - start_f}/{total}")
    cap.release()
    writer.release()
    return out_path


def resize_video(path: Path, out_path: Path, width: int, height: int, progress_cb: Optional[ProgressCB] = None) -> Path:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA))
        idx += 1
        if progress_cb and total:
            progress_cb(min(99, idx / total * 100), f"Resizing {idx}/{total}")
    cap.release()
    writer.release()
    return out_path


def annotate_video_with_detection(
    path: Path,
    out_path: Path,
    mode: str = "motion",               # "motion" | "people" | "face"
    track: bool = True,
    progress_cb: Optional[ProgressCB] = None,
) -> dict:
    """Runs detection_service per frame, tracks with ByteTrack, writes an
    annotated mp4, and returns summary stats (unique track count etc.)."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    tracker = det.new_tracker() if track else None
    bg_sub = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=25, detectShadows=False) if mode == "motion" else None
    seen_ids: set[int] = set()

    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if mode == "motion":
            detections = det.detect_motion_contours(frame, bg_sub)
        elif mode == "people":
            detections = det.detect_people_hog(frame)
        elif mode == "face":
            detections = det.detect_cascade(frame, "face")
        else:
            detections = sv.Detections.empty()

        if tracker is not None and len(detections) > 0:
            detections = tracker.update_with_detections(detections)
            if detections.tracker_id is not None:
                seen_ids.update(int(t) for t in detections.tracker_id)

        annotated = det.annotate(frame, detections, with_trace=track)
        writer.write(annotated)
        idx += 1
        if progress_cb and total:
            progress_cb(min(99, idx / total * 100), f"Analyzing frame {idx}/{total}")

    cap.release()
    writer.release()
    return {"frames_processed": idx, "unique_tracks": len(seen_ids), "mode": mode}
