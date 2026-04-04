"""
LiquidRound — AI-Powered M&A Research Platform
Chat-first FastHTML app. Deployed with uvicorn.
"""
import os, uuid, time, asyncio, collections, json
from dotenv import load_dotenv
load_dotenv()

from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
from starlette.datastructures import UploadFile
from pathlib import Path

# ---------------------------------------------------------------------------
# App setup — NO auth beforeware (login is optional)
# ---------------------------------------------------------------------------
app, rt = fast_app(
    pico=False,
    hdrs=(
        Script(src="https://cdn.tailwindcss.com"),
        Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
        Link(rel="stylesheet", href="/app.css"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
    ),
    static_path="static",
    secret_key=os.getenv("SESSION_SECRET", "liquidround-dev-secret-change-me"),
)

# Register auth routes (login/register still available)
from routes.auth import ar as auth_router
auth_router.to_app(app)

# Register existing tool routes for direct access
from routes.upload import ar as upload_router
from routes.research import ar as research_router
upload_router.to_app(app)
research_router.to_app(app)

# Register API routes (company-profile, score-match, etc.)
from routes.api import ar as api_router
api_router.to_app(app)

# Register pipeline routes
from routes.pipeline import ar as pipeline_router
pipeline_router.to_app(app)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)
DOCS_DATA_DIR = Path("docs-data")
DOCS_DATA_DIR.mkdir(exist_ok=True)

# All folders to search for documents
DOC_FOLDERS = [DOCS_DATA_DIR, DOCS_DIR, UPLOAD_DIR]


# ---------------------------------------------------------------------------
# Document serving routes
# ---------------------------------------------------------------------------
@rt("/doc/view")
async def doc_view(fn: str = ""):
    """Serve a document file (PDF, etc.) from docs/ or uploads/."""
    if not fn:
        return Response("Missing filename", status_code=400)
    filename = Path(fn).name
    for folder in DOC_FOLDERS:
        path = folder / filename
        if path.exists():
            from starlette.responses import FileResponse
            return FileResponse(str(path), media_type="application/pdf" if filename.endswith(".pdf") else "application/octet-stream")
    return Response("File not found", status_code=404)


@rt("/doc/panel")
def doc_panel(fn: str = ""):
    """Return the right-pane document viewer HTML partial."""
    if not fn:
        return _doc_list_for_pane()
    filename = Path(fn).name
    return _doc_viewer_content(filename)


