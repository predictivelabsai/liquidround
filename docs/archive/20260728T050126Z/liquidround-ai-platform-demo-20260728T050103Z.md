# LiquidRound AI Platform Demo

## Current platform guide for M&A, IPO, public markets, and investor relations

Edition generated **2026-07-28** · LiquidRound v0.5.1 · Predictive Labs Ltd · **liquidround.ai**

LiquidRound is a chat-first AI platform for transaction teams, public-markets analysts,
and investor-relations professionals. It combines **30 specialist agents** across **7
categories**, guided tools, live market data, document workflows, and exportable work
products in one workspace.

This guide walks through the platform section by section — from the initial landing
experience through the Investor Relations workflow, the full agent squad, public markets
dashboards, and workspace tools.

---

## Demo at a glance

Use this sequence for a concise platform demonstration:

1. Open the three-pane workspace and show automatic agent routing.
2. Show the always-visible live News pane and run a company profile or deep-research prompt.
3. Expand **Investor Relations** and create a researched press release.
4. Triage a material event with `ir-triage:` to show disclosure go/no-go analysis.
5. Export the drafted release to Markdown, Word, and PDF, then save it to the Data Room.
6. Run `ir-publish:` to finalize an approved draft into a wire-ready package.
7. Open Public Markets, Deal Radar, Analytics, and the Skills editor.

The most important workflow is **Investor Relations → Press Release Creator**. It
turns a guided brief into a researched, publication-ready draft while keeping source
notes and verification warnings visible to the editor. The new IR agent squad covers
the full disclosure lifecycle: triage, drafting, compliance review, publishing, and
distribution.

---

## Getting started

Open **liquidround.ai** and choose a Buyer-Led or Seller-Led entry point. Sign in with
email and password or Google to persist conversations, pipelines, documents, preferences,
share links, bookmarks, and generated investor-relations drafts.

The primary application uses three panes:

- **Left pane:** sessions, 30 agents in seven categories, Tools, Investor Relations,
  Public Markets, Hedge Funds, Workspace, Training, and Help.
- **Centre pane:** routed chat, guided workspace pages, forms, results, and controls.
- **Right pane:** an always-visible desktop News feed for market intelligence. Agent
  tables, charts, citations, and other work products render inline in the conversation;
  generated PDFs open in a dedicated browser tab.

On mobile, the left pane becomes a slide-in menu and the centre pane remains the main
working surface.

![LiquidRound three-pane workspace — buyer view](../screenshots/07-app-buyer.png)

---

## Investor Relations — featured workflow

The Investor Relations category is the newest and most workflow-driven part of the
platform. It covers the complete disclosure lifecycle from event detection through
distribution, with five dedicated agents and a guided Press Release Creator page.

### Press Release Creator

Open **Investor Relations → Press Release Creator** at
`/app/investor-relations/press-release`.

Only **Topic** is required. The guided brief also supports:

- Company name or website
- Release type
- Language and tone
- Intended audience
- Key facts, dates, figures, and approved claims
- Quote guidance and speaker details
- Approved company boilerplate
- Investor and media contacts
- Length, embargo, exchange, and other instructions

Press **Research and draft release**. The workflow searches current web and semantic
sources, sends the evidence and brief to the Press Release Writer, and returns editable
Markdown. Primary and official sources are preferred. When a material fact cannot be
verified, the writer uses a confirmation placeholder or omits the claim.

![Press Release Creator — guided form](../screenshots/19-ir-press-release.png)

### Draft structure and safeguards

The writer produces a news-led headline, optional subheadline, dateline, lead, supporting
facts, attributed or clearly marked draft quotes, boilerplate, contacts, and source
verification notes. It distinguishes completed events from plans and forward-looking
statements. Regulated, earnings, fundraising, clinical, and M&A announcements are flagged
for legal or compliance review.

### Release output actions

- **Copy** — copy the editable Markdown.
- **Markdown** — download a `.md` source file.
- **Word** — download a formatted `.docx` document.
- **PDF** — download a branded, paginated PDF.
- **Save to workspace** — save the draft to the signed-in user's Data Room.

---

## Investor Relations — the IR agent squad (continued)

The Investor Relations category contains 5 agents covering the complete disclosure
workflow from event detection through distribution:

- **IR Event Triage** (`ir-triage:`) — assesses whether an event is material enough to
  require disclosure under Reg FD, MAR Article 17, or exchange rules. Returns a go/no-go
  verdict with urgency window and recommended channel.

- **Press Release Writer** (`write-release:`) — researches the live web and drafts a
  publication-ready investor-relations release from a topic and guided brief.

- **IR Compliance Reviewer** (`ir-compliance:`) — reviews a draft for Reg FD, MAR, and
  exchange-rule compliance before publish. Flags selective disclosure risks, forward-looking
  statement shortfalls, and missing cautionary language.

- **IR Publish Agent** (`ir-publish:`) — takes an approved draft and produces the final
  wire-ready package: exchange-compliant formatting, wire-service fields, and a pre-publish
  checklist.

- **IR Distribution Planner** (`ir-distribute:`) — plans wire-service routing, exchange
  notifications, investor and analyst lists, media targeting, and embargo/timing strategy
  across time zones.

