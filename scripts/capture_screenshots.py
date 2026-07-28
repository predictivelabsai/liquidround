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

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo-capture@liquidround.ai")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Capture2026!")


# (filename, url, wait_selector, full_page, post_action)
# Public pages first (no auth), then auth-gated /app/* pages after login.
TOUR = [
    # ── Public landing pages ──────────────────────────────────────────
    ("01-home.png",            "/",                  "text=ECM Agent Squad",             True,  None),
    ("02-platform.png",        "/platform",          "text=One system",                  True,  None),
    ("03-agents.png",          "/agents",            "text=ECM Agent Squad",              True,  None),
    ("04-agent-detail.png",    "/agents/deal_triage","text=Deal Triage",                 True,  None),
    ("05-how-it-works.png",    "/how-it-works",      "text=How it works",                True,  None),
    ("06-pricing.png",         "/pricing",           "text=synthetic data",              True,  None),
    # ── Sign-in page (captured before logging in) ─────────────────────
    ("18-signin.png",          "/signin",            "text=Sign In",                     False, None),
    # ── Auth-gated /app/* pages (login happens before the first one) ──
    ("07-app-buyer.png",       "/app?role=buyer",    "#chat-input",                      False, "login_first"),
    ("08-app-seller.png",      "/app?role=seller",   "#chat-input",                      False, None),
    ("09-agent-browser.png",   "/app?role=buyer",    "#chat-input",                      False, "expand_agents"),
    # Chat flows
    ("10-chat-triage.png",     "/app?role=buyer",    "#chat-input",                      False, "triage"),
    ("11-chat-dcf.png",        "/app?role=buyer",    "#chat-input",                      False, "dcf"),
    ("12-chat-memo.png",       "/app?role=buyer",    "#chat-input",                      False, "memo"),
    ("13-chat-ipo.png",        "/app?role=seller",   "#chat-input",                      False, "ipo"),
    # Public markets dashboards
    ("15-ipo-map.png",         "/app/ipo-map",       "text=Global IPO heatmap",          False, None),
    ("16-hedgefunds.png",      "/app/hedgefunds",    "text=Hedge Fund Treemap",          False, "wait_treemap"),
    ("17-spacs.png",           "/app/spacs",         "text=SPAC Tracker",                False, None),
    # Investor Relations — press release creator
    ("19-ir-press-release.png",  "/app/investor-relations/press-release", "text=Press Release",   False, None),
    ("20-ir-press-release-form.png", "/app/investor-relations/press-release", "text=Research and draft", False, "scroll_form"),
    # IR agent chat flows
    ("21-chat-ir-triage.png",    "/app?role=buyer",    "#chat-input",                      False, "ir_triage"),
    ("22-chat-ir-publish.png",   "/app?role=buyer",    "#chat-input",                      False, "ir_publish"),
]


CHAT_MSGS = {
    "triage":   "triage: Baltic vet chain, EUR 4M EBITDA, 25% growth",
    "dcf":      "dcf: Grigeo at 9% WACC, 2.5% terminal growth",
    "memo":     "memo: draft the IC memo for InMedica",
    "ipo":      "ipo: Ignitis Group readiness assessment for Nasdaq Baltic",
    "ir_triage": "ir-triage: our CFO resigned unexpectedly — do we need to disclose?",
    "ir_publish": "ir-publish: finalize the approved Q3 earnings release",
}


def _run_chat(page, msg: str) -> None:
    """Type a message and send via the SSE /app/chat endpoint (JS-driven)."""
    page.fill("#chat-input", msg)
    page.evaluate("() => window.sendMessage && window.sendMessage(null)")
    # Wait for at least one message bubble (or a few seconds if the backend
    # errors out without an API key — the UI still shows error bubbles).
    try:
        page.wait_for_selector("#messages .msg", timeout=60_000)
    except Exception:
        log.warning("no message appeared within 60s for: %s", msg)
    time.sleep(1.5)


def _expand_all_agent_groups(page) -> None:
    """Expand the first 2 agent categories to show the 30-agent browser."""
    for cat_id in ["cat-sourcing", "cat-underwriting"]:
        page.evaluate(f"() => window.toggleGroup && window.toggleGroup({cat_id!r})")
    time.sleep(0.4)


_logged_in = False


def _ensure_login(page) -> None:
    """Log in via the signin form so auth-gated /app/* routes are accessible."""
    global _logged_in
    if _logged_in:
        return
    log.info("→ logging in as %s", DEMO_EMAIL)
    page.goto(f"{BASE_URL}/signin", wait_until="networkidle", timeout=30_000)
    page.fill("input[name=email]", DEMO_EMAIL)
    page.fill("input[name=password]", DEMO_PASSWORD)
    page.click("button[type=submit]")
    time.sleep(2)
    _logged_in = True
    log.info("  logged in OK")


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

            if action == "login_first":
                _ensure_login(page)
                page.goto(url, wait_until="networkidle", timeout=30_000)
                if wait_for:
                    try:
                        page.wait_for_selector(wait_for, timeout=15_000)
                    except Exception:
                        log.warning("selector %r didn't appear on %s after login", wait_for, path)
            elif action == "expand_agents":
                _expand_all_agent_groups(page)
            elif action == "wait_treemap":
                time.sleep(20)
            elif action == "scroll_form":
                page.evaluate("() => window.scrollTo(0, 300)")
                time.sleep(0.5)
            elif action and action in CHAT_MSGS:
                _run_chat(page, CHAT_MSGS[action])

            out = SHOTS / fname
            page.screenshot(path=str(out), full_page=full_page)
            log.info("  saved %s", out.relative_to(ROOT))

        browser.close()
    log.info("done — %d frames in %s", len(TOUR), SHOTS)


if __name__ == "__main__":
    main()
