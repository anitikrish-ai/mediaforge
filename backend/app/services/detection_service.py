"""Object detection + tracking.

opencv  -> actual detectors: HOG+SVM person detector and Haar cascades
           (face/eye/body/car) that ship inside opencv-python itself, so no
           extra model downloads are required to satisfy "no unnecessary AI
           models". An optional ONNX YOLO model path can be supplied by the
           user (`detect_yolo_onnx`) for higher-quality multi-class detection
           — fully optional, never required.
supervision -> turns raw boxes into `sv.Detections`, draws boxes/labels, and
           runs ByteTrack for multi-object tracking across video frames.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import supervision as sv

_HOG = cv2.HOGDescriptor()
_HOG.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

_CASCADE_FILES = {
    "face": "haarcascade_frontalface_default.xml",
    "eye": "haarcascade_eye.xml",
    "body": "haarcascade_fullbody.xml",
    "upper_body": "haarcascade_upperbody.xml",
    "car": "haarcascade_car.xml",  # falls back to skip if not bundled on this OpenCV build
}


def _cascade(name: str) -> Optional[cv2.CascadeClassifier]:
    fname = _CASCADE_FILES.get(name)
    if not fname:
        return None
    path = Path(cv2.data.haarcascades) / fname
    if not path.exists():
        return None
    return cv2.CascadeClassifier(str(path))


def detect_people_hog(frame_bgr: np.ndarray) -> sv.Detections:
    """HOG+SVM pedestrian detector (built into OpenCV, no download)."""
    rects, weights = _HOG.detectMultiScale(frame_bgr, winStride=(8, 8), padding=(8, 8), scale=1.05)
    if len(rects) == 0:
        return sv.Detections.empty()
    xyxy = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects], dtype=np.float32)
    confidence = np.array([min(1.0, max(0.1, float(w) / 2)) for w in weights], dtype=np.float32) if len(weights) else np.ones(len(rects))
    class_id = np.zeros(len(rects), dtype=int)
    return sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)


def detect_cascade(frame_bgr: np.ndarray, kind: str, class_id: int = 0) -> sv.Detections:
    clf = _cascade(kind)
    if clf is None:
        return sv.Detections.empty()
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    rects = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(rects) == 0:
        return sv.Detections.empty()
    xyxy = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects], dtype=np.float32)
    confidence = np.ones(len(rects), dtype=np.float32) * 0.9
    class_ids = np.full(len(rects), class_id, dtype=int)
    return sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_ids)


def detect_motion_contours(frame_bgr: np.ndarray, bg_subtractor) -> sv.Detections:
    """Background-subtraction based moving-object detector for video — no model needed."""
    mask = bg_subtractor.apply(frame_bgr)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > 500]
    if not boxes:
        return sv.Detections.empty()
    xyxy = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes], dtype=np.float32)
    return sv.Detections(xyxy=xyxy, confidence=np.ones(len(boxes), dtype=np.float32) * 0.6, class_id=np.zeros(len(boxes), dtype=int))


def detect_yolo_onnx(frame_bgr: np.ndarray, net: cv2.dnn_Net, conf_thres: float = 0.4, names: Optional[list[str]] = None) -> sv.Detections:
    """Optional: run a user-supplied YOLO ONNX model via OpenCV DNN. Never required."""
    h, w = frame_bgr.shape[:2]
    blob = cv2.dnn.blobFromImage(frame_bgr, 1 / 255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    out = net.forward()[0]
    boxes, scores, class_ids = [], [], []
    for row in out:
        conf = row[4]
        if conf < conf_thres:
            continue
        class_scores = row[5:]
        cid = int(np.argmax(class_scores))
        score = float(conf * class_scores[cid])
        if score < conf_thres:
            continue
        cx, cy, bw, bh = row[0:4]
        x1 = (cx - bw / 2) / 640 * w
        y1 = (cy - bh / 2) / 640 * h
        x2 = (cx + bw / 2) / 640 * w
        y2 = (cy + bh / 2) / 640 * h
        boxes.append([x1, y1, x2, y2])
        scores.append(score)
        class_ids.append(cid)
    if not boxes:
        return sv.Detections.empty()
    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        confidence=np.array(scores, dtype=np.float32),
        class_id=np.array(class_ids, dtype=int),
    )


# ------------------------------------------------------------- annotation
_box_annotator = sv.BoxAnnotator(thickness=2)
_label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
_trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=30)


def annotate(frame_bgr: np.ndarray, detections: sv.Detections, labels: Optional[list[str]] = None, with_trace: bool = False) -> np.ndarray:
    annotated = _box_annotator.annotate(scene=frame_bgr.copy(), detections=detections)
    if labels is None:
        labels = [f"#{i} {c:.2f}" for i, c in enumerate(detections.confidence)] if detections.confidence is not None else []
    if len(labels):
        annotated = _label_annotator.annotate(scene=annotated, detections=detections, labels=labels)
    if with_trace and detections.tracker_id is not None:
        annotated = _trace_annotator.annotate(scene=annotated, detections=detections)
    return annotated


def new_tracker() -> sv.ByteTrack:
    return sv.ByteTrack()