![IR Triage — materiality assessment in chat](../screenshots/21-chat-ir-triage.png)

![IR Publish — finalizing a release in chat](../screenshots/22-chat-ir-publish.png)

**Demo prompts:**

- `ir-triage: our CFO resigned unexpectedly — do we need to disclose?`
- `write-release: research Enefit Green and draft a release about a new solar project`
- `ir-compliance: check this draft earnings release for Reg FD issues`
- `ir-publish: finalize the approved Q3 earnings release`
- `ir-distribute: plan distribution for our Q3 earnings release across Nordic exchanges`

---

## The 30-agent squad

The platform's 30 specialist agents are organized into 7 categories. Each agent has a
one-word chat prefix for direct invocation, or the auto-router picks the right agent from
natural language.

### Deal Sourcing and Screening — 4 agents

- **Target Scanner** (`scan:`) — find acquisition targets by sector, geography, and size.
- **Buyer Scanner** (`buyers:`) — map strategic and financial buyers.
- **Deal Triage** (`triage:`) — return a rapid go/no-go against an investment mandate.
- **Seller Intent Signal** (`intent:`) — rank companies by likelihood of entering a sale.

### Valuation and Underwriting — 6 agents

- **Company Profiler** (`profile:`) — build a live company and financial profile.
- **Transaction Comps Finder** (`comps:`) — find precedents and trading comparables.
- **LTM Financials Normalizer** (`ltm:`) — normalize P&L and EBITDA add-backs.
- **DCF Valuer** (`dcf:`) — create a five-year DCF and sensitivity analysis.
- **Multiples Valuer** (`multi:`) — apply peer and transaction multiples.
- **Synergy Analyst** (`synergy:`) — quantify revenue, cost, and operating synergies.

---

## The 30-agent squad (continued)

### Due Diligence — 5 agents

- **VDR Auditor** (`vdr:`) — audit a data room against a comprehensive checklist.
- **Contract Abstractor** (`abstract:`) — extract key terms with page references.
- **Legal and Regulatory Reviewer** (`legal:`) — flag litigation and consent risks.
- **Operational Diligence Reviewer** (`ops:`) — surface operational gaps and actions.
- **ESG and Compliance Risk Flagger** (`esg:`) — assess environmental, social, and governance risks.

### Deal Execution and Capital — 5 agents

- **IC Memo Writer** (`memo:`) — draft an investment-committee memo.
- **Teaser and CIM Designer** (`teaser:`) — create buyer-ready sell-side materials.
- **Bid Strategist** (`bid:`) — structure cash, stock, escrow, earnouts, and terms.
- **IPO Readiness Assessor** (`ipo:`) — assess financial, governance, operating, and market readiness.
- **Match Scorer** (`score:`) — score buyer-target fit across seven dimensions.

### Research and Post-Deal — 2 agents

- **Deep Research Analyst** (`research:`) — combine web and semantic research with citations.
- **Integration and 100-Day Planner** (`integrate:`) — create day-one and 30-60-90-day plans.

---

## The 30-agent squad (continued)

### Public Markets — 3 agents

- **Hedge Fund Analyst** (`hedgefunds:`) — analyze 13F holdings, AUM, concentration, and activist filings.
- **Filing Analyst** (`filings:`) — search and analyze EDGAR filings including 10-K, 10-Q, 8-K, proxy, and XBRL.
- **Press Release Analyst** (`releases:`) — search, read, and aggregate 390K+ historical releases.

### Investor Relations and Communications — 5 agents

- **IR Event Triage** (`ir-triage:`) — materiality go/no-go against Reg FD, MAR, and exchange rules.
- **Press Release Writer** (`write-release:`) — research and draft publication-ready IR releases.
- **IR Compliance Reviewer** (`ir-compliance:`) — Reg FD / MAR / exchange disclosure check before publish.
- **IR Publish Agent** (`ir-publish:`) — approved draft to final wire-ready package with checklist.
- **IR Distribution Planner** (`ir-distribute:`) — wire services, exchanges, investor lists, and timing.

---

## Chat, routing, and artifacts

Ask a natural-language question or start with an agent prefix. Explicit prefixes take
priority; otherwise the router uses intent hints and a classifier. Agent progress and
tool calls stream into the conversation.

The desktop News pane is visible by default and remains dedicated to live market
intelligence. Agent work products — company profiles, result tables, citations, scoring
matrices, and charts — render inline in the conversation, while generated memo PDFs open
in a dedicated browser tab. Use **Copy** to copy the conversation and **Share** to create
a read-only session link.

![Agent routing — deal triage in chat](../screenshots/10-chat-triage.png)

![DCF valuation in chat](../screenshots/11-chat-dcf.png)

---

## Public Markets

### IPO Map and IPO Pipeline

The IPO Map shows recent listings sized by market capitalization and colored by
performance. Filters cover geography, exchange, sector, and other attributes. The IPO
Pipeline tracks private candidates and upcoming calendar entries.

![IPO Map](../screenshots/15-ipo-map.png)

### Prospectus Builder

