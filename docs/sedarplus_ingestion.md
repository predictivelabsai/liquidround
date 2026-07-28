# SEDAR+ Document Ingestion Pipeline

## Overview

LiquidRound ingests Canadian securities filings from **SEDAR+** (sedarplus.ca), the Canadian Securities Administrators' public filing system, and processes them through the same reverse-merger / RTO pipeline used for SEC EDGAR filings. This document describes the full ingestion pipeline from browser-driven discovery through PDF parsing, classification, and database storage.

---

## Architecture

```
sedarplus.ca (JS-rendered search UI)
    ↓  Playwright headless Chromium
utils/sedarplus.py — SedarplusClient
    ↓  search_documents() → list[SedarDocument]
    ↓  download_document() → bytes (PDF/HTML)
utils/filing_intelligence.py — parse_authorized_document()
    ↓  {filename, text, sections, sha256}
utils/reverse_mergers.py — classify_sedar_filing() + candidate_from_sedar()
    ↓  list[dict] (transaction records)
utils/reverse_mergers.py — upsert_transactions()
    ↓
PostgreSQL: liquidround.reverse_merger_transactions + reverse_merger_filings
    ↓
routes/reverse_mergers.py — /app/reverse-mergers (UI dashboard)
    ↓
agents/public_markets/reverse_merger_analyst.py — rto: chat agent
```

---

## Why Playwright?

SEDAR+ is a JavaScript-rendered "viewInstance" application. The public document search at `https://www.sedarplus.ca/csa-party/viewInstance/view.html` renders results dynamically via AJAX — plain HTTP clients (requests, httpx) cannot enumerate search results or resolve document download URLs. A real browser is required to:

1. Navigate to the search page and wait for the JS app to render
2. Fill the document-type autocomplete, content-search box, and date-range filters
3. Read the rendered results table (profile, document, date, jurisdiction, download URL)
4. Download each filing PDF through the browser context (which preserves session/DRM keys in the `resource.html` URL)

---

## Pipeline Components

### 1. Browser Client — `utils/sedarplus.py`

**`SedarplusClient`** — a context-manager Playwright driver:

```python
with SedarplusClient(headless=True) as client:
    rows = client.search_documents(content_query="reverse takeover", days=365)
    pdf_bytes = client.download_document(rows[0].download_url)
```

Key methods:
- `search_documents(document_type, content_query, date_from, date_to, profile_name, jurisdiction, limit)` — fills the SEDAR+ search form, reads the rendered table, paginates via "Next"
- `download_document(url)` — fetches the filing PDF as bytes through the browser context (preserves DRM keys)
- `iter_search(**kwargs)` — generator convenience wrapper

Throttling: ~1.5s sleep between page actions; no published SEDAR+ rate limit.

### 2. Batch Discovery — `utils/sedarplus.discover_documents()`

Runs multiple SEDAR+ searches for reverse-merger-relevant documents:

**Default content queries:**
- `"reverse takeover"`
- `"qualifying transaction"`
- `"capital pool company"`
- `"qualifying acquisition"`

**Default document types:**
- Material change report
- News release
- Management information circular
- Reverse takeover
- Financial statements of RTO

Deduplicates by download URL, returns up to `limit` unique `SedarDocument` rows submitted within the last `days` days.

### 3. Document Parsing — `utils/filing_intelligence.parse_authorized_document()`

The **shared parsing layer** — identical for EDGAR and SEDAR+ documents. Handles:

| Format | Processing |
|---|---|
| `.pdf` | `utils.document_parser.parse_pdf()` via pdfplumber → text extraction |
| `.html` / `.htm` | Decode UTF-8 → `html_to_markdown()` (strips tags, converts headings/breaks) |
| `.txt` / `.xml` | Decode UTF-8 → plain text |
| EDGAR SGML | `parse_complete_submission()` splits `<DOCUMENT>` blocks, extracts TYPE/SEQUENCE/FILENAME/DESCRIPTION fields |

