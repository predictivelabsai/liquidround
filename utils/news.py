"""RSS news feed fetcher for the right-pane news panel.

Fetches from M&A / ECM / capital-markets sources plus global financial
and Baltic regional feeds, returning a unified list sorted by publish date.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from time import mktime

import feedparser

log = logging.getLogger(__name__)

FEEDS: list[dict] = [
    # M&A / ECM / capital markets
    {"name": "Mergermarket",     "url": "https://www.mergermarket.com/info/rss",                 "icon": "MM"},
    {"name": "GlobalCapital",    "url": "https://www.globalcapital.com/rss",                     "icon": "GC"},
    {"name": "PitchBook News",   "url": "https://pitchbook.com/news/feed",                       "icon": "PB"},
    # Global financial
    {"name": "Financial Times",  "url": "https://www.ft.com/rss/home",                           "icon": "FT"},
    {"name": "Wall Street Journal", "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",        "icon": "WSJ"},
    {"name": "Bloomberg",        "url": "https://feeds.bloomberg.com/markets/news.rss",           "icon": "BBG"},
    {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best", "icon": "RTR"},
    {"name": "BBC Business",     "url": "http://feeds.bbci.co.uk/news/business/rss.xml",          "icon": "BBC"},
    # Baltic
    {"name": "ERR News",         "url": "https://news.err.ee/rss",                                "icon": "ERR"},
    {"name": "Baltic Times",     "url": "https://www.baltictimes.com/rss.xml",                    "icon": "BT"},
]

NEWS_TTL = int(os.getenv("NEWS_TTL_SECONDS", "30"))

_cache: dict = {"articles": [], "fetched_at": None}


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
        parsed = feedparser.parse(feed["url"])
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


async def fetch_news() -> list[dict]:
    """Fetch all RSS feeds and return merged, deduplicated, sorted list."""
    now = datetime.now(tz=timezone.utc)
    if _cache["fetched_at"] and (now - _cache["fetched_at"]).total_seconds() < NEWS_TTL:
        return _cache["articles"]

    results = await asyncio.gather(
        *[asyncio.to_thread(_fetch_one, f) for f in FEEDS],
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

    _cache["articles"] = all_articles
    _cache["fetched_at"] = now
    log.info("Fetched %d news articles from %d feeds", len(all_articles), len(FEEDS))
    return all_articles
