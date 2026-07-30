"""Small allow-list HTML sanitizer for generated or database-backed content."""
from __future__ import annotations

import html
from html.parser import HTMLParser
from urllib.parse import urlparse


_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "div", "em", "h1", "h2", "h3",
    "h4", "hr", "i", "li", "ol", "p", "pre", "span", "strong", "table",
    "tbody", "td", "th", "thead", "tr", "ul",
}
_VOID_TAGS = {"br", "hr"}
_ALLOWED_ATTRS = {"class", "colspan", "rowspan", "target"}
_DROP_WITH_CONTENT = {"iframe", "object", "script", "style", "svg"}


def _safe_href(value: str) -> str | None:
    value = value.strip()
    parsed = urlparse(value)
    if value.startswith(("/", "#")) or parsed.scheme in {"http", "https", "mailto"}:
        return value
    return None


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.drop_depth = 0

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in _DROP_WITH_CONTENT:
            self.drop_depth += 1
            return
        if self.drop_depth or tag not in _ALLOWED_TAGS:
            return
        safe_attrs: list[tuple[str, str]] = []
        for name, value in attrs:
            name = name.lower()
            value = value or ""
            if name == "href" and tag == "a":
                href = _safe_href(value)
                if href is not None:
                    safe_attrs.append(("href", href))
            elif name in _ALLOWED_ATTRS:
                safe_attrs.append((name, value))
        if tag == "a" and any(name == "target" and value == "_blank" for name, value in safe_attrs):
            safe_attrs.append(("rel", "noopener noreferrer"))
        rendered = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in safe_attrs
        )
        self.output.append(f"<{tag}{rendered}>")

    def handle_startendtag(self, tag: str, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in _DROP_WITH_CONTENT:
            if self.drop_depth:
                self.drop_depth -= 1
            return
        if not self.drop_depth and tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str):
        if not self.drop_depth:
            self.output.append(html.escape(data))


def sanitize_html(value: str) -> str:
    """Return HTML restricted to inert formatting and public navigation."""
    parser = _Sanitizer()
    parser.feed(value or "")
    parser.close()
    return "".join(parser.output)
