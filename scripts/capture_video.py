"""
LiquidRound - Demo Video Capture Script
Captures frames of the buyer/seller flows, then assembles MP4 + GIF.

Usage:
    python scripts/capture_video.py              # App must be running on port 5007
    python scripts/capture_video.py --start-app  # Auto-start app

Output:
    docs/frames/*.png          - Individual frame captures
    docs/demo_video.mp4        - H.264 video (2 FPS, 1.5s per frame)
    docs/demo_video.gif        - Animated GIF (50% scale)
"""
import asyncio
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRAMES_DIR = ROOT / "docs" / "frames"
DOCS_DIR = ROOT / "docs"
BASE_URL = "http://localhost:5007"

frame_num = 0


async def capture(page, label, pause=1.0):
    """Capture a numbered frame."""
    global frame_num
    await asyncio.sleep(pause)
    path = FRAMES_DIR / f"{frame_num:03d}_{label}.png"
    await page.screenshot(path=str(path), type="png")
    print(f"  [{frame_num:03d}] {label}")
    frame_num += 1


async def send_chat(page, msg, wait=5.0):
    """Type a message and submit via chat form."""
    await page.evaluate(f"""
        () => {{
            var inp = document.querySelector('input[name="msg"]');
            if (inp) {{
                inp.value = {repr(msg)};
                inp.form.requestSubmit();
            }}
        }}
    """)
    await asyncio.sleep(wait)
    # Scroll chat to bottom
    await page.evaluate("""
        () => {
            var c = document.getElementById('chat-area');
            if (c) c.scrollTop = c.scrollHeight;
        }
    """)


async def open_canvas(page):
    """Open the right-side canvas panel."""
    await page.evaluate("""
        () => {
            var rp = document.getElementById('right-pane');
            if (rp) rp.classList.remove('translate-x-full');
        }
    """)
    await asyncio.sleep(0.5)


async def close_canvas(page):
    """Close the right-side canvas panel."""
    await page.evaluate("""
        () => {
            var rp = document.getElementById('right-pane');
            if (rp) rp.classList.add('translate-x-full');
        }
    """)
    await asyncio.sleep(0.3)


async def switch_canvas_tab(page, tab_endpoint):
    """Switch canvas tab via HTMX."""
    await page.evaluate(f"""
        () => {{
            htmx.ajax('GET', '{tab_endpoint}', {{target: '#canvas-content', swap: 'innerHTML'}});
        }}
    """)
    await asyncio.sleep(0.8)


async def click_nav_button(page, button_text):
    """Click a left nav button by text."""
    await page.evaluate(f"""
        () => {{
            var buttons = document.querySelectorAll('#nav-panel button');
            for (var b of buttons) {{
                if (b.textContent.trim() === {repr(button_text)}) {{
                    b.click();
                    break;
                }}
            }}
        }}
    """)


async def expand_nav_section(page, section_text):
    """Open a collapsed nav details section."""
    await page.evaluate(f"""
        () => {{
            var details = document.querySelectorAll('#nav-panel details');
            for (var d of details) {{
                var summary = d.querySelector('summary');
                if (summary && summary.textContent.includes({repr(section_text)})) {{
                    d.open = true;
                    break;
                }}
            }}
        }}
    """)
    await asyncio.sleep(0.3)


