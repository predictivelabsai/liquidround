"""
API routes for HTMX endpoints — chat, scoring, research, company lookup, Phase 8 mocks.
"""
import asyncio, json, uuid, time
from fasthtml.common import *
from components.chat import ChatMessage, AgentProgress
from components.cards import TargetCard, ScoreCard, MetricCard
from components.research_panel import ResearchPanel
from components.charts import RadarChart

ar = APIRouter()


# ---------------------------------------------------------------------------
# Chat endpoint (Phase 7)
# ---------------------------------------------------------------------------
@ar
async def chat(msg: str = ""):
    """Process a chat message, run the workflow, return results."""
    if not msg:
        return P("Please enter a query.", cls="text-sm text-red-500")

    workflow_id = str(uuid.uuid4())[:8]
    parts = [ChatMessage("user", msg)]

    # Determine workflow type from keywords
    query_lower = msg.lower()
    if any(w in query_lower for w in ["find target", "acquire", "acquisition", "buy"]):
        wf_type = "buyer_ma"
    elif any(w in query_lower for w in ["sell", "buyer for", "find buyer", "merger"]):
        wf_type = "seller_ma"
    elif any(w in query_lower for w in ["ipo", "public", "listing"]):
        wf_type = "ipo"
    elif any(w in query_lower for w in ["score", "match", "synergy"]):
        wf_type = "score"
    else:
        wf_type = "buyer_ma"

    # Run research in background
    research_data = {}
    try:
        from utils.research_tools import research_tools
        research_data = await research_tools.deep_research(msg)
        from routes.research import store_research
        store_research(workflow_id, research_data)
    except Exception as e:
        research_data = {"error": str(e)}

    # Run the appropriate workflow
    try:
        from utils.llm_factory import create_llm
        llm = create_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        system_prompts = {
            "buyer_ma": "You are an M&A advisor helping identify acquisition targets. Provide specific, actionable company recommendations with reasoning. Format your response with clear sections.",
            "seller_ma": "You are an M&A advisor helping sellers find strategic and financial buyers. Identify likely acquirers with reasoning.",
            "ipo": "You are a capital markets advisor assessing IPO readiness. Evaluate across financial, governance, operational, and market dimensions.",
            "score": "You are an M&A scoring analyst. Evaluate the deal across synergy dimensions.",
        }

        messages = [
            SystemMessage(content=system_prompts.get(wf_type, system_prompts["buyer_ma"])),
            HumanMessage(content=msg),
        ]
        response = await llm.ainvoke(messages)
        result_text = response.content

        parts.append(AgentProgress("orchestrator", "completed", f"Routed to {wf_type}", 0.3))
        parts.append(AgentProgress("research", "completed",
                                   f"EXA: {len(research_data.get('exa', {}).get('results', []))} results, "
                                   f"Tavily: {len(research_data.get('tavily', {}).get('results', []))} results",
                                   research_data.get('exa', {}).get('elapsed', 0)))

        if wf_type == "score":
            # Try to run scoring agent
            try:
                from agents.scoring_agent import ScoringAgent
                from utils.state import create_initial_state
                state = create_initial_state("buyer_ma", msg)
                scorer = ScoringAgent()
                state = await scorer.execute(state)
                score_result = state["agent_results"].get("scoring", {}).get("result", {})
                if score_result and "dimensions" in score_result:
                    parts.append(AgentProgress("scoring", "completed", f"Composite: {score_result.get('composite_score', 'N/A')}/100", 2.0))
                    parts.append(ScoreCard(score_result))
                    parts.append(RadarChart("score-radar", score_result.get("dimensions", {})))
                else:
                    parts.append(ChatMessage("assistant", result_text))
            except Exception as e:
                parts.append(ChatMessage("assistant", result_text))
        else:
            parts.append(AgentProgress(wf_type.replace("_", " "), "completed", "Analysis complete", 1.5))
            parts.append(ChatMessage("assistant", result_text))

    except Exception as e:
        parts.append(ChatMessage("assistant", f"Error: {str(e)}. Check your API keys in .env"))

    # Update research panel via OOB swap
    research_html = ResearchPanel(research_data) if research_data and "error" not in research_data else Div(P(f"Research error: {research_data.get('error', 'unknown')}", cls="text-sm text-red-500 p-4"))
    parts.append(
        Div(research_html, id="research-content", hx_swap_oob="innerHTML")
    )

    return Div(*parts)


