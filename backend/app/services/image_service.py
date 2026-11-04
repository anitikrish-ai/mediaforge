"""Image manipulation + enhancement.
Pillow -> resize/crop/convert/rotate/format conversion (fast, PIL-native ops)
scikit-image -> denoise/sharpen/contrast/restoration (skimage.restoration + exposure + filters)
opencv -> extra filters (bilateral, CLAHE) used where it outperforms skimage for speed
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from skimage import exposure, filters, restoration, img_as_float, img_as_ubyte

ResizeMode = Literal["fit", "fill", "stretch"]


def open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # respect camera orientation
    return img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img


# ---------------------------------------------------------------- Pillow ops
def resize(img: Image.Image, width: int | None, height: int | None, mode: ResizeMode = "fit") -> Image.Image:
    w0, h0 = img.size
    if not width and not height:
        return img
    width = width or int(w0 * (height / h0))
    height = height or int(h0 * (width / w0))
    if mode == "stretch":
        return img.resize((width, height), Image.LANCZOS)
    if mode == "fill":
        return ImageOps.fit(img, (width, height), Image.LANCZOS)
    # fit: preserve aspect ratio inside box
    img = img.copy()
    img.thumbnail((width, height), Image.LANCZOS)
    return img


def crop(img: Image.Image, left: int, top: int, right: int, bottom: int) -> Image.Image:
    w, h = img.size
    box = (max(0, left), max(0, top), min(w, right), min(h, bottom))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Invalid crop box")
    return img.crop(box)


def rotate(img: Image.Image, degrees: float, expand: bool = True) -> Image.Image:
    return img.rotate(-degrees, expand=expand, resample=Image.BICUBIC)


def flip(img: Image.Image, horizontal: bool, vertical: bool) -> Image.Image:
    if horizontal:
        img = ImageOps.mirror(img)
    if vertical:
        img = ImageOps.flip(img)
    return img


def convert_format(img: Image.Image, fmt: str) -> tuple[Image.Image, str]:
    fmt = fmt.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    if fmt == "JPEG" and img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    return img, fmt


# ------------------------------------------------------------ skimage/cv ops
def _to_np(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"))


def _from_np(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _clip01_to_ubyte(arr: np.ndarray) -> np.ndarray:
    """skimage filters (unsharp mask, nl-means, CLAHE) can overshoot [0,1] slightly;
    img_as_ubyte refuses out-of-range floats, so clip before converting."""
    return img_as_ubyte(np.clip(arr, 0.0, 1.0))


def enhance_auto_contrast(img: Image.Image) -> Image.Image:
    """scikit-image adaptive histogram equalization (CLAHE) for perceptual contrast boost."""
    arr = img_as_float(_to_np(img))
    out = exposure.equalize_adapthist(arr, clip_limit=0.02)
    return _from_np(_clip01_to_ubyte(out))


def enhance_sharpen(img: Image.Image, amount: float = 1.0) -> Image.Image:
    """skimage unsharp mask — amount controls strength."""
    arr = img_as_float(_to_np(img))
    out = filters.unsharp_mask(arr, radius=2, amount=amount, channel_axis=-1)
    return _from_np(_clip01_to_ubyte(out))


def denoise(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """scikit-image non-local means denoising — real restoration, not a blur filter."""
    arr = img_as_float(_to_np(img))
    sigma_est = np.mean(restoration.estimate_sigma(arr, channel_axis=-1))
    out = restoration.denoise_nl_means(
        arr, h=1.15 * sigma_est * strength, fast_mode=True,
        patch_size=5, patch_distance=6, channel_axis=-1,
    )
    return _from_np(_clip01_to_ubyte(out))


def restore_inpaint(img: Image.Image, mask: Image.Image) -> Image.Image:
    """OpenCV inpainting — fills a masked region (scratches/defects) using surrounding texture."""
    src = cv2.cvtColor(_to_np(img), cv2.COLOR_RGB2BGR)
    m = np.array(mask.convert("L"))
    m = cv2.resize(m, (src.shape[1], src.shape[0]))
    _, m = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
    out = cv2.inpaint(src, m, 3, cv2.INPAINT_TELEA)
    return _from_np(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def adjust_brightness_contrast(img: Image.Image, brightness: float = 0.0, contrast: float = 0.0) -> Image.Image:
    """OpenCV linear transform: fast per-pixel alpha/beta adjustment."""
    arr = cv2.cvtColor(_to_np(img), cv2.COLOR_RGB2BGR).astype(np.float32)
    alpha = 1.0 + (contrast / 100.0)
    beta = brightness * 2.55
    out = cv2.convertScaleAbs(arr, alpha=alpha, beta=beta)
    return _from_np(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def apply_filter(img: Image.Image, name: str) -> Image.Image:
    name = name.lower()
    if name == "grayscale":
        return ImageOps.grayscale(img).convert("RGB")
    if name == "blur":
        return img.filter(ImageFilter.GaussianBlur(radius=4))
    if name == "edge":
        arr = cv2.cvtColor(_to_np(img), cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(arr, 100, 200)
        return Image.fromarray(edges).convert("RGB")
    if name == "sepia":
        arr = _to_np(img).astype(np.float64)
        matrix = np.array([[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]])
        out = arr @ matrix.T
        return _from_np(out)
    if name == "sketch":
        gray = cv2.cvtColor(_to_np(img), cv2.COLOR_RGB2GRAY)
        inv = 255 - gray
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur, scale=256)
        return Image.fromarray(sketch).convert("RGB")
    if name == "emboss":
        kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
        out = cv2.filter2D(_to_np(img), -1, kernel)
        return _from_np(out)
    raise ValueError(f"Unknown filter: {name}")
