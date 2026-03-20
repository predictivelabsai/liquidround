# LiquidRound - AI-Powered M&A Investment Research Platform

## Project Overview

LiquidRound helps **buyers find acquisition targets** and **sellers find merger targets / buyers**. It is an AI-powered multi-agent M&A and IPO deal flow platform by Predictive Labs Ltd.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Web Framework** | FastHTML (server-rendered hypermedia, HTMX) |
| **CSS** | Tailwind CSS via CDN |
| **LLM Provider** | XAI (Grok) as primary, swappable via LangChain |
| **LLM Orchestration** | LangChain + LangGraph |
| **Research APIs** | EXA (semantic search), TAVILY (web search) |
| **Financial Data** | yfinance (company profiles, market cap, fundamentals) |
| **Database** | PostgreSQL (schema `liquidround` on remote server) |
| **Real-time Updates** | HTMX SSE (Server-Sent Events) |
| **File Processing** | python-pptx (PPT), openpyxl (XLS/XLSX), PyMuPDF/pdfplumber (PDF) |
| **Charts** | Plotly.js (embedded via FastHTML Script tags) |

## Architecture

### 3-Pane Layout

```
┌──────────────┬──────────────────────────┬──────────────────────┐
│  LEFT PANE   │      MIDDLE PANE         │    RIGHT PANE        │
│  (240px)     │      (flex-1)            │    (slide-out, 400px)│
│              │                          │                      │
│  Shortcuts   │  Sample Query Buttons    │  Research Panel      │
│  & Commands  │  (2 rows x 3 cols)      │  (popup/slide-out)   │
│              │                          │                      │
│  - Buyer MA  │  Chat Interface          │  EXA Results         │
│  - Seller MA │  (HTMX websocket/SSE)   │  TAVILY Results      │
│  - IPO       │                          │  Thinking Trace      │
│  - Upload    │  Agent Progress          │  Source Links        │
│  - Score     │  (real-time via SSE)     │  Timestamps          │
│  - History   │                          │                      │
│  - Settings  │  Results Display         │                      │
│              │  (expandable cards)      │                      │
└──────────────┴──────────────────────────┴──────────────────────┘
```

### File Structure

```
liquidround/
├── main.py                    # FastHTML app entry point (replaces Home.py)
├── CLAUDE.md                  # This file
├── .env                       # API keys (XAI_API, EXA_API_KEY, TAVILY_API_KEY)
├── requirements.txt           # Python dependencies
│
├── routes/                    # FastHTML route modules (APIRouter)
│   ├── __init__.py
│   ├── home.py               # Main 3-pane layout, chat, sample buttons
│   ├── deals.py              # Deal management views
│   ├── market.py             # Market intelligence views
│   ├── upload.py             # File upload handlers (XLS, PPT, PDF)
│   ├── research.py           # EXA/TAVILY research panel endpoints
│   └── api.py                # JSON API endpoints for HTMX
│
├── agents/                    # Multi-agent system
│   ├── __init__.py
│   ├── base_agent.py         # Base class (LangChain + XAI)
│   ├── orchestrator.py       # Routes queries to workflows
│   ├── target_finder.py      # Identifies acquisition targets
│   ├── valuer.py             # Financial valuation (DCF, comps)
│   ├── scoring_agent.py      # NEW: Match scoring with synergy dimensions
│   ├── research_agent.py     # NEW: EXA + TAVILY deep research
│   ├── document_agent.py     # NEW: XLS/PPT/PDF analysis agent
│   └── workflow.py           # LangGraph workflow definition
│
├── prompts/                   # LLM system prompts (Markdown)
│   ├── orchestrator.md
│   ├── target_finder.md
│   ├── valuer.md
│   ├── scoring.md            # NEW: Scoring agent prompt
│   ├── synergy_analyst.md
│   ├── bid_strategist.md
│   ├── seller_prep.md
│   ├── market_outreach.md
│   ├── ipo_readiness_assessor.md
│   └── memo_writer.md
│
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── config.py             # Config (XAI, EXA, TAVILY keys)
│   ├── state.py              # LangGraph state management
│   ├── database.py           # SQLite via fastlite
│   ├── logging.py            # Logging framework
│   ├── llm_factory.py        # NEW: LangChain LLM factory (XAI/OpenAI/Anthropic swap)
│   ├── research_tools.py     # NEW: EXA + TAVILY search wrappers
│   ├── document_parser.py    # NEW: XLS/PPT/PDF parsing utilities
│   ├── yfinance_util.py      # NEW: yfinance company data wrapper
│   ├── workflow_service.py   # Workflow orchestration service
│   ├── market_intelligence.py # Sector performance analysis
│   └── companies_house_api.py # UK Companies House
│
├── components/                # NEW: Reusable FastHTML FT components
│   ├── __init__.py
│   ├── layout.py             # 3-pane shell, nav, header
│   ├── cards.py              # Deal cards, target cards, score cards
│   ├── chat.py               # Chat input, message bubbles
│   ├── research_panel.py     # Right-pane research/thinking trace
│   ├── upload_form.py        # File upload drag-and-drop
│   └── charts.py             # Plotly chart wrappers
│
├── static/                    # Static assets
│   └── app.css               # Custom Tailwind overrides if needed
│
├── db/                        # (legacy — now using remote PostgreSQL)
│
├── sql/                       # Schema definitions
│   └── create-tables.sql
│
├── uploads/                   # Uploaded documents directory
│
├── tests/                     # Test suite
│   ├── test_agents.py
│   ├── test_scoring.py
│   ├── test_research.py
│   └── test_upload.py
│
└── test-data/                 # Test fixtures
```

