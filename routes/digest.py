"""Daily Deal Digest routes — preview + send.

/app/digest          → generate + preview the daily digest
/app/digest/send     → send the digest via Postmark email
"""

from __future__ import annotations

from fasthtml.common import (
    Html, Head, Body, Meta, Title, Link, Script, NotStr,
    Div, Span, H1, P, A, Button,
)
from fasthtml.core import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

ar = APIRouter()


@ar("/app/digest", methods=["GET"])
async def digest_preview():
    """Generate and preview the daily digest (takes ~30-60s for LLM calls)."""
    from utils.digest import build_digest, render_email_html

    digest = build_digest(n_companies=10)
    html = render_email_html(digest)

    n = len(digest.get("companies", []))
    featured = digest.get("featured", {})
    featured_name = featured.get("name", "N/A") if featured else "N/A"

    return Html(
        Head(
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Title("Daily Digest Preview · LiquidRound"),
            Link(rel="icon", type="image/svg+xml", href="/favicon.svg"),
            Link(rel="preconnect", href="https://fonts.googleapis.com"),
            Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
            Link(rel="stylesheet",
                 href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"),
            Script(src="https://cdn.tailwindcss.com"),
            Link(rel="stylesheet", href="/app.css"),
        ),
        Body(
            Div(
                Div(
                    Span("Daily Digest Preview", cls="text-lg font-bold text-gray-200"),
                    Span("·", cls="text-gray-500 mx-2"),
                    Span(f"{n} companies · Deep Dive: {featured_name}",
                         cls="text-sm text-gray-400"),
                    cls="flex items-center gap-1",
                ),
                Div(
                    Button("Send Email",
                           onclick="sendDigest()",
                           cls="text-xs bg-amber-600 hover:bg-amber-500 text-white px-4 py-2 rounded transition-colors"),
                    A("Back to chat", href="/app",
                      cls="text-xs text-gray-400 hover:text-amber-400 border border-gray-600 px-3 py-1.5 rounded transition-colors"),
                    Span(id="send-status", cls="text-xs text-gray-400 ml-2"),
                    cls="flex items-center gap-2",
                ),
                cls="flex items-center justify-between px-5 py-3 border-b border-gray-700",
            ),
            Div(
                NotStr(html),
                cls="overflow-y-auto",
                style="max-height: calc(100vh - 56px);",
            ),
            Script(NotStr("""
async function sendDigest() {
    var status = document.getElementById('send-status');
    status.textContent = 'Sending…';
    status.style.color = '#94a3b8';
    try {
        var resp = await fetch('/app/digest/send', {method: 'POST'});
        var data = await resp.json();
        if (data.ok) {
            status.textContent = 'Sent! (' + (data.message_id || '') + ')';
            status.style.color = '#F59E0B';
        } else {
            status.textContent = 'Error: ' + (data.error || 'unknown');
            status.style.color = '#EF4444';
        }
    } catch(err) {
        status.textContent = 'Send failed';
        status.style.color = '#EF4444';
    }
}
""")),
            style="background: var(--bg); color: var(--ink); font-family: 'Inter', sans-serif; height: 100vh; overflow: hidden;",
        ),
        lang="en",
    )


@ar("/app/digest/send", methods=["POST"])
async def digest_send():
    """Regenerate + send the digest via email."""
    from utils.digest import build_digest, render_email_html, send_digest_email

    digest = build_digest(n_companies=10)
    html = render_email_html(digest)
    result = send_digest_email(html)
    return JSONResponse(result)