# ---------------------------------------------------------------------------
# Company lookup (Phase 6)
# ---------------------------------------------------------------------------
@ar("/api/company-profile")
def company_profile(ticker: str = ""):
    """Look up company via yfinance."""
    if not ticker:
        return P("Enter a ticker symbol.", cls="text-sm text-gray-500")
    from utils.yfinance_util import yfinance_util
    profile = yfinance_util.get_company_profile(ticker)
    financials = yfinance_util.get_financials(ticker)

    if "error" in profile:
        return P(f"Error: {profile['error']}", cls="text-sm text-red-500")

    def _fmt(n):
        if not n: return "N/A"
        if n >= 1e9: return f"${n/1e9:.1f}B"
        if n >= 1e6: return f"${n/1e6:.1f}M"
        return f"${n:,.0f}"

    return Div(
        H2(f"{profile['name']} ({profile['ticker']})", cls="text-xl font-bold text-gray-800 mb-2"),
        Div(
            Span(profile.get("sector", ""), cls="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded"),
            Span(profile.get("industry", ""), cls="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded"),
            Span(profile.get("country", ""), cls="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded"),
            cls="flex gap-2 mb-4",
        ),
        P(profile.get("description", ""), cls="text-sm text-gray-600 mb-4"),
        Div(
            MetricCard("Market Cap", _fmt(profile.get("market_cap")), color="blue"),
            MetricCard("Revenue", _fmt(financials.get("revenue")), color="green"),
            MetricCard("EBITDA", _fmt(financials.get("ebitda")), color="green"),
            MetricCard("Employees", f"{profile.get('employees', 0):,}" if profile.get("employees") else "N/A"),
            MetricCard("EV/EBITDA", f"{financials.get('ev_to_ebitda', 0):.1f}x" if financials.get("ev_to_ebitda") else "N/A", color="yellow"),
            MetricCard("Revenue Growth", f"{financials.get('revenue_growth', 0)*100:.1f}%" if financials.get("revenue_growth") else "N/A", color="green"),
            cls="grid grid-cols-3 gap-4",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


# ---------------------------------------------------------------------------
# Scoring endpoint (Phase 4)
# ---------------------------------------------------------------------------
@ar("/api/score-match")
async def score_match(buyer: str = "", target: str = "", context: str = ""):
    """Run the scoring agent on a buyer-target pair."""
    query = f"Score the acquisition match: Buyer={buyer}, Target={target}. Context: {context}"
    if not buyer and not target:
        return P("Please provide buyer and target.", cls="text-sm text-red-500")

    try:
        from agents.scoring_agent import ScoringAgent
        from utils.state import create_initial_state
        state = create_initial_state("buyer_ma", query)
        state["deal"]["company_name"] = target
        scorer = ScoringAgent()
        state = await scorer.execute(state)
        result = state["agent_results"].get("scoring", {}).get("result", {})
        if result and "dimensions" in result:
            return Div(
                ScoreCard(result),
                RadarChart("score-radar-main", result.get("dimensions", {})),
                Div(
                    H3("Key Risks", cls="text-sm font-semibold text-red-700 mt-4 mb-2"),
                    Ul(*[Li(r, cls="text-sm text-gray-600") for r in result.get("key_risks", [])], cls="list-disc ml-4"),
                    H3("Next Steps", cls="text-sm font-semibold text-blue-700 mt-4 mb-2"),
                    Ul(*[Li(s, cls="text-sm text-gray-600") for s in result.get("next_steps", [])], cls="list-disc ml-4"),
                    cls="bg-white rounded-lg p-4 border border-gray-200 mt-4",
                ),
            )
        return P("Scoring completed but could not parse results.", cls="text-sm text-yellow-600")
    except Exception as e:
        return P(f"Scoring error: {e}", cls="text-sm text-red-500")


# ---------------------------------------------------------------------------
# Target finder endpoint (Phase 7)
# ---------------------------------------------------------------------------
@ar("/api/find-targets")
async def find_targets(industry: str = "", revenue: str = "", geography: str = "", criteria: str = ""):
    """Run target finding workflow."""
    query = f"Find acquisition targets in {industry} with {revenue} revenue in {geography}. {criteria}"
    try:
        from utils.llm_factory import create_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = create_llm()
        messages = [
            SystemMessage(content="You are an M&A advisor. Identify 8-10 specific acquisition targets matching the criteria. For each target provide: company name, estimated revenue, sector, strategic fit score (1-5), and investment highlights. Format as a clear numbered list."),
            HumanMessage(content=query),
        ]
        response = await llm.ainvoke(messages)
        return Div(
            H2("Target Search Results", cls="text-lg font-semibold text-gray-800 mb-3"),
            Div(NotStr(f"<div class='prose prose-sm max-w-none text-gray-700'>{_md_to_html(response.content)}</div>"), cls="bg-white rounded-lg p-4 border border-gray-200"),
        )
    except Exception as e:
        return P(f"Error: {e}", cls="text-sm text-red-500")


@ar("/api/find-buyers")
async def find_buyers(company: str = "", revenue: str = "", description: str = ""):
    """Run buyer finding workflow."""
    query = f"Find strategic and financial buyers for: {company} ({revenue}). {description}"
    try:
        from utils.llm_factory import create_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = create_llm()
        messages = [
            SystemMessage(content="You are an M&A sell-side advisor. Identify 8-10 likely strategic and financial buyers. For each provide: buyer name, rationale, estimated interest level (1-5), and approach strategy."),
            HumanMessage(content=query),
        ]
        response = await llm.ainvoke(messages)
        return Div(
            H2("Potential Buyers", cls="text-lg font-semibold text-gray-800 mb-3"),
            Div(NotStr(f"<div class='prose prose-sm max-w-none text-gray-700'>{_md_to_html(response.content)}</div>"), cls="bg-white rounded-lg p-4 border border-gray-200"),
        )
    except Exception as e:
        return P(f"Error: {e}", cls="text-sm text-red-500")


@ar("/api/ipo-assess")
async def ipo_assess(company: str = "", industry: str = "", context: str = ""):
    """Run IPO readiness assessment."""
    query = f"Assess IPO readiness for {company} in {industry}. {context}"
    try:
        from utils.llm_factory import create_llm
        from langchain_core.messages import HumanMessage, SystemMessage
        llm = create_llm()
        messages = [
            SystemMessage(content="You are an IPO readiness advisor. Evaluate across: Financial Readiness, Corporate Governance, Operational Maturity, Market Conditions. Score each 1-10 and provide specific recommendations."),
            HumanMessage(content=query),
        ]
        response = await llm.ainvoke(messages)
        return Div(
            H2("IPO Readiness Assessment", cls="text-lg font-semibold text-gray-800 mb-3"),
            Div(NotStr(f"<div class='prose prose-sm max-w-none text-gray-700'>{_md_to_html(response.content)}</div>"), cls="bg-white rounded-lg p-4 border border-gray-200"),
        )
    except Exception as e:
        return P(f"Error: {e}", cls="text-sm text-red-500")


# ---------------------------------------------------------------------------
# Phase 8: Mocked M&A Platform Tools
# ---------------------------------------------------------------------------
@ar
def tools():
    """Phase 8: M&A tools dashboard (mocked)."""
    from components.layout import Shell
    tools_list = [
        ("Deal Room", "Virtual data room for secure document sharing and access control", "Available", "green"),
        ("CIM Generator", "Auto-generate Confidential Information Memorandum from uploaded docs", "Available", "green"),
        ("Comparable Transactions", "Database of historical M&A transactions for benchmarking", "Available", "green"),
        ("LOI / Term Sheet Drafter", "AI-generated Letter of Intent and term sheet templates", "Available", "green"),
        ("Due Diligence Checklist", "Auto-generated DD checklist based on deal type and industry", "Available", "green"),
        ("Regulatory Screening", "Antitrust/regulatory risk assessment (HSR filing thresholds)", "Beta", "yellow"),
        ("Stakeholder Mapping", "Map board members, investors, advisors for target companies", "Beta", "yellow"),
        ("Integration Playbook", "Post-merger integration plan generator", "Beta", "yellow"),
        ("Pipeline CRM", "Track deal stages, contacts, next actions (Kanban board)", "Coming Soon", "gray"),
        ("Valuation Sensitivity", "Interactive sensitivity tables (entry multiple x growth rate)", "Coming Soon", "gray"),
        ("Market Sizing (TAM)", "TAM/SAM/SOM analysis for target's market", "Coming Soon", "gray"),
        ("Pitch Deck Builder", "Auto-generate buyer/seller pitch decks from deal data", "Coming Soon", "gray"),
        ("Email Outreach", "Templated outreach to targets/buyers with mail merge", "Planned", "gray"),
        ("Calendar / Timeline", "Deal timeline with milestones and deadlines", "Planned", "gray"),
        ("Benchmarking Dashboard", "Compare target metrics against industry medians", "Planned", "gray"),
    ]
    cards = []
    for name, desc, status, color in tools_list:
        s_cls = {"green": "bg-green-100 text-green-700", "yellow": "bg-yellow-100 text-yellow-700", "gray": "bg-gray-100 text-gray-500"}.get(color, "bg-gray-100 text-gray-500")
        cards.append(
            Div(
                Div(
                    H3(name, cls="font-semibold text-gray-800"),
                    Span(status, cls=f"text-xs px-2 py-0.5 rounded-full font-medium {s_cls}"),
                    cls="flex items-center justify-between mb-2",
                ),
                P(desc, cls="text-sm text-gray-600"),
                Button("Launch", cls="mt-3 text-sm bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed",
                       hx_get=f"/mock-tool/{name.lower().replace(' ', '-').replace('/', '-')}",
                       hx_target="#tool-output",
                       disabled=status in ("Coming Soon", "Planned")),
                cls="bg-white rounded-lg p-4 border border-gray-200",
            )
        )
    return Shell(
        H1("M&A Platform Tools", cls="text-2xl font-bold text-gray-800 mb-2"),
        P("Extended toolkit for end-to-end M&A advisory workflow.", cls="text-gray-500 mb-6"),
        Div(*cards, cls="grid grid-cols-3 gap-4 mb-6"),
        Div(id="tool-output", cls="mt-4"),
    )


@ar("/mock-tool/{tool_name}")
async def mock_tool(tool_name: str = ""):
    """Run a mocked Phase 8 tool."""
    mocks = {
        "deal-room": _mock_deal_room,
        "cim-generator": _mock_cim_generator,
        "comparable-transactions": _mock_comparable_transactions,
        "loi---term-sheet-drafter": _mock_loi_drafter,
        "due-diligence-checklist": _mock_dd_checklist,
        "regulatory-screening": _mock_regulatory,
        "stakeholder-mapping": _mock_stakeholder,
        "integration-playbook": _mock_integration,
    }
    handler = mocks.get(tool_name)
    if handler:
        return handler()
    return P(f"Tool '{tool_name}' is not yet available.", cls="text-sm text-gray-500 italic")


# --- Phase 8 mock implementations ---

def _mock_deal_room():
    files = [
        ("CIM_Acme_Corp_2026.pdf", "PDF", "12.4 MB", "Uploaded 2h ago"),
        ("Financial_Model_v3.xlsx", "XLSX", "2.1 MB", "Uploaded 1d ago"),
        ("Board_Presentation.pptx", "PPTX", "8.7 MB", "Uploaded 3d ago"),
        ("Due_Diligence_Report.pdf", "PDF", "5.3 MB", "Uploaded 5d ago"),
        ("Customer_Contracts_Summary.xlsx", "XLSX", "1.8 MB", "Uploaded 1w ago"),
    ]
    rows = [Tr(Td(f, cls="py-2 text-sm"), Td(t, cls="py-2 text-xs bg-gray-100 px-2 rounded text-center"), Td(s, cls="py-2 text-sm text-gray-500"), Td(d, cls="py-2 text-xs text-gray-400")) for f, t, s, d in files]
    return Div(
        H2("Deal Room", cls="text-lg font-semibold text-gray-800 mb-3"),
        P("Secure virtual data room for document sharing.", cls="text-sm text-gray-500 mb-4"),
        Table(
            Thead(Tr(Th("Document", cls="text-left py-2 text-sm"), Th("Type", cls="py-2 text-sm"), Th("Size", cls="py-2 text-sm"), Th("Uploaded", cls="py-2 text-sm"))),
            Tbody(*rows),
            cls="w-full",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_cim_generator():
    return Div(
        H2("CIM Generator", cls="text-lg font-semibold text-gray-800 mb-3"),
        P("Auto-generated Confidential Information Memorandum outline:", cls="text-sm text-gray-500 mb-4"),
        Div(
            *[Div(
                Span(f"Section {i}", cls="text-xs font-bold text-blue-700"),
                P(section, cls="text-sm text-gray-700"),
                cls="border-l-2 border-blue-300 pl-3 py-1",
            ) for i, section in enumerate([
                "Executive Summary — Company overview, investment highlights, and transaction rationale",
                "Business Description — Products/services, business model, competitive advantages",
                "Market Overview — TAM/SAM/SOM, industry trends, competitive landscape",
                "Financial Overview — Historical P&L, balance sheet, cash flow (3-year)",
                "Growth Strategy — Organic and inorganic growth initiatives",
                "Management Team — Key executives and organizational structure",
                "Transaction Summary — Indicative valuation, process timeline, next steps",
            ], 1)],
            cls="space-y-3",
        ),
        Button("Generate Full CIM (Mock)", cls="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_comparable_transactions():
    txns = [
        ("Broadcom / VMware", "2023", "$61B", "Technology", "12.5x"),
        ("Microsoft / Activision", "2023", "$69B", "Gaming", "14.2x"),
        ("Thoma Bravo / Coupa", "2023", "$8B", "Enterprise SaaS", "10.1x"),
        ("Vista Equity / Citrix", "2022", "$16.5B", "Enterprise SaaS", "8.7x"),
        ("Oracle / Cerner", "2022", "$28.3B", "Healthcare IT", "6.2x"),
        ("Salesforce / Slack", "2021", "$27.7B", "Collaboration", "26.8x"),
    ]
    rows = [Tr(*[Td(v, cls="py-2 text-sm") for v in t]) for t in txns]
    return Div(
        H2("Comparable Transactions", cls="text-lg font-semibold text-gray-800 mb-3"),
        Table(
            Thead(Tr(*[Th(h, cls="text-left py-2 text-sm font-medium text-gray-500") for h in ["Deal", "Year", "Value", "Sector", "EV/Revenue"]])),
            Tbody(*rows),
            cls="w-full",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_loi_drafter():
    return Div(
        H2("LOI / Term Sheet Draft", cls="text-lg font-semibold text-gray-800 mb-3"),
        Div(
            P("LETTER OF INTENT", cls="text-center font-bold text-lg mb-4"),
            *[Div(P(f"**{k}:** {v}", cls="text-sm text-gray-700"), cls="mb-2") for k, v in [
                ("Parties", "[Buyer Name] and [Target Name]"),
                ("Purchase Price", "$[XX]M, subject to customary adjustments"),
                ("Structure", "100% stock acquisition / asset purchase"),
                ("Consideration", "Cash at closing, [XX]% seller note, [XX]% earnout"),
                ("Due Diligence Period", "60 days from execution"),
                ("Exclusivity", "90-day no-shop period"),
                ("Key Conditions", "Board approval, regulatory clearance, financing"),
                ("Break Fee", "[X]% of purchase price"),
            ]],
            cls="bg-gray-50 rounded-lg p-6 font-mono text-sm",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_dd_checklist():
    categories = {
        "Financial": ["Audited financials (3 years)", "Tax returns and compliance", "Revenue breakdown by customer/product", "Working capital analysis", "Debt schedule and covenants"],
        "Legal": ["Corporate structure and org chart", "Material contracts and agreements", "Pending/threatened litigation", "IP portfolio and registrations", "Regulatory licenses and permits"],
        "Commercial": ["Customer concentration analysis", "Sales pipeline and backlog", "Competitive positioning", "Pricing strategy and trends", "Key account references"],
        "Technology": ["Tech stack and architecture", "Code quality and technical debt", "Security audit and compliance", "Scalability assessment", "Key technology dependencies"],
        "HR & Culture": ["Org chart and key employees", "Compensation and benefits summary", "Employee turnover rates", "Non-compete/non-solicit agreements", "Cultural assessment"],
    }
    sections = []
    for cat, items in categories.items():
        checks = [Div(
            Input(type="checkbox", cls="mr-2 rounded border-gray-300"),
            Span(item, cls="text-sm text-gray-700"),
            cls="flex items-center py-1",
        ) for item in items]
        sections.append(Div(H3(cat, cls="font-semibold text-gray-800 mb-2"), *checks, cls="mb-4"))
    return Div(
        H2("Due Diligence Checklist", cls="text-lg font-semibold text-gray-800 mb-3"),
        *sections,
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_regulatory():
    return Div(
        H2("Regulatory Screening", cls="text-lg font-semibold text-gray-800 mb-3"),
        Div(
            _reg_item("HSR Filing", "Required if deal value > $119.5M (2026 threshold)", "yellow"),
            _reg_item("CFIUS Review", "Recommended if target has US government contracts or sensitive tech", "yellow"),
            _reg_item("EU Merger Control", "Required if combined EU turnover > EUR 5B", "green"),
            _reg_item("UK CMA", "Voluntary notification recommended if UK turnover > GBP 70M", "green"),
            _reg_item("Antitrust Risk", "LOW — combined market share likely < 25%", "green"),
            cls="space-y-3",
        ),
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_stakeholder():
    people = [
        ("Jane Smith", "CEO, Target Co", "Key decision maker — 15yr tenure, founded company"),
        ("Bob Chen", "CFO, Target Co", "Running the process — former Goldman VP"),
        ("Sarah Johnson", "Board Chair", "Independent — also serves on 2 other boards"),
        ("PE Fund Alpha", "35% Shareholder", "Looking for exit — 5yr hold, 3.2x MOIC target"),
        ("Lazard", "Sell-side Advisor", "Managing the process — MD: Tom Wilson"),
    ]
    return Div(
        H2("Stakeholder Map", cls="text-lg font-semibold text-gray-800 mb-3"),
        *[Div(
            Div(Span(name, cls="font-semibold text-gray-800"), Span(f" — {role}", cls="text-sm text-gray-500")),
            P(note, cls="text-xs text-gray-600 mt-1"),
            cls="border-b border-gray-100 pb-3 mb-3",
        ) for name, role, note in people],
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _mock_integration():
    phases = [
        ("Day 1-30: Stabilize", ["Announce deal and communicate to employees", "Retain key talent with stay bonuses", "Identify quick wins and synergy capture plan", "Set up integration management office (IMO)"]),
        ("Day 30-90: Integrate", ["Align organizational structures", "Consolidate vendor contracts", "Begin IT system integration planning", "Cross-train sales teams"]),
        ("Day 90-180: Optimize", ["Execute technology platform migration", "Rationalize product portfolio", "Implement unified reporting", "Track synergy realization vs plan"]),
        ("Day 180-365: Scale", ["Achieve run-rate cost synergies", "Launch cross-sell initiatives", "Unified brand and go-to-market", "Full operational integration"]),
    ]
    return Div(
        H2("Integration Playbook", cls="text-lg font-semibold text-gray-800 mb-3"),
        *[Div(
            H3(phase, cls="font-semibold text-blue-700 mb-2"),
            Ul(*[Li(s, cls="text-sm text-gray-700") for s in steps], cls="list-disc ml-4 space-y-1"),
            cls="mb-4",
        ) for phase, steps in phases],
        cls="bg-white rounded-lg p-6 border border-gray-200",
    )


def _reg_item(name, detail, color):
    c = {"green": "bg-green-100 text-green-700", "yellow": "bg-yellow-100 text-yellow-700", "red": "bg-red-100 text-red-700"}.get(color, "bg-gray-100")
    return Div(
        Div(Span(name, cls="font-medium text-gray-800"), cls="flex items-center gap-2"),
        P(detail, cls=f"text-sm mt-1 {c.split()[1] if ' ' in c else 'text-gray-600'}"),
        cls=f"rounded-lg p-3 {c.split()[0] if ' ' in c else c}",
    )


def _md_to_html(text):
    """Simple markdown to HTML conversion."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'^### (.+)$', r'<h3 class="font-semibold text-gray-800 mt-3 mb-1">\1</h3>', text, flags=re.M)
    text = re.sub(r'^## (.+)$', r'<h2 class="text-lg font-semibold text-gray-800 mt-4 mb-2">\1</h2>', text, flags=re.M)
    text = re.sub(r'^# (.+)$', r'<h1 class="text-xl font-bold text-gray-800 mt-4 mb-2">\1</h1>', text, flags=re.M)
    text = re.sub(r'^\d+\.\s+(.+)$', r'<li class="text-sm text-gray-700 ml-4">\1</li>', text, flags=re.M)
    text = re.sub(r'^[-*]\s+(.+)$', r'<li class="text-sm text-gray-700 ml-4">\1</li>', text, flags=re.M)
    text = text.replace('\n\n', '<br><br>').replace('\n', '<br>')
    return text
