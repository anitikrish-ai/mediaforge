"""Website extraction endpoints (trafilatura). URL validated for SSRF before fetch."""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException

from app.core.validation import validate_url
from app.services import web_extract_service as web

router = APIRouter(prefix="/api/extract", tags=["web-extract"])


@router.post("/article")
async def extract_article(url: str = Form(...), include_links: bool = Form(False), include_images: bool = Form(False)):
    validate_url(url)
    try:
        return web.extract_article(url, include_links, include_images)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/markdown")
async def extract_markdown(url: str = Form(...)):
    validate_url(url)
    try:
        md = web.extract_markdown(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"url": url, "markdown": md}
