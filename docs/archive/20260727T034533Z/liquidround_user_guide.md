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

![Landing page](../screenshots/guide-01-landing.png)

LiquidRound is a dual-mode platform for both sides of M&A and IPO deals:

- **Buyers** — find acquisition targets, run diligence, score deals, and draft IC memos
- **Sellers** — prepare for sale (teasers, CIMs), identify potential buyers, and assess IPO readiness

**Accessing the Platform:**

1. Visit [liquidround.ai](https://liquidround.ai)
2. Choose your role: **Buyer-Led** or **Seller-Led**
3. Start chatting with the AI agent squad — no sign-up required for basic use
4. **Sign in** (optional) for persistent conversations, sharing, and full features

**Language Support** — four languages via the flag dropdown in the top-right corner:
🇬🇧 English (default) · 🇪🇪 Eesti · 🇱🇹 Lietuvių · 🇱🇻 Latviešu.
Click the flag icon to switch. The interface, navigation, and tool labels update instantly.

---

## Free Tool: Market Comparables

![Market Comps results](../screenshots/guide-comps-results.png)

The **Market Comparables** tool benchmarks your company against industry M&A transaction multiples using Damodaran's dataset (96 revenue sectors, 92 EBITDA sectors). No sign-in required.

**How to use:**

1. Enter your company website URL and click **Analyse**
2. The AI scrapes your website, identifies your sector, and pre-fills company details
3. Enter your financials: **Revenue**, **Pre-tax Profit**, and **Owner Salary** (EUR)
4. Click **Calculate Comparables** to see:
   - **Sector M&A snapshot** — median EV/Revenue and EV/EBITDA multiples for your industry
   - **Estimated valuation range** — based on your financials applied to sector multiples
   - **Key value drivers** — AI-generated analysis of what drives (or discounts) value in your sector

The tool uses Damodaran's industry classification. If your sector seems off, check that your website clearly describes your core business.

---

## Free Tool: Find Buyers

![Find Buyers results](../screenshots/guide-match-results.png)

The **Find Buyers** tool matches your company with potential acquirers using a hybrid approach: Baltic company databases (Estonia, Lithuania, Latvia) combined with AI-powered web research.

**How to use:**

1. Enter your company website URL and click **Analyse**
2. Review the AI-extracted company profile (sector, sub-sector, products, end markets)
3. Click **Find Buyers** to see matched potential acquirers:
   - **3 full buyer profiles** with AI-generated match rationale
   - **Strategic fit analysis** — why each buyer would be interested
   - **Source** — whether the match came from Baltic registry data or web research

**Data sources:** Estonia (~60K companies), Lithuania (~166K), Latvia (~3.6M) — sourced from national business registries. Combined with Tavily web research to find both local strategic buyers and international PE firms.

---

## Free Tool: Business Valuation

![Valuation results](../screenshots/guide-valuation-results.png)

The **Business Valuation** tool provides a multi-method valuation estimate using industry-standard approaches. No sign-in required. All amounts are in EUR.

**How to use:**

1. Enter your company website URL and click **Analyse**
2. Enter financials: **Revenue**, **Pre-tax Profit**, and **Owner Salary** (EUR)
3. Click **Calculate Valuation** to see a 3-step result:

**Step 1 — Deal Comparables:** Sector transaction multiples (EV/Revenue, EV/EBITDA) from Damodaran's dataset, applied to your financials.

**Step 2 — Value Drivers:** AI-identified factors that positively or negatively affect your company's valuation — recurring revenue, market position, concentration risk, growth trajectory.

**Step 3 — Valuation Range:** Combined estimate showing low/mid/high enterprise values based on multiple methods (SDE, EBITDA multiples, revenue multiples). The valuation is indicative — a full engagement produces a detailed report with sensitivity analysis.

---

## Industry Pages

![Technology industry page](../screenshots/guide-industry-tech.png)

LiquidRound provides sector-specific landing pages with tailored M&A context, sub-sector breakdowns, and regional advisor connections. Four industries covered:

- **Technology & SaaS** — Enterprise SaaS, FinTech, E-Commerce, IT Services
- **Manufacturing** — Precision Engineering, Food & Beverage, Building Materials, Industrial Automation
- **Healthcare** — HealthTech / Digital, Medical Devices, Pharmaceutical, Clinical Services
- **Business Services** — Management Consulting, Accounting & Legal, HR & Staffing, Marketing & Digital

**Each industry page includes:** sector overview and M&A landscape, four sub-sector cards, regional advisor links (🇱🇹 [Orion Corporate Finance](https://www.orion.lt) · 🇪🇪 [Superia](https://superia.ee)), sector-specific FAQs (5 per industry), and an inline buyer search widget.

---

## The Chat Application

![App chat interface](../screenshots/guide-07-app-chat.png)

The core of LiquidRound is the 3-pane chat application at `/app`:

- **Left pane** — Sessions, Agents directory, Tools links, Workspace, Configuration
- **Center pane** — Chat messages with the AI agent squad
- **Right pane** — Artifact canvas (Documents, Research, Scores, Compare tabs)

**Choosing a Role:** Select **Buyer-Led** or **Seller-Led** at entry. This controls which welcome cards, suggested prompts, and agent chips appear. Switch anytime via the **Configuration** widget (type `settings` in chat).

**Chat Commands** — type a prefix like `profile:MSFT`, `financials:AAPL`, `valuation:NVDA`, `targets industry:fintech`, `score buyer:X target:Y`, `keyterms report.pdf`, `news:TSLA`, `buyers sector:saas`, `research`, `docs`, `settings`, `help`, or `clear`. Or just use **natural language** — the AI router picks the best specialist agent automatically.

---

## ECM Agent Squad (22 Agents)

![Agent directory](../screenshots/guide-08-agents.png)

LiquidRound's AI backbone is the **ECM Agent Squad** — 22 specialist agents organized into 5 categories. Invoke via prefix (e.g. `scan: find SaaS in Nordics >€5M ARR`) or natural language.

**Sourcing (4):** `scan:` Deal Scanner · `triage:` Triage Analyst · `intent:` Intent Mapper · `comps:` Comps Analyst

**Underwriting (6):** `ltm:` LTM Builder · `dcf:` DCF Modeller · `multi:` Multiples Analyst · `synergy:` Synergy Analyst · `bid:` Bid Strategist · `integrate:` Integration Planner

**Diligence (5):** `vdr:` VDR Analyst · `abstract:` Abstract Writer · `legal:` Legal Reviewer · `ops:` Ops Analyst · `esg:` ESG Analyst

**Capital Markets (5):** `memo:` IC Memo Writer · `teaser:` Teaser Builder · CIM Drafter · IPO Readiness · Pitch Deck

**Portfolio (2):** Portfolio Monitor · Exit Planner

---

## Documents, Research & Scoring

**Uploading Documents** — upload PDFs, Excel, and PowerPoint files directly in the chat:

- **PDF** — text and table extraction (pdfplumber)
- **XLSX** — all sheets parsed (openpyxl)
- **PPTX** — slide text and notes (python-pptx)

Type `docs` to list uploads, `keyterms filename.pdf` to extract key terms.

**Research Tools** — two integrated engines:

- **EXA** — semantic search for conceptually similar content
- **Tavily** — web search with advanced depth for comprehensive coverage

Type `research topic` for a deep research pass, or let agents invoke tools automatically.

**Deal Scoring** — type `score buyer:CompanyA target:CompanyB` for a 7-dimension radar:
Strategic Fit · Financial Health · Synergy Potential · Market Position · Management Quality · Cultural Fit · Risk Profile.

**In-App Valuation** — type `valuation:TICKER` for multi-method analysis:
DCF · EV/Revenue · EV/EBITDA · EV/EBIT — using Damodaran sector data and yfinance market data.

---

## Account, Sharing & Settings

![Sign-in page](../screenshots/guide-signin.png)

**Sign In** — two authentication methods:

- **Google OAuth** — one-click sign-in
- **Email + Password** — traditional registration

Visit [liquidround.ai/signin](https://liquidround.ai/signin) to sign in, `/register` to create an account, `/forgot` to reset your password.

**Profile Settings** (at `/profile`):

- **Account info** — name, email, company
- **M&A preferences** — deal size range, target sectors, geographic focus
- **Notifications** — daily digest email opt-in/opt-out

**Daily Digest** — automated M&A intelligence email with featured deals, market insights, and company spotlights. Configurable: daily, weekly, or off.

**Sharing** — click **Share** in the chat header to generate a read-only link. Anyone with the link can view the conversation (no auth required).

**PDF Export** — after generating an IC Memo or Teaser, click **Download PDF** for a professionally formatted document. **Shortcuts:** `Enter` to send, `Shift+Enter` for new line. URL param `?role=seller` starts the app in seller mode.

---

## Support

**Predictive Labs Ltd**

- Website: [liquidround.ai](https://liquidround.ai)
- Contact: [liquidround.ai/contact](https://liquidround.ai/contact)
- Email: info@liquidround.com

**Regional M&A Advisory:**

- 🇱🇹 Lithuania: [Orion Corporate Finance](https://www.orion.lt)
- 🇪🇪 Estonia: [Superia](https://superia.ee)

---

<div class="cover">

# Thank You

**LiquidRound** — Your AI ECM Agent Squad for M&A and IPO

[liquidround.ai](https://liquidround.ai)

*© 2026 Predictive Labs Ltd. All rights reserved.*

</div>
