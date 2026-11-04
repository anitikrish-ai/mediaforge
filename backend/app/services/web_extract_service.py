"""Website content extraction via trafilatura — clean article text, metadata,
and optional link/image extraction, with graceful fallback when extraction
yields nothing (paywalled/JS-only pages)."""
from __future__ import annotations

import trafilatura


def extract_article(url: str, include_links: bool = False, include_images: bool = False) -> dict:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Could not download the page. It may be unreachable or blocking automated requests.")

    text = trafilatura.extract(
        downloaded,
        include_links=include_links,
        include_images=include_images,
        include_comments=False,
        favor_precision=True,
    )
    metadata = trafilatura.extract_metadata(downloaded)
    meta_dict = metadata.as_dict() if metadata else {}

    if not text:
        raise ValueError("No readable article content found on this page (it may require JavaScript or be behind a paywall).")

    word_count = len(text.split())
    return {
        "url": url,
        "title": meta_dict.get("title"),
        "author": meta_dict.get("author"),
        "date": meta_dict.get("date"),
        "sitename": meta_dict.get("sitename"),
        "description": meta_dict.get("description"),
        "text": text,
        "word_count": word_count,
        "reading_time_min": max(1, round(word_count / 200)),
    }


def extract_markdown(url: str) -> str:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Could not download the page.")
    md = trafilatura.extract(downloaded, output_format="markdown", favor_precision=True)
    if not md:
        raise ValueError("No readable article content found on this page.")
    return md