Choose uploaded PDF, XLSX, or PPTX materials, extract prospectus sections with AI, edit
the fields, and generate a formatted PDF.

### SPAC Tracker

Track searching, announced, completed, and liquidated SPACs. Review trust values,
redemptions, lifecycle charts, prices, targets, and institutional holders.

![SPAC Tracker](../screenshots/17-spacs.png)

### SEC Filings

Search EDGAR filings, inspect filings and XBRL data, ask the Filing Analyst questions,
and export the workspace overview to PDF.

### Press Release Intelligence

Search releases by keyword, ticker, event type, and look-back period. Read full items,
review predicted market direction when available, run aggregate analysis, and export
the release view to PDF.

---

## Hedge Fund Intelligence

The Fund Treemap visualizes SEC Form 13F positions by portfolio value. Search managers,
set minimum position sizes, adjust result limits, and bookmark funds. Chat shortcuts
surface top holdings, popular securities, portfolio concentration, and Schedule 13D/13G
activist activity.

![Hedge Fund Treemap](../screenshots/16-hedgefunds.png)

---

## Free public tools

The public Tools menu provides three no-sign-in workflows:

- **Market Comparables** — scrape a company site and benchmark relevant transaction multiples.
- **Find Buyers** — identify and score strategic and financial buyers.
- **Business Valuation** — combine financial inputs with sector multiples and value drivers.

Financial fields accept shorthand such as `1M`, `500k`, and `2.5B`.

---

## Workspace

### Companies and company profiles

Search company data by name, sector, and geography. Open detailed profiles, financials,
deal briefs, and company-level CSV/PDF exports.

### Pipelines

Maintain target and buyer pipelines, add items, and move them between stages.

### Deal Radar, Methodology, and Data Coverage

Deal Radar ranks buyer-target synergy pairs and target opportunities. Methodology
documents the weighted scoring model. Data Coverage reports country coverage and supports
manual synchronization of Estonian, Norwegian, and Danish company sources.

### Valuation

Use EV/Revenue, EV/EBITDA, DCF, and combined valuation views with adjustable assumptions.

### Analytics

Ask database questions in plain language and receive tables and charts. Export analytics
documentation to PDF.

### Data Room and Documents

Upload, download, organize, and remove PDF, DOCX, XLSX, PPTX, CSV, image, and text files.
The document agents can parse content, extract terms, and use workspace documents in analysis.
Investor Relations drafts saved from the Press Release Creator appear here.

### Deal History and Daily Deals

Review prior workflows and status charts. Generate, send, preview, and export Daily Deals
digests that combine company scans, synergy pairs, public-market intelligence, and a deep dive.

---

## Skills

Open **Workspace → Skills** at `/app/skills` to review and edit the operating skill for
each registered agent. The editor supports WYSIWYG and Markdown modes, version history,
and reverting. Saved changes clear the agent cache and take effect immediately.

The legacy `/app/instructions` address permanently redirects to Skills.

Investor Relations is represented by five prominently listed skills: **IR Event Triage**,
**Press Release Writer**, **IR Compliance Reviewer**, **IR Publish Agent**, and **IR
Distribution Planner** — each containing research rules, disclosure frameworks, factual
safeguards, tone requirements, and compliance guidance.

---

## Exports and generated documents

LiquidRound supports:

- XLSX exports for structured tables
- DOCX exports for Markdown-based documents
- Branded PDF exports across workspace pages
- CSV and PDF company exports
- Press-release Markdown, Word, and PDF downloads
- In-pane PDF previews for supported work products

Generated documents should be reviewed by the responsible transaction, legal, compliance,
or investor-relations owner before external use.

---

## Account and configuration

Profile settings cover account details, password, preferred currency, buyer/seller role,
deal preferences, and digest notifications. Supported working currencies include EUR,
GBP, and USD.

---

## Training and help

**Deal Street** provides scenario-based training. Help includes Profile/Account, this
User Guide, Scoring Methodology, and agent shortcut references.

Keyboard controls:

- **Enter** — send a chat message.
- **Shift+Enter** — insert a new line.

---

## Demo checklist

- Confirm the user is signed in before demonstrating persistence or Data Room save.
- Start with the Investor Relations creator and use a real, researchable company topic.
- Review source notes and verification placeholders before presenting the draft as final.
- Export the same draft to Markdown, Word, and PDF.
- Save the draft and open it from the Data Room.
- Run `ir-triage:` on a hypothetical material event to show disclosure go/no-go analysis.
- Run `ir-publish:` to show the wire-ready package and pre-publish checklist.
- Contrast `releases:` historical intelligence with `write-release:` creation.
- Show Skills and open the Press Release Writer skill.
- Finish with a public-markets page and an agent-produced artifact.

---

## Document control

This document was generated from the platform state inspected on **2026-07-28**.
Prior guide editions are stored under `docs/archive/`. The repeatable
`regenerate-liquidround-demo` skill archives prior outputs, audits current routes and
agents, refreshes this source guide, and produces timestamped Markdown, PDF, and PPTX
editions.

LiquidRound v0.5.1 — Predictive Labs Ltd
