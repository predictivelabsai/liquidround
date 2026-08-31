from __future__ import annotations

import pytest

from utils import news_feeds


def test_user_feed_overrides_are_merged_without_changing_defaults(monkeypatch):
    monkeypatch.setattr(
        news_feeds,
        "_stored_rows",
        lambda _user_id: [
            {
                "feed_key": "err-news", "name": "ERR News",
                "url": "https://news.err.ee/rss", "icon": "ERR",
                "is_builtin": True, "enabled": False,
            },
            {
                "feed_key": "custom-example", "name": "Example Deals",
                "url": "https://example.com/deals.xml", "icon": "ED",
                "is_builtin": False, "enabled": True,
            },
        ],
    )

    feeds = news_feeds.list_user_feeds("user-1")

    assert next(feed for feed in feeds if feed["key"] == "err-news")["enabled"] is False
    assert next(feed for feed in feeds if feed["key"] == "bloomberg")["enabled"] is True
    assert next(feed for feed in feeds if feed["key"] == "custom-example")["name"] == "Example Deals"


def test_guest_feed_list_uses_enabled_builtins_only(monkeypatch):
    monkeypatch.setattr(news_feeds, "_stored_rows", lambda _user_id: pytest.fail("database should not be queried"))
    feeds = news_feeds.list_user_feeds(None)
    assert len(feeds) == len(news_feeds.BUILTIN_FEEDS)
    assert all(feed["enabled"] for feed in feeds)


def test_discover_feed_detects_title_and_icon(monkeypatch):
    body = b"""<?xml version='1.0'?><rss version='2.0'><channel>
      <title>Example Deal Wire</title><link>https://example.com</link>
      <item><title>Transaction announced</title><link>https://example.com/1</link></item>
    </channel></rss>"""
    monkeypatch.setattr(
        news_feeds, "_download",
        lambda _url: ("https://example.com/rss.xml", body, "application/rss+xml"),
    )
    result = news_feeds.discover_feed("https://example.com")
    assert result == {
        "name": "Example Deal Wire",
        "url": "https://example.com/rss.xml",
        "icon": "EDW",
    }


def test_discover_feed_follows_advertised_feed(monkeypatch):
    html = b'<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head></html>'
    rss = b"<rss><channel><title>Issuer News</title><item><title>One</title><link>https://example.com/one</link></item></channel></rss>"
    calls = []

    def fake_download(url):
        calls.append(url)
        if len(calls) == 1:
            return "https://example.com/news", html, "text/html"
        return "https://example.com/feed.xml", rss, "application/rss+xml"

    monkeypatch.setattr(news_feeds, "_download", fake_download)
    result = news_feeds.discover_feed("https://example.com/news")
    assert calls == ["https://example.com/news", "https://example.com/feed.xml"]
    assert result["name"] == "Issuer News"


def test_discover_feed_rejects_internal_url_before_request(monkeypatch):
    monkeypatch.setattr(
        news_feeds.requests, "get",
        lambda *_args, **_kwargs: pytest.fail("internal URL must not be requested"),
    )
    with pytest.raises(news_feeds.NewsFeedError, match="Private|Local"):
        news_feeds.discover_feed("http://127.0.0.1:5007/feed.xml")
