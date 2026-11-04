"""Media downloading via yt-dlp. Supports format probing (list available
qualities) and downloading with a chosen format/quality, reporting live
progress through a callback so the UI can show a real progress bar.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import yt_dlp

ProgressCB = Callable[[float, str], None]


def probe_formats(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    for f in info.get("formats", []):
        if not f.get("url"):
            continue
        formats.append({
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "resolution": f.get("resolution") or (f"{f.get('width')}x{f.get('height')}" if f.get("width") else None),
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
            "filesize_approx": f.get("filesize") or f.get("filesize_approx"),
            "fps": f.get("fps"),
            "note": f.get("format_note"),
        })
    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "uploader": info.get("uploader"),
        "extractor": info.get("extractor"),
        "formats": formats,
    }


def download(
    url: str,
    out_dir: Path,
    mode: str = "video",                 # "video" | "audio"
    quality: str = "best",                # "best" | "worst" | specific format_id | height like "720"
    audio_format: str = "mp3",
    progress_cb: Optional[ProgressCB] = None,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(title).150B.%(ext)s")

    def hook(d):
        if not progress_cb:
            return
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            speed = d.get("speed")
            speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else ""
            progress_cb(min(99, pct), f"Downloading {pct:.0f}% {speed_str}")
        elif d["status"] == "finished":
            progress_cb(99, "Finalizing...")

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "restrictfilenames": True,
    }

    if mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": audio_format,
            "preferredquality": "192",
        }]
    else:
        if quality == "best":
            opts["format"] = "bestvideo+bestaudio/best"
        elif quality == "worst":
            opts["format"] = "worstvideo+worstaudio/worst"
        elif quality.isdigit():
            opts["format"] = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        else:
            opts["format"] = quality  # explicit format_id
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        if mode == "audio":
            filepath = str(Path(filepath).with_suffix(f".{audio_format}"))

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "filepath": filepath,
        "ext": Path(filepath).suffix.lstrip("."),
    }
