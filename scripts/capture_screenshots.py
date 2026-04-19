"""Capture a tour of the LiquidRound app into ./screenshots.

Drives a real browser via Playwright against a running LiquidRound server
(default http://localhost:5007). Produces a deterministic set of PNG frames
for scripts/make_gif.py.

Usage (server must be running):
    python -m scripts.capture_screenshots
    LIQUIDROUND_URL=http://localhost:5007 python -m scripts.capture_screenshots
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

log = logging.getLogger("capture")

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"

BASE_URL = os.environ.get("LIQUIDROUND_URL", "http://localhost:5007")
VIEWPORT = {"width": 1400, "height": 900}


# (filename, url, wait_selector, full_page, post_action)
TOUR = [
    # Landing pages
    ("01-home.png",            "/",                  "text=ECM Agent Squad",             True,  None),
    ("02-platform.png",        "/platform",          "text=One system",                  True,  None),
    ("03-agents.png",          "/agents",            "text=ECM Agent Squad",              True,  None),
    ("04-agent-detail.png",    "/agents/deal_triage","text=Deal Triage",                 True,  None),
    ("05-how-it-works.png",    "/how-it-works",      "text=How it works",                True,  None),
    ("06-pricing.png",         "/pricing",           "text=synthetic data",              True,  None),
    # Product app — buyer + seller defaults
    ("07-app-buyer.png",       "/app?role=buyer",    "input[name='msg']",                False, None),
    ("08-app-seller.png",      "/app?role=seller",   "input[name='msg']",                False, None),
    # Chat flow (buyer)
    ("09-chat-profile.png",    "/app?role=buyer",    "input[name='msg']",                False, "profile"),
    ("10-chat-triage.png",     "/app?role=buyer",    "input[name='msg']",                False, "triage"),
    ("11-chat-score.png",      "/app?role=buyer",    "input[name='msg']",                False, "score"),
    # Seller
    ("12-chat-buyers.png",     "/app?role=seller",   "input[name='msg']",                False, "buyers"),
    ("13-chat-ipo.png",        "/app?role=seller",   "input[name='msg']",                False, "ipo"),
    # Configuration
    ("14-settings.png",        "/app?role=buyer",    "input[name='msg']",                False, "settings"),
]


CHAT_MSGS = {
    "profile":  "profile: SAP.DE",
    "triage":   "triage: Nordic renewable energy target, EUR 80M revenue, 15% EBITDA margin",
    "score":    "score buyer:Siemens target:Harju Elekter",
    "buyers":   "buyers company:B2B SaaS revenue:15M",
    "ipo":      "ipo company:Ignitis industry:Energy",
    "settings": "settings",
}


def _run_chat(page, msg: str) -> None:
    page.fill("input[name='msg']", msg)
    page.evaluate(
        "() => document.querySelector('form[hx-post=\"/chat\"]').dispatchEvent("
        "new Event('submit', {cancelable: true, bubbles: true}))"
    )
    # Wait for a bubble to render in #chat-area
    try:
        page.wait_for_function(
            """() => {
                const ca = document.getElementById('chat-area');
                if (!ca) return false;
                const bubbles = ca.querySelectorAll('div.bg-white');
                return bubbles.length >= 1;
            }""",
            timeout=60_000,
        )
    except Exception:
        log.warning("chat response didn't appear within 60s for: %s", msg)
    time.sleep(1.0)  # let any late paint settle


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    SHOTS.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = ctx.new_page()

        for fname, path, wait_for, full_page, action in TOUR:
            url = BASE_URL + path
            log.info("→ %s", url)
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
            except Exception as e:
                log.warning("goto failed %s: %s — retrying with 'load'", url, e)
                page.goto(url, wait_until="load", timeout=30_000)

            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=10_000)
                except Exception:
                    log.warning("selector %r didn't appear on %s", wait_for, path)

            if action and action in CHAT_MSGS:
                _run_chat(page, CHAT_MSGS[action])

            out = SHOTS / fname
            page.screenshot(path=str(out), full_page=full_page)
            log.info("  saved %s", out.relative_to(ROOT))

        browser.close()
    log.info("done — %d frames in %s", len(TOUR), SHOTS)


if __name__ == "__main__":
    main()
