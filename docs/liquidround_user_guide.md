---
title: LiquidRound User Guide
subtitle: AI-Powered M&A and IPO Platform
version: v0.3.0
date: June 2026
author: Predictive Labs Ltd
---

<div class="cover">

# ◈ LiquidRound

**AI-Powered M&A and IPO Platform**

Your ECM / IB analyst squad — 22 specialist AI agents across sourcing, underwriting, diligence, capital markets, and portfolio management.

*Version 0.3.0 — June 2026*

*Predictive Labs Ltd*

</div>

---

## Getting Started

LiquidRound is a dual-mode platform for both sides of M&A and IPO deals:

- **Buyers** — find acquisition targets, run diligence, score deals, and draft IC memos
- **Sellers** — prepare for sale (teasers, CIMs), identify potential buyers, and assess IPO readiness

### Accessing the Platform

![Landing page](../screenshots/guide-01-landing.png)

1. Visit [liquidround.ai](https://liquidround.ai)
2. Choose your role: **Buyer-Led** or **Seller-Led**
3. Start chatting with the AI agent squad — no sign-up required for basic use
4. **Sign in** (optional) for persistent conversations, sharing, and full features

### Language Support

LiquidRound supports four languages via the flag dropdown in the navigation bar:

- 🇬🇧 **English** (default)
- 🇪🇪 **Eesti** (Estonian)
- 🇱🇹 **Lietuvių** (Lithuanian)
- 🇱🇻 **Latviešu** (Latvian)

Click the flag icon in the top-right corner of the navigation bar to switch languages. The interface, navigation, and tool labels update instantly.

---

## Free Tools

LiquidRound provides three free lead-magnet tools — no sign-in required. Each tool follows a simple 3-step flow: enter your company website, provide financials, and get instant AI-powered results.

### Market Comparables

![Market Comps tool](../screenshots/guide-02-comps-tool.png)

The **Market Comparables** tool benchmarks your company against industry M&A transaction multiples using Damodaran's dataset (96 revenue sectors, 92 EBITDA sectors).

**How to use:**

1. Enter your company website URL and click **Analyse**
2. The AI scrapes your website, identifies your sector, and pre-fills company details
3. Enter your financials: **Revenue**, **Pre-tax Profit**, and **Owner Salary** (EUR)
4. Click **Calculate Comparables** to see:
   - **Sector M&A snapshot** — median EV/Revenue and EV/EBITDA multiples for your industry
   - **Estimated valuation range** — based on your financials applied to sector multiples
   - **Key value drivers** — AI-generated analysis of what drives (or discounts) value in your sector

> **Tip:** The tool uses Damodaran's industry classification. If your sector seems off, check that your website clearly describes your core business.

---

### Find Buyers

![Find Buyers tool](../screenshots/guide-03-match-tool.png)

The **Find Buyers** tool matches your company with potential acquirers using a hybrid approach: Baltic company databases (Estonia, Lithuania, Latvia) combined with AI-powered web research.

**How to use:**

1. Enter your company website URL and click **Analyse**
2. Review the AI-extracted company profile (sector, sub-sector, products, end markets)
3. Click **Find Buyers** to see matched potential acquirers:
   - **3 full buyer profiles** with AI-generated match rationale
   - **Strategic fit analysis** — why each buyer would be interested
   - **Source** — whether the match came from Baltic registry data or web research

**Data sources:**

| Country | Companies | Source |
|---------|-----------|--------|
| Estonia | ~60,000 | Estonian Business Registry |
| Lithuania | ~166,000 | Lithuanian Registry Centre |
| Latvia | ~3,600,000 | Latvian Enterprise Register |

The tool combines sector/sub-sector matching from these databases with Tavily web research to find both local strategic buyers and international PE firms.

---

### Business Valuation

![Valuation tool](../screenshots/guide-04-valuation-tool.png)

The **Business Valuation** tool provides a multi-method valuation estimate using industry-standard approaches.

**How to use:**

1. Enter your company website URL and click **Analyse**
2. Enter financials: **Revenue**, **Pre-tax Profit**, and **Owner Salary** (EUR)
3. Click **Calculate Valuation** to see a 3-step result:

**Step 1 — Deal Comparables:**
Sector transaction multiples (EV/Revenue, EV/EBITDA) from Damodaran's dataset, applied to your financials.

**Step 2 — Value Drivers:**
AI-identified factors that positively or negatively affect your company's valuation — recurring revenue, market position, concentration risk, growth trajectory.

**Step 3 — Valuation Range:**
Combined estimate showing low/mid/high enterprise values based on multiple methods (SDE, EBITDA multiples, revenue multiples).

> **Tip:** All amounts are in EUR. The valuation is indicative — a full engagement produces a detailed report with sensitivity analysis.

---

## Industry Pages

![Industries overview](../screenshots/guide-05-industries.png)

LiquidRound provides sector-specific landing pages with tailored M&A context, sub-sector breakdowns, and regional advisor connections.

### Available Industries

| Industry | URL | Sub-sectors |
|----------|-----|-------------|
| **Technology & SaaS** | `/industries/technology` | Enterprise SaaS, FinTech, E-Commerce, IT Services |
| **Manufacturing** | `/industries/manufacturing` | Precision Engineering, Food & Beverage, Building Materials, Industrial Automation |
| **Healthcare** | `/industries/healthcare` | HealthTech / Digital, Medical Devices, Pharmaceutical, Clinical Services |
| **Business Services** | `/industries/business-services` | Management Consulting, Accounting & Legal, HR & Staffing, Marketing & Digital |

### What Each Industry Page Includes

![Industry detail page](../screenshots/guide-06-industry-detail.png)

- **Sector overview** — M&A landscape, typical deal characteristics, and market trends
- **Sub-sector cards** — four specialist categories with descriptions
- **Regional advisors** — direct links to local M&A advisory partners:
  - 🇱🇹 Lithuania → [Orion Corporate Finance](https://www.orion.lt)
  - 🇪🇪 Estonia → [Superia](https://superia.ee)
- **FAQ section** — sector-specific questions about selling, valuation, and timelines
- **Inline buyer search** — enter a URL directly from the industry page to find matched buyers

---

## The Chat Application

![App chat interface](../screenshots/guide-07-app-chat.png)

The core of LiquidRound is the 3-pane chat application at `/app`. It provides a conversational interface to the full ECM Agent Squad.

### Layout

- **Left pane** — Sessions, Agents directory, Tools links, Workspace, Configuration
- **Center pane** — Chat messages with the AI agent squad
- **Right pane** — Artifact canvas (Documents, Research, Scores, Compare tabs)

### Choosing a Role

When you first enter the app, choose **Buyer-Led** or **Seller-Led**. This controls:

- Which welcome cards and suggested prompts appear
- Which agent chips are surfaced
- Which nav section opens by default

You can switch roles anytime via the **Configuration** widget (type `settings` in chat).

### Chat Commands

LiquidRound supports two ways to interact:

**Legacy command prefixes** (direct, structured output):

| Command | Example | What it does |
|---------|---------|--------------|
| `profile:` | `profile:MSFT` | Company profile card |
| `financials:` | `financials:AAPL` | Financial summary table |
| `news:` | `news:TSLA` | Recent news aggregation |
| `valuation:` | `valuation:NVDA` | Multi-method valuation |
| `targets` | `targets industry:fintech` | Target search by criteria |
| `buyers` | `buyers sector:saas` | Buyer search |
| `score` | `score buyer:X target:Y` | 7-dimension deal scoring |
| `keyterms` | `keyterms filename.pdf` | Key terms extraction from documents |

**Natural language** — just describe what you need. The AI router picks the best specialist agent automatically.

---

## ECM Agent Squad

![Agent directory](../screenshots/guide-08-agents.png)

LiquidRound's AI backbone is the **ECM Agent Squad** — 22 specialist agents organized into 5 workflow categories.

### Agent Categories

#### Sourcing (4 agents)

| Agent | Prefix | Purpose |
|-------|--------|---------|
| Deal Scanner | `scan:` | Screen M&A pipeline, filter by criteria |
| Triage Analyst | `triage:` | Rapid initial assessment of targets |
| Intent Mapper | `intent:` | Map strategic buyer intent and themes |
| Comps Analyst | `comps:` | Comparable transactions analysis |

#### Underwriting (6 agents)

| Agent | Prefix | Purpose |
|-------|--------|---------|
| LTM Builder | `ltm:` | Last-twelve-months financials construction |
| DCF Modeller | `dcf:` | Discounted cash flow analysis |
| Multiples Analyst | `multi:` | Trading and transaction multiples |
| Synergy Analyst | `synergy:` | Revenue and cost synergy quantification |
| Bid Strategist | `bid:` | Bid pricing and negotiation strategy |
| Integration Planner | `integrate:` | Post-merger integration planning |

#### Diligence (5 agents)

| Agent | Prefix | Purpose |
|-------|--------|---------|
| VDR Analyst | `vdr:` | Virtual data room document review |
| Abstract Writer | `abstract:` | Executive summary generation |
| Legal Reviewer | `legal:` | Legal risk identification |
| Ops Analyst | `ops:` | Operational due diligence |
| ESG Analyst | `esg:` | ESG and sustainability assessment |

#### Capital Markets (5 agents)

| Agent | Prefix | Purpose |
|-------|--------|---------|
| IC Memo Writer | `memo:` | Investment committee memo drafting |
| Teaser Builder | `teaser:` | One-page teaser creation |
| CIM Drafter | — | Confidential information memorandum |
| IPO Readiness | — | IPO readiness assessment |
| Pitch Deck | — | Pitch deck content generation |

#### Portfolio (2 agents)

| Agent | Prefix | Purpose |
|-------|--------|---------|
| Portfolio Monitor | — | Track portfolio company performance |
| Exit Planner | — | Exit strategy and timing analysis |

### Using Specialist Agents

You can invoke a specialist agent in two ways:

1. **Prefix syntax** — type the prefix followed by your query:
   ```
   scan: find SaaS companies in Nordics with >€5M ARR
   dcf: build a DCF for Bolt Technology
   memo: draft IC memo for the Wise acquisition
   ```

2. **Natural language** — the AI router automatically selects the best agent:
   ```
   What are the comparable transactions for enterprise SaaS in Europe?
   Help me prepare a teaser for selling my consulting firm
   ```

---

## Documents and Research

### Uploading Documents

Upload PDFs, Excel files, and PowerPoint presentations directly in the chat. Supported formats:

- **PDF** — extracted via pdfplumber (text, tables)
- **XLSX** — parsed via openpyxl (all sheets, formulas evaluated)
- **PPTX** — parsed via python-pptx (slide text, notes)

Type `docs` in chat to see your uploaded documents, or `keyterms filename.pdf` to extract key terms from a specific file.

### Research Tools

The platform integrates two research engines:

- **EXA** — semantic search for finding conceptually similar content
- **Tavily** — web search with advanced depth for comprehensive coverage

Type `research topic` to trigger a deep research pass, or let agents invoke research tools automatically when answering complex questions.

---

## Scoring and Valuation

### Deal Scoring

Type `score buyer:CompanyA target:CompanyB` to generate a 7-dimension radar chart:

1. **Strategic Fit** — alignment of business models and markets
2. **Financial Health** — target's financial stability and growth
3. **Synergy Potential** — revenue and cost synergy opportunities
4. **Market Position** — competitive positioning and market share
5. **Management Quality** — leadership team assessment
6. **Cultural Fit** — organizational compatibility
7. **Risk Profile** — regulatory, operational, and market risks

### In-App Valuation

Type `valuation:TICKER` for a quick multi-method valuation using:

- DCF (discounted cash flow)
- EV/Revenue multiples
- EV/EBITDA multiples
- EV/EBIT multiples

The valuation uses Damodaran's sector-specific cost of capital, country risk premiums, and current market data from yfinance.

---

## Sharing and Collaboration

### Shared Chat Links

Logged-in users can share any conversation:

1. Click the **Share** button in the chat header
2. A unique URL is generated and copied to your clipboard
3. Anyone with the link can view the conversation (read-only, no auth required)

### PDF Export

After generating an IC Memo or Teaser, the platform offers PDF export:

1. The memo renders in the right-pane canvas
2. Click **Download PDF** to get a professionally formatted document
3. PDFs are content-addressed (identical memos reuse cached files)

---

## Account and Settings

### Sign In

![Sign-in page](../screenshots/guide-signin.png)

LiquidRound supports two authentication methods:

- **Google OAuth** — one-click sign-in with your Google account
- **Email + Password** — traditional registration with email verification

Sign in at [liquidround.ai/signin](https://liquidround.ai/signin). Registration is at `/register`. Password reset is available via `/forgot`.

### Profile Settings

After signing in, access your profile at `/profile` to configure:

- **Account info** — name, email, company
- **M&A preferences** — deal size range, target sectors, geographic focus
- **Notifications** — daily digest email opt-in/opt-out

### Daily Digest

LiquidRound sends a daily M&A digest email with:

- **Featured deals** — AI-curated deal opportunities matching your preferences
- **Market insights** — sector trends and notable transactions
- **Company spotlights** — deep-dive analysis on featured targets

The digest runs automatically (configurable: daily, weekly, or off). Opt in/out via Profile settings.

---

## Configuration

### Switching Roles

Type `settings` in chat to open the Configuration widget. From there you can switch between **Buyer** and **Seller** modes, which adjusts the agent selection, welcome prompts, and nav defaults.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in message |
| `Ctrl+K` | Focus chat input |

### URL Parameters

| Parameter | Values | Effect |
|-----------|--------|--------|
| `role` | `buyer`, `seller` | Set initial role mode |

Example: `liquidround.ai/app?role=seller` opens the app in seller mode.

---

## Support

**Predictive Labs Ltd**

- Website: [liquidround.ai](https://liquidround.ai)
- Contact: [liquidround.ai/contact](https://liquidround.ai/contact)
- Email: info@liquidround.com

For regional M&A advisory:

- 🇱🇹 Lithuania: [Orion Corporate Finance](https://www.orion.lt)
- 🇪🇪 Estonia: [Superia](https://superia.ee)

---

<div class="cover">

# Thank You

**LiquidRound** — Your AI ECM Agent Squad for M&A and IPO

[liquidround.ai](https://liquidround.ai)

*© 2026 Predictive Labs Ltd. All rights reserved.*

</div>
