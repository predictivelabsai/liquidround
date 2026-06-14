"""IPO news for the IPO Map page — thin wrapper over Tavily web search."""
from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


async def get_ipo_news(query: str = "latest IPO market news and recent stock market debuts",
                       limit: int = 6) -> List[Dict]:
    """Return a list of ``{title, url, summary, source, score}`` news items."""
    try:
        from .research_tools import ResearchTools
        res = await ResearchTools().tavily_search(query)
        items = []
        for r in res.get("results", [])[:limit]:
            url = r.get("url", "")
            source = ""
            if url:
                try:
                    source = url.split("/")[2].replace("www.", "")
                except IndexError:
                    source = ""
            items.append({
                "title": r.get("title") or "Untitled",
                "url": url,
                "summary": r.get("content") or "",
                "source": source,
                "score": r.get("score", 0),
            })
        return items
    except Exception as e:  # noqa: BLE001
        logger.warning("IPO news fetch failed: %s", e)
        return []
