# LiquidRound User Guide

Welcome to LiquidRound v0.4.0 — your AI-powered M&A and capital markets research platform by Predictive Labs Ltd.

## Getting Started

LiquidRound provides three modes of operation:

- **Buyer-Led** — Find acquisition targets, run diligence, score matches, and draft IC memos
- **Seller-Led** — Prepare for sale (teasers / CIMs), identify buyers, and assess IPO readiness
- **Public Markets / Hedge Funds** — Explore SEC 13F institutional holdings, fund AUM rankings, and activist filings

Sign in or register to save your sessions, conversations, and pipelines. Guest users can still use the chat with in-memory sessions.

## The Chat Interface

The chat is your primary interface. Type a message or use a **prefix command** to route your query to a specific agent.

### Prefix Commands

| Prefix | Agent | What it does |
|--------|-------|-------------|
| `profile:` | Company Profiler | Look up a company by ticker |
| `scan:` | Target Scanner | Find acquisition targets |
| `buyers:` | Buyer Scanner | Identify strategic/financial buyers |
| `triage:` | Deal Triage | Quick deal screening |
| `intent:` | Seller Intent | Analyze seller motivation |
| `dcf:` | DCF Valuer | Discounted cash flow model |
| `multi:` | Multiples Valuer | EV/Revenue, EV/EBITDA comps |
| `comps:` | Comps Finder | Comparable transactions |
| `ltm:` | LTM Normalizer | Normalize trailing-twelve-month P&L |
| `synergy:` | Synergy Analyst | Revenue and cost synergy modelling |
| `score` | Match Scorer | 7-dimension buyer-target scoring |
| `vdr:` | VDR Auditor | Audit data room completeness |
| `abstract:` | Contract Abstractor | Extract key terms from contracts |
| `legal:` | Legal Reviewer | Open litigation and legal risk |
| `ops:` | Operational DD | Working capital and operations review |
| `esg:` | ESG Reviewer | Environmental, social, governance screening |
| `memo:` | IC Memo Writer | Draft an investment committee memo |
| `teaser:` | Teaser Designer | Blind teaser for sell-side |
| `bid:` | Bid Strategist | Cash/stock mix and offer structuring |
| `ipo:` | IPO Readiness | Assess public offering readiness |
| `integrate:` | Integration Planner | Post-merger 100-day plan |
| `research:` | Research Analyst | Deep web + semantic research |
| `hedgefunds:` | Hedge Fund Analyst | SEC 13F holdings, fund AUM, activist filings |

### Free-Form Chat

If you don't use a prefix, the **auto-router** picks the best agent for your query based on keywords and context.

## ECM Agent Squad

LiquidRound includes 23 specialized AI agents organized into 6 categories:

- **Deal Sourcing & Screening** (4 agents) — Deal triage, target scanning, buyer scanning, seller intent analysis
- **Valuation & Underwriting** (6 agents) — Company profiling, DCF, comps, LTM normalization, multiples, synergy modelling
- **Due Diligence Stack** (5 agents) — VDR audit, contract abstraction, legal review, operational review, ESG screening
- **Deal Execution & Capital** (5 agents) — IC memo writing, teaser design, bid strategy, IPO readiness, integration planning
- **Research & Post-Deal** (2 agents) — Research analyst, match scorer
- **Public Markets & Hedge Funds** (1 agent) — Hedge fund analyst with SEC 13F data

Each agent has its own system prompt and tool set. You can view and edit agent prompts in **Instructions**.

## Public Markets

Access via the **Public Markets** section in the left navigation:

### IPO Map

Interactive world map of recent and upcoming IPOs. Filter by geography and sector.

### IPO Pipeline

Track the IPO pipeline with deal stages, expected pricing dates, and offering sizes.

### Prospectus

Browse and analyze IPO prospectus documents.

## Hedge Funds

Access via the **Hedge Funds** section in the left navigation:

### Fund Treemap

