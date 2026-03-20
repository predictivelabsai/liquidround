# LiquidRound: Streamlit → FastHTML Migration Plan

## Phase 1: Foundation (Core Infrastructure)

### 1.1 Update Dependencies
**File: `requirements.txt`**
```
# Remove
- streamlit

# Add
python-fasthtml
fastlite
httpx
python-pptx        # PPT parsing
openpyxl           # XLS/XLSX parsing
pdfplumber         # PDF parsing
exa-py             # EXA search SDK
tavily-python      # Tavily search SDK
langchain-xai      # XAI/Grok via LangChain (or use langchain-openai with base_url)
```

### 1.2 LLM Factory — Swap LLMs via LangChain
**File: `utils/llm_factory.py`**
- `create_llm(provider="xai", model="grok-3-mini-fast")` → returns `ChatOpenAI` instance
- Supported providers: `xai` (default), `openai`, `anthropic`
- XAI uses `ChatOpenAI(base_url="https://api.x.ai/v1")` — OpenAI-compatible
- Config reads from `.env`: `XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

### 1.3 Update Config
**File: `utils/config.py`**
- Add `xai_api_key`, `tavily_api_key` fields
- Change `default_model` to `grok-3-mini-fast`
- Remove hard dependency on `openai_api_key` (make optional alongside XAI)

### 1.4 Update Base Agent
**File: `agents/base_agent.py`**
- Replace direct `ChatOpenAI(model="gpt-4.1-nano")` with `llm_factory.create_llm()`
- All agents automatically use XAI/Grok, swappable via config

---

## Phase 2: FastHTML App Shell (3-Pane Layout)

### 2.1 Main App Entry Point
**File: `main.py`** (replaces `Home.py`)
```python
from fasthtml.common import *

app, rt = fast_app(
    pico=False,
    hdrs=(
        Script(src="https://cdn.tailwindcss.com"),
        Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
        Script(src="https://unpkg.com/htmx-ext-sse@2.2.3/sse.js"),
        Link(rel="stylesheet", href="/static/app.css"),
    )
)
```

### 2.2 Layout Components
**File: `components/layout.py`**

Three-pane shell:
- **Left sidebar** (w-60, fixed): Navigation shortcuts & commands
- **Middle content** (flex-1): Sample buttons + chat + results
- **Right panel** (w-96, slide-out): Research links & thinking trace

```
def Shell(*children, research_open=False):
    return Div(
        LeftPane(),
        Div(*children, cls="flex-1 overflow-y-auto p-6"),
        RightPane(open=research_open),
        cls="flex h-screen bg-gray-50"
    )
```

### 2.3 Left Pane — Shortcuts & Commands
**File: `components/layout.py` → `LeftPane()`**

Navigation items:
- 🔍 **Find Targets** — buyer-led M&A search
- 🏷️ **Find Buyers** — seller-led matching
- 📊 **IPO Assessment** — IPO readiness
- 📁 **Upload Documents** — XLS/PPT/PDF upload
- ⚖️ **Score Match** — synergy scoring
- 📈 **Market Intel** — sector heatmaps
- 🏢 **Company Search** — yfinance lookup
- 📋 **Deal History** — past workflows
- ⚙️ **Settings** — LLM provider, model selection

Each item is a button with `hx_get` that loads content into middle pane.

### 2.4 Middle Pane — Sample Buttons + Chat
**File: `routes/home.py`**

Top section: 6 sample query buttons (2 rows x 3 cols) with Tailwind grid
- "Find Fintech Targets ($20-100M)"
- "Healthcare SaaS Acquisitions"
- "Prepare Company for Sale"
- "Find Strategic Buyers"
- "IPO Readiness Assessment"
- "Score Acquisition Match"

Below: Chat input form with `hx_post` → triggers workflow → SSE streams progress

### 2.5 Right Pane — Research & Thinking Trace
**File: `components/research_panel.py`**

Slide-out panel (hidden by default, toggled via HTMX):
- **EXA Results**: Semantic search results with titles, URLs, snippets
- **TAVILY Results**: Web search results with source links
- **Thinking Trace**: Step-by-step reasoning from the LLM
- **Timestamps**: When each research step was executed
- Updated via `hx_get="/research/{workflow_id}"` polling or SSE

---

## Phase 3: Research Integration (EXA + TAVILY)

### 3.1 Research Tools
**File: `utils/research_tools.py`**

```python
class ResearchTools:
    async def exa_search(query, num_results=10) -> list[dict]
        # Semantic search via EXA API
        # Returns: [{title, url, snippet, score, published_date}]

    async def tavily_search(query, search_depth="advanced") -> list[dict]
        # Web search via Tavily API
        # Returns: [{title, url, content, score}]

    async def deep_research(query) -> dict
        # Combined EXA + TAVILY search
        # Returns: {exa_results, tavily_results, thinking_trace}
