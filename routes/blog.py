"""Public blog routes — /blog, /blog/{slug}, /blog/rss

Renders archived daily digests as SEO-friendly blog posts.
No authentication required.
"""
from __future__ import annotations

import math
from datetime import datetime
from fasthtml.common import *
from fasthtml.core import APIRouter
from starlette.responses import Response

from components.landing import landing_page
from components.blog import blog_index_section, blog_post_section

ar = APIRouter()


@ar("/blog")
def blog_index(page: int = 1):
    from utils.digest import get_archived_digests
    per_page = 12
    digests, total = get_archived_digests(page=page, per_page=per_page)
    total_pages = max(1, math.ceil(total / per_page))
    return landing_page(
        blog_index_section(digests, page, total_pages),
        active="blog",
        title="Blog — LiquidRound",
        description="Daily AI-generated investment theses on Baltic M&A companies.",
        canonical="https://liquidround.ai/blog",
    )


@ar("/blog/rss")
def blog_rss():
    from utils.digest import get_archived_digests
    digests, _ = get_archived_digests(page=1, per_page=20)
    items = []
    for d in digests:
        pub_date = d.get("created_at", "")
        if pub_date:
            try:
                dt = datetime.fromisoformat(str(pub_date))
                pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except (ValueError, TypeError):
                pub_date = ""
        desc = f"{d.get('company_count', 0)} Baltic companies with AI investment theses. Featured: {d.get('featured_company', '—')}"
        items.append(f"""    <item>
      <title>{_xml_escape(d.get('title', ''))}</title>
      <link>https://liquidround.ai/blog/{d.get('slug', '')}</link>
      <guid isPermaLink="true">https://liquidround.ai/blog/{d.get('slug', '')}</guid>
      <description>{_xml_escape(desc)}</description>
      <pubDate>{pub_date}</pubDate>
    </item>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>LiquidRound Baltic M&amp;A Daily Digest</title>
    <link>https://liquidround.ai/blog</link>
    <description>AI-generated investment theses on Lithuanian &amp; Estonian companies with live M&amp;A angles.</description>
    <language>en</language>
    <atom:link href="https://liquidround.ai/blog/rss" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/rss+xml")


@ar("/blog/{slug}")
def blog_post(slug: str):
    from utils.digest import get_archived_digest
    archive = get_archived_digest(slug)
    if not archive:
        return Response("Not found", status_code=404)

    desc = f"{archive.get('company_count', 0)} Baltic companies. Featured: {archive.get('featured_company', '—')}"
    return landing_page(
        blog_post_section(archive),
        active="blog",
        title=f"{archive.get('title', 'Digest')} — LiquidRound",
        description=desc,
        canonical=f"https://liquidround.ai/blog/{slug}",
    )


@ar("/sitemap.xml")
def sitemap():
    from utils.digest import get_archived_digests
    base = "https://liquidround.ai"
    today = datetime.utcnow().strftime("%Y-%m-%d")

    static_pages = [
        ("/", "1.0", "weekly"),
        ("/platform", "0.8", "monthly"),
        ("/agents", "0.8", "monthly"),
        ("/pricing", "0.7", "monthly"),
        ("/contact", "0.5", "monthly"),
        ("/how-it-works", "0.7", "monthly"),
        ("/industries", "0.7", "monthly"),
        ("/tools/comparables", "0.6", "monthly"),
        ("/tools/match", "0.6", "monthly"),
        ("/tools/valuation", "0.6", "monthly"),
        ("/blog", "0.9", "daily"),
        ("/blog/rss", "0.3", "daily"),
    ]

    urls = []
    for path, priority, freq in static_pages:
        urls.append(f"""  <url>
    <loc>{base}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    # Agent detail pages
    try:
        from agents.registry import AGENTS
        for spec in AGENTS:
            urls.append(f"""  <url>
    <loc>{base}/agents/{spec.slug}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>""")
    except Exception:
        pass

    # Blog post pages
    digests, _ = get_archived_digests(page=1, per_page=100)
    for d in digests:
        post_date = str(d.get("digest_date", today))[:10]
        urls.append(f"""  <url>
    <loc>{base}/blog/{d.get('slug', '')}</loc>
    <lastmod>{post_date}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.7</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))