Interactive Plotly treemap at `/app/hedgefunds` showing SEC Form 13F institutional holdings. The visualization groups positions by fund manager, with cell size proportional to portfolio value.

**Filter controls:**
- **Fund** — Search for a specific fund manager (e.g. "Bridgewater", "Vanguard")
- **Min Value ($)** — Filter positions by minimum value ($1M, $10M, $100M, $1B)
- **Limit** — Number of positions to display (200, 500, 1000)

Click **Apply** to refresh the treemap with your filters.

### Chat Commands

Click these in the left nav or type the prefix in chat:

- **Top Holdings** — `hedgefunds: top funds by AUM` — Shows the largest institutional investors ranked by total portfolio value
- **Popular Securities** — `hedgefunds: most popular securities across all funds` — The most widely held stocks across all 13F filers
- **Activist Filings** — `hedgefunds: recent activist filings` — Recent Schedule 13D/13G beneficial ownership filings (indicates activist stakes)

### Data Source

All hedge fund data comes from SEC Form 13F filings — mandatory quarterly disclosures by institutional investment managers with over $100M in qualifying assets. Key points:

- Data reflects the **latest available quarter** with a 45-day filing lag
- Values are reported in **thousands of dollars** (the SEC standard)
- Only **long equity positions** are included (no shorts, options, or fixed income)
- Approximately **10,000+ fund managers** and **7 million+ holdings** in the database

## Lead-Magnet Tools

Three free tools are available without sign-in, accessible from the **Tools** section:

### Market Comps

Enter a company URL to get sector M&A benchmarks — EV/Revenue and EV/EBITDA multiples compared to sector averages.

### Find Buyers

Enter a company URL to identify potential strategic and financial buyers with match scoring.

### Valuation

Enter a company URL and basic financials to get an indicative valuation range based on sector benchmarks.

All three tools work by scraping the company website, identifying the sector, and applying relevant multiples and buyer databases.

## Workspace Pages

### Companies

Search the company database by name, sector, or geography. Click a company to see its full profile with financials, description, and deal brief.

### Pipelines

Track your deal pipeline — add targets or buyers, set deal stages, and monitor progress.

### Daily Deals

AI-curated daily digest of M&A-relevant companies with thesis analysis and sector comps.

### Valuation

Interactive valuation simulator with 4 methods: EV/Revenue multiples, EV/EBITDA multiples, DCF (WACC + equity bridge), and combined view.

### Analytics

Text-to-SQL analytics — ask questions in plain English and get charts + tables from the database.

### Data Room

Upload and manage deal documents organized by company. Supports PDF, DOCX, XLSX, PPTX, CSV, and image files.

### Documents

Browse and view uploaded documents. Extract key terms or score documents against buyer criteria.

### Deal History

View your workflow history with charts showing deal types, timeline, and status distribution.

### Instructions

View and customize agent system prompts to tailor AI behavior to your firm's standards.

### Help

In-app help and quick reference.

## Exports

### Excel (XLSX)

When an agent produces a table, click the **Download XLSX** button to get a formatted Excel file with styled headers.

### Word (DOCX)

IC memos, teasers, and other markdown content can be exported as Word documents via the **Download DOCX** button.

### PDF

IC memos produce a PDF preview in the right pane. Company cards can also be downloaded as PDF files with LiquidRound branding.

## Configuration

### Currency

Switch between EUR, GBP, and USD in the Configuration section of the left pane.

### Role

Set your default view to Buyer, Seller, or Both. This affects which agents and suggestions appear first.

## Keyboard Shortcuts

- **Enter** — Send message
- **Shift+Enter** — New line in message

## Tips

- Use the **Copy** button to copy all chat messages to clipboard
- Use the **Share** button to generate a shareable link for your chat session
- The **News** tab in the right pane shows live M&A news from major financial sources
- The **Artifact** tab shows agent-produced tables, charts, and citations
- Upload documents via the paperclip button or drag-and-drop
- All collapsible nav sections (Agents, Tools, Public Markets, Hedge Funds, Workspace) can be expanded by clicking the section header