def _doc_viewer_content(filename: str):
    """Build the document viewer pane content."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        viewer = Iframe(src=f"/doc/view?fn={filename}", cls="w-full h-full border-0", style="min-height: 70vh;")
    else:
        viewer = Div(P(f"Preview not available for {ext} files.", cls="text-sm text-gray-500"), P("Use the download link below.", cls="text-xs text-gray-400 mt-1"))
    return Div(
        Div(
            Span(filename, cls="text-sm font-medium text-gray-800 truncate"),
            A("Download", href=f"/doc/view?fn={filename}", target="_blank", cls="text-xs text-blue-600 hover:underline"),
            cls="flex items-center justify-between mb-2",
        ),
        viewer,
        Div(
            Button(
                "Key Terms",
                hx_post="/chat",
                hx_vals=json.dumps({"msg": f"keyterms {filename}"}),
                hx_target="#chat-area",
                hx_swap="beforeend",
                hx_on__before_request=_THINKING_JS,
                hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
                cls="flex-1 mt-3 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700",
            ),
            Button(
                "Score: Find Buyers",
                hx_post="/chat",
                hx_vals=json.dumps({"msg": f"score doc:{filename}"}),
                hx_target="#chat-area",
                hx_swap="beforeend",
                hx_on__before_request=_THINKING_JS,
                hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
                cls="flex-1 mt-3 bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700",
            ),
            cls="flex gap-2",
        ),
        cls="p-3 h-full flex flex-col",
    )


def _doc_list_for_pane():
    """List all available documents in docs/ and uploads/."""
    files = []
    for folder in DOC_FOLDERS:
        if folder.exists():
            for f in sorted(folder.iterdir()):
                if f.is_file() and f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".pptx", ".ppt"):
                    files.append(f.name)
    if not files:
        return Div(P("No documents yet.", cls="text-sm text-gray-400 italic"), P("Upload a file via the chat or use the paperclip button.", cls="text-xs text-gray-300 mt-1"), cls="p-4")
    items = []
    for fname in files:
        ext = Path(fname).suffix.lower()
        badge_cls = {"pdf": "bg-red-100 text-red-700", ".xlsx": "bg-green-100 text-green-700", ".xls": "bg-green-100 text-green-700", ".pptx": "bg-orange-100 text-orange-700", ".ppt": "bg-orange-100 text-orange-700"}
        b_cls = badge_cls.get(ext, "bg-gray-100 text-gray-600")
        items.append(
            Div(
                Div(
                    Span(ext[1:].upper(), cls=f"text-xs font-bold px-1.5 py-0.5 rounded {b_cls}"),
                    Span(fname, cls="text-sm text-gray-800 truncate ml-2"),
                    cls="flex items-center",
                ),
                Div(
                    Button("View", hx_get=f"/doc/panel?fn={fname}", hx_target="#canvas-content", cls="text-xs text-blue-600 hover:underline"),
                    Button("Key Terms", hx_post="/chat", hx_vals=json.dumps({"msg": f"keyterms {fname}"}), hx_target="#chat-area", hx_swap="beforeend", hx_on__before_request=_THINKING_JS, hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();", cls="text-xs text-purple-600 hover:underline ml-2"),
                    Button("Score", hx_post="/chat", hx_vals=json.dumps({"msg": f"score doc:{fname}"}), hx_target="#chat-area", hx_swap="beforeend", hx_on__before_request=_THINKING_JS, hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();", cls="text-xs text-green-600 hover:underline ml-2"),
                    cls="flex mt-1",
                ),
                cls="py-2 border-b border-gray-100",
            )
        )
    return Div(
        P("Documents", cls="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
        *items,
        cls="p-3",
    )


# ---------------------------------------------------------------------------
# Canvas routes — dynamic right pane content
# ---------------------------------------------------------------------------
# In-memory store for last research/score/compare results per session
_canvas_state = {}

@rt("/canvas/docs")
def canvas_docs():
    """Canvas tab: document list."""
    return _doc_list_for_pane()

@rt("/canvas/research")
def canvas_research():
    """Canvas tab: last research results."""
    data = _canvas_state.get("research")
    if not data:
        return Div(
            P("No research results yet.", cls="text-sm text-gray-400 italic"),
            P("Run a research query or ask a question to see results here.", cls="text-xs text-gray-300 mt-1"),
            cls="p-4",
        )
    parts = []
    for r in data.get("exa", {}).get("results", [])[:8]:
        parts.append(Div(
            Span("EXA", cls="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded mr-2"),
            A(r.get("title",""), href=r.get("url",""), target="_blank", cls="text-sm text-blue-700 hover:underline"),
            P(r.get("snippet","")[:150], cls="text-xs text-gray-500 mt-0.5"),
            cls="py-2 border-b border-gray-50",
        ))
    for r in data.get("tavily", {}).get("results", [])[:8]:
        parts.append(Div(
            Span("TAV", cls="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded mr-2"),
            A(r.get("title",""), href=r.get("url",""), target="_blank", cls="text-sm text-blue-700 hover:underline"),
            P(r.get("content","")[:150], cls="text-xs text-gray-500 mt-0.5"),
            cls="py-2 border-b border-gray-50",
        ))
    if not parts:
        parts.append(P("No results found.", cls="text-sm text-gray-400"))
    return Div(
        P("Research Results", cls="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
        *parts,
        cls="p-3",
    )

@rt("/canvas/scores")
def canvas_scores():
    """Canvas tab: last scoring results."""
    data = _canvas_state.get("scores")
    if not data:
        return Div(
            P("No scoring results yet.", cls="text-sm text-gray-400 italic"),
            P("Score a buyer-target match or a pitch deck to see results here.", cls="text-xs text-gray-300 mt-1"),
            cls="p-4",
        )
    # Render stored score data
    parts = []
    profile = data.get("company_profile", {})
    if profile:
        parts.append(Div(
            H3(f"Company: {profile.get('name', 'Unknown')}", cls="font-semibold text-gray-800 text-sm"),
            P(profile.get("business_model", ""), cls="text-xs text-gray-600 mt-1"),
            cls="bg-gray-50 rounded-lg p-3 mb-3",
        ))
    matches = data.get("buyer_matches", [])
    if not matches and "dimensions" in data:
        # Single score result
        from components.cards import ScoreCard
        from components.charts import RadarChart
        parts.append(ScoreCard(data))
        parts.append(RadarChart("canvas-radar", data.get("dimensions", {})))
    else:
        for i, match in enumerate(matches, 1):
            parts.append(_buyer_match_card(match, i))
    return Div(
        P("Scoring Results", cls="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
        *parts,
        cls="p-3",
    )

@rt("/canvas/compare")
def canvas_compare():
    """Canvas tab: last valuation comparison."""
    data = _canvas_state.get("compare")
    if not data:
        return Div(
            P("No comparison data yet.", cls="text-sm text-gray-400 italic"),
            P("Run a valuation comparison to see results here.", cls="text-xs text-gray-300 mt-1"),
            cls="p-4",
        )
    return Div(
        P("Valuation Comparison", cls="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2"),
        data,  # Pre-rendered FT component
        cls="p-3",
    )


def _buyer_match_card(match, index):
    """Reusable buyer match card for chat and canvas."""
    rec = match.get("recommendation", "N/A")
    rec_cls = {"STRONG BUY": "bg-green-100 text-green-800", "PROCEED": "bg-blue-100 text-blue-800",
               "CAUTIOUS": "bg-yellow-100 text-yellow-800", "PASS": "bg-red-100 text-red-800"}.get(rec, "bg-gray-100")
    dims = match.get("dimensions", {})
    dim_bars = []
    for dk in ["revenue_synergies","cost_synergies","strategic_fit","cultural_fit","financial_health","integration_risk","market_timing"]:
        dv = dims.get(dk, {})
        s = dv.get("score", 5) if isinstance(dv, dict) else 5
        bar_w = s * 10
        bar_c = "bg-green-500" if s >= 7 else "bg-yellow-500" if s >= 5 else "bg-red-500"
        dim_bars.append(Div(
            Div(Span(dk.replace("_"," ").title(), cls="text-xs text-gray-500"), Span(f"{s}/10", cls="text-xs font-medium"), cls="flex justify-between"),
            Div(Div(cls=f"{bar_c} h-1.5 rounded-full", style=f"width:{bar_w}%"), cls="w-full bg-gray-200 rounded-full h-1.5"),
            cls="mb-1",
        ))
    return Div(
        Div(
            Div(
                Span(f"#{index}", cls="text-xs font-bold text-gray-400 mr-2"),
                Span(match.get("buyer","Unknown"), cls="font-semibold text-gray-800"),
                Span(f" ({match.get('buyer_type','')})", cls="text-xs text-gray-500"),
            ),
            Div(
                Span(str(match.get("composite_score",0)), cls="text-lg font-bold text-blue-700"),
                Span(rec, cls=f"text-xs px-2 py-0.5 rounded-full font-medium {rec_cls} ml-2"),
            ),
            cls="flex items-center justify-between mb-2",
        ),
        P(match.get("rationale",""), cls="text-sm text-gray-600 mb-2"),
        *dim_bars,
        cls="bg-white rounded-lg p-4 border border-gray-200 mb-2",
    )


# ---------------------------------------------------------------------------
# Per-session state
# ---------------------------------------------------------------------------
class SessionState:
    TTL = 7200
    def __init__(self):
        self.messages = []  # [{role, content_html}]
        self.last_accessed = time.time()

_sessions = {}

def _get_ss(session) -> SessionState:
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    if sid not in _sessions:
        _sessions[sid] = SessionState()
    ss = _sessions[sid]
    ss.last_accessed = time.time()
    return ss


# ---------------------------------------------------------------------------
# Chat-first UI
# ---------------------------------------------------------------------------
def _user_bubble(text):
    return Div(
        Div(P(text, cls="text-sm"), cls="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-xl"),
        cls="flex justify-end mb-3",
    )

def _assistant_bubble(*children, label=""):
    return Div(
        Div(
            P(label, cls="text-xs font-medium text-blue-600 mb-1") if label else "",
            *children,
            cls="bg-white rounded-2xl rounded-bl-sm px-4 py-3 max-w-2xl border border-gray-200 shadow-sm",
        ),
        cls="flex justify-start mb-3",
    )

def _thinking_indicator():
    return Div(
        Div(
            Div(cls="w-2 h-2 bg-blue-400 rounded-full animate-bounce"),
            Div(cls="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.1s]"),
            Div(cls="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.2s]"),
            cls="flex gap-1",
        ),
        cls="flex justify-start mb-3",
        id="thinking",
    )


_THINKING_JS = """
    var ca = document.getElementById('chat-area');
    if (ca) {
        var t = document.createElement('div');
        t.id = 'thinking-live';
        t.className = 'flex justify-start mb-3';
        t.innerHTML = '<div class="bg-white rounded-2xl rounded-bl-sm px-4 py-3 border border-gray-200 shadow-sm"><div class="flex items-center gap-2"><div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div><div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay:0.1s"></div><div class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay:0.2s"></div><span class="text-xs text-blue-600 ml-2">Thinking...</span></div></div>';
        ca.appendChild(t);
        ca.scrollTop = ca.scrollHeight;
        var ws = document.getElementById('welcome-section'); if(ws) ws.remove();
    }
