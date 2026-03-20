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
        Link(rel="stylesheet", href="/static/app.css"),
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

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Document serving routes
# ---------------------------------------------------------------------------
@rt("/doc/view")
async def doc_view(fn: str = ""):
    """Serve a document file (PDF, etc.) from docs/ or uploads/."""
    if not fn:
        return Response("Missing filename", status_code=400)
    filename = Path(fn).name
    for folder in [DOCS_DIR, UPLOAD_DIR]:
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
        Button(
            "Score: Find Buyers",
            hx_post="/chat",
            hx_vals=json.dumps({"msg": f"score doc:{filename}"}),
            hx_target="#chat-area",
            hx_swap="beforeend",
            cls="w-full mt-3 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700",
        ),
        cls="p-3 h-full flex flex-col",
    )


def _doc_list_for_pane():
    """List all available documents in docs/ and uploads/."""
    files = []
    for folder in [DOCS_DIR, UPLOAD_DIR]:
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
                    Button("View", hx_get=f"/doc/panel?fn={fname}", hx_target="#doc-pane-content", cls="text-xs text-blue-600 hover:underline"),
                    Button("Score", hx_post="/chat", hx_vals=json.dumps({"msg": f"score doc:{fname}"}), hx_target="#chat-area", hx_swap="beforeend", cls="text-xs text-green-600 hover:underline ml-2"),
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


def _nav_section(session):
    """Left navigation — visible by default, toggleable."""
    user = session.get("user")
    nav_items = [
        ("targets industry:renewable energy", "Find Targets"),
        ("buyers company:Enefit Green", "Find Buyers"),
        ("ipo company:Ignitis", "IPO Assessment"),
        ("profile:SAP.DE", "Company Profile"),
        ("news:NOVO-B.CO", "Company News"),
        ("financials:SIE.DE", "Financials"),
        ("valuation:TAL1T.TL,EQNR.OL,NESTE.HE", "Valuation Comp"),
        ("score buyer:Siemens target:Harju Elekter", "Score Match"),
        ("research:Baltic M&A renewable energy", "Deep Research"),
        ("docs", "Documents"),
        ("deals", "Deal History"),
        ("market", "Market Intel"),
        ("tools", "M&A Tools"),
        ("settings", "Settings"),
        ("help", "Help"),
    ]
    shortcut_buttons = [
        Button(
            label,
            hx_post="/chat",
            hx_vals=json.dumps({"msg": cmd}),
            hx_target="#chat-area",
            hx_swap="beforeend",
            cls="text-left text-xs text-gray-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded transition-colors w-full",
        )
        for cmd, label in nav_items
    ]

    # Auth section (bottom-left, optional)
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
        # Toggle button
        Button(
            Span("LiquidRound", cls="text-xs font-bold text-blue-700"),
            Span("beta", cls="text-xs text-gray-400 ml-1"),
            id="nav-toggle",
            onclick="document.getElementById('nav-panel').classList.toggle('hidden')",
            cls="fixed top-3 left-3 z-30 bg-white border border-gray-200 rounded-lg px-3 py-1.5 flex items-center shadow-sm hover:bg-blue-50 cursor-pointer",
        ),
        # Collapsible nav panel
        Div(
            Div(
                H2("LiquidRound", cls="text-sm font-bold text-blue-800"),
                P("M&A Research", cls="text-xs text-gray-400"),
                cls="px-3 py-3 border-b border-gray-200",
            ),
            Div(
                P("Shortcuts", cls="text-xs font-semibold text-gray-400 uppercase tracking-wide px-3 mb-1"),
                *shortcut_buttons,
                cls="flex-1 overflow-y-auto py-2",
            ),
            auth_section,
            Div(P("Predictive Labs Ltd", cls="text-xs text-gray-300 text-center py-1")),
            id="nav-panel",
            cls="fixed left-0 top-0 h-screen w-56 bg-white border-r border-gray-200 z-20 flex flex-col shadow-lg",
        ),
    )


def _sample_pills():
    """Quick-start pills above chat input."""
    pills = [
        ("profile:SAP.DE", "SAP Profile"),
        ("news:NOVO-B.CO", "Novo Nordisk News"),
        ("valuation:TAL1T.TL,TSM1T.TL,IGN1L.VS", "Baltic Valuation"),
        ("targets industry:renewable energy", "Energy Targets"),
        ("score buyer:Siemens target:Harju Elekter", "Score Match"),
        ("help", "Commands"),
    ]
    return Div(
        *[Button(
            label,
            hx_post="/chat",
            hx_vals=json.dumps({"msg": cmd}),
            hx_target="#chat-area",
            hx_swap="beforeend",
            cls="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-1.5 rounded-full hover:border-blue-400 hover:text-blue-700 transition-colors",
        ) for cmd, label in pills],
        cls="flex flex-wrap gap-2 justify-center mb-4",
    )