## Key Design Decisions

### 1. FastHTML + HTMX (not React/Vue)
- Server-rendered HTML with HTMX for interactivity
- SSE for real-time agent progress streaming
- WebSockets for chat interface
- No client-side JS framework (FastHTML constraint)

### 2. Tailwind CSS
- Via CDN `<script src="https://cdn.tailwindcss.com"></script>`
- No Pico CSS (`pico=False` in `fast_app()`)
- Utility-first classes for all styling

### 3. XAI as Primary LLM via LangChain
- `ChatOpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API, model="grok-3-mini-fast")`
- LangChain abstraction allows swapping to OpenAI, Anthropic, etc.
- Factory pattern in `utils/llm_factory.py`

### 4. Research Panel (Right Pane)
- Slide-out panel triggered by research actions
- Shows EXA semantic search results with links
- Shows TAVILY web search results with snippets
- Displays LLM thinking trace / reasoning steps
- Updated via HTMX `hx-get` with `hx-swap="innerHTML"`

### 5. yfinance for Company Data
- Company profiles, market cap, sector, industry
- Financial statements (revenue, EBITDA, margins)
- NOT for real-time price tracking (this is research, not trading)

### 6. Scoring Agent Dimensions
The scoring agent evaluates buyer-target matches across:
- **Revenue Synergies** (0-10): Cross-sell, market expansion, pricing power
- **Cost Synergies** (0-10): Operational overlap, procurement, headcount
- **Strategic Fit** (0-10): Vision alignment, market positioning, competitive moat
- **Cultural Fit** (0-10): Management style, org structure, geographic overlap
- **Financial Health** (0-10): Balance sheet strength, cash flow, debt capacity
- **Integration Risk** (0-10, inverted): Technical complexity, regulatory, timeline
- **Market Timing** (0-10): Sector trends, valuation cycle, macro conditions

## Authentication

- **Sign up**: Email/password or Google OAuth
- **Sign in**: Email/password or Google OAuth
- **Password reset**: Token-based (1-hour expiry)
- **Session**: FastHTML session middleware with `SESSION_SECRET`
- **Beforeware**: All routes protected except `/signin`, `/register`, `/login`, `/logout`, `/forgot`, `/reset`
- **User isolation**: `user_id` column on `workflows`, `deals`, `documents` tables
- **Password hashing**: bcrypt
- **Google OAuth**: authlib (OpenID Connect)

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (serves on port 5001)
python main.py

# Run with Docker
docker compose up --build
```

## Environment Variables (.env)

```
XAI_API_KEY=...              # XAI/Grok API key (primary LLM)
OPENAI_API_KEY=...           # OpenAI key (fallback LLM)
EXA_API_KEY=...              # Exa.ai semantic search
TAVILY_API_KEY=...           # Tavily web search
DB_URL=postgresql://user:pass@host:5432/dbname  # PostgreSQL (schema: liquidround)
DEFAULT_MODEL=grok-3-mini-fast
DEFAULT_TEMPERATURE=0.7
ENVIRONMENT=development
```

## Conventions

- FastHTML routes use decorator `@rt` with function-name-as-path
- FT components are Python functions returning FastTags (Div, P, H1, etc.)
- HTMX attributes: `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `hx_trigger`
- Use `serve()` to run (no `if __name__ == "__main__"` needed)
- Prefer Python over JS; use vanilla JS only when necessary
- No React, Vue, or Svelte (FastHTML constraint)
- Use `NotStr()` for raw HTML (e.g., markdown rendering)
- Use SSE for streaming agent responses
- All database operations through `utils/database.py` (psycopg2 → PostgreSQL `liquidround` schema)
- No local SQLite — remote PostgreSQL only