"""

def _nav_page_link(label, href):
    """Nav link that loads a static page into main-content."""
    return A(
        label,
        hx_get=href,
        hx_target="#main-content",
        hx_push_url="true",
        cls="text-left text-xs text-gray-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors w-full block",
    )

def _nav_context_button(label, context_key):
    """Nav button that loads context-specific cards into welcome section."""
    return Button(
        label,
        hx_get=f"/cards/{context_key}",
        hx_target="#welcome-section",
        hx_swap="innerHTML",
        cls="text-left text-xs text-gray-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors w-full",
    )

def _nav_button(label, cmd, accent="gray"):
    """Single nav button that posts to chat."""
    return Button(
        label,
        hx_post="/chat",
        hx_vals=json.dumps({"msg": cmd}),
        hx_target="#chat-area",
        hx_swap="beforeend",
        hx_on__before_request=_THINKING_JS,
        hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove(); var ca=document.getElementById('chat-area'); if(ca) ca.scrollTo({top:ca.scrollHeight, behavior:'smooth'});",
        cls="text-left text-xs text-gray-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors w-full",
    )

def _nav_section(session):
    """Left navigation — grouped by buyer/seller workflow."""
    user = session.get("user")

    # Auth section
    if user:
        auth_section = Div(
            Div(
                Span(user.get("display_name", user.get("email","?"))[0].upper(), cls="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold"),
                Span(user.get("display_name", user.get("email","")), cls="text-xs text-gray-700 truncate"),
                cls="flex items-center gap-2",
            ),
            A("Sign out", href="/logout", cls="text-xs text-gray-400 hover:text-red-500"),
            cls="flex items-center justify-between px-3 py-2 border-t border-gray-200",
        )
    else:
        auth_section = Div(
            A("Sign in", href="/signin", cls="text-xs text-blue-600 hover:underline"),
            Span(" / ", cls="text-xs text-gray-400"),
            A("Register", href="/register", cls="text-xs text-blue-600 hover:underline"),
            cls="text-center px-3 py-2 border-t border-gray-200",
        )

    return Div(
        # Restore button — visible only when nav is hidden
        Button(
            NotStr('<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>'),
            id="nav-restore",
            onclick="document.getElementById('nav-panel').classList.remove('-translate-x-full'); this.classList.add('hidden');",
            cls="fixed top-3 left-3 z-30 bg-white border border-gray-200 rounded-lg p-2 shadow-sm hover:bg-blue-50 cursor-pointer hidden text-gray-500 hover:text-blue-600",
        ),
        # Collapsible nav panel
        Div(
            # Header with brand + close
            Div(
                Div(
                    H2("LiquidRound", cls="text-sm font-bold text-blue-800"),
                    Span("beta", cls="text-xs text-gray-400 ml-1"),
                    cls="flex items-center",
                ),
                P("M&A Research Platform", cls="text-xs text-gray-400 mt-0.5"),
                Button(
                    NotStr('<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'),
                    onclick="document.getElementById('nav-panel').classList.add('-translate-x-full'); document.getElementById('nav-restore').classList.remove('hidden');",
                    cls="absolute top-3 right-3 text-gray-400 hover:text-gray-600 cursor-pointer",
                ),
                cls="px-3 py-3 border-b border-gray-200 relative",
            ),
            Div(
                # New Chat button + Chat History (logged-in only)
                *([
                    A("+ New Chat", href="/conversation/new",
                      cls="block text-center text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg px-3 py-2 mx-3 mb-2 transition-colors"),
                    Details(
                        Summary(
                            Span("CHAT HISTORY", cls="text-xs font-bold text-gray-500 uppercase tracking-wide"),
                            cls="px-3 py-2 cursor-pointer hover:bg-gray-50 rounded list-none flex items-center nav-section-header",
                        ),
                        Div(
                            Input(name="q", placeholder="Search chats...",
                                  hx_get="/conversations/search", hx_trigger="keyup changed delay:300ms",
                                  hx_target="#chat-history",
                                  cls="w-full text-xs border border-gray-200 rounded px-2 py-1 mb-2 focus:outline-none focus:ring-1 focus:ring-blue-400"),
                            Div(id="chat-history", hx_get="/conversations", hx_trigger="load", hx_swap="innerHTML"),
                            cls="px-1",
                        ),
                        open=True,
                        cls="mb-2",
                    ),
                ] if user else []),
                # I'M BUYING section (open by default)
                Details(
                    Summary(
                        Span("I'M BUYING", cls="text-xs font-bold text-blue-700 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-blue-50 rounded list-none flex items-center nav-section-header",
                    ),
                    Div(
                        _nav_context_button("Find Targets", "find-targets"),
                        _nav_context_button("Company Profile", "company-profile"),
                        _nav_context_button("Valuation Comp", "valuation-comp"),
                        _nav_context_button("Score Match", "score-match"),
                        *([ A("Target Pipeline", hx_get="/pipeline/target", hx_target="#main-content", hx_push_url="true",
                              cls="text-left text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors w-full block font-medium") ] if user else []),
                        cls="pl-2 border-l-2 border-blue-200 ml-3 mb-2",
                    ),
                    open=True,
                    cls="mb-1",
                ),
                # I'M SELLING section (open by default)
                Details(
                    Summary(
                        Span("I'M SELLING", cls="text-xs font-bold text-green-700 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-green-50 rounded list-none flex items-center nav-section-header",
                    ),
                    Div(
                        _nav_context_button("Find Buyers", "find-buyers"),
                        _nav_context_button("Score Pitch Deck", "score-pitch-deck"),
                        _nav_context_button("IPO Assessment", "ipo-assessment"),
                        *([ A("Buyer Pipeline", hx_get="/pipeline/buyer", hx_target="#main-content", hx_push_url="true",
                              cls="text-left text-xs text-green-600 hover:text-green-800 hover:bg-green-50 px-3 py-1.5 rounded transition-colors w-full block font-medium") ] if user else []),
                        cls="pl-2 border-l-2 border-green-200 ml-3 mb-2",
                    ),
                    open=True,
                    cls="mb-1",
                ),
                # RESEARCH section (collapsed)
                Details(
                    Summary(
                        Span("RESEARCH", cls="text-xs font-bold text-gray-500 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-gray-50 rounded list-none flex items-center nav-section-header",
                    ),
                    Div(
                        _nav_button("Deep Research", "research:Baltic M&A renewable energy"),
                        _nav_button("Company News", "news:NOVO-B.CO"),
                        _nav_button("Financials", "financials:SIE.DE"),
                        _nav_button("Market Intel", "market"),
                        cls="pl-2 border-l-2 border-gray-200 ml-3 mb-2",
                    ),
                    cls="mb-1",
                ),
                # WORKSPACE section (collapsed)
                Details(
                    Summary(
                        Span("WORKSPACE", cls="text-xs font-bold text-gray-500 uppercase tracking-wide"),
                        cls="px-3 py-2 cursor-pointer hover:bg-gray-50 rounded list-none flex items-center nav-section-header",
                    ),
                    Div(
                        _nav_page_link("Documents", "/page/documents"),
                        _nav_page_link("Deal History", "/page/deals"),
                        _nav_page_link("M&A Tools", "/page/tools"),
                        cls="pl-2 border-l-2 border-gray-200 ml-3 mb-2",
                    ),
                    cls="mb-1",
                ),
                # Bottom utility links
                Div(
                    _nav_button("Settings", "settings"),
                    _nav_button("Help", "help"),
                    cls="mt-2 pt-2 border-t border-gray-100",
                ),
                cls="flex-1 overflow-y-auto py-2",
            ),
            auth_section,
            Div(P("Predictive Labs Ltd", cls="text-xs text-gray-300 text-center py-1")),
            id="nav-panel",
            cls="fixed left-0 top-0 h-screen w-56 bg-white border-r border-gray-200 z-20 flex flex-col shadow-lg transition-transform duration-300",
        ),
    )


def _action_card(label, subtitle, cmd, color="blue"):
    """Single action card that posts to chat."""
    border = f"border-{color}-100 hover:border-{color}-400"
    label_cls = f"text-{color}-700"
    return Div(
        H3(label, cls=f"font-medium text-gray-800 text-sm"),
        P(subtitle, cls="text-xs text-gray-500 mt-1"),
        hx_post="/chat",
        hx_vals=json.dumps({"msg": cmd}),
        hx_target="#chat-area",
        hx_swap="beforeend",
        hx_on__before_request=_THINKING_JS,
        hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
        cls=f"bg-white border-2 {border} rounded-xl p-4 cursor-pointer transition-colors",
    )

# Context card definitions: 3 cards per nav context
_CONTEXT_CARDS = {
    "default": {
        "title": "Quick Start",
        "subtitle": "Choose an action to begin",
        "cards": [
            ("Find Acquisition Targets", "Search by industry, size, geography", "targets industry:renewable energy", "blue"),
            ("Score a Deal", "Evaluate buyer-target synergy", "score buyer:Siemens target:Harju Elekter", "purple"),
            ("Analyze a Pitch Deck", "Extract key terms from documents", "docs", "green"),
        ],
    },
    "find-targets": {
        "title": "Find Acquisition Targets",
        "subtitle": "Search for companies to acquire",
        "cards": [
            ("Renewable Energy - Nordics", "Wind, solar, hydrogen in Baltic/Nordic region", "targets industry:renewable energy geography:Nordics", "blue"),
            ("Fintech - Europe", "Payments, lending, insurance tech", "targets industry:fintech geography:Europe", "indigo"),
            ("Healthcare SaaS - US", "Digital health, clinical software", "targets industry:healthcare SaaS geography:US", "green"),
        ],
    },
    "company-profile": {
        "title": "Company Profile",
        "subtitle": "Look up a company by ticker",
        "cards": [
            ("SAP SE", "Enterprise software, Germany", "profile:SAP.DE", "blue"),
            ("Novo Nordisk", "Pharma, Denmark", "profile:NOVO-B.CO", "green"),
            ("Siemens", "Industrial tech, Germany", "profile:SIE.DE", "indigo"),
        ],
    },
    "valuation-comp": {
        "title": "Valuation Comparison",
        "subtitle": "Compare multiples across companies",
        "cards": [
            ("Baltic Energy", "TAL1T, EQNR, NESTE", "valuation:TAL1T.TL,EQNR.OL,NESTE.HE", "blue"),
            ("Nordic Tech", "NOVO-B, SIE, SAP", "valuation:NOVO-B.CO,SIE.DE,SAP.DE", "indigo"),
            ("EU Financials", "ING, SAN, BNP", "valuation:INGA.AS,SAN.PA,BNP.PA", "green"),
        ],
    },
    "score-match": {
        "title": "Score M&A Match",
        "subtitle": "Evaluate buyer-target compatibility",
        "cards": [
            ("Siemens + Harju Elekter", "Industrial automation synergy", "score buyer:Siemens target:Harju Elekter", "blue"),
            ("SAP + NovaTech", "Supply chain SaaS acquisition", "score buyer:SAP target:NovaTech Solutions", "indigo"),
            ("Upload & Score", "Score a document against buyers", "docs", "green"),
        ],
    },
    "find-buyers": {
        "title": "Find Buyers",
        "subtitle": "Identify strategic and financial buyers",
        "cards": [
            ("SaaS Company (EUR 15M)", "B2B software with recurring revenue", "buyers company:B2B SaaS revenue:15M", "green"),
            ("Manufacturing (EUR 50M)", "Industrial manufacturer seeking exit", "buyers company:Manufacturing revenue:50M", "blue"),
            ("Tech Platform", "Digital marketplace platform", "buyers company:Tech Platform revenue:10M", "indigo"),
        ],
    },
    "score-pitch-deck": {
        "title": "Score Pitch Deck",
        "subtitle": "Extract key terms and find buyers",
        "cards": [
            ("NovaTech Pitch Deck", "10-page investment presentation", "keyterms NovaTech-Pitch-Deck.pdf", "blue"),
            ("NovaTech Term Sheet", "Draft acquisition terms", "keyterms NovaTech-TermSheet-Draft.pdf", "green"),
            ("Upload New Document", "Analyze your own pitch deck", "docs", "indigo"),
        ],
    },
    "ipo-assessment": {
        "title": "IPO Readiness",
        "subtitle": "Assess public offering readiness",
        "cards": [
            ("Ignitis Group", "Baltic energy utility", "ipo company:Ignitis industry:Energy", "blue"),
            ("Baltic Tech Co", "SaaS platform IPO candidate", "ipo company:Baltic Tech industry:SaaS", "green"),
            ("Nordic Fintech", "Payments company IPO", "ipo company:Nordic Payments industry:Fintech", "indigo"),
        ],
    },
}


def _render_context_cards(context_key: str):
    """Render 3 context-sensitive action cards."""
    ctx = _CONTEXT_CARDS.get(context_key, _CONTEXT_CARDS["default"])
    cards = [_action_card(label, sub, cmd, color) for label, sub, cmd, color in ctx["cards"]]
    return Div(
        Div(
            H2(ctx["title"], cls="text-lg font-bold text-gray-800"),
            P(ctx["subtitle"], cls="text-sm text-gray-500 mt-0.5"),
            cls="text-center mb-4",
        ),
        Div(*cards, cls="grid grid-cols-3 gap-3 max-w-2xl mx-auto"),
    )


def _contextual_chips(context_type: str, data: dict = {}):
    """Context-aware suggestion chips, returned via OOB swap."""
    chip_sets = {
        "buyer_welcome": [
            ("Find energy targets in Nordics", "targets industry:renewable energy geography:Nordics"),
            ("Profile SAP.DE", "profile:SAP.DE"),
            ("Baltic valuation comp", "valuation:TAL1T.TL,EQNR.OL,NESTE.HE"),
            ("Score: Siemens + Harju Elekter", "score buyer:Siemens target:Harju Elekter"),
        ],
        "seller_welcome": [
            ("Find buyers for SaaS company", "buyers company:SaaS revenue:15M"),
            ("View NovaTech pitch deck", "docs"),
            ("IPO readiness: Ignitis", "ipo company:Ignitis"),
            ("Score NovaTech pitch deck", "score doc:NovaTech-Pitch-Deck.pdf"),
        ],
        "post_profile": [
            (f"Financials for {data.get('ticker','')}", f"financials:{data.get('ticker','')}"),
            (f"News about {data.get('ticker','')}", f"news:{data.get('ticker','')}"),
            (f"Find targets in {data.get('industry','this sector')}", f"targets industry:{data.get('industry','')}"),
            (f"Score as buyer", f"score buyer:{data.get('name','')} target:"),
        ],
        "post_score": [
            ("Deep research", f"research:{data.get('target','')} M&A"),
            ("View documents", "docs"),
            ("Deal history", "deals"),
            ("Help", "help"),
        ],
        "post_targets": [
            ("Score top match", f"score buyer: target:{data.get('first_target','')}"),
            ("Deep research", f"research:{data.get('industry','')} M&A targets"),
            ("Market intel", "market"),
            ("Valuation comp", f"valuation:{data.get('tickers','')}"),
        ],
        "post_research": [
            ("Find targets", "targets industry:"),
            ("Find buyers", "buyers company:"),
            ("Score match", "score buyer: target:"),
            ("Market intel", "market"),
        ],
        "default": [
            ("Find targets", "targets industry:renewable energy"),
            ("Find buyers", "buyers company:Enefit Green"),
            ("Company profile", "profile:SAP.DE"),
            ("Help", "help"),
        ],
    }
    pills = chip_sets.get(context_type, chip_sets["default"])
    return Div(
        *[Button(
            label,
            hx_post="/chat",
            hx_vals=json.dumps({"msg": cmd}),
            hx_target="#chat-area",
            hx_swap="beforeend",
            hx_on__before_request=_THINKING_JS,
            hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
            cls="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-1.5 rounded-full hover:border-blue-400 hover:text-blue-700 transition-colors",
        ) for label, cmd in pills],
        id="suggestion-chips",
        hx_swap_oob="true",
        cls="flex flex-wrap gap-2 justify-center mb-4",
    )


def _canvas_tab(label, tab_id, endpoint, active=False):
    """Single canvas tab button."""
    active_cls = "border-b-2 border-blue-600 text-blue-700 font-medium" if active else "text-gray-500 hover:text-gray-700"
    return Button(
        label,
        hx_get=endpoint,
        hx_target="#canvas-content",
        onclick=f"document.querySelectorAll('.canvas-tab').forEach(t=>t.className=t.className.replace(/border-b-2 border-blue-600 text-blue-700 font-medium/g,'text-gray-500 hover:text-gray-700')); this.className=this.className.replace('text-gray-500 hover:text-gray-700','border-b-2 border-blue-600 text-blue-700 font-medium');",
        cls=f"canvas-tab text-xs px-3 py-2 {active_cls}",
        id=f"tab-{tab_id}",
    )

def _right_pane():
    """Right pane — dynamic canvas with tabs: Documents, Research, Scores, Compare."""
    return Div(
        # Header
        Div(
            Div(
                H2("Canvas", cls="text-sm font-semibold text-gray-800", id="canvas-title"),
                Button(
                    "X", cls="text-gray-400 hover:text-gray-600 text-xs font-bold",
                    onclick="document.getElementById('right-pane').classList.add('translate-x-full')",
                ),
                cls="flex items-center justify-between",
            ),
            cls="px-3 py-2 border-b border-gray-200",
        ),
        # Tab bar
        Div(
            _canvas_tab("Documents", "docs", "/canvas/docs", active=True),
            _canvas_tab("Research", "research", "/canvas/research"),
            _canvas_tab("Scores", "scores", "/canvas/scores"),
            _canvas_tab("Compare", "compare", "/canvas/compare"),
            cls="flex border-b border-gray-200",
            id="canvas-tabs",
        ),
        # Content area
        Div(
            _doc_list_for_pane(),
            id="canvas-content",
            cls="flex-1 overflow-y-auto",
        ),
        id="right-pane",
        cls="fixed right-0 top-0 h-screen w-[440px] bg-white border-l border-gray-200 flex flex-col transition-transform duration-300 translate-x-full z-20 shadow-lg",
    )


@rt
def index(session):
    ss = _get_ss(session)
    return (
        Title("LiquidRound"),
        _nav_section(session),
        Main(
            # Header
            Div(
                Div(
                    H1("LiquidRound", cls="text-2xl font-bold text-blue-800"),
                    P("AI-Powered M&A Research Platform", cls="text-sm text-gray-500"),
                    cls="text-center",
                ),
                # Canvas toggle (top-right)
                Button(
                    "Canvas", id="canvas-toggle",
                    onclick="document.getElementById('right-pane').classList.toggle('translate-x-full')",
                    cls="fixed top-3 right-3 z-30 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 shadow-sm hover:bg-blue-50 hover:text-blue-700 cursor-pointer",
                ),
                cls="pt-6 mb-4",
            ),
            # Welcome section (buyer/seller cards)
            Div(_render_context_cards("default"), id="welcome-section"),
            # Suggestion chips (updated dynamically via OOB)
            Div(id="suggestion-chips", cls="flex flex-wrap gap-2 justify-center mb-4"),
            # Chat area
            Div(
                Div(
                    id="chat-area",
                    cls="space-y-2 mb-4 max-h-[calc(100vh-280px)] overflow-y-auto px-2",
                ),
                # Input row: paperclip + text + send
                Div(
                    # Paperclip triggers the hidden upload form's file input
                    Label(
                        NotStr('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'),
                        htmlFor="file-upload",
                        cls="flex items-center justify-center w-10 h-10 border border-gray-300 rounded-xl text-gray-400 hover:text-blue-600 hover:border-blue-400 cursor-pointer transition-colors",
                        title="Upload document (PDF, XLS, PPT)",
                    ),
                    cls="flex items-center",
                ),
                Form(
                    Div(
                        Input(
                            name="msg", placeholder="Ask a question or describe what you're looking for...",
                            autofocus=True, autocomplete="off",
                            cls="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                        ),
                        Button("Send", type="submit",
                               cls="bg-blue-600 text-white px-5 py-3 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"),
                        cls="flex gap-2 items-center flex-1",
                    ),
                    hx_post="/chat",
                    hx_target="#chat-area",
                    hx_swap="beforeend",
                    hx_on__before_request=_THINKING_JS,
                    hx_on__after_request="this.reset(); var t=document.getElementById('thinking-live'); if(t) t.remove(); var ca=document.getElementById('chat-area'); if(ca) ca.scrollTo({top:ca.scrollHeight, behavior:'smooth'}); var ws=document.getElementById('welcome-section'); if(ws) ws.remove();",
                    cls="flex-1",
                ),
                # Upload form — file input triggered by paperclip label
                Form(
                    Input(
                        type="file", name="file", id="file-upload",
                        accept=".pdf,.xlsx,.xls,.pptx,.ppt",
                        cls="hidden",
                        onchange=_THINKING_JS + " document.getElementById('upload-form').requestSubmit();",
                    ),
                    id="upload-form",
                    hx_post="/chat-upload",
                    hx_target="#chat-area",
                    hx_swap="beforeend",
                    hx_encoding="multipart/form-data",
                    hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
                    cls="hidden",
                ),
                cls="max-w-3xl mx-auto flex gap-2 items-center",
            ),
            id="main-content",
            cls="min-h-screen bg-gray-50 px-4 pb-6 ml-56",
        ),
        _right_pane(),
    )


# ---------------------------------------------------------------------------
# Chat endpoint — processes commands and free-form chat
# ---------------------------------------------------------------------------
def _determine_context(msg: str, result_components: list) -> tuple:
    """Determine chip context type and data from the command and results."""
    from utils.command_parser import parse_command
    cmd, subject, params = parse_command(msg)

    # Detect buyer/seller intent from natural language
    msg_lower = msg.lower()
    if cmd is None:
        if any(w in msg_lower for w in ["acquire", "buy", "acquisition", "target"]):
            return "buyer_welcome", {}
        if any(w in msg_lower for w in ["sell", "exit", "raise capital", "buyer"]):
            return "seller_welcome", {}

    if cmd == "profile":
        return "post_profile", {"ticker": subject, "name": subject, "industry": ""}
    if cmd == "score":
        return "post_score", {"target": params.get("target", subject)}
    if cmd in ("targets", "buyers"):
        return "post_targets", {"industry": params.get("industry", subject), "first_target": "", "tickers": ""}
    if cmd == "research":
        return "post_research", {}
    if cmd == "docs":
        return "seller_welcome", {}
    return "default", {}


# ---------------------------------------------------------------------------
# Context cards route
# ---------------------------------------------------------------------------
@rt("/cards/{context_key}")
def context_cards(context_key: str = "default"):
    """Return 3 context-sensitive action cards."""
    return _render_context_cards(context_key)


# ---------------------------------------------------------------------------
# Static workspace pages (not chat)
# ---------------------------------------------------------------------------
@rt("/page/documents")
def page_documents():
    """Static document manager page."""
    files = []
    for folder in DOC_FOLDERS:
        if folder.exists():
            for f in sorted(folder.iterdir()):
                if f.is_file() and f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".pptx", ".ppt"):
                    files.append((f.name, f.suffix.lower(), f"{f.stat().st_size / 1024 / 1024:.1f} MB", str(folder)))
    rows = []
    for fname, ext, size, folder_name in files:
        badge_cls = {".pdf": "bg-red-100 text-red-700", ".xlsx": "bg-green-100 text-green-700", ".pptx": "bg-orange-100 text-orange-700"}.get(ext, "bg-gray-100 text-gray-600")
        rows.append(Tr(
            Td(Span(ext[1:].upper(), cls=f"text-xs font-bold px-1.5 py-0.5 rounded {badge_cls}")),
            Td(Span(fname, cls="text-sm text-gray-800")),
            Td(Span(size, cls="text-xs text-gray-400")),
            Td(
                Button("View", hx_get=f"/doc/panel?fn={fname}", hx_target="#canvas-content",
                       onclick="document.getElementById('right-pane').classList.remove('translate-x-full');",
                       cls="text-xs text-blue-600 hover:underline mr-3"),
                Button("Key Terms", hx_post="/chat", hx_vals=json.dumps({"msg": f"keyterms {fname}"}),
                       hx_target="#chat-area", hx_swap="beforeend",
                       hx_on__before_request=_THINKING_JS,
                       hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
                       cls="text-xs text-purple-600 hover:underline mr-3"),
                Button("Score", hx_post="/chat", hx_vals=json.dumps({"msg": f"score doc:{fname}"}),
                       hx_target="#chat-area", hx_swap="beforeend",
                       hx_on__before_request=_THINKING_JS,
                       hx_on__after_request="var t=document.getElementById('thinking-live'); if(t) t.remove();",
                       cls="text-xs text-green-600 hover:underline"),
            ),
        ))
    return Div(
        H1("Documents", cls="text-xl font-bold text-gray-800 mb-1"),
        P(f"{len(files)} files available", cls="text-sm text-gray-500 mb-4"),
        Table(
            Thead(Tr(*[Th(h, cls="text-xs text-gray-500 text-left py-2 px-2") for h in ["Type", "Name", "Size", "Actions"]])),
            Tbody(*rows),
            cls="w-full",
        ) if rows else P("No documents yet. Upload via the paperclip button.", cls="text-sm text-gray-400 italic"),
        cls="p-6 max-w-4xl",
    )


@rt("/page/deals")
def page_deals():
    """Deal history with Plotly dashboard."""
    from utils.database import db_service
    from components.charts import DealsByTypeChart, DealTimelineChart, DealStatusPie
    from components.cards import MetricCard

    stats = db_service.get_deal_stats()
    recent = db_service.get_recent_workflows(15)

    # Metrics row
    metrics = Div(
        MetricCard("Total Workflows", stats["total"], color="blue"),
        MetricCard("Conversations", stats["by_type"].get("conversation", 0), color="green"),
        MetricCard("Completed", stats["by_status"].get("completed", 0), color="green"),
        MetricCard("Active", stats["by_status"].get("active", 0), color="yellow"),
        cls="grid grid-cols-4 gap-3 mb-6",
    )

    # Charts row
    charts = Div(
        Div(DealsByTypeChart("deals-by-type", stats["by_type"]), cls="bg-white rounded-lg p-4 border border-gray-200"),
        Div(DealTimelineChart("deals-timeline", stats["timeline"]), cls="bg-white rounded-lg p-4 border border-gray-200"),
        Div(DealStatusPie("deals-status", stats["by_status"]), cls="bg-white rounded-lg p-4 border border-gray-200"),
        cls="grid grid-cols-3 gap-3 mb-6",
    )

    # Recent table
    table_rows = []
    for w in recent:
        status_cls = {"completed": "bg-green-100 text-green-700", "active": "bg-blue-100 text-blue-700", "failed": "bg-red-100 text-red-700", "pending": "bg-yellow-100 text-yellow-700"}.get(w.get("status",""), "bg-gray-100 text-gray-600")
        table_rows.append(Tr(
            Td(Span(w.get("workflow_type","").replace("_"," ").title(), cls="text-xs font-medium")),
            Td(Span(w.get("user_query","")[:60], cls="text-xs text-gray-600")),
            Td(Span(w.get("status",""), cls=f"text-xs px-2 py-0.5 rounded-full {status_cls}")),
            Td(Span(w.get("created_at","")[:16], cls="text-xs text-gray-400")),
        ))

    table = Table(
        Thead(Tr(*[Th(h, cls="text-xs text-gray-500 text-left py-2") for h in ["Type", "Query", "Status", "Created"]])),
        Tbody(*table_rows),
        cls="w-full",
    ) if table_rows else P("No workflows yet.", cls="text-sm text-gray-400 italic")

    return Div(
        H1("Deal History", cls="text-xl font-bold text-gray-800 mb-1"),
        P("Workflow activity and analytics", cls="text-sm text-gray-500 mb-4"),
        metrics,
        charts,
        H2("Recent Workflows", cls="text-sm font-bold text-gray-700 mb-2"),
        Div(table, cls="bg-white rounded-lg p-4 border border-gray-200"),
        cls="p-6",
    )


@rt("/page/tools")
def page_tools():
    """Static M&A tools page."""
    tools = [
        ("Deal Room", "Secure virtual data room for due diligence", "Available", "green"),
        ("CIM Generator", "Confidential Information Memorandum builder", "Available", "green"),
        ("Comparable Transactions", "Transaction comp analysis", "Available", "green"),
        ("LOI Drafter", "Letter of Intent template generator", "Available", "green"),
        ("DD Checklist", "Due diligence checklist management", "Available", "green"),
        ("Regulatory Screening", "Cross-border regulatory analysis", "Beta", "yellow"),
        ("Stakeholder Mapping", "Key stakeholder identification", "Beta", "yellow"),
        ("Integration Playbook", "Post-merger integration planning", "Beta", "yellow"),
        ("Pipeline CRM", "Deal pipeline management", "Available", "green"),
    ]
    cards = []
    for name, desc, status, color in tools:
        status_cls = f"bg-{color}-100 text-{color}-700"
        cards.append(Div(
            Div(
                Span(name, cls="text-sm font-medium text-gray-800"),
                Span(status, cls=f"text-xs px-2 py-0.5 rounded-full {status_cls}"),
                cls="flex items-center justify-between mb-1",
            ),
            P(desc, cls="text-xs text-gray-500"),
            cls="bg-white rounded-lg p-4 border border-gray-200 hover:shadow-sm transition-shadow",
        ))
    return Div(
        H1("M&A Tools", cls="text-xl font-bold text-gray-800 mb-1"),
        P("Platform tools for deal execution", cls="text-sm text-gray-500 mb-4"),
        Div(*cards, cls="grid grid-cols-3 gap-3"),
        cls="p-6",
    )


# ---------------------------------------------------------------------------
# Conversation management (logged-in users)
# ---------------------------------------------------------------------------
@rt("/conversation/new")
def conversation_new(session):
    """Start a new conversation."""
    session.pop("conversation_id", None)
    return RedirectResponse("/", status_code=303)

@rt("/conversation/{conv_id}")
def conversation_load(session, conv_id: str):
    """Load a previous conversation's messages into the chat area."""
    user = session.get("user")
    if not user:
        return ""
    from utils.database import db_service
    messages = db_service.get_messages(conv_id)
    session["conversation_id"] = conv_id
    parts = []
    for m in messages:
        if m["role"] == "user":
            parts.append(_user_bubble(m["content"]))
        else:
            parts.append(_assistant_bubble(Div(NotStr(m["content"]), cls="text-sm text-gray-800 leading-relaxed")))
    if not parts:
        parts.append(_assistant_bubble(P("Empty conversation.", cls="text-sm text-gray-400")))
    return Div(*parts)

