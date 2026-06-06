# LiquidRound User Guide

Welcome to LiquidRound — your AI-powered M&A research platform by Predictive Labs Ltd.

## Getting Started

LiquidRound provides two modes of operation:

- **Buyer-Led** — Find acquisition targets, run diligence, score matches, and draft IC memos
- **Seller-Led** — Prepare for sale (teasers / CIMs), identify buyers, and assess IPO readiness

Sign in or register to save your sessions, conversations, and pipelines. Guest users can still use the chat with in-memory sessions.

## The Chat Interface

The chat is your primary interface. Type a message or use a **prefix command** to route your query to a specific agent.

### Prefix Commands

| Prefix | Agent | What it does |
|--------|-------|-------------|
| `profile:` | Company Profiler | Look up a company by ticker |
| `financials:` | Financial analyst | Revenue, EBITDA, margins |
| `news:` | News analyst | Recent headlines for a ticker |
| `valuation:` | Valuation agent | EV/Revenue, EV/EBITDA comps |
| `targets` | Target Scanner | Find acquisition targets |
| `buyers` | Buyer Scanner | Identify strategic/financial buyers |
| `score` | Match Scorer | 7-dimension buyer-target scoring |
| `dcf:` | DCF Valuer | Discounted cash flow model |
| `comps:` | Comps Finder | Comparable transactions |
| `memo:` | IC Memo Writer | Draft an investment committee memo |
| `teaser:` | Teaser Designer | Blind teaser for sell-side |
| `vdr:` | VDR Auditor | Audit data room completeness |
| `research:` | Research Analyst | Deep web + semantic research |
| `ipo:` | IPO Readiness | Assess public offering readiness |

### Free-Form Chat

If you don't use a prefix, the **auto-router** picks the best agent for your query based on keywords and context.

## ECM Agent Squad

LiquidRound includes 22 specialized AI agents organized into 5 categories:

- **Sourcing** (4 agents) — Deal triage, target scanning, buyer scanning, intent analysis
- **Underwriting** (6 agents) — Company profiling, DCF, comps, LTM analysis, multiples, synergy modelling
- **Diligence** (5 agents) — VDR audit, contract abstraction, legal review, operational review, ESG screening
- **Capital** (5 agents) — IC memo writing, teaser design, bid strategy, IPO readiness, integration planning
- **Portfolio** (2 agents) — Research analyst, market intelligence

Each agent has its own system prompt and tool set. You can view and edit agent prompts in **Instructions**.

## Workspace Pages

### Companies

Search the company database by name, sector, or geography. Click a company to see its full profile with financials, description, and deal brief.

### Pipelines

Track your deal pipeline — add targets or buyers, set deal stages, and monitor progress.

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

## Exports

### Excel (XLSX)

When an agent produces a table, click the **Download XLSX** button to get a formatted Excel file with styled headers.

### Word (DOCX)

IC memos, teasers, and other markdown content can be exported as Word documents via the **Download DOCX** button.

### PDF

Company cards and IC memos can be downloaded as PDF files with LiquidRound branding.

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
