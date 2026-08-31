"""Per-user RSS sources and safe automatic feed discovery."""
from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
from urllib.parse import urljoin

import feedparser
import requests
from psycopg2.extras import RealDictCursor

from utils.database import get_conn
from utils.security import validate_public_url, validate_redirect_url


BUILTIN_FEEDS: tuple[dict, ...] = (
    {"key": "mergermarket", "name": "Mergermarket", "url": "https://www.mergermarket.com/info/rss", "icon": "MM"},
    {"key": "globalcapital", "name": "GlobalCapital", "url": "https://www.globalcapital.com/rss", "icon": "GC"},
    {"key": "pitchbook-news", "name": "PitchBook News", "url": "https://pitchbook.com/news/feed", "icon": "PB"},
    {"key": "financial-times", "name": "Financial Times", "url": "https://www.ft.com/rss/home", "icon": "FT"},
    {"key": "wall-street-journal", "name": "Wall Street Journal", "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "icon": "WSJ"},
    {"key": "bloomberg", "name": "Bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss", "icon": "BBG"},
    {"key": "reuters-business", "name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best", "icon": "RTR"},
    {"key": "bbc-business", "name": "BBC Business", "url": "http://feeds.bbci.co.uk/news/business/rss.xml", "icon": "BBC"},
    {"key": "err-news", "name": "ERR News", "url": "https://news.err.ee/rss", "icon": "ERR"},
    {"key": "baltic-times", "name": "Baltic Times", "url": "https://www.baltictimes.com/rss.xml", "icon": "BT"},
)

MAX_FEED_BYTES = 1_000_000
USER_AGENT = "LiquidRound-RSS/0.8.1 (+https://liquidround.ai)"


class NewsFeedError(ValueError):
    pass


class _AlternateFeedParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "link":
            return
        values = {str(key).lower(): str(value) for key, value in attrs if value is not None}
        rel = values.get("rel", "").lower().split()
        kind = values.get("type", "").lower()
        if "alternate" in rel and kind in {"application/rss+xml", "application/atom+xml"} and values.get("href"):
            self.urls.append(values["href"])


def _download(url: str) -> tuple[str, bytes, str]:
    """Download a small public document, validating every redirect hop."""
    current = validate_public_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=.5"}
    for _ in range(4):
        try:
            response = requests.get(current, headers=headers, timeout=(5, 15), allow_redirects=False, stream=True)
        except requests.RequestException as exc:
            raise NewsFeedError("The feed could not be reached") from exc
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("location", "")
            response.close()
            if not location:
                raise NewsFeedError("The feed returned an invalid redirect")
            try:
                current = validate_redirect_url(current, location)
            except ValueError as exc:
                raise NewsFeedError(str(exc)) from exc
            continue
        try:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(64 * 1024):
                content.extend(chunk)
                if len(content) > MAX_FEED_BYTES:
                    raise NewsFeedError("The feed is larger than 1 MB")
            return current, bytes(content), response.headers.get("content-type", "")
        except requests.RequestException as exc:
            raise NewsFeedError(f"The feed returned HTTP {response.status_code}") from exc
        finally:
            response.close()
    raise NewsFeedError("The feed redirected too many times")


def download_feed_document(url: str) -> bytes:
    """Return a validated, size-bounded public feed document."""
    return _download(url)[1]


def _clean_name(value: str) -> str:
    name = " ".join(html.unescape(value or "").split()).strip()
    return name[:180] or "Custom feed"


def _icon_for(name: str) -> str:
    words = [word for word in name.replace("&", " ").split() if word]
    icon = "".join(word[0] for word in words[:3]).upper()
    return (icon or name[:3].upper() or "RSS")[:8]


def discover_feed(url: str) -> dict:
    """Resolve a feed or page URL and infer its title and icon."""
    try:
        final_url, content, content_type = _download(url)
    except ValueError as exc:
        raise NewsFeedError(str(exc)) from exc
    parsed = feedparser.parse(content)
    if not parsed.entries and not parsed.feed.get("title"):
        parser = _AlternateFeedParser()
        if "html" in content_type.lower() or b"<html" in content[:1000].lower():
            parser.feed(content.decode("utf-8", errors="ignore"))
        if parser.urls:
            alternate = urljoin(final_url, parser.urls[0])
            try:
                final_url, content, _ = _download(alternate)
            except ValueError as exc:
                raise NewsFeedError(str(exc)) from exc
            parsed = feedparser.parse(content)
    if not parsed.entries and not parsed.feed.get("title"):
        raise NewsFeedError("No RSS or Atom feed was found at that address")
    name = _clean_name(parsed.feed.get("title", "Custom feed"))
    return {"name": name, "url": final_url, "icon": _icon_for(name)}


def _stored_rows(user_id: str) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """SELECT feed_key, name, url, icon, is_builtin, enabled
               FROM liquidround.user_news_feeds
               WHERE user_id = %s ORDER BY created_at, id""",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def list_user_feeds(user_id: str | None) -> list[dict]:
    """Merge built-ins with the signed-in user's overrides and custom feeds."""
    rows = _stored_rows(user_id) if user_id else []
    overrides = {row["feed_key"]: row for row in rows if row["is_builtin"]}
    merged = []
    for source in BUILTIN_FEEDS:
        item = {**source, "is_builtin": True, "enabled": True}
        override = overrides.get(source["key"])
        if override:
            item["enabled"] = bool(override["enabled"])
        merged.append(item)
    merged.extend(
        {**row, "key": row["feed_key"]}
        for row in rows if not row["is_builtin"]
    )
    return merged


def active_news_feeds(user_id: str | None) -> list[dict]:
    return [feed for feed in list_user_feeds(user_id) if feed["enabled"]]


def set_feed_enabled(user_id: str, feed_key: str, enabled: bool) -> None:
    builtin = next((feed for feed in BUILTIN_FEEDS if feed["key"] == feed_key), None)
    with get_conn() as conn:
        cur = conn.cursor()
        if builtin:
            cur.execute(
                """INSERT INTO liquidround.user_news_feeds
                       (user_id, feed_key, name, url, icon, is_builtin, enabled)
                   VALUES (%s, %s, %s, %s, %s, TRUE, %s)
                   ON CONFLICT (user_id, feed_key) DO UPDATE
                   SET enabled = EXCLUDED.enabled, updated_at = NOW()""",
                (user_id, feed_key, builtin["name"], builtin["url"], builtin["icon"], enabled),
            )
        else:
            cur.execute(
                """UPDATE liquidround.user_news_feeds
                   SET enabled = %s, updated_at = NOW()
                   WHERE user_id = %s AND feed_key = %s AND is_builtin = FALSE""",
                (enabled, user_id, feed_key),
            )
            if cur.rowcount != 1:
                raise NewsFeedError("News feed not found")


def add_custom_feed(user_id: str, url: str) -> dict:
    discovered = discover_feed(url)
    builtin = next((feed for feed in BUILTIN_FEEDS if feed["url"] == discovered["url"]), None)
    if builtin:
        set_feed_enabled(user_id, builtin["key"], True)
        return {**builtin, "is_builtin": True, "enabled": True}
    feed_key = "custom-" + hashlib.sha256(discovered["url"].encode()).hexdigest()[:20]
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """INSERT INTO liquidround.user_news_feeds
                   (user_id, feed_key, name, url, icon, is_builtin, enabled)
               VALUES (%s, %s, %s, %s, %s, FALSE, TRUE)
               ON CONFLICT (user_id, feed_key) DO UPDATE
               SET name = EXCLUDED.name, icon = EXCLUDED.icon, enabled = TRUE, updated_at = NOW()
               RETURNING feed_key, name, url, icon, is_builtin, enabled""",
            (user_id, feed_key, discovered["name"], discovered["url"], discovered["icon"]),
        )
        row = dict(cur.fetchone())
    return {**row, "key": row["feed_key"]}


def delete_custom_feed(user_id: str, feed_key: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM liquidround.user_news_feeds WHERE user_id = %s AND feed_key = %s AND is_builtin = FALSE",
            (user_id, feed_key),
        )
        if cur.rowcount != 1:
            raise NewsFeedError("Custom feed not found")