@rt("/conversations")
def conversations_list(session):
    """Return conversation list HTML partial for nav sidebar."""
    user = session.get("user")
    if not user:
        return ""
    from utils.database import db_service
    convs = db_service.get_user_conversations(user["user_id"], limit=20)
    return _conversation_list_html(convs, session.get("conversation_id"))

@rt("/conversations/search")
def conversations_search(session, q: str = ""):
    """Search conversations by title."""
    user = session.get("user")
    if not user:
        return ""
    from utils.database import db_service
    if q.strip():
        convs = db_service.search_conversations(user["user_id"], q.strip())
    else:
        convs = db_service.get_user_conversations(user["user_id"], limit=20)
    return _conversation_list_html(convs, session.get("conversation_id"))

def _conversation_list_html(convs, active_id=None):
    """Render conversation list items."""
    if not convs:
        return P("No conversations yet.", cls="text-xs text-gray-400 italic px-3 py-2")
    items = []
    for c in convs:
        title = c.get("conversation_title") or c.get("user_query", "Untitled")
        title = title[:50] + "..." if len(title) > 50 else title
        is_active = c["id"] == active_id if active_id else False
        active_cls = "bg-blue-50 text-blue-700" if is_active else "text-gray-600 hover:bg-gray-50"
        items.append(
            A(
                Span(title, cls="text-xs truncate block"),
                hx_get=f"/conversation/{c['id']}",
                hx_target="#chat-area",
                hx_swap="innerHTML",
                onclick=f"document.getElementById('welcome-section')?.remove();",
                cls=f"block px-3 py-1.5 rounded cursor-pointer transition-colors {active_cls}",
            )
        )
    return Div(*items)