```

### 3.2 Research Agent
**File: `agents/research_agent.py`**

New agent that:
1. Takes a user query or company name
2. Runs parallel EXA semantic search + TAVILY web search
3. Synthesizes findings into structured research brief
4. Stores thinking trace for display in right pane
5. Returns: research_summary, sources, thinking_trace

### 3.3 Research Panel SSE Endpoint
**File: `routes/research.py`**

- `GET /research/{workflow_id}` — returns current research state as HTML partial
- `GET /research/stream/{workflow_id}` — SSE stream for real-time updates
- Each research step emits an SSE event → right pane updates incrementally

---

## Phase 4: Scoring Agent

### 4.1 Scoring Agent Implementation
**File: `agents/scoring_agent.py`**

Scores buyer-target match across 7 synergy dimensions (0-10 each):

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| Revenue Synergies | 20% | Cross-sell, market expansion, pricing power |
| Cost Synergies | 20% | Operational overlap, procurement, headcount |
| Strategic Fit | 15% | Vision alignment, market positioning, moat |
| Cultural Fit | 10% | Management style, org structure, values |
| Financial Health | 15% | Balance sheet, cash flow, debt capacity |
| Integration Risk | 10% | Technical complexity, regulatory, timeline (inverted) |
| Market Timing | 10% | Sector trends, valuation cycle, macro |

**Weighted composite score** = sum(dimension_score × weight) → 0-100

**Output format:**
```json
{
    "buyer": "Company A",
    "target": "Company B",
    "composite_score": 78,
    "dimensions": {
        "revenue_synergies": {"score": 8, "reasoning": "..."},
        "cost_synergies": {"score": 7, "reasoning": "..."},
        ...
    },
    "recommendation": "STRONG BUY / PROCEED / CAUTIOUS / PASS",
    "key_risks": ["...", "..."],
    "next_steps": ["...", "..."]
}
```

### 4.2 Scoring Prompt
**File: `prompts/scoring.md`**

Structured prompt that instructs the LLM to:
- Analyze buyer and target across all 7 dimensions
- Provide specific reasoning for each score
- Reference research data from EXA/TAVILY
- Consider uploaded documents (CIMs, financials)
- Generate actionable recommendation

### 4.3 Score Display Component
**File: `components/cards.py` → `ScoreCard()`**

Visual score card with:
- Radar/spider chart (Plotly) showing dimension scores
- Color-coded bars for each dimension
- Overall composite score (large number)
- Expandable reasoning sections
- Recommendation badge (green/yellow/red)

---

## Phase 5: Document Upload & Processing

### 5.1 Document Parser
**File: `utils/document_parser.py`**

```python
class DocumentParser:
    def parse_xlsx(file_path) -> dict    # openpyxl → sheets, tables, key metrics
    def parse_pptx(file_path) -> dict    # python-pptx → slides, text, charts
    def parse_pdf(file_path) -> dict     # pdfplumber → pages, text, tables
    def extract_financials(parsed) -> dict  # Heuristic extraction of key M&A metrics
```

Key metrics extracted: revenue, EBITDA, margins, growth rates, headcount, geography.

### 5.2 Upload Route
**File: `routes/upload.py`**

- `GET /upload` — renders drag-and-drop upload form
- `POST /upload` — handles file upload (UploadFile), parses, stores
- Supports: `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.pdf`
- Max file size: 50MB
- Stored in `uploads/` directory with metadata in SQLite

### 5.3 Upload UI Component
**File: `components/upload_form.py`**

Tailwind-styled drag-and-drop zone:
- Dashed border area with upload icon
- File type badges (XLS, PPT, PDF)
- Progress indicator during upload
- Preview of extracted content after parsing
- "Analyze with AI" button to feed into scoring/research agents

### 5.4 Document Agent
**File: `agents/document_agent.py`**

Agent that:
1. Receives parsed document data
2. Extracts key M&A metrics (revenue, EBITDA, margins, etc.)
3. Identifies company profile from document content
4. Feeds extracted data into scoring and research workflows
5. Summarizes document contents for the chat interface

---

## Phase 6: yfinance Company Data

### 6.1 yfinance Utility
**File: `utils/yfinance_util.py`**

```python
class YFinanceUtil:
    def get_company_profile(ticker) -> dict
        # sector, industry, description, employees, website, market_cap

    def get_financials(ticker) -> dict
        # revenue, ebitda, net_income, margins, growth_rates

    def get_comparable_companies(sector, industry) -> list[dict]
        # Find peers via sector ETF holdings

    def search_companies(query) -> list[dict]
        # Ticker search and company name matching
```

### 6.2 Company Search Route
**File: `routes/home.py` or `routes/api.py`**

- `GET /company/{ticker}` — company profile card
- `GET /company/search?q=...` — HTMX search-as-you-type
- Integrated into target finder and scoring workflows

---

## Phase 7: Chat & Workflow Integration

### 7.1 Chat Interface (WebSocket)
**File: `routes/home.py`**

Following FastHTML websocket pattern from `fastHTML-ctx.txt`:
```python
app, rt = fast_app(exts='ws')

