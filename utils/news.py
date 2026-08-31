"""RSS news feed fetcher for the right-pane news panel.

Fetches from M&A / ECM / capital-markets sources plus global financial
and Baltic regional feeds, returning a unified list sorted by publish date.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from time import mktime

import feedparser

from utils.news_feeds import active_news_feeds, download_feed_document

log = logging.getLogger(__name__)

NEWS_TTL = int(os.getenv("NEWS_TTL_SECONDS", "30"))

_cache: dict[str, dict] = {}


def _parse_date(entry) -> datetime:
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None) or entry.get(field)
        if val:
            try:
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
            except Exception:
                pass
    return datetime.now(tz=timezone.utc)


def _extract_image(entry) -> str | None:
    for media in getattr(entry, "media_thumbnail", []):
        if "url" in media:
            return media["url"]
    for media in getattr(entry, "media_content", []):
        if "url" in media:
            return media["url"]
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
    return None


def _fetch_one(feed: dict) -> list[dict]:
    try:
        parsed = feedparser.parse(download_feed_document(feed["url"]))
    except Exception as e:
        log.warning("RSS fetch failed for %s: %s", feed["name"], e)
        return []

    articles = []
    for entry in parsed.entries[:10]:
        url = entry.get("link", "").strip()
        if not url:
            continue
        summary = entry.get("summary", "")
        if summary and len(summary) > 300:
            summary = summary[:297] + "..."
        articles.append({
            "title": entry.get("title", "Untitled").strip(),
            "url": url,
            "summary": summary.strip(),
            "source": feed["name"],
            "icon": feed["icon"],
            "published": _parse_date(entry).isoformat(),
            "image": _extract_image(entry),
        })
    return articles


def clear_news_cache() -> None:
    _cache.clear()


async def fetch_news(user_id: str | None = None) -> list[dict]:
    """Fetch enabled RSS feeds and return a merged, deduplicated list."""
    feeds = active_news_feeds(user_id)
    signature = hashlib.sha256(
        json.dumps([(f["key"], f["url"]) for f in feeds], separators=(",", ":")).encode()
    ).hexdigest()
    now = datetime.now(tz=timezone.utc)
    cached = _cache.get(signature)
    if cached and (now - cached["fetched_at"]).total_seconds() < NEWS_TTL:
        return cached["articles"]

    results = await asyncio.gather(
        *[asyncio.to_thread(_fetch_one, feed) for feed in feeds],
        return_exceptions=True,
    )

    all_articles = []
    seen_urls: set[str] = set()
    for result in results:
        if isinstance(result, Exception):
            log.warning("RSS feed error: %s", result)
            continue
        for article in result:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)

    all_articles.sort(key=lambda a: a["published"], reverse=True)
    all_articles = all_articles[:50]

    _cache[signature] = {"articles": all_articles, "fetched_at": now}
    log.info("Fetched %d news articles from %d feeds", len(all_articles), len(feeds))
    return all_articles