@rt("/chat")
async def chat(session, msg: str = ""):
    if not msg.strip():
        return ""

    from agents.render_agent import render_agent

    # User bubble
    parts = [_user_bubble(msg)]

    # Special: clear
    if msg.strip().lower() in ("clear", "cls"):
        session.pop("conversation_id", None)
        return Div(
            _assistant_bubble(P("Chat cleared.", cls="text-sm text-gray-500")),
            Script("document.getElementById('chat-area').innerHTML = '';"),
        )

    # Persist user message (logged-in users only)
    user = session.get("user")
    conv_id = session.get("conversation_id") if user else None
    if user and not conv_id:
        try:
            from utils.database import db_service
            conv_id = db_service.create_conversation(user["user_id"], msg[:200])
            session["conversation_id"] = conv_id
        except Exception:
            conv_id = None
    if conv_id:
        try:
            from utils.database import db_service
            db_service.add_message(conv_id, "user", msg)
            db_service.update_conversation_timestamp(conv_id)
        except Exception:
            pass

    # Process with render agent
    response_text = ""
    try:
        result_components = await render_agent.process(msg)
        if result_components:
            parts.append(_assistant_bubble(*result_components))
            response_text = msg  # Fallback: store the query as context
        else:
            parts.append(_assistant_bubble(P("Done.", cls="text-sm text-gray-500")))
            response_text = "Done."
    except Exception as e:
        parts.append(_assistant_bubble(P(f"Error: {str(e)[:300]}", cls="text-sm text-red-600")))
        response_text = f"Error: {str(e)[:300]}"

    # Persist assistant response
    if conv_id:
        try:
            from utils.database import db_service
            db_service.add_message(conv_id, "assistant", response_text)
        except Exception:
            pass

    # Contextual suggestion chips (OOB swap)
    context_type, context_data = _determine_context(msg, parts)
    parts.append(_contextual_chips(context_type, context_data))

    # Auto-open canvas for document/score/research commands
    from utils.command_parser import parse_command
    cmd, subject, params = parse_command(msg)

    # Detect pitch deck / term sheet references in free-form text
    msg_lower = msg.lower()
    if cmd is None and ("pitch deck" in msg_lower or "term sheet" in msg_lower):
        pitch_path = DOCS_DATA_DIR / "NovaTech-Pitch-Deck.pdf"
        if pitch_path.exists():
            fn = "NovaTech-TermSheet-Draft.pdf" if "term sheet" in msg_lower else "NovaTech-Pitch-Deck.pdf"
            parts.append(Script(
                f"document.getElementById('right-pane').classList.remove('translate-x-full');"
                f"htmx.ajax('GET', '/doc/panel?fn={fn}', '#canvas-content');"
            ))

    # Refresh conversation list in nav (OOB)
    if conv_id:
        parts.append(Div(
            hx_get="/conversations",
            hx_trigger="load",
            hx_target="#chat-history",
            hx_swap="innerHTML",
            id="chat-history-refresh",
            hx_swap_oob="true",
            cls="hidden",
        ))

    return Div(*parts)


