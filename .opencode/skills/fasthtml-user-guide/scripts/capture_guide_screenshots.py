#!/usr/bin/env python3
"""Capture the user-guide screenshots from a running FastClinic cockpit.

Drives a headless Chromium through the cockpit and saves one screenshot per
feature page into docs/img/. These feed the landscape user guide
(docs/fastclinic_user_guide_<date>.md → PDF + PPTX).

Usage (server must be running):
    DEMO_BASE_URL=http://localhost:5005 python scripts/capture_guide_screenshots.py

Env: FASTCLINIC_ADMIN_EMAIL / FASTCLINIC_ADMIN_PASSWORD (defaults match the demo).
"""
from __future__ import annotations

import argparse
import os
import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 1440, "height": 900}

# (filename, kind, target) — kind drives the interaction.
SHOTS = [
    ("00-login.png",       "login",   "/login"),
    ("01-overview.png",    "goto",    "/"),
    ("02-copilot.png",     "copilot", "/due"),
    ("03-reminders.png",   "goto",    "/activation/reminders"),
    ("04-lapsed.png",      "goto",    "/activation/lapsed"),
    ("05-followup.png",    "goto",    "/activation/followup"),
    ("06-loop.png",        "loop",    "/activation/loop"),
    ("07-appointments.png","goto",    "/appointments"),
    ("08-patients.png",    "goto",    "/patients"),
    ("09-patient.png",     "goto",    "/patients/1206"),
    ("10-clinical.png",    "goto",    "/clinical"),
    ("11-revenue.png",     "goto",    "/revenue"),
    ("12-billing.png",     "billing", "/billing"),
    ("13-sms.png",         "goto",    "/ops/sms"),
    ("14-email.png",       "goto",    "/ops/email"),
    ("15-ai.png",          "goto",    "/ai"),
    ("16-seo.png",         "goto",    "/seo"),
    ("17-data.png",        "goto",    "/admin/data"),
]


def _settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(1400)  # let Plotly/animations finish painting


def capture(base_url: str, out_dir: str, only: set[str] | None = None):
    email = os.getenv("FASTCLINIC_ADMIN_EMAIL", "admin@fastclinic.example")
    password = os.getenv("FASTCLINIC_ADMIN_PASSWORD", "FastClinic2026$")
    os.makedirs(out_dir, exist_ok=True)
    shots = [s for s in SHOTS if not only or s[0] in only]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1)
        page = ctx.new_page()

        # pre-auth login shot
        login_shot = next((s for s in shots if s[1] == "login"), None)
        if login_shot:
            page.goto(f"{base_url}/login")
            _settle(page)
            page.screenshot(path=os.path.join(out_dir, login_shot[0]))
            print(f"  ✓ {login_shot[0]}")

        # login
        page.goto(f"{base_url}/login")
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        for fname, kind, target in shots:
            if kind == "login":
                continue
            dest = os.path.join(out_dir, fname)
            try:
                if kind == "goto":
                    page.goto(f"{base_url}{target}")
                    _settle(page)
                elif kind == "copilot":
                    page.goto(f"{base_url}/")
                    _settle(page)
                    try:
                        page.fill("#chat-input", target)
                        page.press("#chat-input", "Enter")
                        page.wait_for_timeout(2500)
                    except Exception:
                        pass
                elif kind == "loop":
                    page.goto(f"{base_url}{target}")
                    _settle(page)
                    # populate the loop so the page isn't empty
                    try:
                        page.click("text=Queue due reminders")
                        page.wait_for_timeout(1500)
                    except Exception:
                        pass
                elif kind == "billing":
                    page.goto(f"{base_url}{target}")
                    _settle(page)
                page.screenshot(path=dest)
                print(f"  ✓ {fname}")
            except Exception as e:  # keep going; report the miss
                print(f"  ✗ {fname}: {e}", file=sys.stderr)
        browser.close()
    print(f"✓ Saved screenshots to {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.getenv("DEMO_BASE_URL", "http://localhost:5005"))
    ap.add_argument("--out", default="docs/img")
    ap.add_argument("--only", default="", help="comma-separated filenames to (re)capture")
    a = ap.parse_args()
    only = {s.strip() for s in a.only.split(",") if s.strip()} or None
    capture(a.base_url.rstrip("/"), a.out, only)
