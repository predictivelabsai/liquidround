"""Signed-in user configuration for the contextual RSS news pane."""
from __future__ import annotations

from urllib.parse import quote_plus

from fasthtml.common import (
    APIRouter, A, Button, Div, Form, H1, Input, Label, P, Script, Span, Title,
)
from starlette.responses import RedirectResponse

from utils.news import clear_news_cache
from utils.news_feeds import (
    NewsFeedError, add_custom_feed, delete_custom_feed, list_user_feeds,
    set_feed_enabled,
)

ar = APIRouter()


def _user_id(session) -> str | None:
    return (session.get("user") or {}).get("user_id")


def _shell(session, content):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user") or {}
    sessions = []
    if user.get("user_id"):
        try:
            from utils.database import db_service
            conversations = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions = [
                {"id": item["id"], "title": item.get("conversation_title") or item.get("user_query", "Untitled")}
                for item in conversations
            ]
        except Exception:
            pass
    return (
        Title("News feeds · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=user.get("email"), sessions=sessions, current_sid="",
                current_path="/app/news-feeds",
                current_currency=session.get("currency", "EUR"),
                current_role=session.get("role", "buyer"),
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        H1("News feeds", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span("Configuration", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    cls="chat-header",
                ),
                Div(content, cls="news-feeds-page"),
                cls="center-pane pipeline-center",
            ),
            right_pane(),
            cls="app",
        ),
        Script(src="/chat.js?v=4"),
    )


@ar("/app/news-feeds")
def news_feeds_page(session, added: str = "", error: str = ""):
    user_id = _user_id(session)
    try:
        feeds = list_user_feeds(user_id)
    except Exception:
        feeds = []
        error = error or "Feed settings could not be loaded."
    active_count = sum(1 for feed in feeds if feed["enabled"])
    cards = []
    for feed in feeds:
        toggle_label = "Disable" if feed["enabled"] else "Enable"
        controls = Form(
            Input(type="hidden", name="feed_key", value=feed["key"]),
            Input(type="hidden", name="enabled", value="false" if feed["enabled"] else "true"),
            Button(
                Span(cls="news-feed-switch-knob"),
                Span(toggle_label, cls="sr-only"),
                type="submit",
                cls=f"news-feed-switch{' active' if feed['enabled'] else ''}",
                title=f"{toggle_label} {feed['name']}",
                aria_label=f"{toggle_label} {feed['name']}",
            ),
            action="/app/news-feeds/toggle", method="post", cls="news-feed-toggle-form",
        ) if user_id else Span("Sign in to manage", cls="news-feed-signin")
        delete = (
            Form(
                Input(type="hidden", name="feed_key", value=feed["key"]),
                Button("Remove", type="submit", cls="news-feed-remove",
                       aria_label=f"Remove {feed['name']}"),
                action="/app/news-feeds/delete", method="post",
            ) if user_id and not feed["is_builtin"] else ""
        )
        cards.append(Div(
            Div(Span(feed["icon"], cls="news-feed-icon"), cls="news-feed-icon-wrap"),
            Div(
                Div(
                    Span(feed["name"], cls="news-feed-name"),
                    Span("Built in" if feed["is_builtin"] else "Custom", cls="news-feed-kind"),
                    cls="news-feed-name-row",
                ),
                A(feed["url"], href=feed["url"], target="_blank", rel="noopener",
                  cls="news-feed-url"),
                cls="news-feed-copy",
            ),
            Div(toggle_label if not user_id else "", delete, controls, cls="news-feed-actions"),
            cls=f"news-feed-card{' disabled' if not feed['enabled'] else ''}",
            data_feed_key=feed["key"],
        ))

    content = Div(
        Div(
            Div(
                Span("Context sources", cls="news-feeds-eyebrow"),
                H1("Control your market news", cls="news-feeds-title"),
                P("Enable the sources you want in the right-hand News pane. Paste an RSS, Atom, or publication URL and LiquidRound will detect the feed name and badge automatically.",
                  cls="news-feeds-intro"),
            ),
            Div(Span(str(active_count), cls="news-feeds-stat-value"), Span("active feeds", cls="news-feeds-stat-label"), cls="news-feeds-stat"),
            cls="news-feeds-hero",
        ),
        Div(error, cls="news-feeds-alert error", role="alert") if error else "",
        Div(f"Added {added}.", cls="news-feeds-alert success", role="status") if added else "",
        Div(
            Label("Add a publication", fr="news-feed-url", cls="news-feeds-add-label"),
            P("Enter a feed URL or a publication page that advertises RSS/Atom.", cls="news-feeds-add-help"),
            Form(
                Input(type="url", id="news-feed-url", name="url", required=True,
                      placeholder="https://example.com/news/rss", cls="news-feeds-input",
                      disabled=not bool(user_id)),
                Button("Detect and add", type="submit", cls="news-feeds-add-button",
                       disabled=not bool(user_id)),
                action="/app/news-feeds/add", method="post", cls="news-feeds-add-form",
            ),
            P("Sign in to add or change personal feeds." if not user_id else "We validate public URLs and follow only safe redirects.",
              cls="news-feeds-security-note"),
            cls="news-feeds-add-card",
        ),
        Div(
            Div(Span("Your sources", cls="news-feeds-section-title"),
                Span(f"{len(feeds)} total", cls="news-feeds-total"), cls="news-feeds-section-head"),
            Div(*cards, cls="news-feeds-grid"),
        ),
    )
    return _shell(session, content)


@ar("/app/news-feeds/add", methods=["POST"])
def add_news_feed(session, url: str = ""):
    user_id = _user_id(session)
    if not user_id:
        return RedirectResponse("/signin?next=/app/news-feeds", status_code=303)
    try:
        feed = add_custom_feed(user_id, url)
        clear_news_cache()
        return RedirectResponse(f"/app/news-feeds?added={quote_plus(feed['name'])}", status_code=303)
    except (NewsFeedError, ValueError) as exc:
        return RedirectResponse(f"/app/news-feeds?error={quote_plus(str(exc))}", status_code=303)
    except Exception:
        return RedirectResponse("/app/news-feeds?error=Feed+could+not+be+saved", status_code=303)


@ar("/app/news-feeds/toggle", methods=["POST"])
def toggle_news_feed(session, feed_key: str = "", enabled: str = "false"):
    user_id = _user_id(session)
    if not user_id:
        return RedirectResponse("/signin?next=/app/news-feeds", status_code=303)
    try:
        set_feed_enabled(user_id, feed_key, enabled.lower() == "true")
        clear_news_cache()
    except NewsFeedError as exc:
        return RedirectResponse(f"/app/news-feeds?error={quote_plus(str(exc))}", status_code=303)
    return RedirectResponse("/app/news-feeds", status_code=303)


@ar("/app/news-feeds/delete", methods=["POST"])
def remove_news_feed(session, feed_key: str = ""):
    user_id = _user_id(session)
    if not user_id:
        return RedirectResponse("/signin?next=/app/news-feeds", status_code=303)
    try:
        delete_custom_feed(user_id, feed_key)
        clear_news_cache()
    except NewsFeedError as exc:
        return RedirectResponse(f"/app/news-feeds?error={quote_plus(str(exc))}", status_code=303)
    return RedirectResponse("/app/news-feeds", status_code=303)
