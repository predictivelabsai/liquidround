"""SEDAR+ (sedarplus.ca) document discovery client — Playwright headless.

SEDAR+ is the Canadian Securities Administrators' public filing system. The
public search UI is a JavaScript-rendered "viewInstance" application, so plain
HTTP clients cannot enumerate results. This module drives a real headless
Chromium browser via Playwright to:

  1. navigate to the public document-search page,
  2. fill document-type / content-search / date-range filters,
  3. read the rendered results table (profile, document, submitted date,
     jurisdiction, file size, download URL),
  4. download each filing PDF through the browser context (which preserves the
     session/DRM keys embedded in the `resource.html` URL),
  5. hand the bytes to `utils.filing_intelligence.parse_authorized_document` so
     the downstream document model is identical to EDGAR's.

Throttling: SEDAR+ has no published rate limit; we sleep ~1.5s between page
actions and cap concurrent document downloads to be polite. The browser is
reused for the whole discovery run and closed on exit.

Public document search page:
    https://www.sedarplus.ca/csa-party/viewInstance/view.html?id=0c11f8b7998bcd96fb9cb36b800b9dfdd7cbf07b7cf2bde3

Document download URL pattern:
    https://www.sedarplus.ca/csa-party/viewInstance/resource.html?node=...&drmKey=...&drr=...&id=...
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Iterator
from urllib.parse import urlparse

log = logging.getLogger(__name__)

SEARCH_PAGE_URL = (
    "https://www.sedarplus.ca/csa-party/viewInstance/view.html?"
    "id=0c11f8b7998bcd96fb9cb36b800b9dfdd7cbf07b7cf2bde3"
)
LANDING_URL = "https://sedarplus.ca/home/"

# Document-type labels on SEDAR+ that are most likely to surface reverse-merger
# / RTO / CPC-qualifying-transaction / SPAC-QA events. Used as free-text filters
# in the "Document type" autocomplete when the caller does not override.
RTO_DOCUMENT_TYPES: tuple[str, ...] = (
    "Material change report",
    "News release",
    "Management information circular",
    "Reverse takeover",
    "Financial statements of RTO",
)

# Content-search terms that reliably surface reverse-merger/RTO filings when
# run through the "Document content search" box.
RTO_CONTENT_QUERIES: tuple[str, ...] = (
    "reverse takeover",
    "qualifying transaction",
    "capital pool company",
    "qualifying acquisition",
)

_PROFILE_RE = re.compile(r"(.+?)\s*\((\d{9})\)\s*$", re.DOTALL)


@dataclass
class SedarDocument:
    """One row from the SEDAR+ document-search results table."""

    profile_name: str
    profile_number: str
    document_name: str
    submitted_date: str
    jurisdiction: str
    file_size: str
    download_url: str
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "profile_name": self.profile_name,
            "profile_number": self.profile_number,
            "document_name": self.document_name,
            "submitted_date": self.submitted_date,
            "jurisdiction": self.jurisdiction,
            "file_size": self.file_size,
            "download_url": self.download_url,
        }


class SedarplusClient:
    """Headless Chromium driver for the SEDAR+ public document search.

    Used as a context manager so the browser is always closed::

        with SedarplusClient() as c:
            rows = c.search_documents(content_query="reverse takeover")
            pdf = c.download_document(rows[0].download_url)
    """

    def __init__(self, *, headless: bool = True, timeout_ms: int = 45_000,
                 action_sleep: float = 1.5):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.action_sleep = action_sleep
        self._pw = None
        self._browser = None
        self._page = None

    # ------------------------------------------------------------------ ctx mgr
    def __enter__(self) -> "SedarplusClient":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
        )
        self._page.set_default_timeout(self.timeout_ms)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._pw:
                self._pw.stop()
        self._page = self._browser = self._pw = None

    # ------------------------------------------------------------------ helpers
    def _sleep(self) -> None:
        time.sleep(self.action_sleep)

    def _goto_search(self) -> None:
        """Navigate to the document-search page and wait for it to render."""
        page = self._page
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        # The viewInstance app renders asynchronously; wait for the search
        # form anchor that every variant of the page exposes.
        try:
            page.wait_for_selector("text=Search and download documents",
                                   timeout=self.timeout_ms)
        except Exception:
            # Some renderings use a slightly different heading; fall back to
            # the document-content-search input which is always present.
            try:
                page.wait_for_selector("[name='documentContentSearch'], input[placeholder*='content']",
                                       timeout=self.timeout_ms)
            except Exception:
                page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
        self._sleep()

    # ------------------------------------------------------------------ search
    def search_documents(
        self,
        *,
        document_type: str = "",
        content_query: str = "",
        date_from: str = "",
        date_to: str = "",
        profile_name: str = "",
        jurisdiction: str = "",
        limit: int = 50,
    ) -> list[SedarDocument]:
        """Run one SEDAR+ document search and return the rendered rows.

        Parameters mirror the public search form. Dates are ``YYYY-MM-DD``.
        ``document_type`` is matched against the autocomplete list (e.g.
        "Material change report"). ``content_query`` is free text fed to the
        document-content-search box.
        """
        page = self._page
        self._goto_search()

        # --- document content search -----------------------------------------
        if content_query:
            self._fill_content_search(content_query)

        # --- document type autocomplete --------------------------------------
        if document_type:
            self._fill_document_type(document_type)

        # --- date range ------------------------------------------------------
        if date_from:
            self._fill_date("from", date_from)
        if date_to:
            self._fill_date("to", date_to)

        # --- profile name ----------------------------------------------------
        if profile_name:
            self._fill_profile(profile_name)

        # --- submit + read results ------------------------------------------
        self._click_search()
        return self._read_results(limit=limit)

    def iter_search(self, **kwargs) -> Iterator[SedarDocument]:
        """Convenience generator over a single search call."""
        yield from self.search_documents(**kwargs)

    # ------------------------------------------------------------------ fillers
    def _fill_content_search(self, query: str) -> None:
        page = self._page
        # The content-search box has a placeholder mentioning "content".
        sel = "[name='documentContentSearch'], input[placeholder*='content' i], textarea[placeholder*='content' i]"
        loc = page.locator(sel).first
        loc.fill(query)
        self._sleep()

    def _fill_document_type(self, doc_type: str) -> None:
        page = self._page
        # The document-type field is an autocomplete; typing triggers a list.
        sel = "[name='documentType'], input[placeholder*='document type' i], input[placeholder*='Document name' i]"
        loc = page.locator(sel).first
        loc.fill(doc_type)
        self._sleep()
        # Pick the first matching autocomplete suggestion if one appears.
        try:
            page.locator(f"li:has-text('{doc_type}')").first.click(timeout=3000)
            self._sleep()
        except Exception:
            # Autocomplete optional — leaving the typed text is acceptable.
            pass

    def _fill_date(self, which: str, value: str) -> None:
        page = self._page
        sel = f"input[name='date{which.capitalize()}'], input[placeholder*='{which}' i]"
        loc = page.locator(sel).first
        loc.fill(value)
        self._sleep()

    def _fill_profile(self, name: str) -> None:
        page = self._page
        sel = "[name='profileName'], input[placeholder*='profile' i]"
        page.locator(sel).first.fill(name)
        self._sleep()

    def _click_search(self) -> None:
        page = self._page
        # The Search button is a submit-style link/button.
        for sel in ("button:has-text('Search')", "a:has-text('Search')",
                    "input[type='submit'][value='Search']"):
            try:
                page.locator(sel).first.click(timeout=5000)
                break
            except Exception:
                continue
        # Wait for results table or an explicit empty-state message.
        try:
            page.wait_for_selector("table", timeout=self.timeout_ms)
        except Exception:
            page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
        self._sleep()

    # ------------------------------------------------------------------ results
    def _read_results(self, *, limit: int) -> list[SedarDocument]:
        page = self._page
        rows: list[SedarDocument] = []
        # SEDAR+ renders results in a table; the Actions column holds the
        # Generate-URL / document link. We page through "Next" until we hit
        # the limit or run out of rows.
        while True:
            page_rows = self._parse_current_page(limit - len(rows))
            rows.extend(page_rows)
            if len(rows) >= limit:
                return rows[:limit]
            if not self._click_next():
                break
        return rows[:limit]

    def _parse_current_page(self, max_rows: int) -> list[SedarDocument]:
        page = self._page
        out: list[SedarDocument] = []
        # The results table rows; the first row is usually a header.
        trs = page.locator("table tbody tr, table tr").all()
        for tr in trs:
            if len(out) >= max_rows:
                break
            try:
                cells = tr.locator("td").all()
                if len(cells) < 4:
                    continue
                profile_text = cells[0].inner_text(timeout=2000).strip()
                doc_text = cells[1].inner_text(timeout=2000).strip()
                submitted = cells[2].inner_text(timeout=2000).strip()
                jurisdiction = cells[3].inner_text(timeout=2000).strip() if len(cells) > 3 else ""
                file_size = cells[4].inner_text(timeout=2000).strip() if len(cells) > 4 else ""
            except Exception:
                continue
            profile_name, profile_number = _split_profile(profile_text)
            download_url = _extract_doc_url(tr)
            if not download_url and doc_text:
                # Fall back to any anchor inside the document cell.
                try:
                    href = tr.locator("a").first.get_attribute("href", timeout=1000)
                    if href:
                        download_url = _absolutize(href)
                except Exception:
                    pass
            if not profile_name and not doc_text:
                continue
            out.append(SedarDocument(
                profile_name=profile_name,
                profile_number=profile_number,
                document_name=doc_text,
                submitted_date=_norm_date(submitted),
                jurisdiction=jurisdiction,
                file_size=file_size,
                download_url=download_url,
                raw={"profile_text": profile_text, "doc_text": doc_text},
            ))
        return out

    def _click_next(self) -> bool:
        page = self._page
        for sel in ("a:has-text('Next')", "button:has-text('Next')",
                    "a[rel='next']", "li.next a"):
            try:
                loc = page.locator(sel).first
                cls = loc.get_attribute("class", timeout=1000) or ""
                if "disabled" in cls.lower():
                    return False
                loc.click(timeout=3000)
                page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
                self._sleep()
                return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------ download
    def download_document(self, url: str) -> bytes:
        """Fetch a SEDAR+ document PDF as bytes via the browser context.

        The browser session is what makes the DRM-keyed `resource.html` URL
        resolve, so we always download through `page.goto` + response capture
        rather than a plain `requests.get`.
        """
        page = self._page
        if not url:
            raise ValueError("download_document requires a non-empty URL")
        with page.expect_response(re.escape(url), timeout=self.timeout_ms) as resp_info:
            page.goto(url, wait_until="domcontentloaded")
        resp = resp_info.value
        body = resp.body()
        # If the URL serves HTML (e.g. a viewer page), try the first PDF link.
        if _looks_html(resp.headers.get("content-type", "")) or _looks_html_body(body):
            pdf_url = _find_pdf_link_in(page)
            if pdf_url:
                with page.expect_response(re.escape(pdf_url), timeout=self.timeout_ms) as r2:
                    page.goto(pdf_url, wait_until="domcontentloaded")
                return r2.value.body()
        return body


# ------------------------------------------------------------------ helpers
def _split_profile(text: str) -> tuple[str, str]:
    """Split 'Bunker Hill Mining Corp. (000032649)' into (name, number)."""
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    m = _PROFILE_RE.search(clean)
    if m:
        return m.group(1).strip(), m.group(2)
    # Sometimes the number is on its own line; keep what we have.
    return clean, ""


def _norm_date(value: str) -> str:
    """Best-effort normalization of SEDAR+ submitted-date strings to ISO."""
    clean = re.sub(r"\s+", " ", (value or "")).strip()
    # Common SEDAR+ formats: "2026-01-15", "Jan 15, 2026", "15-Jan-2026".
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d-%b-%Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            from datetime import datetime
            return datetime.strptime(clean, fmt).date().isoformat()
        except ValueError:
            continue
    # Fall back to the first 10 chars if they look like a date prefix.
    return clean[:10]


def _extract_doc_url(row_locator) -> str:
    """Pull the document download URL from an Actions cell / Generate-URL link."""
    # The Actions column usually has a 'Generate URL' link that, when clicked,
    # reveals the real resource.html link. We also look for direct anchors.
    for selector in (
        "a[href*='resource.html']",
        "a[href*='viewInstance/resource']",
        "a:has-text('Generate URL')",
        "a:has-text('Download')",
        "a[href*='.pdf']",
    ):
        try:
            href = row_locator.locator(selector).first.get_attribute("href", timeout=1000)
            if href:
                return _absolutize(href)
        except Exception:
            continue
    return ""


def _absolutize(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.sedarplus.ca" + href
    return "https://www.sedarplus.ca/" + href


def _looks_html(content_type: str) -> bool:
    return "text/html" in (content_type or "").lower()


def _looks_html_body(body: bytes) -> bool:
    head = body[:200].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or head.startswith(b"<head")


def _find_pdf_link_in(page) -> str:
    for selector in ("a[href$='.pdf']", "a[href*='resource.html']", "a:has-text('Download')"):
        try:
            href = page.locator(selector).first.get_attribute("href", timeout=2000)
            if href:
                return _absolutize(href)
        except Exception:
            continue
    return ""


# ------------------------------------------------------------------ discovery
def discover_documents(
    *,
    content_queries: tuple[str, ...] = RTO_CONTENT_QUERIES,
    document_types: tuple[str, ...] = (),
    days: int = 365,
    limit: int = 60,
    headless: bool = True,
) -> list[SedarDocument]:
    """Run a batch of SEDAR+ searches for reverse-merger-relevant documents.

    Combines content-search queries (default: RTO/CPC/QA terms) with optional
    document-type filters, dedupes by download URL, and returns up to ``limit``
    unique documents submitted within the last ``days`` days.
    """
    from datetime import date, timedelta

    date_from = (date.today() - timedelta(days=days)).isoformat()
    date_to = date.today().isoformat()
    seen: set[str] = set()
    out: list[SedarDocument] = []
    with SedarplusClient(headless=headless) as client:
        queries = content_queries or (None,)
        for query in queries:
            for doc_type in (document_types or ("",)):
                try:
                    rows = client.search_documents(
                        content_query=query or "",
                        document_type=doc_type or "",
                        date_from=date_from,
                        date_to=date_to,
                        limit=limit,
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning("SEDAR+ search '%s' / '%s' failed: %s", query, doc_type, exc)
                    continue
                for row in rows:
                    key = row.download_url or f"{row.profile_number}|{row.document_name}|{row.submitted_date}"
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(row)
                    if len(out) >= limit:
                        return out
    return out


def fetch_document_text(url: str, *, headless: bool = True) -> dict:
    """Download a single SEDAR+ document and run it through the canonical parser.

    Returns the ``parse_authorized_document`` shape
    (``{filename, text, sections, sha256}``) so callers can feed it straight
    into ``reverse_mergers.classify_filing`` / ``extract_transaction_terms``.
    """
    from utils.filing_intelligence import parse_authorized_document

    with SedarplusClient(headless=headless) as client:
        content = client.download_document(url)
    filename = _filename_from_url(url)
    return parse_authorized_document(content, filename)


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path
    name = path.rsplit("/", 1)[-1]
    if "." not in name:
        # resource.html URLs don't carry the original filename; synthesize one.
        name = "sedarplus_document.pdf"
    return name
