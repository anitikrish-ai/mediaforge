"""Upload / URL validation helpers shared by every router.
Fail fast with clear HTTPExceptions rather than letting a library crash deep
inside a service.
"""
from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile

from app.core.config import settings

_PRIVATE_HOST_RE = re.compile(r"^(localhost|127\.|10\.|172\.(1[6-9]|2\d|3[0-1])\.|192\.168\.|0\.0\.0\.0)")


def validate_extension(filename: str, allowed: set[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}",
        )
    return ext


async def validate_upload_size(file: UploadFile, max_mb: int) -> bytes:
    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > max_mb:
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f}MB). Limit is {max_mb}MB.")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    await file.seek(0)
    return data


def validate_url(url: str) -> str:
    """Basic SSRF-aware URL validation: require http(s), block obvious internal hosts."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    if not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL.")
    host = parsed.hostname or ""
    if _PRIVATE_HOST_RE.match(host):
        raise HTTPException(status_code=400, detail="URLs pointing at local/private addresses are not allowed.")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise HTTPException(status_code=400, detail="URLs pointing at local/private addresses are not allowed.")
    except ValueError:
        pass  # host is a domain name, not an IP literal — fine
    return url


def safe_filename(name: str) -> str:
    name = Path(name).name  # strip any path components
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return name[:200] or "file"