Returns: `{filename, text, sections, sha256}`

- **`sha256`** is stored in `reverse_merger_filings.document_hash` for dedup/change detection
- **`sections`** extracts 8-K item sections (ITEM 1.01, 2.01, 5.01, 5.06, 9.01) when present
- Documents are **never mirrored** — only metadata + content hash are stored

### 4. Classification — `utils/reverse_mergers.classify_sedar_filing()`

Classifies SEDAR+ documents using Canadian RTO/CPC/SPAC-QA signal language:

| Signal | Pattern |
|---|---|
| `reverse-takeover language` | "reverse takeover", "reverse acquisition", "reverse merger", "backdoor listing", "share exchange agreement" |
| `CPC qualifying-transaction language` | "qualifying transaction", "capital pool company" |
| `SPAC qualifying-acquisition language` | "special purpose acquisition", "qualifying acquisition" |
| `material change report` | Document name contains "material change report" |
| `completion language` | "completed the", "closed the", "closing of", "consummated", "effective date" |

**Transaction types:**

| Type | Trigger |
|---|---|
| `ca_rto` | Reverse takeover language detected |
| `ca_cpc_qt` | Capital pool company / qualifying transaction |
| `ca_spac_qa` | SPAC qualifying acquisition |
| `candidate` | No specific signals (filtered out by discovery) |

Confidence: `0.40 + 0.10 × signals + 0.15 if completed` (capped at 0.98)

Risk flags:
- `completion_not_confirmed` — transaction language found but no completion language
- `financial_statements_not_detected` — RTO/CPC-QT but no "financial statements" mention

### 5. Candidate Building — `utils/reverse_mergers.candidate_from_sedar()`

Transforms a `SedarDocument` + parsed text into a normalized transaction record:

```python
{
    "transaction_key": "sedar:<sha1[:20]>",     # dedup handle
    "jurisdiction": "CA",
    "transaction_type": "ca_rto",
    "status": "completed|announced|candidate",
    "public_company": "<SEDAR+ profile name>",
    "public_ticker": None,
    "private_target": "<extracted from text>",
    "exchange": "TSX|TSXV|CSE|Cboe Canada|None",  # inferred from jurisdiction
    "announcement_date": "<submitted_date>",
    "completion_date": "<submitted_date if completed>",
    "deal_value": <extracted USD/CAD amount>,
    "source_url": "<SEDAR+ download URL>",
    "source_type": "SEDAR+",
    "source_filing_id": "<SEDAR+ profile number>",
    "risk_flags": [...],
    "confidence": 0.75,
    "metadata": {
        "signals": [...],
        "ingestion": "sedarplus_scraper",
        "document_mirrored": False,
        "document_name": "...",
        "profile_number": "...",
        "principal_jurisdiction": "...",
        "file_size": "...",
        "extraction": "sedar_text_v1",
    },
}
```

Exchange inference from SEDAR+ jurisdiction:
- "venture" / "tsxv" → TSXV
- "cse" / "canadian securities" → CSE
- "tsx" / "ontario" / "toronto" → TSX
- "cboe" / "alpha" → Cboe Canada

### 6. Database Storage — `sql/18-reverse-mergers.sql`

Two tables in the `liquidround` schema, shared with the EDGAR pipeline:

**`reverse_merger_transactions`** — one row per discovered transaction:
- `transaction_key TEXT UNIQUE` — dedup handle (`sedar:<sha1>` or `edgar:<accession>`)
- `jurisdiction TEXT CHECK IN ('US', 'CA')` — distinguishes SEC vs SEDAR+ records
- `transaction_type`, `status`, `public_company`, `private_target`, `exchange`
- `deal_value`, `announcement_date`, `completion_date`
- `source_url`, `source_type`, `source_filing_id`
- `risk_flags JSONB`, `confidence NUMERIC(4,3)`, `review_status`
- `metadata JSONB` — includes `ingestion: "sedarplus_scraper"` tag

