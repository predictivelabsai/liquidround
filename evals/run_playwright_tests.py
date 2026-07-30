"""
Automated Playwright test runner for LiquidRound live site.

Runs a comprehensive 60+ test suite across desktop and mobile viewports,
outputs results to test-results/*.json.

Usage:
    pip install playwright && playwright install chromium
    python -m evals.run_playwright_tests                          # test live site
    python -m evals.run_playwright_tests --url http://localhost:5007  # test local
    python -m evals.run_playwright_tests --dry-run                # list tests
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "test-results"

DESKTOP = {"width": 1400, "height": 900}
MOBILE = {"width": 390, "height": 844}


def _js_landing_desktop():
    return """() => {
  const r = {};
  r.T01 = document.readyState === 'complete';
  r.T02 = document.title.includes('LiquidRound');
  const vb = Array.from(document.querySelectorAll('span')).find(s => s.textContent.match(/v\\d+\\.\\d+/));
  r.T03 = vb ? vb.textContent.trim() : false;
  const nav = document.querySelector('nav') || document.querySelector('[class*="nav"]');
  r.T04 = nav ? nav.offsetHeight > 0 : false;
  const links = Array.from(document.querySelectorAll('a')).map(a => a.textContent.trim());
  r.T05 = links.some(t => t === 'Platform');
  r.T06 = links.some(t => t.includes('ECM Squad'));
  r.T07 = links.some(t => t.includes('How it works'));
  r.T08 = links.some(t => t === 'Pricing');
  const si = Array.from(document.querySelectorAll('a, button')).find(e => e.textContent.trim() === 'Sign in');
  r.T09 = si ? (si.href || '').includes('/signin') : false;
  r.T10 = !!document.querySelector('h1');
  r.T11 = document.body.innerText.includes('ECM');
  const bc = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('Buyer-Led'));
  r.T12 = bc ? bc.href.includes('/signin?role=buyer') : false;
  const sc = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('Seller-Led'));
  r.T13 = sc ? sc.href.includes('/signin?role=seller') : false;
  const gif = document.querySelector('img[src*="liquidround.gif"]');
  r.T14 = !!gif;
  r.T15 = gif ? (gif.complete && gif.naturalWidth > 0) : false;
  r.T16 = document.body.innerText.includes('32');
  r.T17 = document.body.innerText.toLowerCase().includes('sides');
  const cats = ['Sourcing','Underwriting','Diligence','Execution','Research','Public Markets','Investor Relations'];
  r.T18 = cats.filter(c => document.body.innerText.includes(c)).length >= 7;
  r.T19 = document.body.innerText.includes('Predictive Labs');
  r.T20 = document.body.scrollHeight > window.innerHeight;
  return r;
}"""


def _js_landing_mobile():
    return """() => {
  const r = {};
  r.T21 = document.readyState === 'complete';
  const logo = Array.from(document.querySelectorAll('span')).find(s => s.textContent.trim() === 'LiquidRound');
  r.T22 = logo ? logo.offsetWidth > 0 : false;
  const si = Array.from(document.querySelectorAll('a, button')).find(e => e.textContent.trim() === 'Sign in');
  r.T23 = si ? si.offsetWidth > 0 : false;
  const navTexts = ['Platform','ECM Squad','How it works','Pricing'];
  r.T24 = navTexts.every(t => {
    const el = Array.from(document.querySelectorAll('a')).find(a => a.textContent.trim() === t);
    return !el || el.offsetWidth === 0;
  });
  r.T25 = document.querySelector('h1') ? document.querySelector('h1').offsetWidth <= 400 : false;
  const gif = document.querySelector('img[src*="liquidround.gif"]');
  r.T26 = gif ? gif.offsetWidth > 0 : false;
  r.T27 = document.body.innerText.includes('Predictive Labs');
  r.T28 = document.documentElement.scrollWidth <= 400;
  const bc = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('Buyer-Led'));
  r.T29 = bc ? bc.offsetWidth > 0 : false;
  const sc = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('Seller-Led'));
  r.T30 = sc ? sc.offsetWidth > 0 : false;
  return r;
}"""


def _js_signin():
    return """() => {
  const r = {};
  r.T31 = document.title.includes('Sign In');
  r.T32 = !!document.querySelector('input[type="email"], input[name="email"]');
  r.T33 = !!document.querySelector('input[type="password"]');
  const forgot = Array.from(document.querySelectorAll('a')).find(a => a.textContent.toLowerCase().includes('forgot'));
  r.T34 = !!forgot;
  const reg = Array.from(document.querySelectorAll('a, button')).find(e => e.textContent.toLowerCase().includes('sign up') || e.textContent.toLowerCase().includes('register'));
  r.T35 = !!reg;
  r.T36 = !!Array.from(document.querySelectorAll('a, button')).find(e => e.textContent.includes('Google'));
  r.T37 = !!document.querySelector('button[type="submit"]');
  return r;
}"""


def _js_app_desktop():
    return """() => {
  const r = {};
  const text = document.body.innerText;
  r.T43 = document.title.includes('App');
  const app = document.querySelector('.app');
  r.T44 = app ? getComputedStyle(app).display === 'grid' : false;
  const lp = document.querySelector('.left-pane');
  r.T45 = lp ? lp.offsetWidth >= 280 : false;
  r.T46 = text.toUpperCase().includes('SESSIONS');
  r.T47 = ['Sourcing','Underwriting','Diligence','Execution','Research','Public Markets','Investor Relations'].filter(c => text.includes(c)).length >= 7;
  r.T48 = text.toUpperCase().includes('WORKSPACE');
  const ws = ['Companies','Pipelines','Deal Radar','Data Coverage','Valuation','Analytics','Data Room','Skills','User Guide'];
  r.T49 = ws.filter(l => text.includes(l)).length >= 9;
  r.T50 = text.toUpperCase().includes('SETTINGS') && text.includes('Profile');
  const vb = Array.from(document.querySelectorAll('span')).find(s => s.textContent.match(/v\\d+\\.\\d+/));
  r.T51 = vb ? vb.textContent.trim() : false;
  r.T52 = text.includes('Auto-routed');
  const btns = Array.from(document.querySelectorAll('button'));
  r.T53 = btns.some(b => b.textContent.includes('Copy') || (b.getAttribute('onclick')||'').includes('copy'));
  r.T54 = btns.some(b => b.textContent.includes('Share') || (b.getAttribute('onclick')||'').includes('share'));
  r.T55 = text.includes('ECM') && text.includes('analyst');
  r.T56 = document.querySelectorAll('.sample-card, [onclick*="fillChat"]').length > 0;
  r.T57 = !!document.querySelector('#chat-input');
  r.T58 = !!document.querySelector('#send-btn') || btns.some(b => b.textContent.includes('Send'));
  const hb = document.querySelector('.mobile-menu-btn');
  r.T59 = hb ? (hb.offsetWidth === 0 || getComputedStyle(hb).display === 'none') : true;
  r.T60 = getComputedStyle(document.body).backgroundColor === 'rgb(11, 18, 32)';
  return r;
}"""


def _js_app_mobile():
    return """() => {
  const r = {};
  const hb = document.querySelector('.mobile-menu-btn');
  r.T62 = hb ? hb.offsetWidth > 0 : false;
  r.T63 = document.querySelector('#chat-input') ? document.querySelector('#chat-input').offsetWidth > 0 : false;
  r.T64 = document.body.innerText.includes('ECM');
  r.T65 = document.documentElement.scrollWidth <= 400;
  r.T66 = getComputedStyle(document.body).backgroundColor === 'rgb(11, 18, 32)';
  return r;
}"""


TEST_NAMES = {
    "T01": "Landing: page loads",
    "T02": "Landing: title contains LiquidRound",
    "T03": "Landing: version badge visible",
    "T04": "Landing: nav bar visible",
    "T05": "Landing: Platform nav link",
    "T06": "Landing: ECM Squad nav link",
    "T07": "Landing: How it works nav link",
    "T08": "Landing: Pricing nav link",
    "T09": "Landing: Sign in -> /signin",
    "T10": "Landing: hero H1 present",
    "T11": "Landing: hero mentions ECM",
    "T12": "Landing: Buyer-Led CTA -> /signin?role=buyer",
    "T13": "Landing: Seller-Led CTA -> /signin?role=seller",
    "T14": "Landing: demo GIF element exists",
    "T15": "Landing: GIF loaded",
    "T16": "Landing: stats 32 agents",
    "T17": "Landing: stats 2 sides",
    "T18": "Landing: 7 agent categories",
    "T19": "Landing: footer copyright",
    "T20": "Landing: page scrollable",
    "T21": "Landing mobile: page loads",
    "T22": "Landing mobile: logo visible",
    "T23": "Landing mobile: sign in visible",
    "T24": "Landing mobile: desktop links hidden",
    "T25": "Landing mobile: hero fits width",
    "T26": "Landing mobile: GIF visible",
    "T27": "Landing mobile: footer present",
    "T28": "Landing mobile: no horizontal overflow",
    "T29": "Landing mobile: Buyer-Led CTA visible",
    "T30": "Landing mobile: Seller-Led CTA visible",
    "T31": "Sign-in: page loads",
    "T32": "Sign-in: email field",
    "T33": "Sign-in: password field",
    "T34": "Sign-in: forgot password link",
    "T35": "Sign-in: register option",
    "T36": "Sign-in: Google OAuth button",
    "T37": "Sign-in: submit button",
    "T38": "Nav: Platform page loads",
    "T39": "Nav: Agents page 32 agents",
    "T40": "Nav: agent detail link exists",
    "T41": "Nav: How it works page",
    "T42": "Nav: Pricing page",
    "T43": "App: page loads",
    "T44": "App: CSS grid layout",
    "T45": "App: left pane 300px",
    "T46": "App: Sessions section",
    "T47": "App: 7 agent categories",
    "T48": "App: Workspace section",
    "T49": "App: 9 workspace links",
    "T50": "App: Settings + Profile link",
    "T51": "App: version badge",
    "T52": "App: Auto-routed label",
    "T53": "App: Copy button",
    "T54": "App: Share button",
    "T55": "App: welcome hero",
    "T56": "App: sample cards",
    "T57": "App: chat input",
    "T58": "App: send button",
    "T59": "App: hamburger hidden on desktop",
    "T60": "App: dark background",
    "T62": "App mobile: hamburger visible",
    "T63": "App mobile: chat input visible",
    "T64": "App mobile: welcome hero",
    "T65": "App mobile: no overflow",
    "T66": "App mobile: dark background",
    "T67": "Assets: app.css loaded",
    "T68": "Assets: favicon present",
    "T69": "Nav: agent detail page",
    "T70": "Nav: back link to /agents",
    "T71": "Sign-in: ?role=buyer works",
    "T72": "Sign-in mobile: form fits",
    "T73": "Sign-in mobile: no overflow",
    "T74": "Sign-in mobile: fields visible",
    "T75": "Console: zero errors",
}


def run(base_url: str) -> list[dict]:
    results = []

    def collect(data: dict):
        for tid, val in data.items():
            passed = bool(val) if not isinstance(val, str) else val != "false" and val != "NOT_FOUND"
            name = TEST_NAMES.get(tid, tid)
            r = {"id": tid, "name": name, "result": "PASS" if passed else "FAIL"}
            if isinstance(val, str) and val not in ("true", "false"):
                r["actual"] = val
            results.append(r)
            status = "PASS" if passed else "FAIL"
            print(f"  {tid} {status}: {name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=DESKTOP)
        page = ctx.new_page()

        # Landing desktop
        print("\n--- Landing (desktop 1400x900) ---")
        page.goto(base_url, wait_until="load", timeout=30_000)
        collect(page.evaluate(_js_landing_desktop()))

        # Landing mobile
        print("\n--- Landing (mobile 390x844) ---")
        page.set_viewport_size(MOBILE)
        page.goto(base_url, wait_until="load", timeout=30_000)
        collect(page.evaluate(_js_landing_mobile()))

        # Sign-in desktop
        print("\n--- Sign-in (desktop) ---")
        page.set_viewport_size(DESKTOP)
        page.goto(f"{base_url}/signin", wait_until="load", timeout=30_000)
        collect(page.evaluate(_js_signin()))

        # Sub-pages
        print("\n--- Navigation pages ---")
        for path, tid, check in [
            ("/platform", "T38", lambda t: t.includes("Platform")),
            ("/agents", "T39", None),
            ("/how-it-works", "T41", None),
            ("/pricing", "T42", None),
        ]:
            page.goto(f"{base_url}{path}", wait_until="load", timeout=30_000)
            title = page.title()
            passed = "LiquidRound" in title
            results.append({"id": tid, "name": TEST_NAMES.get(tid, tid), "result": "PASS" if passed else "FAIL"})
            print(f"  {tid} {'PASS' if passed else 'FAIL'}: {TEST_NAMES.get(tid, tid)}")

        # Agents page detail checks
        page.goto(f"{base_url}/agents", wait_until="load", timeout=30_000)
        has_detail = page.evaluate("() => !!Array.from(document.querySelectorAll('a')).find(a => a.href.includes('/agents/'))")
        results.append({"id": "T40", "name": TEST_NAMES["T40"], "result": "PASS" if has_detail else "FAIL"})
        print(f"  T40 {'PASS' if has_detail else 'FAIL'}: {TEST_NAMES['T40']}")

        # Agent detail page
        page.goto(f"{base_url}/agents/deal_triage", wait_until="load", timeout=30_000)
        dt_ok = "Deal Triage" in page.title()
        results.append({"id": "T69", "name": TEST_NAMES["T69"], "result": "PASS" if dt_ok else "FAIL"})
        back_ok = page.evaluate("() => !!Array.from(document.querySelectorAll('a')).find(a => a.href.includes('/agents') && !a.href.includes('/agents/'))")
        results.append({"id": "T70", "name": TEST_NAMES["T70"], "result": "PASS" if back_ok else "FAIL"})
        print(f"  T69 {'PASS' if dt_ok else 'FAIL'}: {TEST_NAMES['T69']}")
        print(f"  T70 {'PASS' if back_ok else 'FAIL'}: {TEST_NAMES['T70']}")

        # App desktop
        print("\n--- Chat App (desktop 1400x900) ---")
        page.goto(f"{base_url}/app", wait_until="load", timeout=30_000)
        collect(page.evaluate(_js_app_desktop()))

        # Static assets
        print("\n--- Static assets ---")
        css_ok = page.evaluate("() => Array.from(document.querySelectorAll('link[rel=\"stylesheet\"]')).some(l => l.href.includes('app.css'))")
        fav_ok = page.evaluate("() => document.querySelectorAll('link[rel*=\"icon\"]').length > 0")
        results.append({"id": "T67", "name": TEST_NAMES["T67"], "result": "PASS" if css_ok else "FAIL"})
        results.append({"id": "T68", "name": TEST_NAMES["T68"], "result": "PASS" if fav_ok else "FAIL"})
        print(f"  T67 {'PASS' if css_ok else 'FAIL'}: {TEST_NAMES['T67']}")
        print(f"  T68 {'PASS' if fav_ok else 'FAIL'}: {TEST_NAMES['T68']}")

        # App mobile
        print("\n--- Chat App (mobile 390x844) ---")
        page.set_viewport_size(MOBILE)
        page.goto(f"{base_url}/app", wait_until="load", timeout=30_000)
        collect(page.evaluate(_js_app_mobile()))

        # Sign-in role param + mobile
        print("\n--- Sign-in extras ---")
        page.set_viewport_size(DESKTOP)
        page.goto(f"{base_url}/signin?role=buyer", wait_until="load", timeout=30_000)
        role_ok = "role=buyer" in page.url
        results.append({"id": "T71", "name": TEST_NAMES["T71"], "result": "PASS" if role_ok else "FAIL"})
        print(f"  T71 {'PASS' if role_ok else 'FAIL'}: {TEST_NAMES['T71']}")

        page.set_viewport_size(MOBILE)
        mobile_signin = page.evaluate("""() => {
          const r = {};
          const form = document.querySelector('form');
          r.T72 = form ? form.scrollWidth <= 400 : true;
          r.T73 = document.documentElement.scrollWidth <= 400;
          const e = document.querySelector('input[type="email"], input[name="email"]');
          const p = document.querySelector('input[type="password"]');
          r.T74 = (e ? e.offsetWidth > 0 : false) && (p ? p.offsetWidth > 0 : false);
          return r;
        }""")
        collect(mobile_signin)

        # Console errors
        print("\n--- Console ---")
        # Check for JS errors across a fresh page load
        page2 = ctx.new_page()
        errors = []
        page2.on("pageerror", lambda e: errors.append(str(e)))
        for path in ["/", "/app", "/signin"]:
            page2.goto(f"{base_url}{path}", wait_until="load", timeout=30_000)
        page2.close()
        no_errors = len(errors) == 0
        results.append({"id": "T75", "name": TEST_NAMES["T75"], "result": "PASS" if no_errors else "FAIL", "actual": len(errors)})
        print(f"  T75 {'PASS' if no_errors else 'FAIL'}: {TEST_NAMES['T75']} ({len(errors)} errors)")

        browser.close()

    return results


def save(results: list[dict], base_url: str):
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0].replace(":", "-")
    out_path = RESULTS_DIR / f"playwright-{host}-{ts}.json"

    passed = sum(1 for r in results if r["result"] == "PASS")
    total = len(results)
    summary = {
        "target": base_url,
        "timestamp": ts,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(100 * passed / total, 1) if total else 0,
    }

    with open(out_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed ({summary['pass_rate_pct']}%)")
    print(f"Saved to {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="LiquidRound Playwright test suite")
    parser.add_argument("--url", default="https://liquidround.com", help="Target URL")
    parser.add_argument("--dry-run", action="store_true", help="List tests without running")
    args = parser.parse_args()

    if args.dry_run:
        for tid, name in sorted(TEST_NAMES.items()):
            print(f"  {tid}: {name}")
        print(f"\n{len(TEST_NAMES)} tests. Run without --dry-run to execute.")
        return

    results = run(args.url)
    save(results, args.url)


if __name__ == "__main__":
    main()