# ---------------------------------------------------------------------------
# File upload via chat (drag-drop or button)
# ---------------------------------------------------------------------------
@rt("/chat-upload")
async def chat_upload(file: UploadFile):
    if not file or not file.filename:
        return _assistant_bubble(P("No file selected.", cls="text-sm text-red-500"))

    ext = Path(file.filename).suffix.lower()
    allowed = {".xlsx", ".xls", ".pptx", ".ppt", ".pdf"}
    if ext not in allowed:
        return _assistant_bubble(P(f"Unsupported: {ext}", cls="text-sm text-red-500"))

    content = await file.read()
    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(content)

    from utils.document_parser import document_parser
    parsed = document_parser.parse(str(save_path))
    from components.upload_form import UploadResult
    return Div(
        _user_bubble(f"Uploaded: {file.filename}"),
        _assistant_bubble(
            UploadResult(parsed),
            Div(
                Button(
                    "Score: Find Buyers",
                    hx_post="/chat",
                    hx_vals=json.dumps({"msg": f"score doc:{file.filename}"}),
                    hx_target="#chat-area",
                    hx_swap="beforeend",
                    cls="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 mt-3",
                ),
            ),
        ),
        # Open document in right pane
        Script(f"document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/doc/panel?fn={file.filename}', '#canvas-content');"),
    )


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------
serve(port=int(os.getenv("PORT", "5007")))
