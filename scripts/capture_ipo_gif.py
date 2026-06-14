"""Capture the IPO Map + IPO Pipeline sections into an animated GIF for social.

Drives a real browser via Playwright against a running LiquidRound server
(default http://localhost:5007) and composes the frames into a looping GIF.

Usage (server must be running, with IPO data + pipeline populated):
    python -m scripts.capture_ipo_gif

Output:
    screenshots/ipo/*.png          (individual frames)
    screenshots/liquidround-ipo.gif (animated, 5-panel rotation)
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots" / "ipo"
OUT_GIF = ROOT / "screenshots" / "liquidround-ipo.gif"
BASE_URL = os.environ.get("LIQUIDROUND_URL", "http://localhost:5007")
VIEWPORT = {"width": 1440, "height": 900}

# (filename, url, wait_selector, scroll_y, settle_seconds, hold_ms)
FRAMES = [
    ("01-map-treemap.png",   "/app/ipo-map",      "#ipo-treemap",     0,    3.0, 3000),
    ("02-map-charts.png",    "/app/ipo-map",      "#ipo-hist",        720,  3.0, 2600),
    ("03-map-tables.png",    "/app/ipo-map",      "#ipo-map-body",    1500, 3.0, 2600),
    ("04-pipeline-vals.png", "/app/ipo-pipeline", "#ipo-pl-valbar",   0,    3.0, 3000),
    ("05-pipeline-cards.png","/app/ipo-pipeline", "#ipo-pipeline-body",760, 2.5, 2800),
]

TARGET_W, TARGET_H = 1280, 800
BG = (11, 18, 32)  # LiquidRound navy #0B1220


def capture() -> list[tuple[Path, int]]:
    SHOTS.mkdir(parents=True, exist_ok=True)
    out: list[tuple[Path, int]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        for fname, url, sel, scroll_y, settle, hold in FRAMES:
            page.goto(f"{BASE_URL}{url}", wait_until="networkidle")
            try:
                page.wait_for_selector(sel, timeout=15000)
            except Exception:
                print(f"  ! selector {sel} not found on {url}")
            time.sleep(settle)  # let Plotly finish drawing
            if scroll_y:
                page.evaluate(
                    "(y) => { const el = document.querySelector('.ipo-wrap') "
                    "|| document.querySelector('.center-pane') || document.scrollingElement; "
                    "el.scrollTo(0, y); }", scroll_y,
                )
                time.sleep(1.0)
            path = SHOTS / fname
            page.screenshot(path=str(path))
            print(f"  captured {fname}")
            out.append((path, hold))
        browser.close()
    return out


def make_gif(frames: list[tuple[Path, int]]):
    images, durations = [], []
    for path, hold in frames:
        img = Image.open(path).convert("RGB")
        # fit into a uniform navy canvas
        scale = min(TARGET_W / img.width, TARGET_H / img.height)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        canvas = Image.new("RGB", (TARGET_W, TARGET_H), BG)
        canvas.paste(img, ((TARGET_W - img.width) // 2, (TARGET_H - img.height) // 2))
        images.append(canvas)
        durations.append(hold)
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        OUT_GIF, save_all=True, append_images=images[1:],
        duration=durations, loop=0, optimize=True, disposal=2,
    )
    print(f"GIF written: {OUT_GIF} ({len(images)} frames, {OUT_GIF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    make_gif(capture())
