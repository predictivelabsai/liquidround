"""Merger-topic RSS ingestion for GlobeNewswire, Business Wire, and PR Newswire."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import feedparser
from dateutil import parser as date_parser

from utils.filing_intelligence import html_to_markdown
from utils.reverse_mergers import extract_transaction_terms


FEEDS = {
    "globenewswire": (
        "https://www.globenewswire.com/RssFeed/subjectcode/"
        "27-Mergers%20and%20Acquisitions/feedTitle/"
        "GlobeNewswire%20-%20Mergers%20and%20Acquisitions"
    ),
    # Finespresso's proven Business Wire feed; filtered locally to merger events.
    "businesswire": (
        "https://feed.businesswire.com/rss/home/"
        "?rss=G1QFDERJXkJeEFpRXEMGSQ5SS1JVEUFeEEZRXEUDGkRJXhlZVl1cFQ=="
    ),
    "prnewswire": "https://www.prnewswire.com/rss/news-releases-list.rss",
}

_MERGER_RE = re.compile(
    r"\b(acquir(?:e|es|ed|ing|er|ition)|merg(?:e|er|es|ed|ing)|takeover|"
    r"business combination|reverse merger|reverse takeover|rto|"
    r"to be acquired|definitive agreement|sale to|combine forces)\b",
    re.IGNORECASE,
)
_REVERSE_RE = re.compile(
    r"\b(reverse merger|reverse takeover|reverse acquisition|rto|"
    r"change in shell company status|ceased to be a shell)\b",
    re.IGNORECASE,
)
_NOISE_RE = re.compile(
    r"\b(form 8\.[35]|investor alert|shareholder alert|class action|"
    r"investigation alert|securities fraud|application deadline|law firm|"
    r"litigation|lawsuit|court denies)\b",
    re.IGNORECASE,
)


def canonical_url(value: str) -> str:
    parts = urlsplit(value or "")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, "", ""))


def classify_stage(text: str) -> str:
    lower = re.sub(r"\s+", " ", text or "").lower()
    if any(term in lower for term in ("terminated", "termination of", "withdraws offer", "abandoned")):
        return "terminated"
    if any(term in lower for term in ("completed its acquisition", "completes acquisition",
                                      "completion of the acquisition", "closed the acquisition",
                                      "consummated the merger", "merger completed",
                                      " acquires ", " acquired ")):
        return "completed"
    if any(term in lower for term in ("shareholders approve", "stockholders approve",
                                      "shareholder approval", "regulatory approval")):
        return "approved"
    if any(term in lower for term in ("definitive agreement", "to acquire", "will acquire",
                                      "agrees to acquire", "merger agreement")):
        return "announced"
    if any(term in lower for term in ("proposal", "non-binding offer", "letter of intent", " loi ")):
        return "proposed"
    return "other"


def parse_entry(source: str, entry) -> dict | None:
    title = html_to_markdown(entry.get("title", "")).strip()
    summary = html_to_markdown(
        entry.get("summary", "") or entry.get("description", "")
    ).strip()
    evidence = f"{title}\n{summary}"
    if _NOISE_RE.search(evidence) or not _MERGER_RE.search(evidence):
        return None
    link = canonical_url(entry.get("link", ""))
    external_id = str(entry.get("id") or entry.get("guid") or link or title)
    published = entry.get("published") or entry.get("updated")
    try:
        # Business Wire emits the obsolete "UT" timezone abbreviation.
        published = re.sub(r"\bUT\b", "GMT", published) if published else published
        published_at = date_parser.parse(published).astimezone(timezone.utc) if published else None
    except (ValueError, TypeError, OverflowError):
        published_at = None
    terms = extract_transaction_terms(evidence)
    return {
        "source": source,
        "external_id": hashlib.sha256(external_id.encode()).hexdigest(),
        "title": title,
        "source_url": link,
        "published_at": published_at,
        "summary": summary[:4000] or None,
        "event_stage": classify_stage(evidence),
        "target": terms["private_target"],
        "deal_value": terms["deal_value"],
        "is_reverse_merger": bool(_REVERSE_RE.search(evidence)),
        "metadata": {
            "rss_topic": "mergers_and_acquisitions",
            "feed_url": FEEDS[source],
        },
    }


def fetch_merger_news(*, max_items_per_feed: int | None = None) -> list[dict]:
    records = []
    seen_urls = set()
    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        entries = feed.entries[:max_items_per_feed] if max_items_per_feed else feed.entries
        for entry in entries:
            record = parse_entry(source, entry)
            if not record or not record["source_url"] or record["source_url"] in seen_urls:
                continue
            seen_urls.add(record["source_url"])
            records.append(record)
    return records


def upsert_merger_news(records: list[dict]) -> int:
    if not records:
        return 0
    from utils.database import get_conn

    sql = """
        INSERT INTO liquidround.merger_news
          (source,external_id,title,source_url,published_at,summary,event_stage,
           acquirer,target,deal_value,is_reverse_merger,metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        ON CONFLICT (source,external_id) DO UPDATE SET
          title=EXCLUDED.title,source_url=EXCLUDED.source_url,
          published_at=EXCLUDED.published_at,summary=EXCLUDED.summary,
          event_stage=EXCLUDED.event_stage,
          target=COALESCE(EXCLUDED.target,liquidround.merger_news.target),
          deal_value=COALESCE(EXCLUDED.deal_value,liquidround.merger_news.deal_value),
          is_reverse_merger=EXCLUDED.is_reverse_merger,
          metadata=EXCLUDED.metadata,updated_at=NOW()
    """
    with get_conn() as connection:
        cursor = connection.cursor()
        cursor.execute(
            r"""DELETE FROM liquidround.merger_news
                WHERE (title || ' ' || COALESCE(summary, '')) ~*
                '\m(form 8\.[35]|investor alert|shareholder alert|class action|investigation alert|securities fraud|application deadline|law firm|litigation|lawsuit|court denies)\M'"""
        )
        for record in records:
            cursor.execute(sql, (
                record["source"], record["external_id"], record["title"],
                record["source_url"], record["published_at"], record["summary"],
                record["event_stage"], record.get("acquirer"), record.get("target"),
                record.get("deal_value"), record["is_reverse_merger"],
                json.dumps(record["metadata"]),
            ))
    return len(records)


def list_merger_news(*, source: str = "", stage: str = "", limit: int = 150) -> list[dict]:
    from utils.database import get_conn

    clauses, params = [], []
    if source:
        clauses.append("source=%s"); params.append(source)
    if stage:
        clauses.append("event_stage=%s"); params.append(stage)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with get_conn() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""SELECT source,title,source_url,published_at,summary,event_stage,
                       target,deal_value,is_reverse_merger
                FROM liquidround.merger_news{where}
                ORDER BY published_at DESC NULLS LAST LIMIT %s""",
            params,
        )
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