**`reverse_merger_filings`** — child table for individual filing documents:
- `transaction_id BIGINT FK → reverse_merger_transactions(id) ON DELETE CASCADE`
- `regulator TEXT` — "SEC" or "SEDAR+"
- `form_type`, `filing_date`, `accession_number`
- `source_url TEXT`, `document_hash TEXT` (sha256 of document content)
- `detected_items JSONB` — extracted section items
- `UNIQUE(regulator, accession_number, source_url)` — prevents duplicate filing inserts

Upsert: `INSERT ... ON CONFLICT (transaction_key) DO UPDATE SET ...` per record, with per-record try/except + rollback.

---

## Sync Script — `scripts/sync_reverse_mergers_sedar.py`

CLI entry point for batch SEDAR+ ingestion:

```bash
# Full sync (default: 365 days, 40 records, headless)
python -m scripts.sync_reverse_mergers_sedar

# Preview without writing to DB
python -m scripts.sync_reverse_mergers_sedar --dry-run --limit 5

# Wider window
python -m scripts.sync_reverse_mergers_sedar --days 730 --limit 80

# Visible browser for debugging selectors
python -m scripts.sync_reverse_mergers_sedar --no-headless --limit 5
```

Flags:
- `--days N` — lookback window in days (default: 365)
- `--limit N` — max records to store (default: 40)
- `--dry-run` — discover and parse but don't write to DB
- `--no-headless` — run Chromium visibly (debugging)

Returns: `{"discovered": N, "stored": M, "dry_run": bool}`

---

## UI Integration — `routes/reverse_mergers.py`

### Routes

| Route | Method | Description |
|---|---|---|
| `/app/reverse-mergers` | GET | Dashboard page with summary cards, filter tabs (US/CA/All), transaction table |
| `/app/reverse-mergers/body` | GET | HTMX partial for filter re-renders |
| `/app/reverse-mergers/sync-sedar` | POST | Triggers `sync_reverse_mergers_sedar.main()` synchronously, returns status |
| `/app/reverse-mergers/sync-edgar` | POST | Triggers EDGAR sync (parallel endpoint) |
| `/app/reverse-mergers/import` | POST | Manual single-transaction import (reviewed Canadian filings) |

### UI — `components/reverse_mergers.py`

- **Summary cards** — total candidates, completed, announced, by jurisdiction (US/CA)
- **Filter tabs** — All / US (EDGAR) / CA (SEDAR+)
- **Transaction table** — company, target, type, status, deal value, confidence, source
- **Sync buttons** — "Sync SEDAR+ (CA)" and "Sync EDGAR (US)" with HTMX indicators
- **Import panel** — manual Canadian transaction entry with provenance

---

## Agent Integration — `tools/reverse_mergers.py`

The `reverse_merger_analyst` agent (prefix: `rto:`) has access to SEDAR+ search:

```python
search_sedarplus_filings_tool = StructuredTool.from_function(
    func=_search_sedar,
    name="search_sedarplus_filings",
    description="Search sedarplus.ca for Canadian regulatory filings (RTO, CPC qualifying transaction, SPAC qualifying acquisition).",
)
```

Usage in chat:
- `rto: search SEDAR+ for recent reverse takeover filings in Ontario`
- `rto: find Canadian CPC qualifying transactions from the last 90 days`
- `rto: show me SEDAR+ filings for Bunker Hill Mining`

The tool calls `utils.sedarplus.discover_documents()` with the user's query, returns a table artifact via `tools.artifact.emit()`.

---

## Full Pipeline — End to End

