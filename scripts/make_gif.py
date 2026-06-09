"""Compose LiquidRound demo screenshots into an animated GIF.

Usage:
    python -m scripts.make_gif

Output: docs/liquidround.gif (also copies to static/liquidround.gif so the
landing page `<img src="/static/liquidround.gif">` picks it up immediately).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"
OUT_GIF = ROOT / "docs" / "liquidround.gif"
STATIC_GIF = ROOT / "static" / "liquidround.gif"

# App-focused tour. Landing frames intentionally shortened (the GIF lives ON
# the landing page — no point watching it play the landing again).
FRAMES = [
    ("07-app-buyer.png",       2200),  # chat buyer view
    ("09-agent-browser.png",   2800),  # ECM Squad agent browser expanded
    ("10-chat-triage.png",     3200),  # triage
    ("11-chat-dcf.png",        3200),  # DCF
    ("12-chat-memo.png",       3400),  # IC memo
    ("08-app-seller.png",      2000),  # seller default view
    ("13-chat-ipo.png",        3200),  # IPO readiness
    ("14-settings.png",        2400),  # profile & preferences
]

TARGET_W = 1200
TARGET_H = 820
BG = (11, 18, 32)  # LiquidRound navy (#0B1220)


def load_frame(path: Path) -> Image.Image:
    img = Image.open(path).convert("RGB")
    ratio = TARGET_W / img.width
    img = img.resize((TARGET_W, int(img.height * ratio)), Image.LANCZOS)
    if img.height > TARGET_H:
        img = img.crop((0, 0, TARGET_W, TARGET_H))
    else:
        canvas = Image.new("RGB", (TARGET_W, TARGET_H), BG)
        canvas.paste(img, (0, 0))
        img = canvas
    return img


def main() -> None:
    frames: list[Image.Image] = []
    durations: list[int] = []
    for fname, dur in FRAMES:
        p = SHOTS / fname
        if not p.exists():
            print(f"  skip (missing): {p}")
            continue
        frames.append(load_frame(p))
        durations.append(dur)
        print(f"  added {fname}  ({dur} ms)")

    if not frames:
        raise SystemExit("No frames found — run scripts/capture_screenshots.py first.")

    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames[1:],
        optimize=True,
        duration=durations,
        loop=0,
        disposal=2,
    )
    size_kb = OUT_GIF.stat().st_size / 1024
    print(f"\nWrote {OUT_GIF}  ({size_kb:.1f} KB, {len(frames)} frames)")

    # Also copy to /static so the landing page picks it up without a mount.
    STATIC_GIF.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT_GIF, STATIC_GIF)
    print(f"Copied to {STATIC_GIF}")


if __name__ == "__main__":
    main()
