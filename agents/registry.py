"""Central registry of all LiquidRound specialist agents.

Each `AgentSpec` is the source of truth for:
  - Routing (prefix, keywords)
  - UI rendering (landing /agents page, in-app agent browser)
  - Prompt loading (prompts/system/<slug>.md)

Agents are tagged with `audience` (buyer | seller | shared) so the landing
page and the in-app nav can filter by the user's current role.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Audience = Literal["buyer", "seller", "shared"]


@dataclass(frozen=True)
class AgentSpec:
    slug: str
    name: str
    category: str        # sourcing | underwriting | diligence | capital | portfolio
    audience: Audience   # buyer | seller | shared
    icon: str            # unicode glyph for UI
    one_liner: str       # marketing sub-heading (short)
    description: str     # full sentence for /agents page
    prefix: str          # router prefix (e.g. "triage:")
    example_prompts: tuple[str, ...] = field(default_factory=tuple)


CATEGORIES: list[dict] = [
    {
        "key": "sourcing",
        "name": "Deal Sourcing & Screening",
        "blurb": "Surface acquisition targets and qualified buyers before they hit auction.",
        "icon": "◉",
    },
    {
        "key": "underwriting",
        "name": "Valuation & Underwriting",
        "blurb": "From a ticker to an IC-ready valuation in minutes.",
        "icon": "◈",
    },
    {
        "key": "diligence",
        "name": "Due Diligence Stack",
        "blurb": "VDR audited, contracts abstracted, risks surfaced early.",
        "icon": "◆",
    },
    {
        "key": "capital",
        "name": "Deal Execution & Capital",
        "blurb": "Teasers, CIMs, IC memos and IPO readiness — all in one workspace.",
        "icon": "◐",
    },
    {
        "key": "portfolio",
        "name": "Research & Post-Deal",
        "blurb": "Deep research, integration planning and match scoring.",
        "icon": "◼",
    },
    {
        "key": "public_markets",
        "name": "Public Markets & Hedge Funds",
        "blurb": "SEC 13F filings, institutional ownership, activist stakes.",
        "icon": "◉",
    },
    {
        "key": "investor_relations",
        "name": "Investor Relations & Communications",
        "blurb": "Triage material events, draft and publish disclosure-compliant press releases.",
        "icon": "✉",
    },
]


AGENTS: tuple[AgentSpec, ...] = (
    # ─────────────────────────────────────────────────────────────────────
    # Deal Sourcing & Screening (4)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="target_scanner", name="Target Scanner",
        category="sourcing", audience="buyer", icon="⚯", prefix="scan:",
        one_liner="Find acquisition targets by sector, geography, size — ranked by fit.",
        description="Scans public markets and proprietary databases for acquisition candidates matching a buyer's mandate. Returns a short list ranked by strategic fit, size, and acquirability.",
        example_prompts=(
            "scan: renewable energy targets in the Nordics, EUR 50-200M EV",
            "Find founder-owned SaaS companies in DACH with $5-15M EBITDA",
            "What healthcare services targets surfaced this week?",
            "Find Baltic industrial manufacturers under EUR 100M revenue",
        ),
    ),
    AgentSpec(
        slug="buyer_scanner", name="Buyer Scanner",
        category="sourcing", audience="seller", icon="⚒", prefix="buyers:",
        one_liner="Identify strategic + financial buyers for a sell-side process.",
        description="Maps the buyer universe for a sale process: strategic acquirers, PE sponsors, family offices. Ranks by check-size fit, mandate alignment, and historical activity.",
        example_prompts=(
            "buyers: SaaS company with EUR 15M revenue, EU-based, recurring contracts",
            "Find strategic buyers for a Baltic renewable energy platform",
            "Who are the active PE sponsors in mid-market European industrials?",
            "Identify buyers for a Nordic fintech with EUR 50M GMV",
        ),
    ),
    AgentSpec(
        slug="deal_triage", name="Deal Triage",
        category="sourcing", audience="shared", icon="✓", prefix="triage:",
        one_liner="Go / no-go in 90 seconds against your investment mandate.",
        description="Screens a deal against buyer or seller criteria — size, sector, geography, growth, margin — and returns a go/no-go with a 3-bullet rationale.",
        example_prompts=(
            "triage: vertical SaaS, $8M EBITDA, 20% growth, $85M ask",
            "Triage a Baltic renewable platform for a Nordic strategic",
            "Go/no-go on a $45M EV HCIT platform with 14% growth",
            "Should we pursue the Meridian carve-out at EUR 120M EV?",
        ),
    ),
    AgentSpec(
        slug="seller_intent", name="Seller Intent Signal",
        category="sourcing", audience="buyer", icon="∿", prefix="intent:",
        one_liner="Rank companies by likelihood of sale in the next 12 months.",
        description="Uses founder age, fund vintage, sponsor hold period, hiring signals, and regulatory filings to score candidates by likelihood of entering a sale process.",
        example_prompts=(
            "intent: founder-owned logistics companies, EUR 50-150M revenue, Baltics",
            "Which sponsor-owned industrials are past the 5-year hold mark?",
            "Rank founder-owned Nordic software firms by sale likelihood",
            "Show family-owned consumer businesses with succession risk in Europe",
        ),
    ),

    # ─────────────────────────────────────────────────────────────────────
    # Valuation & Underwriting (6)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="company_profiler", name="Company Profiler",
        category="underwriting", audience="shared", icon="☰", prefix="profile:",
        one_liner="Ticker → clean profile: business model, financials, industry.",
        description="Pulls a live company profile from real-time market data: business model, key products, markets, market cap, revenue, EBITDA, margins, and sector multiples.",
        example_prompts=(
            "profile: SAP.DE",
            "profile: NOVO-B.CO",
            "Profile Siemens (SIE.DE)",
            "Get company details for TAL1T.TL",
        ),
    ),
    AgentSpec(
        slug="comps_finder", name="Transaction Comps Finder",
        category="underwriting", audience="shared", icon="≡", prefix="comps:",
        one_liner="Precedent M&A and trading comps with outlier filtering.",
        description="Pulls precedent M&A transactions and public trading comparables from multiple sources, filters outliers, and returns a tight set for EV/EBITDA and EV/Revenue benchmarking.",
        example_prompts=(
            "comps: SaaS M&A precedents 2022-2024, <EUR 500M EV",
            "Find trading comps for a mid-market Nordic industrial",
            "What's the median EV/EBITDA for European HCIT deals?",
            "Benchmark EV/Revenue for specialty distributors in Europe",
        ),
    ),
    AgentSpec(
        slug="ltm_normalizer", name="LTM Financials Normalizer",
        category="underwriting", audience="shared", icon="∑", prefix="ltm:",
        one_liner="Messy seller financials → clean, add-back-adjusted LTM EBITDA.",
        description="Normalizes seller-provided financials onto a standard chart of accounts, applies quality-of-earnings add-backs, separates one-time items, and flags anomalies vs. industry benchmarks.",
        example_prompts=(
            "ltm: normalize the LTM P&L for NovaTech with standard add-backs",
            "Show the add-back bridge from reported to adjusted EBITDA",
            "Compare NovaTech EBITDA margin to SaaS peer median",
            "Revenue growth CAGR for NovaTech over the last 24 months",
        ),
    ),
    AgentSpec(
        slug="dcf_valuer", name="DCF Valuer",
        category="underwriting", audience="shared", icon="▤", prefix="dcf:",
        one_liner="Discounted cash flow with sensitivity to WACC and terminal growth.",
        description="Builds a 5-year DCF model with explicit-period forecasts, terminal value, and sensitivity to WACC and terminal growth. Outputs implied equity value and an EV range.",
        example_prompts=(
            "dcf: value Harju Elekter at 9% WACC and 2.5% terminal growth",
            "Build a DCF for Enefit Green with downside scenarios",
            "What's Baltic Horizon Fund's implied equity value at 10% WACC?",
            "Sensitivity grid: WACC 8-11% x TGR 1.5-3% for TAL1T",
        ),
    ),
    AgentSpec(
        slug="multiples_valuer", name="Multiples Valuer",
        category="underwriting", audience="shared", icon="▥", prefix="multi:",
        one_liner="EV/EBITDA and EV/Revenue across precedents and peers.",
        description="Applies sector peer and precedent transaction multiples to the target's LTM financials, producing an EV range with bridge to equity value through net debt.",
        example_prompts=(
            "multi: value TAL1T at peer-median EV/EBITDA",
            "What's the EV range for Enefit Green using renewable-energy precedents?",
            "Compare SAP-implied EV using software peers vs precedents",
            "Apply industrial distributor multiples to Harju Elekter",
        ),
    ),
    AgentSpec(
        slug="synergy_analyst", name="Synergy Analyst",
        category="underwriting", audience="shared", icon="◈", prefix="synergy:",
        one_liner="Revenue, cost and operational synergies — quantified.",
        description="Quantifies revenue (cross-sell, pricing, geographic expansion) and cost synergies (overhead, procurement, systems) between a specific buyer and target. Returns dollar/EUR ranges and timelines.",
        example_prompts=(
            "synergy: Siemens + Harju Elekter",
            "Quantify revenue synergies for SAP acquiring NovaTech",
            "What cost synergies exist between Enefit and Ignitis?",
            "Build a 3-year synergy realization plan for the Meridian deal",
        ),
    ),

    # ─────────────────────────────────────────────────────────────────────
    # Due Diligence Stack (5)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="vdr_auditor", name="VDR Auditor",
        category="diligence", audience="buyer", icon="☷", prefix="vdr:",
        one_liner="Cross-checks the data room against a 140-item DD checklist.",
        description="Audits the seller's virtual data room against a comprehensive M&A diligence checklist, flagging missing documents, stale versions, and internal inconsistencies across legal, financial, commercial, and tech workstreams.",
        example_prompts=(
            "vdr: audit the NovaTech data room",
            "Which DD items are missing in the Meridian VDR?",
            "What's still outstanding on tax and legal for the Baltic deal?",
            "Compare VDR completeness across my top 3 active deals",
        ),
    ),
    AgentSpec(
        slug="contract_abstractor", name="Contract Abstractor",
        category="diligence", audience="shared", icon="▢", prefix="abstract:",
        one_liner="Contracts → structured abstracts with key terms and page citations.",
        description="Abstracts PDF contracts (customer MSAs, supplier agreements, employment contracts, IP licenses) into structured records — term, renewal, change-of-control, exclusivity, termination — with cited page references.",
        example_prompts=(
            "abstract: the top-10 customer MSAs for NovaTech",
            "Any change-of-control triggers across NovaTech's supplier contracts?",
            "List auto-renew + exclusivity clauses across top customers",
            "Which contracts expire in the next 12 months?",
        ),
    ),
    AgentSpec(
        slug="legal_reviewer", name="Legal & Regulatory Reviewer",
        category="diligence", audience="shared", icon="◰", prefix="legal:",
        one_liner="Litigation, regulatory, and change-of-control consents — flagged.",
        description="Parses corporate minute books, litigation searches, and regulatory filings. Flags material breaches, open litigation, licensure gaps, and change-of-control consents required at close.",
        example_prompts=(
            "legal: summarize legal issues for NovaTech",
            "Any GDPR or licensing gaps flagged on the Baltic deal?",
            "Which change-of-control consents are required at close?",
            "Open litigation above EUR 1M exposure at NovaTech",
        ),
    ),
    AgentSpec(
        slug="operational_dd", name="Operational Diligence Reviewer",
        category="diligence", audience="buyer", icon="⌂", prefix="ops:",
        one_liner="Reads operational DD + QoE, builds a 100-day plan.",
        description="Reads operational reviews, quality-of-earnings reports, and process maps. Extracts working-capital drag, systems gaps, and unit economics. Outputs a 100-day post-close value-creation plan.",
        example_prompts=(
            "ops: what operational gaps are flagged for NovaTech?",
            "Build a 100-day plan for Meridian post-close",
            "Where is working capital tied up at NovaTech?",
            "What ERP/systems gaps need remediation post-close?",
        ),
    ),
    AgentSpec(
        slug="esg_reviewer", name="ESG & Compliance Risk Flagger",
        category="diligence", audience="buyer", icon="⚠", prefix="esg:",
        one_liner="Environmental, social, governance — risks surfaced early.",
        description="Reads ESG disclosures, environmental site assessments, worker-safety records and governance reports. Identifies exposures and recommends scope where further review is warranted.",
        example_prompts=(
            "esg: environmental liabilities at the Baltic industrial deal",
            "ESG risk summary across my current pipeline",
            "What governance red flags were flagged for NovaTech?",
            "Any diversity / turnover risks at the target?",
        ),
    ),

    # ─────────────────────────────────────────────────────────────────────
    # Deal Execution & Capital (5)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="ic_memo_writer", name="IC Memo Writer",
        category="capital", audience="buyer", icon="✎", prefix="memo:",
        one_liner="Full IC memo — exec summary, thesis, risks, returns.",
        description="Drafts a full investment-committee memo — exec summary, thesis, market, financials, value creation, risks, returns — from the deal's data in your workspace.",
        example_prompts=(
            "memo: draft the IC memo for Harju Elekter",
            "Write a 5-page IC memo for the NovaTech acquisition",
            "Build the thesis + risks sections for Meridian",
            "Summarize the returns analysis for the IC pre-read",
        ),
    ),
    AgentSpec(
        slug="teaser_designer", name="Teaser & CIM Designer",
        category="capital", audience="seller", icon="✦", prefix="teaser:",
        one_liner="Blind teaser + full CIM positioning — buyer-ready.",
        description="Generates a branded blind teaser and a full confidential information memorandum (CIM) — cover, market opportunity, financials, management, value drivers, process timeline — for sell-side distribution.",
        example_prompts=(
            "teaser: build a blind teaser for NovaTech",
            "Draft the executive summary section of the NovaTech CIM",
            "Create a 1-page tombstone for the deal announcement",
            "Build the management biographies for the CIM",
        ),
    ),
    AgentSpec(
        slug="bid_strategist", name="Bid Strategist",
        category="capital", audience="buyer", icon="◈", prefix="bid:",
        one_liner="Deal structure: cash vs stock, escrow, earnouts, risk allocation.",
        description="Designs bid strategy and deal structure — cash vs. stock mix, earnouts, escrow, reps & warranties insurance, change-of-control, break fees. Produces a term-sheet outline with negotiation levers.",
        example_prompts=(
            "bid: design a structure for a EUR 150M deal with 30% earnout",
            "Propose escrow and R&W for the NovaTech acquisition",
            "What cash/stock mix maximizes IRR on the Meridian deal?",
            "Draft the key-term outline for an initial IOI",
        ),
    ),
    AgentSpec(
        slug="ipo_readiness", name="IPO Readiness Assessor",
        category="capital", audience="seller", icon="⇡", prefix="ipo:",
        one_liner="Financial, governance, operational readiness for a listing.",
        description="Assesses IPO readiness across four pillars: financial (reporting, audits, internal controls), governance (board, policies), operational (systems, scalability), and market (timing, comparables, investor demand).",
        example_prompts=(
            "ipo: assess Ignitis Group for a Nasdaq Baltic listing",
            "IPO readiness review for a SaaS platform",
            "What's the gap analysis for a Nordic fintech going public?",
            "Timeline and workstreams for an 18-month IPO path",
        ),
    ),
    AgentSpec(
        slug="match_scorer", name="Match Scorer",
        category="capital", audience="shared", icon="◎", prefix="score:",
        one_liner="Score a buyer-target match across 7 synergy dimensions.",
        description="Scores a specific buyer-target pair across revenue synergies, cost synergies, strategic fit, cultural fit, financial health, integration risk, and market timing. Returns a composite score with recommendation: STRONG BUY, PROCEED, CAUTIOUS, PASS.",
        example_prompts=(
            "score buyer:Siemens target:Harju Elekter",
            "Score SAP as a buyer for NovaTech",
            "score doc:NovaTech-Pitch-Deck.pdf",
            "Score a strategic match between Enefit and Ignitis",
        ),
    ),

    # ─────────────────────────────────────────────────────────────────────
    # Research & Post-Deal (2)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="research_analyst", name="Deep Research Analyst",
        category="portfolio", audience="shared", icon="⌬", prefix="research:",
        one_liner="Real-time deep research across web, filings, and industry sources.",
        description="Runs deep research across real-time semantic and web search. Returns a synthesized summary with cited sources covering market context, competitive landscape, and recent news.",
        example_prompts=(
            "research: Baltic M&A trends in renewable energy 2024",
            "Deep research on European HCIT consolidation",
            "Competitive landscape for Nordic fintech unicorns",
            "Recent news and signals on Enefit Green",
        ),
    ),
    AgentSpec(
        slug="integration_planner", name="Integration & 100-Day Planner",
        category="portfolio", audience="buyer", icon="⚒", prefix="integrate:",
        one_liner="Post-close integration plan with milestones and owners.",
        description="Builds a post-close integration plan with day-one actions, 30-60-90 day milestones, and a 100-day value-creation roadmap. Assigns workstream owners and tracks synergy realization.",
        example_prompts=(
            "integrate: build a 100-day plan for Siemens + Harju Elekter",
            "Day-one readiness checklist for the NovaTech acquisition",
            "Integration workstream map for a cross-border EU deal",
            "Synergy tracking plan for the Meridian integration",
        ),
    ),

    # ─────────────────────────────────────────────────────────────────────
    # Public Markets & Hedge Funds (4)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="hedge_fund_analyst", name="Hedge Fund Analyst",
        category="public_markets", audience="shared", icon="◉", prefix="hedgefunds:",
        one_liner="SEC 13F filings — fund holdings, market concentration, activist stakes.",
        description="Analyses SEC Form 13F quarterly filings: fund AUM rankings, portfolio holdings, security popularity across institutional investors, market concentration metrics, and Schedule 13D/13G activist filings.",
        example_prompts=(
            "hedgefunds: top 20 funds by AUM",
            "hedgefunds: what does Berkshire Hathaway hold?",
            "hedgefunds: which funds own Apple and what are they long vs short?",
            "hedgefunds: recent 13D activist filings — any new campaigns worth watching?",
            "hedgefunds: most concentrated portfolios — which funds have the highest conviction bets?",
            "hedgefunds: what are the most popular tech stocks among hedge funds?",
        ),
    ),
    AgentSpec(
        slug="filing_analyst", name="Filing Analyst",
        category="public_markets", audience="shared", icon="▤", prefix="filings:",
        one_liner="SEC EDGAR filing search and analysis — 10-K, 10-Q, 8-K, proxy, XBRL.",
        description="Search and analyze SEC EDGAR filings — 10-K, 10-Q, 8-K, proxy statements. Ask questions about any public company's regulatory filings.",
        example_prompts=(
            "filings: AAPL 10-K filings",
            "filings: search for 'material weakness' in recent 10-K filings",
            "filings: show me MSFT's latest proxy statement",
            "filings: XBRL financial data for TSLA",
            "What did Apple disclose in their most recent 8-K?",
            "Search SEC filings for goodwill impairment disclosures",
        ),
    ),
    AgentSpec(
        slug="press_release_analyst", name="Press Release Analyst",
        category="public_markets", audience="shared", icon="◩", prefix="releases:",
        one_liner="Search and analyze 390K+ press releases from GlobeNewswire, Euronext, and Nordic exchanges.",
        description="Search and analyze 390K+ press releases from GlobeNewswire, PR Newswire, Nasdaq Nordic/Baltic, and Euronext. Filter by company, event type, or ask analytical questions.",
        example_prompts=(
            "releases: recent M&A announcements in the Nordics",
            "releases: earnings releases for NOVO-B.CO",
            "What press releases has Enefit Green issued this quarter?",
            "releases: clinical study announcements in biotech last 90 days",
            "How many press releases were issued by Euronext companies this month?",
            "releases: management changes at Baltic companies",
        ),
    ),
    AgentSpec(
        slug="reverse_merger_analyst", name="Reverse Merger Analyst",
        category="public_markets", audience="shared", icon="⇄", prefix="rto:",
        one_liner="US reverse mergers, Canadian RTOs and SPAC/de-SPAC comparison.",
        description="Discovers and analyzes reverse mergers from SEC EDGAR, compares them with SPAC/de-SPAC transactions, and evaluates reviewed Canadian RTO and CPC records.",
        example_prompts=(
            "rto: recent US reverse mergers in the last 90 days",
            "rto: compare traditional reverse mergers with de-SPACs",
            "rto: show completed Canadian RTO and CPC transactions",
            "Analyze shell, dilution and seasoning risks for this reverse merger",
        ),
    ),
    # ─────────────────────────────────────────────────────────────────────
    # Investor Relations & Communications (5)
    # ─────────────────────────────────────────────────────────────────────
    AgentSpec(
        slug="ir_triage", name="IR Event Triage",
        category="investor_relations", audience="shared", icon="⚖", prefix="ir-triage:",
        one_liner="Is this material enough to disclose? Go / no-go against disclosure rules.",
        description="Triages an incoming event, news item, or rumor against materiality thresholds and disclosure obligations (EU MAR, US Reg FD, exchange rules). Returns a go / no-go on whether a press release is required, with a rationale, urgency window, and recommended disclosure channel.",
        example_prompts=(
            "ir-triage: our CFO resigned unexpectedly — do we need to disclose?",
            "ir-triage: a competitor just filed a patent infringement suit against us",
            "ir-triage: we missed Q3 guidance by 8% — material?",
            "ir-triage: a major customer notified us they are switching suppliers",
        ),
    ),
    AgentSpec(
        slug="press_release_writer", name="Press Release Writer",
        category="investor_relations", audience="shared", icon="✦", prefix="write-release:",
        one_liner="Research a topic and draft a publication-ready investor relations press release.",
        description="Researches companies and current developments on the web, then drafts factual, publication-ready investor relations releases with headlines, quotes, boilerplates, contacts, and source notes.",
        example_prompts=(
            "write-release: draft a partnership announcement for Acme and Northstar",
            "Create an investor relations release about our new CEO appointment",
            "Research Enefit Green and draft a release about a new solar project",
            "Draft a product launch press release with a quote from the CEO",
        ),
    ),
    AgentSpec(
        slug="ir_compliance", name="IR Compliance Reviewer",
        category="investor_relations", audience="shared", icon="⚠", prefix="ir-compliance:",
        one_liner="Reg FD / MAR / exchange disclosure check before publish.",
        description="Reviews a draft press release for compliance with US Reg FD, EU MAR (Market Abuse Regulation), and major exchange disclosure rules (Nasdaq Nordic/Baltic, NYSE, Euronext). Flags selective disclosure risks, forward-looking statement shortfalls, missing cautionary language, and inside-information handling issues.",
        example_prompts=(
            "ir-compliance: check this draft earnings release for Reg FD issues",
            "ir-compliance: review our CEO appointment release for MAR compliance",
            "ir-compliance: does this M&A release meet Nasdaq Stockholm disclosure rules?",
            "ir-compliance: flag any selective disclosure risks in this draft",
        ),
    ),
    AgentSpec(
        slug="ir_publish", name="IR Publish Agent",
        category="investor_relations", audience="shared", icon="⇒", prefix="ir-publish:",
        one_liner="Approved draft → final publication-ready release with formatting and checklist.",
        description="Takes an approved draft press release and produces the final publication-ready artifact: exchange-compliant formatting, wire-service fields (headline, subhead, dateline, body, about, contacts), a pre-publish checklist (embargo timing, exchange notification, investor list, website posting), and a distribution-ready package.",
        example_prompts=(
            "ir-publish: finalize the approved Q3 earnings release",
            "ir-publish: produce the final wire-ready package for the CEO appointment",
            "ir-publish: format this M&A release for GlobeNewswire submission",
            "ir-publish: generate the pre-publish checklist for our product launch release",
        ),
    ),
    AgentSpec(
        slug="ir_distribute", name="IR Distribution Planner",
        category="investor_relations", audience="shared", icon="☂", prefix="ir-distribute:",
        one_liner="Distribution plan — wire services, exchanges, investor lists, timing.",
        description="Plans the distribution of a finalized press release: wire-service routing (GlobeNewswire, PR Newswire, Business Wire), exchange notifications (Nasdaq, Euronext, NYSE), investor and analyst contact lists, media targeting, social/website posting schedule, and embargo/timing strategy across time zones.",
        example_prompts=(
            "ir-distribute: plan distribution for our Q3 earnings release across Nordic exchanges",
            "ir-distribute: which wire service should we use for a Euronext-listed company?",
            "ir-distribute: build the investor contact list for our M&A announcement",
            "ir-distribute: schedule a cross-timezone release for a US + Nordic dual-listed company",
        ),
    ),
)


# ─── Lookups ──────────────────────────────────────────────────────────────

AGENTS_BY_SLUG: dict[str, AgentSpec] = {a.slug: a for a in AGENTS}
AGENTS_BY_CATEGORY: dict[str, list[AgentSpec]] = {}
for _a in AGENTS:
    AGENTS_BY_CATEGORY.setdefault(_a.category, []).append(_a)


def all_agents() -> tuple[AgentSpec, ...]:
    return AGENTS


def by_slug(slug: str) -> AgentSpec | None:
    return AGENTS_BY_SLUG.get(slug)


def by_audience(audience: str) -> list[AgentSpec]:
    if audience not in ("buyer", "seller"):
        return list(AGENTS)
    return [a for a in AGENTS if a.audience == audience or a.audience == "shared"]


assert len(AGENTS) == 31, f"expected 31 agents, got {len(AGENTS)}"