```
1. User clicks "Sync SEDAR+ (CA)" in the Reverse Mergers dashboard
   OR runs: python -m scripts.sync_reverse_mergers_sedar --days 365 --limit 40

2. scripts/sync_reverse_mergers_sedar.py calls:
   utils.reverse_mergers.discover_sedarplus_candidates(days=365, limit=40*2)

3. discover_sedarplus_candidates() calls:
   utils.sedarplus.discover_documents(days=365, limit=80, headless=True)

4. SedarplusClient (Playwright headless Chromium):
   a. Navigates to https://www.sedarplus.ca/csa-party/viewInstance/view.html?id=...
   b. For each content query ("reverse takeover", "qualifying transaction", ...):
      - Fills the content-search box
      - Fills date range (today - 365 days → today)
      - Clicks Search
      - Reads rendered results table → list[SedarDocument]
      - Paginates via "Next" button
   c. Deduplicates by download URL
   d. Returns up to 80 SedarDocument objects

5. For each SedarDocument:
   a. fetch_document_text(url) → SedarplusClient.download_document(url)
      - Browser navigates to resource.html URL (preserves DRM key)
      - Captures response body (PDF bytes)
      - If HTML served, finds PDF link inside
   b. parse_authorized_document(bytes, filename) →
      - PDF: pdfplumber extracts text
      - HTML: html_to_markdown() strips tags
      - Returns {filename, text, sections, sha256}
   c. classify_sedar_filing(text, document_name, company_name) →
      - Detects RTO/CPC/SPAC-QA signals
      - Returns {transaction_type, signals, risk_flags, confidence, completed}
   d. extract_transaction_terms(text) →
      - Regex extraction of private_target, deal_value, announced, completed
   e. candidate_from_sedar(document, text) →
      - Builds normalized transaction record dict
      - transaction_key = "sedar:<sha1 of profile_number|url|doc_name>"
   f. Filters out records where transaction_type == "candidate" (no signals)
   g. Stops at limit (40 records)

6. upsert_transactions(records):
   For each record:
   a. INSERT INTO reverse_merger_transactions ... ON CONFLICT (transaction_key) DO UPDATE
   b. INSERT INTO reverse_merger_filings ... (linked to transaction via FK)

7. Dashboard re-renders with new CA records
```

---

## Database Schema

```sql
-- Already defined in sql/18-reverse-mergers.sql
-- Shared between US (EDGAR) and CA (SEDAR+) records

CREATE TABLE liquidround.reverse_merger_transactions (
    id                  BIGSERIAL PRIMARY KEY,
    transaction_key     TEXT UNIQUE NOT NULL,      -- sedar:<sha1> or edgar:<accession>
    jurisdiction        TEXT NOT NULL CHECK (jurisdiction IN ('US', 'CA')),
    transaction_type    TEXT NOT NULL,             -- ca_rto, ca_cpc_qt, ca_spac_qa, us_rto, ...
    status              TEXT NOT NULL DEFAULT 'candidate',  -- candidate, announced, completed
    public_company      TEXT NOT NULL,
    public_ticker       TEXT,
    public_cik          TEXT,
    private_target      TEXT,
    exchange            TEXT,                       -- TSX, TSXV, CSE, Cboe Canada, NYSE, NASDAQ
    announcement_date   DATE,
    completion_date     DATE,
    deal_value          NUMERIC,
    source_url          TEXT NOT NULL,
    source_type         TEXT NOT NULL,              -- "SEDAR+" or "SEC EDGAR"
    source_filing_id    TEXT,                       -- SEDAR+ profile number or EDGAR accession
    risk_flags          JSONB NOT NULL DEFAULT '[]',
    confidence          NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    review_status       TEXT NOT NULL DEFAULT 'unreviewed',
    metadata            JSONB NOT NULL DEFAULT '{}', -- includes ingestion: "sedarplus_scraper"
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE liquidround.reverse_merger_filings (
    id              BIGSERIAL PRIMARY KEY,
    transaction_id  BIGINT REFERENCES liquidround.reverse_merger_transactions(id) ON DELETE CASCADE,
    regulator       TEXT NOT NULL,                 -- "SEDAR+" or "SEC"
    form_type       TEXT,
    filing_date     DATE,
    accession_number TEXT,
    source_url      TEXT NOT NULL,
    detected_items  JSONB NOT NULL DEFAULT '[]',
    document_hash   TEXT,                          -- sha256 of document content
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (regulator, accession_number, source_url)
);
```

