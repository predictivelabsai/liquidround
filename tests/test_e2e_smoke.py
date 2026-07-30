"""Local/CI Playwright smoke tests for the current 32-agent product shell."""
from __future__ import annotations

import os

import pytest

BASE_URL = os.environ.get("LIQUIDROUND_URL", "http://localhost:5007")

try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    _PLAYWRIGHT_OK = True
except ImportError:
    _PLAYWRIGHT_OK = False

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _PLAYWRIGHT_OK,
        reason="playwright not installed — pip install playwright && playwright install chromium",
    ),
]


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True)
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    instance = context.new_page()
    console_errors: list[str] = []
    server_failures: list[str] = []
    instance.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )
    instance.on(
        "response",
        lambda response: server_failures.append(f"{response.status} {response.url}")
        if response.status >= 500 else None,
    )
    yield instance
    assert console_errors == []
    assert server_failures == []
    context.close()


def test_landing_has_hero_and_two_ctas(page):
    page.goto(BASE_URL + "/")
    page.wait_for_selector("text=analyst squad", timeout=10_000)
    assert page.get_by_text("Equity Capital Markets").count() >= 1
    assert page.get_by_text("BYOD").count() >= 1
    assert page.get_by_text("Buyer-Led").count() >= 1
    assert page.get_by_text("Seller-Led").count() >= 1


def test_agents_page_shows_32_cards(page):
    page.goto(BASE_URL + "/agents")
    page.wait_for_selector(".agent-card", timeout=10_000)
    assert page.locator(".agent-card").count() == 32


def test_app_buyer_role_renders_current_shell(page):
    page.goto(BASE_URL + "/app?role=buyer")
    page.wait_for_selector("#chat-input", timeout=10_000)
    assert page.locator(".left-pane").count() == 1
    assert page.locator("#right-pane.open").count() == 1
    assert page.locator(".cfg-role-chip.role-buyer.active").count() == 1
    assert page.locator(".agent-item").count() == 32
    assert page.locator(".cat-toggle").count() >= 7


def test_seller_role_and_configuration(page):
    page.goto(BASE_URL + "/app?role=seller")
    page.wait_for_selector("#chat-input", timeout=10_000)
    page.locator("#btn-sec-configuration").click()
    assert page.locator(".cfg-chip").count() == 3
    assert page.locator(".cfg-role-chip").count() == 3
    assert page.locator(".cfg-role-chip.role-seller.active").count() == 1


def test_sample_cards_and_hermes_launcher(page):
    page.goto(BASE_URL + "/app")
    page.wait_for_selector(".sample-cards")
    assert page.locator(".sample-card").count() == 4
    assert page.get_by_text("Hermes Orchestrator", exact=True).count() >= 1


def test_mobile_context_pane_opens_and_closes(browser):
    from playwright.sync_api import expect
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(BASE_URL + "/app")
    page.wait_for_selector("#chat-input")
    assert page.locator("#right-pane.open").count() == 0
    assert page.locator("#mobile-news-launcher").is_visible()
    page.locator("#mobile-news-launcher").click()
    assert page.locator("#right-pane.open").count() == 1
    expect(page.locator("#right-pane")).to_have_css("right", "0px")
    right = page.locator("#right-pane").bounding_box()
    assert right and right["x"] < 390
    page.locator("#right-pane .right-close").click()
    assert page.locator("#right-pane.open").count() == 0
    assert page.locator("#mobile-news-launcher").is_visible()
    context.close()


def test_reverse_mergers_is_paginated_with_evidence_metadata(page):
    page.goto(BASE_URL + "/app/reverse-mergers")
    page.wait_for_selector(".rto-page")
    assert page.locator(".rto-table tbody tr").count() <= 50
    if page.locator(".rto-table tbody tr").count():
        assert page.locator(".rto-confidence").count() >= 1


def test_investor_relations_hub_and_progressive_form(page):
    page.goto(BASE_URL + "/app/investor-relations")
    page.wait_for_url("**/app/investor-relations/press-release")
    page.wait_for_selector(".ir-form")
    assert page.locator(".ir-advanced-summary").count() == 1
    assert page.locator("textarea[name=key_facts]").count() == 1


def test_memo_pdf_render_opens_external_viewer(page):
    page.goto(BASE_URL + "/app")
    page.wait_for_selector("#chat-input")
    result = page.evaluate(
        """async () => {
            window.__openedPdf = "";
            window.open = (url) => { window.__openedPdf = url; return null; };
            const data = await window.renderMemoPdf(
                "# Test Memo\\n\\n## Deal size\\n\\nEUR 120M EV.",
                "Test IC memo"
            );
            return {...data, opened: window.__openedPdf};
        }"""
    )
    assert result["file_id"]
    assert "mozilla.github.io/pdf.js" in result["opened"]
    assert result["file_id"] in result["opened"]
    assert page.request.get(BASE_URL + result["file_url"]).status == 200


def test_health_routes(page):
    live = page.request.get(BASE_URL + "/health/live")
    ready = page.request.get(BASE_URL + "/health/ready")
    assert live.status == 200
    assert ready.status == 200
    assert ready.json()["status"] == "ok"
