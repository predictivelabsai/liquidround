"""
Render Agent — builds FastHTML components server-side based on command type.
Handles structured commands (profile:MSFT) and free-form chat.
Streams results back as HTML partials for HTMX swap.
"""
import json, time, asyncio
from typing import Optional
from fasthtml.common import *

from utils.command_parser import parse_command, get_help_text
from utils.config import config


class RenderAgent:
    """Processes user input and returns FastHTML components."""

    async def process(self, user_input: str) -> list:
        """
        Process user input. Returns a list of FT components.
        Components are rendered into HTML and streamed to the chat.
        """
        cmd, subject, params = parse_command(user_input)

        # Normalize ticker-style subjects to uppercase
        ticker_cmds = {"profile", "financials", "news", "analysts", "valuation"}
        if cmd in ticker_cmds and subject:
            subject = subject.upper()

        if cmd == "help":
            return [self._markdown_bubble(get_help_text())]
        if cmd == "clear":
            return []  # Handled by caller
        if cmd == "profile":
            return await self._profile(subject)
        if cmd == "financials":
            return await self._financials(subject)
        if cmd == "news":
            return await self._news(subject, params)
        if cmd == "analysts":
            return await self._analysts(subject)
        if cmd == "valuation":
            return await self._valuation(subject)
        if cmd == "movers":
            return [self._markdown_bubble("Market movers coming soon. Try `profile:AAPL` or ask a question.")]
        if cmd == "docs":
            return [self._docs_widget()]
        if cmd == "targets":
            return await self._llm_query(f"Find acquisition targets: {subject} {self._params_str(params)}", "target_finder")
        if cmd == "buyers":
            return await self._llm_query(f"Find strategic buyers for: {subject} {self._params_str(params)}", "buyer_finder")
        if cmd == "ipo":
            return await self._llm_query(f"Assess IPO readiness: {subject} {self._params_str(params)}", "ipo_assessor")
        if cmd == "score":
            return await self._score(subject, params)
        if cmd == "keyterms":
            return await self._key_terms(subject, params)
        if cmd == "research":
            return await self._research(subject or user_input)
        if cmd == "deals":
            return [self._deals_widget()]
        if cmd == "market":
            return [self._market_widget()]
        if cmd == "tools":
            return [self._tools_widget()]
        if cmd == "upload":
            return [self._upload_widget()]
        if cmd == "settings":
            return [self._settings_widget()]

        # Free-form chat — LLM with research
        return await self._chat(user_input)

    # ------------------------------------------------------------------
    # Structured commands → rich components
    # ------------------------------------------------------------------
    async def _profile(self, ticker: str) -> list:
        if not ticker:
            return [self._error("Usage: `profile:MSFT`")]
        from utils.yfinance_util import yfinance_util
        p = await asyncio.to_thread(yfinance_util.get_company_profile, ticker)
        f = await asyncio.to_thread(yfinance_util.get_financials, ticker)
        if "error" in p:
            return [self._error(f"Could not find {ticker}: {p['error']}")]

        return [Div(
            Div(
                H3(f"{p['name']} ({p['ticker']})", cls="font-semibold text-gray-800"),
                Div(
                    *[Span(t, cls="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded") for t in [p.get("sector",""), p.get("industry",""), p.get("country","")] if t],
                    cls="flex gap-2 mt-1",
                ),
                cls="mb-3",
            ),
            P(p.get("description", "")[:400], cls="text-sm text-gray-600 mb-3"),
            Div(
                self._metric("Market Cap", self._fmt(p.get("market_cap"))),
                self._metric("Revenue", self._fmt(f.get("revenue"))),
                self._metric("EBITDA", self._fmt(f.get("ebitda"))),
                self._metric("Employees", f"{p.get('employees',0):,}" if p.get("employees") else "N/A"),
                self._metric("EV/EBITDA", f"{f.get('ev_to_ebitda',0):.1f}x" if f.get("ev_to_ebitda") else "N/A"),
                self._metric("Growth", f"{f.get('revenue_growth',0)*100:.1f}%" if f.get("revenue_growth") else "N/A"),
                cls="grid grid-cols-3 gap-2",
            ),
            cls="bg-white rounded-lg p-4 border border-gray-200",
        )]

    async def _financials(self, ticker: str) -> list:
        if not ticker:
            return [self._error("Usage: `financials:AAPL`")]
        from utils.yfinance_util import yfinance_util
        f = await asyncio.to_thread(yfinance_util.get_financials, ticker)
        if "error" in f:
            return [self._error(f"Error: {f['error']}")]
        rows = [("Revenue", self._fmt(f.get("revenue"))), ("EBITDA", self._fmt(f.get("ebitda"))),
                ("Net Income", self._fmt(f.get("net_income"))), ("Free Cash Flow", self._fmt(f.get("free_cashflow"))),
                ("Gross Margin", self._pct(f.get("gross_margins"))), ("EBITDA Margin", self._pct(f.get("ebitda_margins"))),
                ("Profit Margin", self._pct(f.get("profit_margins"))), ("Revenue Growth", self._pct(f.get("revenue_growth"))),
                ("P/E Ratio", f"{f.get('pe_ratio',0):.1f}" if f.get("pe_ratio") else "N/A"),
                ("EV/EBITDA", f"{f.get('ev_to_ebitda',0):.1f}x" if f.get("ev_to_ebitda") else "N/A"),
                ("D/E Ratio", f"{f.get('debt_to_equity',0):.1f}" if f.get("debt_to_equity") else "N/A")]
        return [Div(
            H3(f"Financials: {ticker.upper()}", cls="font-semibold text-gray-800 mb-3"),
            *[Div(Span(k, cls="text-xs text-gray-500 w-32 inline-block"), Span(v, cls="text-sm font-medium text-gray-800"), cls="py-1 border-b border-gray-100") for k, v in rows],
            cls="bg-white rounded-lg p-4 border border-gray-200",
        )]

    async def _news(self, ticker: str, params: dict) -> list:
        """News via Tavily search."""
        query = f"{ticker} stock company latest news 2026" if ticker else "M&A market news today"
        from utils.research_tools import research_tools
        res = await research_tools.tavily_search(query)
        results = res.get("results", [])
        if not results:
            return [self._info(f"No news found for {ticker or 'market'}.")]
        items = []
        for r in results[:8]:
            items.append(Div(
                A(r.get("title","Untitled"), href=r.get("url",""), target="_blank", cls="text-sm font-medium text-blue-700 hover:underline"),
                P(r.get("content","")[:150], cls="text-xs text-gray-500 mt-0.5"),
                cls="py-2 border-b border-gray-100",
            ))
        return [Div(H3(f"News: {ticker or 'Market'}", cls="font-semibold text-gray-800 mb-2"), *items, cls="bg-white rounded-lg p-4 border border-gray-200")]

    async def _analysts(self, ticker: str) -> list:
        if not ticker:
            return [self._error("Usage: `analysts:AAPL`")]
        return await self._llm_query(f"What are the current analyst ratings, price targets, and consensus for {ticker}?", "analyst")

    async def _valuation(self, tickers_str: str) -> list:
        if not tickers_str:
            return [self._error("Usage: `valuation:AAPL,MSFT`")]
        tickers = [t.strip().upper() for t in tickers_str.replace(" ", ",").split(",") if t.strip()]
        from utils.yfinance_util import yfinance_util
        rows = []
        for t in tickers[:5]:
            f = await asyncio.to_thread(yfinance_util.get_financials, t)
            p = await asyncio.to_thread(yfinance_util.get_company_profile, t)
            rows.append(Tr(
                Td(t, cls="font-medium"), Td(self._fmt(p.get("market_cap"))),
                Td(f"{f.get('pe_ratio',0):.1f}" if f.get("pe_ratio") else "—"),
                Td(f"{f.get('ev_to_ebitda',0):.1f}x" if f.get("ev_to_ebitda") else "—"),
                Td(self._pct(f.get("revenue_growth"))),
                Td(self._pct(f.get("profit_margins"))),
            ))
        return [Div(
            H3("Valuation Comparison", cls="font-semibold text-gray-800 mb-2"),
            Table(
                Thead(Tr(*[Th(h, cls="text-xs text-gray-500 text-left py-1") for h in ["Ticker","Mkt Cap","P/E","EV/EBITDA","Growth","Margin"]])),
                Tbody(*rows), cls="w-full text-sm",
            ),
            cls="bg-white rounded-lg p-4 border border-gray-200",
        )]

    def _store_canvas(self, key, data):
        """Store data for canvas pane display."""
        import main
        main._canvas_state[key] = data

    async def _score(self, subject: str, params: dict) -> list:
        # Document-based scoring: score doc:filename.pdf
        doc_file = params.get("doc", "")
        if not doc_file and subject.lower().startswith("doc:"):
            doc_file = subject[4:]
        if doc_file:
            return await self._score_document(doc_file)

        buyer = params.get("buyer", subject)
        target = params.get("target", "")
        context = params.get("context", "")
        if not buyer and not target:
            return [self._error("Usage: `score buyer:Salesforce target:HubSpot` or `score doc:filename.pdf`")]
        query = f"Score acquisition: Buyer={buyer}, Target={target}. {context}"
        try:
            from agents.scoring_agent import ScoringAgent
            from utils.state import create_initial_state
            state = create_initial_state("buyer_ma", query)
            state["deal"]["company_name"] = target
            scorer = ScoringAgent()
            state = await scorer.execute(state)
            result = state["agent_results"].get("scoring", {}).get("result", {})
            if result and "dimensions" in result:
                from components.cards import ScoreCard
                from components.charts import RadarChart
                self._store_canvas("scores", result)
                from components.pipeline import AddToPipelineButton
                return [
                    ScoreCard(result),
                    RadarChart("score-radar-inline", result.get("dimensions", {})),
                    AddToPipelineButton(target or buyer, "target", score=result.get("composite_score"), metadata={"buyer": buyer, "target": target}),
                    Script("document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/canvas/scores', '#canvas-content');"),
                ]
        except Exception as e:
            pass
        return await self._llm_query(query, "scoring")

    async def _score_document(self, filename: str) -> list:
        """Score a document — find best buyer matches using document content."""
        from pathlib import Path
        # Find the file (including docs-data/)
        file_path = None
        for folder in [Path("docs-data"), Path("docs"), Path("uploads")]:
            p = folder / filename
            if p.exists():
                file_path = str(p)
                break
        if not file_path:
            return [self._error(f"Document not found: `{filename}`. Try `docs` to list available files.")]

        # Parse document
        from utils.document_parser import document_parser
        parsed = document_parser.parse(file_path)
        if "error" in parsed:
            return [self._error(f"Parse error: {parsed['error']}")]
        doc_text = document_parser.extract_all_text(parsed)
        if not doc_text.strip():
            return [self._error("Document appears to be empty or could not be parsed.")]

        # Run scoring agent's document buyer matching skill
        try:
            from agents.scoring_agent import ScoringAgent
            scorer = ScoringAgent()
            result = await scorer.score_document_buyers(doc_text, filename)
        except Exception as e:
            return [self._error(f"Scoring error: {str(e)[:200]}")]

        # Store for canvas
        self._store_canvas("scores", result)

        # Render results
        parts = []
        profile = result.get("company_profile", {})
        if profile:
            parts.append(Div(
                H3(f"Company: {profile.get('name', filename)}", cls="font-semibold text-gray-800"),
                Div(
                    *[Span(t, cls="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded") for t in [profile.get("sector",""), profile.get("revenue","")] if t],
                    cls="flex gap-2 mt-1 mb-2",
                ),
                P(profile.get("business_model", ""), cls="text-sm text-gray-600"),
                Div(
                    P("Key Strengths:", cls="text-xs font-semibold text-gray-500 mt-2"),
                    *[P(f"- {s}", cls="text-xs text-gray-600") for s in profile.get("key_strengths", [])],
                ),
                cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
            ))

        # Buyer match cards (using shared helper from main.py)
        matches = result.get("buyer_matches", [])
        if matches:
            parts.append(H3(f"Top {len(matches)} Buyer Matches", cls="font-semibold text-gray-800 mb-2"))
            import main
            from components.pipeline import AddToPipelineButton
            for i, match in enumerate(matches, 1):
                parts.append(main._buyer_match_card(match, i))
                parts.append(AddToPipelineButton(
                    match.get("buyer", "Unknown"), "buyer",
                    score=match.get("composite_score"),
                    metadata={"buyer_type": match.get("buyer_type", ""), "target": profile.get("name", filename)},
                ))
        else:
            parts.append(self._info("No buyer matches could be generated. Try with a more detailed document."))

        # Auto-open canvas to Scores tab
        parts.append(
            Script("document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/canvas/scores', '#canvas-content');")
        )
        return parts

    async def _key_terms(self, subject: str, params: dict) -> list:
        """Extract key terms from a document using LLM."""
        # Determine filename
        doc_file = params.get("doc", "")
        if not doc_file and subject:
            doc_file = subject.strip()
        if not doc_file:
            return [self._error("Usage: `keyterms doc:NovaTech-Pitch-Deck.pdf` or `keyterms NovaTech-Pitch-Deck.pdf`")]

        from pathlib import Path
        file_path = None
        for folder in [Path("docs-data"), Path("docs"), Path("uploads")]:
            p = folder / doc_file
            if p.exists():
                file_path = str(p)
                break
        if not file_path:
            return [self._error(f"Document not found: `{doc_file}`")]

        # Parse document
        from utils.document_parser import document_parser
        parsed = document_parser.parse(file_path)
        if "error" in parsed:
            return [self._error(f"Parse error: {parsed['error']}")]
        doc_text = document_parser.extract_all_text(parsed)
        if not doc_text.strip():
            return [self._error("Document appears empty.")]

        # Load the key_terms prompt
        prompt_path = Path("prompts/key_terms.md")
        if prompt_path.exists():
            system_prompt = prompt_path.read_text()
        else:
            system_prompt = "Extract key terms from this M&A document. Return JSON with: document_type, company_name, summary, company_profile, financials, transaction_terms, key_metrics, investment_highlights, key_risks."

        # Call LLM
        try:
            from utils.llm_factory import create_llm
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = create_llm()
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Document: {doc_file}\n\n{doc_text[:8000]}"),
            ]
            response = await llm.ainvoke(messages)
            result = self._parse_json(response.content)
        except Exception as e:
            return [self._error(f"Key terms extraction error: {str(e)[:200]}")]

        # Render results
        parts = []

        # Header
        company = result.get("company_name", doc_file)
        doc_type = result.get("document_type", "document").replace("_", " ").title()
        parts.append(Div(
            H3(f"Key Terms: {company}", cls="font-semibold text-gray-800"),
            Div(
                Span(doc_type, cls="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded"),
                Span(doc_file, cls="text-xs text-gray-500 ml-2"),
                cls="flex items-center gap-1 mt-1",
            ),
            P(result.get("summary", ""), cls="text-sm text-gray-600 mt-2"),
            cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
        ))

        # Company profile
        profile = result.get("company_profile", {})
        if profile:
            rows = [(k.replace("_", " ").title(), v) for k, v in profile.items() if v]
            if rows:
                parts.append(Div(
                    H4("Company Profile", cls="font-semibold text-gray-700 text-sm mb-2"),
                    *[Div(Span(k, cls="text-xs text-gray-500 w-32 inline-block"), Span(str(v), cls="text-sm font-medium"), cls="py-1 border-b border-gray-50") for k, v in rows],
                    cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
                ))

        # Financials
        fins = result.get("financials", {})
        if fins:
            rows = [(k.replace("_", " ").title(), v) for k, v in fins.items() if v]
            if rows:
                parts.append(Div(
                    H4("Financials", cls="font-semibold text-gray-700 text-sm mb-2"),
                    Div(
                        *[Div(P(k, cls="text-xs text-gray-500"), P(str(v), cls="text-sm font-bold text-gray-800"), cls="bg-gray-50 rounded p-2") for k, v in rows],
                        cls="grid grid-cols-3 gap-2",
                    ),
                    cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
                ))

        # Transaction terms
        terms = result.get("transaction_terms", {})
        if terms:
            rows = [(k.replace("_", " ").title(), v) for k, v in terms.items() if v]
            if rows:
                parts.append(Div(
                    H4("Transaction Terms", cls="font-semibold text-gray-700 text-sm mb-2"),
                    *[Div(Span(k, cls="text-xs text-gray-500 w-40 inline-block"), Span(str(v), cls="text-sm"), cls="py-1 border-b border-gray-50") for k, v in rows],
                    cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
                ))

        # Investment highlights
        highlights = result.get("investment_highlights", [])
        if highlights:
            parts.append(Div(
                H4("Investment Highlights", cls="font-semibold text-gray-700 text-sm mb-2"),
                *[P(f"- {h}", cls="text-sm text-gray-700") for h in highlights],
                cls="bg-green-50 rounded-lg p-4 border border-green-200 mb-3",
            ))

        # Key risks
        risks = result.get("key_risks", [])
        if risks:
            parts.append(Div(
                H4("Key Risks", cls="font-semibold text-gray-700 text-sm mb-2"),
                *[P(f"- {r}", cls="text-sm text-gray-700") for r in risks],
                cls="bg-red-50 rounded-lg p-4 border border-red-200 mb-3",
            ))

        # Key people
        people = result.get("key_people", [])
        if people:
            parts.append(Div(
                H4("Key People", cls="font-semibold text-gray-700 text-sm mb-2"),
                *[Div(Span(p.get("name",""), cls="text-sm font-medium"), Span(f" - {p.get('role','')}", cls="text-xs text-gray-500"), cls="py-1") for p in people],
                cls="bg-white rounded-lg p-4 border border-gray-200 mb-3",
            ))

        # Auto-open canvas with the document
        parts.append(Script(f"document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/doc/panel?fn={doc_file}', '#canvas-content');"))

        return parts

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from LLM response, handling markdown fences."""
        import re
        # Strip markdown code fences
        text = re.sub(r'^```(?:json)?\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text.strip())
        try:
            return json.loads(text)
        except Exception:
            return {}

    async def _research(self, query: str) -> list:
        from utils.research_tools import research_tools
        res = await research_tools.deep_research(query)

        # Store for canvas Research tab
        self._store_canvas("research", res)

        parts = []
        # Thinking trace
        trace = res.get("thinking_trace", [])
        if trace:
            from components.research_panel import ThinkingTrace
            parts.append(ThinkingTrace(trace))
        # EXA results
        for r in res.get("exa", {}).get("results", [])[:5]:
            parts.append(Div(
                Span("EXA", cls="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded mr-2"),
                A(r.get("title",""), href=r.get("url",""), target="_blank", cls="text-sm text-blue-700 hover:underline"),
                P(r.get("snippet","")[:150], cls="text-xs text-gray-500 mt-0.5"),
                cls="py-1.5 border-b border-gray-50",
            ))
        # Tavily results
        for r in res.get("tavily", {}).get("results", [])[:5]:
            parts.append(Div(
                Span("TAV", cls="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded mr-2"),
                A(r.get("title",""), href=r.get("url",""), target="_blank", cls="text-sm text-blue-700 hover:underline"),
                P(r.get("content","")[:150], cls="text-xs text-gray-500 mt-0.5"),
                cls="py-1.5 border-b border-gray-50",
            ))
        if not parts:
            parts.append(P("No research results found.", cls="text-sm text-gray-400"))

        # Auto-open canvas Research tab
        parts.append(Script("document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/canvas/research', '#canvas-content');"))
        return [Div(*parts, cls="bg-white rounded-lg p-4 border border-gray-200")]

    # ------------------------------------------------------------------
    # Free-form chat — LLM
    # ------------------------------------------------------------------
    async def _chat(self, user_input: str) -> list:
        """Free-form question → LLM + optional research."""
        parts = []
        # Run research in parallel
        research_data = {}
        try:
            from utils.research_tools import research_tools
            research_data = await research_tools.deep_research(user_input)
            # Store for canvas Research tab
            if research_data:
                self._store_canvas("research", research_data)
        except Exception:
            pass

        # LLM call with research context
        try:
            from utils.llm_factory import create_llm
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = create_llm()

            research_context = ""
            for src in ["exa", "tavily"]:
                for r in research_data.get(src, {}).get("results", [])[:3]:
                    title = r.get("title", "")
                    snippet = r.get("snippet", r.get("content", ""))[:200]
                    research_context += f"- {title}: {snippet}\n"

            system = (
                "You are LiquidRound, an AI M&A research assistant by Predictive Labs Ltd. "
                "Help users find acquisition targets, evaluate deals, and research companies. "
                "Be concise and specific. Use markdown formatting."
            )
            if research_context:
                system += f"\n\nRecent research results:\n{research_context}"

            messages = [SystemMessage(content=system), HumanMessage(content=user_input)]
            response = await llm.ainvoke(messages)
            parts.append(self._markdown_bubble(response.content))
        except Exception as e:
            parts.append(self._error(f"LLM error: {str(e)[:200]}"))

        # Append research links if available
        links = []
        for src in ["exa", "tavily"]:
            for r in research_data.get(src, {}).get("results", [])[:3]:
                if r.get("url"):
                    links.append(A(r.get("title","Link")[:60], href=r["url"], target="_blank", cls="text-xs text-blue-600 hover:underline block"))
        if links:
            parts.append(Div(
                P("Sources", cls="text-xs font-semibold text-gray-500 mb-1"),
                *links,
                cls="bg-gray-50 rounded p-2 mt-2",
            ))

        return parts

    async def _llm_query(self, prompt: str, agent_label: str) -> list:
        try:
            from utils.llm_factory import create_llm
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = create_llm()
            messages = [
                SystemMessage(content="You are an M&A research analyst at Predictive Labs Ltd. Be specific, use data, format with markdown."),
                HumanMessage(content=prompt),
            ]
            response = await llm.ainvoke(messages)
            return [self._markdown_bubble(response.content)]
        except Exception as e:
            return [self._error(f"Error ({agent_label}): {str(e)[:200]}")]

    # ------------------------------------------------------------------
    # Widget components (inline in chat)
    # ------------------------------------------------------------------
    def _deals_widget(self) -> "FT":
        from utils.database import db_service
        try:
            recent = db_service.get_recent_workflows(10)
        except Exception:
            recent = []
        if not recent:
            return self._info("No deals yet. Start by running a query!")
        items = [Div(
            Div(Span(w.get("workflow_type","").upper(), cls="text-xs font-bold text-blue-700"), Span(f" — {w.get('status','')}", cls="text-xs text-gray-500")),
            P(w.get("user_query","")[:80], cls="text-sm text-gray-700 mt-0.5"),
            cls="py-2 border-b border-gray-100",
        ) for w in recent]
        return Div(H3("Recent Deals", cls="font-semibold text-gray-800 mb-2"), *items, cls="bg-white rounded-lg p-4 border border-gray-200")

    def _market_widget(self) -> "FT":
        from components.charts import SectorHeatmap
        sectors = ["Technology","Healthcare","Financials","Consumer","Energy","Utilities","Materials","Industrials","Real Estate","Comm Services"]
        years = ["2022","2023","2024","2025","2026 YTD"]
        values = [[-28,57,35,22,8],[-2,2,12,5,3],[-11,12,28,15,6],[-37,42,22,10,4],[64,-1,-2,-8,2],[1,-7,24,8,5],[-12,10,8,3,1],[-5,18,17,12,4],[-26,12,6,4,2],[-40,55,32,18,7]]
        return Div(SectorHeatmap("heatmap-inline", sectors, years, values), cls="bg-white rounded-lg p-4 border border-gray-200")

    def _tools_widget(self) -> "FT":
        tools = [("Deal Room","Available"),("CIM Generator","Available"),("Comparable Transactions","Available"),
                 ("LOI Drafter","Available"),("DD Checklist","Available"),("Regulatory Screening","Beta"),
                 ("Stakeholder Mapping","Beta"),("Integration Playbook","Beta"),("Pipeline CRM","Coming Soon")]
        items = [Div(Span(n, cls="text-sm font-medium text-gray-800"), Span(s, cls=f"text-xs ml-2 px-1.5 py-0.5 rounded {'bg-green-100 text-green-700' if s=='Available' else 'bg-yellow-100 text-yellow-700' if s=='Beta' else 'bg-gray-100 text-gray-500'}"), cls="py-1") for n,s in tools]
        return Div(H3("M&A Tools", cls="font-semibold text-gray-800 mb-2"), *items, cls="bg-white rounded-lg p-4 border border-gray-200")

    def _docs_widget(self) -> "FT":
        """List available documents from docs/ and uploads/ with view + score actions."""
        from pathlib import Path
        files = []
        for folder in [Path("docs-data"), Path("docs"), Path("uploads")]:
            if folder.exists():
                for f in sorted(folder.iterdir()):
                    if f.is_file() and f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".pptx", ".ppt"):
                        files.append((f.name, f.suffix.lower(), f"{f.stat().st_size / 1024 / 1024:.1f} MB"))
        if not files:
            return self._info("No documents found. Upload a PDF, XLS, or PPT via the paperclip button.")
        rows = []
        for fname, ext, size in files:
            badge_cls = {"pdf": "bg-red-100 text-red-700", ".xlsx": "bg-green-100 text-green-700", ".pptx": "bg-orange-100 text-orange-700"}.get(ext, "bg-gray-100 text-gray-600")
            rows.append(Div(
                Div(
                    Span(ext[1:].upper(), cls=f"text-xs font-bold px-1.5 py-0.5 rounded {badge_cls}"),
                    Span(fname, cls="text-sm text-gray-800 ml-2 truncate"),
                    Span(size, cls="text-xs text-gray-400 ml-auto"),
                    cls="flex items-center",
                ),
                Div(
                    A("View", href="#", onclick=f"document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/doc/panel?fn={fname}', '#canvas-content'); return false;", cls="text-xs text-blue-600 hover:underline"),
                    Span(" | ", cls="text-xs text-gray-300"),
                    A("Score Buyers", href="#", hx_post="/chat", hx_vals=json.dumps({"msg": f"score doc:{fname}"}), hx_target="#chat-area", hx_swap="beforeend", cls="text-xs text-green-600 hover:underline"),
                    cls="mt-1",
                ),
                cls="py-2 border-b border-gray-100",
            ))
        return Div(
            H3(f"Documents ({len(files)})", cls="font-semibold text-gray-800 mb-2"),
            *rows,
            cls="bg-white rounded-lg p-4 border border-gray-200",
        )

    def _upload_widget(self) -> "FT":
        from components.upload_form import UploadZone
        return UploadZone()

    def _settings_widget(self) -> "FT":
        return Div(
            H3("Configuration", cls="font-semibold text-gray-800 mb-2"),
            *[Div(Span(k, cls="text-xs text-gray-500 w-28 inline-block"), Span(v, cls="text-sm font-medium"), cls="py-1") for k, v in [
                ("Provider", config.default_provider.upper()),("Model", config.default_model),
                ("Temperature", str(config.default_temperature)),("EXA", "Configured" if config.exa_api_key else "Not set"),
                ("Tavily", "Configured" if config.tavily_api_key else "Not set"),
            ]],
            cls="bg-white rounded-lg p-4 border border-gray-200",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _metric(self, label, value):
        return Div(P(label, cls="text-xs text-gray-500 uppercase"), P(str(value), cls="text-sm font-bold text-gray-800"), cls="bg-gray-50 rounded p-2")

    def _markdown_bubble(self, md_text: str):
        import re
        html = md_text
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'^### (.+)$', r'<h4 class="font-semibold text-gray-800 mt-2 mb-1">\1</h4>', html, flags=re.M)
        html = re.sub(r'^## (.+)$', r'<h3 class="font-semibold text-gray-800 mt-3 mb-1">\1</h3>', html, flags=re.M)
        html = re.sub(r'^# (.+)$', r'<h2 class="text-lg font-bold text-gray-800 mt-3 mb-1">\1</h2>', html, flags=re.M)
        html = re.sub(r'^\d+\.\s+(.+)$', r'<li class="ml-4 text-sm">\1</li>', html, flags=re.M)
        html = re.sub(r'^[-*]\s+(.+)$', r'<li class="ml-4 text-sm">\1</li>', html, flags=re.M)
        html = re.sub(r'`([^`]+)`', r'<code class="bg-gray-100 px-1 rounded text-xs">\1</code>', html)
        html = html.replace('\n\n', '<br>').replace('\n', '<br>')
        return Div(NotStr(html), cls="text-sm text-gray-800 leading-relaxed")

    def _error(self, msg: str):
        return Div(P(msg, cls="text-sm text-red-600"), cls="bg-red-50 rounded-lg p-3 border border-red-200")

    def _info(self, msg: str):
        return Div(P(msg, cls="text-sm text-gray-600"), cls="bg-blue-50 rounded-lg p-3 border border-blue-200")

    def _fmt(self, n):
        if not n: return "N/A"
        n = float(n)
        if n >= 1e12: return f"${n/1e12:.1f}T"
        if n >= 1e9: return f"${n/1e9:.1f}B"
        if n >= 1e6: return f"${n/1e6:.1f}M"
        return f"${n:,.0f}"

    def _pct(self, n):
        if not n: return "N/A"
        return f"{float(n)*100:.1f}%"

    def _params_str(self, params):
        return " ".join(f"{k}: {v}" for k, v in params.items())


render_agent = RenderAgent()
