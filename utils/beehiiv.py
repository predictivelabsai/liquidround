"""Beehiiv newsletter syndication — publish digest posts via REST API v2."""

import logging
import os
import requests

log = logging.getLogger(__name__)


def publish_to_beehiiv(title: str, content_html: str, subtitle: str = "") -> dict:
    api_key = os.getenv("BEEHIIV_API_KEY")
    pub_id = os.getenv("BEEHIIV_PUBLICATION_ID")

    if not api_key or not pub_id:
        return {"ok": False, "skipped": True}

    try:
        resp = requests.post(
            f"https://api.beehiiv.com/v2/publications/{pub_id}/posts",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "subtitle": subtitle,
                "content_html": content_html,
                "status": "published",
                "send_to": "all",
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            return {
                "ok": True,
                "post_id": data.get("id", ""),
                "web_url": data.get("web_url", ""),
            }
        log.warning("Beehiiv publish failed: %s %s", resp.status_code, resp.text[:300])
        return {"ok": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        log.warning("Beehiiv request error: %s", e)
        return {"ok": False, "error": str(e)}
