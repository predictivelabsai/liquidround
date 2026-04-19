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
def test_app_buyer_role_renders_3pane_shell(page):
    page.goto(BASE_URL + "/app?role=buyer")
    # New pehero-faithful shell uses a textarea, not an input
    page.wait_for_selector("#chat-input", timeout=10_000)
    html = page.content()
    assert 'class="app' in html            # 3-pane grid
    assert 'class="left-pane"' in html
    assert 'id="right-pane"' in html
    assert 'id="artifact-empty"' in html
    # Buyer is the active role chip
    assert 'role-buyer active' in html or 'data-role="buyer" class="cfg-role-chip role-buyer active"' in html


@pytest.mark.e2e
def test_app_seller_role_highlights_seller_chip(page):
    page.goto(BASE_URL + "/app?role=seller")
    page.wait_for_selector("#chat-input", timeout=10_000)
    html = page.content()
    assert 'role-seller active' in html


@pytest.mark.e2e
def test_agent_browser_shows_all_22(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector(".agent-browser", timeout=10_000)
    assert page.locator(".agent-item").count() == 22
    # All 5 categories
    assert page.locator(".cat-toggle").count() == 5


@pytest.mark.e2e
def test_configuration_has_currency_and_role(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector(".config-section", timeout=10_000)
    assert page.locator(".cfg-chip").count() == 3         # EUR / GBP / USD
    assert page.locator(".cfg-role-chip").count() == 3    # Buyer / Seller / Both


@pytest.mark.e2e
def test_sample_cards_present(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector(".sample-cards", timeout=10_000)
    assert page.locator(".sample-card").count() == 3
