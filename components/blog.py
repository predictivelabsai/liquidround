"""Blog page components — digest archive rendered as public blog posts."""
from __future__ import annotations

import math
from fasthtml.common import *

BG        = "#0B1220"
BG_ELEV   = "#111A2E"
INK       = "#E5E7EB"
INK_MUTED = "#94A3B8"
CTA       = "#F59E0B"
LINE      = "#1E293B"


def blog_index_section(digests: list[dict], page: int, total_pages: int):
    cards = []
    for d in digests:
        date_str = str(d.get("digest_date", ""))
        cards.append(
            A(
                Div(
                    Span(date_str, cls="text-xs mono", style=f"color:{CTA};"),
                    cls="mb-2",
                ),
                H3(d.get("title", "Untitled"),
                   cls="text-base font-semibold mb-1", style=f"color:{INK};"),
                P(f"Featured: {d.get('featured_company', '—')}",
                  cls="text-sm mb-2", style=f"color:{INK_MUTED};"),
                Div(
                    Span(f"{d.get('company_count', 0)} companies",
                         cls="text-xs px-2 py-0.5 rounded-full",
                         style=f"border:1px solid {LINE}; color:{INK_MUTED};"),
                    Span("Read →", cls="text-xs font-medium", style=f"color:{CTA};"),
                    cls="flex items-center justify-between",
                ),
                href=f"/blog/{d.get('slug', '')}",
                cls="block p-5 rounded-lg no-underline transition-all",
                style=f"background:{BG_ELEV}; border:1px solid {LINE};",
                onmouseover=f"this.style.borderColor='{CTA}'",
                onmouseout=f"this.style.borderColor='{LINE}'",
            )
        )

    empty = Div(
        P("No digests published yet.", cls="text-sm", style=f"color:{INK_MUTED};"),
        cls="text-center py-20",
    ) if not cards else None

    return Div(
        Div(
            H1("Baltic M&A Daily Digest", cls="text-2xl md:text-3xl font-bold tighter mb-2"),
            P("AI-generated investment theses on Lithuanian & Estonian companies with live M&A angles.",
              cls="text-sm md:text-base", style=f"color:{INK_MUTED};"),
            Div(
                A("Subscribe via email →", href="/signin",
                  cls="text-xs font-medium px-3 py-1.5 rounded no-underline",
                  style=f"background:{CTA}; color:{BG};"),
                cls="mt-4",
            ),
            cls="text-center py-12 md:py-16",
        ),
        empty if empty else Div(
            *cards,
            cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4",
        ),
        blog_pagination(page, total_pages) if total_pages > 1 else None,
        cls="max-w-6xl mx-auto px-4 sm:px-6 pb-16",
    )


def blog_post_section(archive: dict):
    return Div(
        Div(
            A("← All Digests", href="/blog",
              cls="text-xs no-underline", style=f"color:{CTA};"),
            cls="mb-6",
        ),
        H1(archive.get("title", ""), cls="text-2xl md:text-3xl font-bold tighter mb-2"),
        P(str(archive.get("digest_date", "")),
          cls="text-sm mono mb-8", style=f"color:{INK_MUTED};"),
        Div(
            NotStr(archive.get("blog_html", "")),
            cls="blog-content",
        ),
        Div(
            P("AI-generated analysis for informational purposes only. Not investment advice.",
              cls="text-xs", style=f"color:{INK_MUTED};"),
            cls="mt-8 pt-4",
            style=f"border-top:1px solid {LINE};",
        ),
        cls="max-w-4xl mx-auto px-4 sm:px-6 py-12",
    )


def blog_pagination(page: int, total_pages: int):
    links = []
    if page > 1:
        links.append(
            A("← Newer", href=f"/blog?page={page - 1}",
              cls="text-sm no-underline font-medium", style=f"color:{CTA};")
        )
    links.append(
        Span(f"Page {page} of {total_pages}", cls="text-xs", style=f"color:{INK_MUTED};")
    )
    if page < total_pages:
        links.append(
            A("Older →", href=f"/blog?page={page + 1}",
              cls="text-sm no-underline font-medium", style=f"color:{CTA};")
        )
    return Div(*links, cls="flex items-center justify-center gap-6 mt-10")
