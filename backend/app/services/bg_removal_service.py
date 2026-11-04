"""AI background removal via rembg. Sessions are cached per model so repeated
calls don't reload ONNX weights every request.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

# Models that ship with rembg and run fully offline/local (no paid API calls).
SUPPORTED_MODELS = {
    "u2net": "General purpose (default, balanced speed/quality)",
    "u2netp": "Lightweight general purpose (fastest)",
    "u2net_human_seg": "Optimized for people/portraits",
    "isnet-general-use": "Higher quality general purpose",
    "silueta": "Small footprint, good for batch jobs",
}


@lru_cache(maxsize=4)
def _session(model: str):
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported rembg model '{model}'. Choose from: {', '.join(SUPPORTED_MODELS)}")
    return new_session(model)


def remove_background(
    img: Image.Image,
    model: str = "u2net",
    alpha_matting: bool = False,
    bg_color: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    session = _session(model)
    out = remove(
        img,
        session=session,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=270,
        alpha_matting_background_threshold=20,
        alpha_matting_erode_size=11,
    )
    if bg_color is not None:
        flat = Image.new("RGBA", out.size, bg_color)
        flat.alpha_composite(out)
        return flat.convert("RGB") if bg_color[3] == 255 else flat
    return out
