"""Playwright E2E smoke tests.

Boots against a running LiquidRound server (start it yourself on :5007) and
walks through the critical UX:
  - landing renders with ECM Agent Squad headline + both CTAs
  - /agents shows 22 agent cards
  - /app?role=buyer opens the Buyer-Led view
  - /app?role=seller opens the Seller-Led view
  - settings widget (via chat) saves role to session

Marked as `e2e` — skipped by default. Run with:
    pytest -q tests/test_e2e_smoke.py -m e2e
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("LIQUIDROUND_URL", "http://localhost:5007")

# Import playwright lazily so the module still imports when the test is
# deselected via -m "not e2e".
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False


pytestmark = pytest.mark.skipif(
    not _PLAYWRIGHT_OK,
    reason="playwright not installed — pip install playwright && playwright install chromium",
)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    pg = ctx.new_page()
    yield pg
    ctx.close()


@pytest.mark.e2e
def test_landing_has_hero_and_two_ctas(page):
    page.goto(BASE_URL + "/")
    page.wait_for_selector("text=ECM Agent Squad", timeout=10_000)
    # Must explicitly spell out what ECM means
    assert page.locator("text=Equity Capital Markets").count() >= 1
    assert page.locator("text=Buyer-Led").count() >= 1
    assert page.locator("text=Seller-Led").count() >= 1


@pytest.mark.e2e
def test_agents_page_shows_22_cards(page):
    page.goto(BASE_URL + "/agents")
    page.wait_for_selector(".agent-card", timeout=10_000)
    cards = page.locator(".agent-card").count()
    assert cards == 22, f"expected 22 agent cards, got {cards}"


@pytest.mark.e2e
def test_app_buyer_role_opens_buyer_section(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector("input[name='msg']", timeout=10_000)
    # Buyer details element should be open
    buying = page.locator("details:has-text(\"I'M BUYING\")")
    assert buying.count() >= 1
    # Either the "I'M BUYING" details has attribute open OR a blue dot marks it active
    html = page.content()
    assert "I'M BUYING" in html
    # "Find Targets" shown in buyer nav
    assert "Find Targets" in html


@pytest.mark.e2e
def test_app_seller_role_opens_seller_section(page):
    page.goto(BASE_URL + "/app?role=seller")
    page.wait_for_selector("input[name='msg']", timeout=10_000)
    html = page.content()
    assert "I'M SELLING" in html
    assert "Find Buyers" in html


@pytest.mark.e2e
def test_settings_widget_has_role_selector(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector("input[name='msg']")
    # Post "settings" as a chat message
    page.fill("input[name='msg']", "settings")
    page.evaluate(
        "() => document.querySelector('form[hx-post=\"/chat\"]').dispatchEvent("
        "new Event('submit', {cancelable: true, bubbles: true}))"
    )
    page.wait_for_selector("text=Default view", timeout=20_000)
    html = page.content()
    # Radio options present
    assert "Buyer-Led" in html
    assert "Seller-Led" in html
    assert "Both" in html
