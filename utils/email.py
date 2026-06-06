"""Postmark email sender for LiquidRound.

Sends transactional email via Postmark's HTTP API.
Requires POSTMARK_API_TOKEN env var.
"""
from __future__ import annotations

import json
import logging
import os

import requests

log = logging.getLogger(__name__)

POSTMARK_API_URL = "https://api.postmarkapp.com/email"


def send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    from_email: str | None = None,
    tag: str = "",
    api_token: str | None = None,
) -> dict:
    """Send a single email via Postmark.

    Returns the Postmark API response dict on success,
    or {"error": "..."} on failure.
    """
    token = api_token or os.getenv("POSTMARK_API_TOKEN")
    if not token:
        return {"error": "POSTMARK_API_TOKEN not set"}

    sender = from_email or os.getenv("FROM_EMAIL", "info@liquidround.com")
    sender_name = os.getenv("FROM_NAME", "PE Hero Ltd")
    if sender_name and "<" not in sender:
        sender = f"{sender_name} <{sender}>"

    payload = {
        "From": sender,
        "To": to,
        "Subject": subject,
        "HtmlBody": html_body,
        "MessageStream": "outbound",
    }
    if text_body:
        payload["TextBody"] = text_body
    if tag:
        payload["Tag"] = tag

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": token,
    }

    try:
        resp = requests.post(POSTMARK_API_URL, headers=headers,
                             data=json.dumps(payload), timeout=15)
        result = resp.json()
        if resp.status_code == 200 and result.get("ErrorCode") == 0:
            log.info(f"Email sent to {to}: {result.get('MessageID')}")
        else:
            log.error(f"Postmark error: {result}")
        return result
    except Exception as e:
        log.exception("Postmark send failed")
        return {"error": str(e)}
