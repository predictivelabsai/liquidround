# LiquidRound

**AI ECM Agent Squad for M&A, IPO & Public Markets**

[liquidround.ai](https://liquidround.ai) · Predictive Labs Ltd

![LiquidRound Demo](docs/liquidround.gif)

LiquidRound is an AI-powered chat-first workspace for investment banking and equity capital markets. A squad of specialist AI agents covers the full deal lifecycle — buyer-led sourcing and diligence, seller-led positioning and IPO readiness, and public markets intelligence.

## What it does

- **Buy-side M&A** — find acquisition targets, run diligence, score matches, build IC memos
- **Sell-side M&A** — prepare teasers / CIMs, identify buyers, assess IPO readiness
- **Public Markets** — IPO tracking (map, pipeline, prospectus), SPAC lifecycle dashboard
- **Hedge Fund Intelligence** — SEC 13F institutional holdings, fund AUM rankings, activist filings
- **BYOD** — upload pitch books, CIMs, term sheets; agents read, cite, and draft from them

## AI Agent Squad

Six workflow categories with 23 specialist agents:

| Category | Agents | Examples |
|----------|--------|----------|
| Deal Sourcing & Screening | 4 | Target Scanner, Buyer Scanner, Deal Triage, Seller Intent |
| Valuation & Underwriting | 6 | Company Profiler, DCF, Comps, LTM, Multiples, Synergy |
| Due Diligence Stack | 5 | VDR Auditor, Contract Abstractor, Legal, Operational, ESG |
| Deal Execution & Capital | 5 | IC Memo, Teaser, Bid Strategy, IPO Readiness, Integration |
| Research & Post-Deal | 2 | Research Analyst, Match Scorer |
| Public Markets | 1 | Hedge Fund Analyst (13F, AUM, activist filings) |

Type a natural-language question and the auto-router picks the right agent, or use a prefix shortcut (`scan:`, `dcf:`, `memo:`, `hedgefunds:`, etc.) to route directly.

## Key Features

### Chat Interface
Three-pane layout: left nav (sessions, agents, workspace), center chat with streaming responses, right artifact canvas (tables, charts, PDF previews).

### Public Markets Dashboard
- **IPO Map** — global treemap sized by market cap, colored by post-IPO performance (RdYlGn)
- **IPO Pipeline** — upcoming US IPOs from NASDAQ calendar, private mega-caps by sector
- **SPAC Tracker** — KPI cards, annual IPO chart, status donut, searchable table with 13F cross-reference
- **Prospectus Builder** — analyze IPO prospectus documents

### Hedge Fund Treemap
Interactive Plotly treemap of SEC 13F institutional holdings. Filter by fund, min value, and position count. 10K+ funds, 7M+ holdings.

### Workspace
Companies directory, deal pipelines (kanban), daily AI-curated digest, valuation simulator (DCF + multiples), text-to-SQL analytics, virtual data room, document management, deal history.

### Free Tools (no sign-in)
- Market Comparables — sector M&A benchmarks
- Business Valuation — indicative range with AI value drivers
- Find Buyers — strategic and financial buyer matching

### Exports
- **XLSX** — agent tables as formatted spreadsheets
- **DOCX** — IC memos and teasers as Word documents
- **PDF** — memo preview in-app, company cards as branded PDFs

## Quick Start

```bash
uv pip install -r requirements.txt
python main.py                    # starts on port 5007
```

Or with Docker:

```bash
docker compose up --build
```

### Environment

```
XAI_API_KEY=...          # primary LLM (Grok via x.ai)
OPENAI_API_KEY=...       # fallback LLM
EXA_API_KEY=...          # semantic search
TAVILY_API_KEY=...       # web search
DB_URL=postgresql://...  # PostgreSQL
SESSION_SECRET=...       # session cookie signing
```

At least one of `XAI_API_KEY` or `OPENAI_API_KEY` is required.

## Testing

```bash
pytest -q                              # unit tests (125 cases)
pytest -q tests/test_registry.py       # agent registry integrity
pytest -m e2e                          # Playwright E2E (requires server on :5007)
```

## Tech Stack

- **Backend** — Python, FastHTML, HTMX, LangGraph, LangChain
- **LLM** — Grok (x.ai) or OpenAI via `utils/llm_factory`
- **Database** — PostgreSQL (`liquidround` + `hedgefolio` schemas)
- **Charts** — Plotly.js (treemaps, bar, donut, histograms)
- **Styling** — Tailwind CSS (CDN), custom dark navy + amber palette
- **Data** — yfinance, SEC EDGAR, Exa, Tavily, NASDAQ calendar
- **Deploy** — Docker Compose on Coolify, Postmark for email

## Data Pipelines

```bash
python -m scripts.sync_spacs --enrich       # SPAC data (NASDAQ + EDGAR + yfinance)
python -m scripts.download_sec_13f          # quarterly 13F institutional holdings
python -m scripts.sync_activist             # daily 13D/G activist filings
python -m scripts.daily_deals --all         # send daily digest to opted-in users
```

## License

Proprietary — Predictive Labs Ltd. All rights reserved.

---

**Predictive Labs Ltd** · [liquidround.ai](https://liquidround.ai)