@app.ws('/ws')
async def ws(msg: str, send):
    # 1. Display user message
    # 2. Start workflow via orchestrator
    # 3. Stream agent progress via send()
    # 4. Stream research results to right pane
    # 5. Display final results
```

### 7.2 Agent Progress SSE
**File: `routes/api.py`**

- `GET /stream/{workflow_id}` — SSE endpoint
- Emits events: `agent_start`, `agent_complete`, `research_update`, `workflow_complete`
- Middle pane subscribes via `hx_ext="sse"` + `sse_connect`

### 7.3 Workflow Service Update
**File: `utils/workflow_service.py`**

- Wire up research agent into buyer_ma and seller_ma workflows
- Add scoring step after target finding
- Store research trace in state for right-pane display
- Emit SSE events at each workflow step

---

## Phase 8: Additional M&A Platform Tools (Suggested)

### New Tools to Build

| Tool | Purpose | Priority |
|------|---------|----------|
| **Deal Room** | Virtual data room for document sharing & access control | High |
| **CIM Generator** | Auto-generate Confidential Information Memorandum from uploaded docs | High |
| **Comparable Transactions DB** | Database of historical M&A transactions for benchmarking | High |
| **LOI/Term Sheet Drafter** | AI-generated Letter of Intent and term sheet templates | Medium |
| **Due Diligence Checklist** | Auto-generated DD checklist based on deal type and industry | Medium |
| **Regulatory Screening** | Antitrust/regulatory risk assessment (HSR filing thresholds) | Medium |
| **Stakeholder Mapping** | Map board members, investors, advisors for target companies | Medium |
| **Integration Playbook** | Post-merger integration plan generator | Medium |
| **Pipeline CRM** | Track deal stages, contacts, next actions (Kanban board) | Medium |
| **Valuation Sensitivity** | Interactive sensitivity tables (entry multiple × growth rate) | Medium |
| **Market Sizing** | TAM/SAM/SOM analysis for target's market | Low |
| **Pitch Deck Builder** | Auto-generate buyer/seller pitch decks from deal data | Low |
| **Email Outreach** | Templated outreach to targets/buyers with mail merge | Low |
| **Calendar/Timeline** | Deal timeline with milestones and deadlines | Low |
| **Benchmarking Dashboard** | Compare target metrics against industry medians | Low |

### New Research Integrations

| Integration | Purpose |
|-------------|---------|
| **SEC EDGAR** | 10-K, 10-Q, 8-K filings for US public companies |
| **Companies House** | UK company filings (already partially built) |
| **PitchBook / Crunchbase API** | Private company data, funding rounds |
| **LinkedIn API** | Management team profiles, employee count trends |
| **Google News API** | Recent news about target companies |
| **Glassdoor API** | Cultural fit signals (employee reviews, ratings) |

---

## Implementation Order

```
Phase 1: Foundation          → Day 1-2  (deps, config, LLM factory)
Phase 2: FastHTML Shell      → Day 2-4  (3-pane layout, Tailwind, routes)
Phase 3: Research (EXA/TAV)  → Day 4-5  (search tools, research agent, right pane)
Phase 4: Scoring Agent       → Day 5-6  (scoring logic, prompt, score cards)
Phase 5: Document Upload     → Day 6-7  (parser, upload UI, document agent)
Phase 6: yfinance            → Day 7    (company profiles, search)
Phase 7: Chat & Workflow     → Day 7-8  (websocket chat, SSE progress, integration)
Phase 8: Additional Tools    → Ongoing  (prioritized backlog)
```

## Migration Notes

### What Changes
- `Home.py` (Streamlit) → `main.py` (FastHTML)
- `pages/*.py` (Streamlit multi-page) → `routes/*.py` (FastHTML APIRouter)
- `st.sidebar` → Left pane FT component
- `st.chat_input` → WebSocket form
- `st.spinner` → SSE-driven progress indicators
- `st.session_state` → FastHTML session middleware
- `st.metric` → Tailwind-styled metric cards
- Custom CSS in `st.markdown()` → Tailwind utility classes

### What Stays the Same
- `agents/` — core logic unchanged, just swap LLM provider
- `prompts/` — all prompts reused as-is
- `utils/state.py` — LangGraph state unchanged
- `utils/database.py` — migrated to fastlite but same schema
- `utils/logging.py` — unchanged
- `sql/create-tables.sql` — unchanged
- `tests/` — adapted for new routes

### Reference: alpatrade Patterns
Borrow from `/home/julian/dev/plai/alpatrade`:
- `web_app.py` — FastHTML session management, command routing, log streaming
- `agui_app.py` — 3-pane layout, WebSocket chat, artifact panel
- `utils/market_research_util.py` — research tool patterns
- `tui/command_processor.py` — command routing pattern