def _right_pane():
    """Right pane — document viewer and file browser."""
    return Div(
        Div(
            Div(
                H2("Documents", cls="text-sm font-semibold text-gray-800"),
                Button(
                    "X", cls="text-gray-400 hover:text-gray-600 text-xs font-bold",
                    onclick="document.getElementById('right-pane').classList.add('translate-x-full')",
                ),
                cls="flex items-center justify-between",
            ),
            cls="px-3 py-2 border-b border-gray-200",
        ),
        Div(
            _doc_list_for_pane(),
            id="doc-pane-content",
            cls="flex-1 overflow-y-auto",
        ),
        id="right-pane",
        cls="fixed right-0 top-0 h-screen w-96 bg-white border-l border-gray-200 flex flex-col transition-transform duration-300 translate-x-full z-20 shadow-lg",
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
                # Doc pane toggle (top-right)
                Button(
                    "Docs", id="doc-toggle",
                    onclick="document.getElementById('right-pane').classList.toggle('translate-x-full')",
                    cls="fixed top-3 right-3 z-30 bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 shadow-sm hover:bg-blue-50 hover:text-blue-700 cursor-pointer",
                ),
                cls="pt-6 mb-4",
            ),
            # Sample pills
            _sample_pills(),
            # Chat area
            Div(
                Div(
                    _assistant_bubble(
                        P("Welcome! I'm your M&A research assistant. Try a command like ", cls="text-sm text-gray-600"),
                        Div(
                            Code("profile:SAP.DE", cls="bg-gray-100 px-1.5 py-0.5 rounded text-xs"),
                            Code("news:NOVO-B.CO", cls="bg-gray-100 px-1.5 py-0.5 rounded text-xs ml-1"),
                            Code("valuation:TAL1T.TL,IGN1L.VS", cls="bg-gray-100 px-1.5 py-0.5 rounded text-xs ml-1"),
                            cls="mt-1",
                        ),
                        P("or just ask a question in plain English.", cls="text-sm text-gray-600 mt-1"),
                    ),
                    id="chat-area",
                    cls="space-y-2 mb-4 max-h-[calc(100vh-260px)] overflow-y-auto px-2",
                ),
                # Input row: paperclip + text + send
                Form(
                    Div(
                        # Paperclip upload
                        Label(
                            NotStr('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'),
                            htmlFor="file-upload",
                            cls="flex items-center justify-center w-10 h-10 border border-gray-300 rounded-xl text-gray-400 hover:text-blue-600 hover:border-blue-400 cursor-pointer transition-colors",
                            title="Upload document (PDF, XLS, PPT)",
                        ),
                        Input(
                            type="file", name="file", id="file-upload",
                            accept=".pdf,.xlsx,.xls,.pptx,.ppt",
                            cls="hidden",
                            onchange="document.getElementById('upload-form').requestSubmit()",
                        ),
                        Input(
                            name="msg", placeholder="Type a command or question... (try help)",
                            autofocus=True, autocomplete="off",
                            cls="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                        ),
                        Button("Send", type="submit",
                               cls="bg-blue-600 text-white px-5 py-3 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"),
                        cls="flex gap-2 items-center",
                    ),
                    hx_post="/chat",
                    hx_target="#chat-area",
                    hx_swap="beforeend",
                    hx_on__after_request="this.reset(); document.getElementById('chat-area').scrollTo({top: document.getElementById('chat-area').scrollHeight, behavior: 'smooth'});",
                ),
                # Hidden upload form
                Form(
                    Input(type="file", name="file", id="file-upload-hidden", cls="hidden",
                          accept=".pdf,.xlsx,.xls,.pptx,.ppt"),
                    id="upload-form",
                    hx_post="/chat-upload",
                    hx_target="#chat-area",
                    hx_swap="beforeend",
                    hx_encoding="multipart/form-data",
                    cls="hidden",
                ),
                cls="max-w-3xl mx-auto",
            ),
            cls="min-h-screen bg-gray-50 px-4 pb-6 ml-56",
        ),
        _right_pane(),
    )


# ---------------------------------------------------------------------------
# Chat endpoint — processes commands and free-form chat
# ---------------------------------------------------------------------------
@rt("/chat")
async def chat(msg: str = ""):
    if not msg.strip():
        return ""

    from agents.render_agent import render_agent

    # User bubble
    parts = [_user_bubble(msg)]

    # Special: clear
    if msg.strip().lower() in ("clear", "cls"):
        return Div(
            _assistant_bubble(P("Chat cleared.", cls="text-sm text-gray-500")),
            Script("document.getElementById('chat-area').innerHTML = '';"),
        )

    # Process with render agent
    try:
        result_components = await render_agent.process(msg)
        if result_components:
            parts.append(_assistant_bubble(*result_components))
        else:
            parts.append(_assistant_bubble(P("Done.", cls="text-sm text-gray-500")))
    except Exception as e:
        parts.append(_assistant_bubble(P(f"Error: {str(e)[:300]}", cls="text-sm text-red-600")))

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
        Script(f"document.getElementById('right-pane').classList.remove('translate-x-full'); htmx.ajax('GET', '/doc/panel/{file.filename}', '#doc-pane-content');"),
    )


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------
serve(port=int(os.getenv("PORT", "5007")))