async def run():
    """Main capture flow."""
    global frame_num
    frame_num = 0

    from playwright.async_api import async_playwright

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

    print("LiquidRound Demo Video Capture")
    print(f"  Frames: {FRAMES_DIR}")
    print(f"  Target: {BASE_URL}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # ---- WELCOME SCREEN ----
        print("1. Welcome screen")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await capture(page, "welcome", pause=1.5)
        await capture(page, "welcome_hold", pause=1.0)

        # ---- BUYER FLOW ----
        print("2. Buyer flow - click 'I want to acquire'")
        # Click the BUYER card
        await page.evaluate("""
            () => {
                var cards = document.querySelectorAll('#welcome-section > div:last-child > div');
                if (cards.length > 0) cards[0].click();
            }
        """)
        await asyncio.sleep(6)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "buyer_welcome_response", pause=1.0)

        # ---- HELP COMMAND ----
        print("3. Help command")
        await send_chat(page, "help", wait=3)
        await capture(page, "help_response", pause=0.5)

        # Scroll to see full help
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "help_scrolled", pause=0.5)

        # ---- COMPANY PROFILE ----
        print("4. Company profile: SAP.DE")
        await send_chat(page, "profile:SAP.DE", wait=10)
        await capture(page, "profile_sap", pause=1.0)

        # Scroll to see profile card
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "profile_sap_card", pause=1.0)

        # ---- CONTEXTUAL CHIPS ----
        print("5. Contextual chips after profile")
        # Scroll to top to show chips
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = 0; }")
        await capture(page, "contextual_chips_profile", pause=0.5)

        # ---- OPEN CANVAS - DOCUMENTS TAB ----
        print("6. Canvas panel - Documents")
        await open_canvas(page)
        await capture(page, "canvas_documents", pause=1.0)

        # ---- VIEW PITCH DECK IN CANVAS ----
        print("7. View NovaTech pitch deck")
        await page.evaluate("""
            () => {
                htmx.ajax('GET', '/doc/panel?fn=NovaTech-Pitch-Deck.pdf', {target: '#canvas-content', swap: 'innerHTML'});
            }
        """)
        await asyncio.sleep(2)
        await capture(page, "canvas_pitch_deck", pause=1.5)

        # ---- VIEW TERM SHEET ----
        print("8. View NovaTech term sheet")
        await page.evaluate("""
            () => {
                htmx.ajax('GET', '/doc/panel?fn=NovaTech-TermSheet-Draft.pdf', {target: '#canvas-content', swap: 'innerHTML'});
            }
        """)
        await asyncio.sleep(2)
        await capture(page, "canvas_term_sheet", pause=1.5)

        # ---- SWITCH TO RESEARCH TAB ----
        print("9. Canvas - Research tab")
        await switch_canvas_tab(page, "/canvas/research")
        await capture(page, "canvas_research_empty", pause=0.8)

        # ---- SWITCH TO SCORES TAB ----
        print("10. Canvas - Scores tab")
        await switch_canvas_tab(page, "/canvas/scores")
        await capture(page, "canvas_scores_empty", pause=0.8)

        # ---- CLOSE CANVAS ----
        await close_canvas(page)

        # ---- SELLER FLOW ----
        print("11. Clear and show seller flow")
        await send_chat(page, "clear", wait=1)

        # Navigate back to fresh state (reload)
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)

        # Click SELLER card
        await page.evaluate("""
            () => {
                var cards = document.querySelectorAll('#welcome-section > div:last-child > div');
                if (cards.length > 1) cards[1].click();
            }
        """)
        await asyncio.sleep(6)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "seller_welcome_response", pause=1.0)

        # ---- DOCS COMMAND ----
        print("12. Documents listing")
        await send_chat(page, "docs", wait=3)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "docs_listing", pause=1.0)

        # ---- NAV SECTIONS ----
        print("13. Navigation sections")
        # Expand RESEARCH section
        await expand_nav_section(page, "RESEARCH")
        await capture(page, "nav_research_expanded", pause=0.5)

        # Expand WORKSPACE section
        await expand_nav_section(page, "WORKSPACE")
        await capture(page, "nav_workspace_expanded", pause=0.5)

        # ---- MARKET INTEL ----
        print("14. Market Intel")
        await send_chat(page, "market", wait=3)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "market_intel", pause=1.5)

        # ---- M&A TOOLS ----
        print("15. M&A Tools")
        await send_chat(page, "tools", wait=2)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "ma_tools", pause=1.0)

        # ---- SETTINGS ----
        print("16. Settings")
        await send_chat(page, "settings", wait=2)
        await page.evaluate("() => { var c = document.getElementById('chat-area'); if (c) c.scrollTop = c.scrollHeight; }")
        await capture(page, "settings", pause=1.0)

        # ---- FINAL: WELCOME SCREEN ----
        print("17. Final welcome")
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        await capture(page, "final_welcome", pause=1.5)

        await browser.close()

    print(f"\nCapture complete: {frame_num} frames in {FRAMES_DIR}")


def build_video():
    """Assemble frames into MP4 and GIF."""
    from PIL import Image
    import av
    import numpy as np

    frames = sorted(FRAMES_DIR.glob("*.png"))
    if not frames:
        print("No frames found!")
        return

    print(f"\nBuilding video from {len(frames)} frames...")
    images = [np.array(Image.open(f)) for f in frames]

    # -- MP4 --
    mp4_path = DOCS_DIR / "demo_video.mp4"
    fps = 2
    hold_frames = 3  # Each screenshot held for 1.5 seconds at 2 FPS

    container = av.open(str(mp4_path), mode="w")
    h, w = images[0].shape[:2]
    w_enc = w if w % 2 == 0 else w - 1
    h_enc = h if h % 2 == 0 else h - 1

    stream = container.add_stream("libx264", rate=fps)
    stream.width = w_enc
    stream.height = h_enc
    stream.pix_fmt = "yuv420p"

    for img in images:
        img_cropped = img[:h_enc, :w_enc, :3]
        frame = av.VideoFrame.from_ndarray(img_cropped, format="rgb24")
        for _ in range(hold_frames):
            for packet in stream.encode(frame):
                container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)
    container.close()
    print(f"  MP4: {mp4_path} ({mp4_path.stat().st_size // 1024} KB)")

    # -- GIF --
    gif_path = DOCS_DIR / "demo_video.gif"
    pil_frames = []
    for img in images:
        pil_img = Image.fromarray(img[:, :, :3])
        pil_img = pil_img.resize((w // 2, h // 2), Image.LANCZOS)
        pil_frames.append(pil_img)

    pil_frames[0].save(
        str(gif_path),
        save_all=True,
        append_images=pil_frames[1:],
        duration=1500,
        loop=0,
        optimize=True,
    )
    print(f"  GIF: {gif_path} ({gif_path.stat().st_size // 1024} KB)")


def main():
    start_app = "--start-app" in sys.argv

    if start_app:
        print("Starting app...")
        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        time.sleep(5)
        try:
            asyncio.run(run())
            build_video()
        finally:
            proc.terminate()
            proc.wait()
            print("App stopped.")
    else:
        asyncio.run(run())
        build_video()


if __name__ == "__main__":
    main()