---

## Comparison: EDGAR vs SEDAR+ Pipelines

| Aspect | SEC EDGAR (US) | SEDAR+ (CA) |
|---|---|---|
| **Source** | `efts.sec.gov` full-text search API | `sedarplus.ca` JS-rendered search UI |
| **Client** | `utils/edgar.py` (HTTP + `requests`) | `utils/sedarplus.py` (Playwright headless Chromium) |
| **Discovery** | EDGAR full-text search for 8-K items | SEDAR+ content search for RTO/CPC/QA terms |
| **Document download** | `get_filing_submission()` (HTTP) | `SedarplusClient.download_document()` (browser context) |
| **Parsing** | `filing_intelligence.build_filing_document()` (SGML) | `filing_intelligence.parse_authorized_document()` (PDF/HTML) |
| **Classification** | `classify_filing()` (8-K items) | `classify_sedar_filing()` (Canadian RTO/CPC/QA language) |
| **Jurisdiction** | `US` | `CA` |
| **Transaction key prefix** | `edgar:` | `sedar:` |
| **Sync script** | `scripts/sync_reverse_mergers_edgar.py` | `scripts/sync_reverse_mergers_sedar.py` |
| **DB tables** | Same (`reverse_merger_transactions` + `reverse_merger_filings`) | Same |
| **Agent tool** | `search_sec_filings` | `search_sedarplus_filings` |

---

## Prerequisites

- **Playwright + Chromium** — `python -m playwright install chromium`
- **pdfplumber** — included in `requirements.txt` (PDF text extraction)
- **PostgreSQL** — `liquidround` schema with `sql/18-reverse-mergers.sql` applied
- **Headless browser environment** — X11 not required; Chromium runs headless by default

---

## File Inventory

| File | Purpose |
|---|---|
| `utils/sedarplus.py` | Playwright headless Chromium client for SEDAR+ search + download |
| `utils/filing_intelligence.py` | Shared document parser (PDF, HTML, SGML → text + sha256) |
| `utils/reverse_mergers.py` | Classification, candidate building, discovery, DB upsert |
| `scripts/sync_reverse_mergers_sedar.py` | CLI sync script with `--days`, `--limit`, `--dry-run`, `--no-headless` |
| `sql/18-reverse-mergers.sql` | Database schema for `reverse_merger_transactions` + `reverse_merger_filings` |
| `routes/reverse_mergers.py` | UI routes — dashboard, sync endpoints, manual import |
| `components/reverse_mergers.py` | UI components — cards, table, sync buttons, import panel |
| `tools/reverse_mergers.py` | LangChain tools for the `rto:` agent (includes `search_sedarplus_filings`) |
| `agents/public_markets/reverse_merger_analyst.py` | Agent module with `rto:` prefix |
| `prompts/system/reverse_merger_analyst.md` | System prompt for the RTO analyst agent |

---

## Operational Notes

- **Politeness**: 1.5s sleep between page actions; single concurrent browser; no aggressive crawling
- **Document storage**: Documents are never mirrored — only metadata + `sha256` content hash are stored in the database
- **Dedup**: `transaction_key` (`sedar:<sha1>`) prevents duplicate transactions; `UNIQUE(regulator, accession_number, source_url)` prevents duplicate filings
- **Error handling**: Per-record try/except with rollback — one bad document doesn't abort the whole sync
- **Review workflow**: All discovered records start with `review_status='unreviewed'`; manual imports start with `review_status='reviewed'`
- **Headless by default**: Chromium runs headless in production; use `--no-headless` for selector debugging
- **DRM keys**: SEDAR+ document download URLs contain `drmKey` and `drr` parameters that are session-bound — downloads must go through the browser context, not plain HTTP
