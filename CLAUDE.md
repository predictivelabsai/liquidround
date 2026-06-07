# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LiquidRound is Predictive Labs Ltd's AI platform for **both sides of an M&A / IPO deal**. Buyers use it to find acquisition targets, underwrite, run diligence, and draft IC memos. Sellers use it to prepare for sale (teasers / CIMs), identify buyers, and assess IPO readiness. Marketing positions the agents as the "ECM Agent Squad" (ECM = Equity Capital Markets).

## Commands

```bash
pip install -r requirements.txt
playwright install chromium      # needed for E2E tests + demo GIF

# Run (port 5007, configurable via PORT env)
python main.py
# or docker compose up --build

# Tests
pytest -q                                         # unit only (pytest.ini excludes `e2e` by default)
pytest -q tests/test_registry.py                  # 22-agent registry integrity (120 cases)
pytest -q tests/test_e2e_smoke.py -m e2e          # Playwright — requires server on :5007
pytest -q tests/test_registry.py -k prefix_routing  # run a single test

# Daily digest email (standalone, no server needed)
python -m scripts.daily_deals                    # send to TO_EMAIL
python -m scripts.daily_deals --all              # send to all opted-in users
python -m scripts.daily_deals --dry-run          # print HTML, don't send

# Regenerate landing-page demo GIF (server must be running on :5007)
python -m scripts.capture_screenshots   # -> screenshots/*.png (14 frames)
python -m scripts.make_gif              # -> docs/liquidround.gif + static/liquidround.gif
```

## Architecture (big picture)

**Two FastHTML shells share one process:**

1. **`/` -- the landing page** (`routes/landing.py` + `components/landing.py`). Dark-navy hero with two role CTAs (`Buyer-Led -> /app?role=buyer`, `Seller-Led -> /app?role=seller`), product-demo GIF, agent directory, pricing, contact. Distinct visual identity (navy #0B1220 + amber #F59E0B accents).
2. **`/app` -- the chat-first product** (`main.py`). Left nav, chat area, slide-out right "canvas" pane (Documents / Research / Scores / Compare tabs). The `@rt("/app")` function is the entry point, backed by in-memory `SessionState` keyed by `session["sid"]`.

**Route wiring** -- all in `main.py`'s top-level block. Order matters: `routes/landing.py` is mounted **first** so `/` resolves to the landing, not the chat. Mounted routers (in order): `landing`, `auth`, `upload`, `research`, `api`, `pipeline`, `companies`, `digest`, `memo_pdf`, `valuation`, `game`, `analytics`, `exports`, `dataroom`, `help`, `instructions`. `routes/home.py` exists but is **not mounted** -- dead code.

**Role modes.** `/app?role=buyer|seller` writes to `session["role"]`, which drives: (a) which nav section opens by default in `_nav_section()`, (b) which welcome cards render, (c) which agent chips surface. Persisted best-effort to `liquidround.users.default_role` (see `sql/04-add-default-role.sql`) when a user is logged in. The Configuration widget (type `settings` in chat) lets the user switch; POST `/settings/save` persists.

**Two agent entry paths -- keep them straight.**

1. `agents/render_agent.py` (legacy, but live) -- the dispatcher wired to `main.py`'s `/chat` HTMX endpoint. Handles the command DSL parsed by `utils/command_parser.py`: `profile:MSFT`, `targets industry:fintech`, `score buyer:X target:Y`, `keyterms filename.pdf`, `settings`, `help`, `clear`. Returns FastHTML `FT` components that go straight into the chat bubble.

2. `agents/registry.py` + `agents/router.py` + `agents/base.py` + 22 per-slug modules under `agents/<category>/<slug>.py` -- the **ECM Agent Squad** architecture, modelled after `~/dev/plai/pehero`. Each agent module exports `SPEC` + `TOOLS` + `build()`. `build_agent(spec, tools)` wraps a `create_react_agent(llm, tools, prompt=system)` LangGraph app. `cached_agent(slug)` imports the module and returns its cached graph. If the LLM can't be constructed (no API key), falls back to `build_simple_agent` -- the structural tests still pass without keys.

   - Categories: `sourcing` (4), `underwriting` (6), `diligence` (5), `capital` (5), `portfolio` (2) = **22 agents**.
   - Router in `agents/router.py` picks a slug: (1) explicit prefix match (`has_specialist_prefix`), (2) keyword heuristics, (3) LLM fallback. `strip_prefix` removes the leading `xxx:` for the agent.

**How they compose in the running chat:**
- Legacy command prefixes (`profile:`, `financials:`, `news:`, `valuation:`, `targets`, `buyers`, `ipo`, `score`, `keyterms`, `research`, `settings`, `help`, `clear`, `market`, `tools`, `upload`, `docs`, `deals`) -- handled inline by `render_agent.process()` with hand-rolled `FT` components.
- **New specialist prefixes** (`scan:`, `triage:`, `intent:`, `comps:`, `ltm:`, `dcf:`, `multi:`, `synergy:`, `vdr:`, `abstract:`, `legal:`, `ops:`, `esg:`, `memo:`, `teaser:`, `bid:`, `integrate:`) -- `render_agent._specialist()` invokes the LangGraph agent via `cached_agent(slug).ainvoke(...)`, extracts the final `AIMessage`, and renders both the text bubble and any `__ARTIFACT__` payloads as inline tables / citations. Matching artifacts land in the right-pane canvas (`_canvas_state`) as well.
- **SSE streaming endpoint** `/app/chat` (POST) -- the **primary chat path** used by `static/chat.js`. Pehero-compatible event stream: `agent_route`, `token`, `tool_start`, `tool_end`, `artifact_show`, `session`, `done`, `error`. Helpers in `chat_sse.py`. This endpoint also creates conversations in DB for logged-in users and emits a `session` event with the `{sid}` so the client can update the URL and enable the Share button.
- **HTMX `/chat` endpoint** -- the older HTMX-based chat path; still functional but `chat.js` uses the SSE endpoint by default.
- **Memo -> PDF pipeline** (`chat_memo_pdf.py`, mounted as `/app/memo-pdf/*`) -- after an IC Memo / Teaser response, the client POSTs rendered markdown to `/app/memo-pdf/render`, which generates a reportlab PDF and returns a `file_id`. A PDF.js iframe in the right pane loads `/app/memo-pdf/file/<file_id>`. Content-addressed (sha1) so identical memos reuse cached PDFs.
- **3-pane chat shell** (`components/chat_shell.py`) -- ported from pehero: left pane (Sessions / Agents / Workspace / Configuration), center pane (header + messages + chat input), right pane (artifact canvas). Composed in `main.py`'s `/app` route. `center_pane()` accepts `readonly=True` for the shared chat view.

**Chat sharing.** `POST /app/share` generates a `share_token` (UUID hex) on the `liquidround.workflows` row and returns the URL. `GET /app/s/{token}` renders a read-only view (no auth required, no input form, Copy button only). The JS `shareChat()` copies the URL to clipboard. `setSid()` is exposed as `window.setSid` so the server can push the conversation ID to the client.

**`tools/` layer** -- LangChain StructuredTools consumed by the 22 agents. Each tool is a sync function wrapped with `StructuredTool.from_function(...)` and, where relevant, emits an artifact via `tools.artifact.emit(...)` (which prepends `__ARTIFACT__` + JSON). Current tools:
- `tools/companies.py` -- `get_company_profile`, `get_financials`, `get_peer_companies` (wraps `utils/yfinance_util`).
- `tools/research.py` -- `exa_search`, `tavily_search`, `deep_research` (sync wrappers around async `utils/research_tools`).
- `tools/documents.py` -- `read_document`, `extract_key_terms`, `list_documents` (wraps `utils/document_parser`).
- `tools/valuation.py` -- `dcf_valuer`, `multiples_valuer` (pure Python, consumes yfinance data).
- `tools/scoring.py` -- `score_match` (invokes legacy `ScoringAgent` for 7-dimension radar).
- `tools/artifact.py` -- `emit`, `is_artifact`, `parse_artifact`, `ARTIFACT_PREFIX`.

**LLM.** All LLM calls flow through `utils/llm_factory.create_llm()` -- swap providers via `DEFAULT_PROVIDER` env (`xai` | `openai`). XAI/Grok hits `https://api.x.ai/v1` via `ChatOpenAI`. Never construct `ChatOpenAI` directly outside this factory.

**Research / data tools.** `utils/yfinance_util.py` for company fundamentals (profile, financials, market cap -- not real-time quotes), `utils/research_tools.py` for EXA (semantic) + Tavily (web). `utils/document_parser.py` for PDF (pdfplumber) / XLSX (openpyxl) / PPTX (python-pptx). `utils/command_parser.py` is the legacy command DSL; `agents/router.py` is the newer free-form router. Both must stay in sync for new prefixes.

**Database.** PostgreSQL, schema `liquidround`. Connection via `utils/database.py` (`get_conn()` + `db_service = DatabaseService()`). Tables: `users`, `workflows` (doubles as conversations), `messages`, `user_preferences`, `deals`, `documents`, `scoring_results`, `research_results`, `ipo_data`, `pipeline_items`, `prompt_versions`. Always qualify tables as `liquidround.<table>` -- do not rely on `search_path`. Migrations are numbered SQL files in `sql/` (01 through 09). The `workflows.status` column has a CHECK constraint: valid values are `pending`, `routing`, `executing`, `completed`, `failed` -- conversations use `completed`.

**User preferences.** `utils/preferences.py` provides CRUD for `liquidround.user_preferences` (account info, M&A deal filters, notification toggles). `routes/auth.py` serves the `/profile` page with 3 HTMX-powered sections. `get_digest_recipients()` returns all opted-in users (LEFT JOIN with COALESCE so users without a preferences row default to opted-in).

**Daily digest pipeline.** `utils/digest.py` orchestrates: Tavily research -> LLM extracts companies -> yfinance comps -> LLM thesis per company -> LLM picks featured -> LLM deep dive. `render_email_html()` produces the styled HTML email. `send_digest_to_all()` builds once, sends to all opted-in users via Postmark. Routes: `GET /app/digest` (preview), `POST /app/digest/send` (single), `POST /app/digest/send-all` (batch).

**In-process scheduler.** `utils/scheduler.py` runs digest jobs as a daemon thread -- no external cron needed. Starts automatically on app boot via `main.py`. Configured by `DIGEST_FREQUENCY`, `DIGEST_HOUR_UTC`, `DIGEST_WEEKDAY` env vars. Set `DIGEST_FREQUENCY=off` to disable.

**Email.** Postmark for transactional email (password reset, daily digest). `utils/email.py` is the generic sender; `utils/digest.py` has its own `send_digest_email()` for digest-specific formatting.

**Authentication is optional, not enforced.** `main.py` has **no auth beforeware** -- guests can use chat. `routes/auth.py` provides `/signin`, `/register`, `/login`, `/logout`, `/forgot`, `/reset`, Google OAuth. Logged-in users get persistent conversations (`liquidround.workflows` with `workflow_type='conversation'`) and share links; guests use the in-memory `SessionState` dict in `main.py`.

## Conventions

- **FastHTML + HTMX only.** No React / Vue / Svelte. Server-rendered hypermedia with `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `hx_swap_oob`. Vanilla JS only when HTMX can't cover it. `NotStr(...)` when you need raw HTML (markdown rendering, inline SVG icons).
- **No Pico CSS.** `fast_app(pico=False)`. Styling is Tailwind via CDN; any CSS overrides go in `static/app.css`. The landing page has its own palette + fonts defined inline in `components/landing.py` -- keep it distinct from the chat app.
- **Static files served at root**, not `/static/...`. `fast_app(static_path="static")` exposes `static/foo.png` as `/foo.png`. `static/app.css` is referenced as `/app.css`; favicons are `/favicon.svg` etc.
- **Dark chat theme.** `/app` sets `<body class="lr-dark">` (via a tiny Script in `app_shell`) + inline `<style>` for the navy background to avoid a flash of light content. `static/app.css` contains the overrides that convert Tailwind light utility classes (`bg-gray-50`, `bg-white`, `text-gray-600`, blue accents) to the landing palette (navy `#0B1220`, slate text, amber accents). Don't use the `.lr-dark` class on the landing -- the landing has its own inline palette via `components/landing.py`.
- **Adding a new 22-agent entry:** append an `AgentSpec` to `agents/registry.py` (keep the `assert len(AGENTS) == 22` honest by bumping it or keeping the count), add `prompts/system/<slug>.md`, and if it needs custom tools or non-LLM logic, create `agents/<category>/<slug>.py` with `SPEC` + `build() -> callable`. Add the prefix to the router's `_best_in_category_for` if it should win on keyword matches. Re-run `pytest tests/test_registry.py`.
- **E2E test isolation:** Playwright tests live in `tests/test_e2e_smoke.py` with `@pytest.mark.e2e`. `pytest.ini` has `addopts = -m "not e2e"` so the default run is unit-only. Run E2E explicitly: `pytest -m e2e`. They assume a server on `$LIQUIDROUND_URL` (default `http://localhost:5007`).
- **Commit style:** sentence-case, one short line describing the change (see `git log --oneline`). Commits created by Claude are co-authored per the project default.

## Environment

```
XAI_API_KEY=...              # primary LLM (Grok via x.ai OpenAI-compat endpoint)
OPENAI_API_KEY=...           # fallback LLM
EXA_API_KEY=...              # semantic search
TAVILY_API_KEY=...           # web search
DB_URL=postgresql://...      # PostgreSQL, schema `liquidround`
SESSION_SECRET=...           # FastHTML session cookie signing
DEFAULT_PROVIDER=xai         # xai | openai -- drives utils/llm_factory.create_llm
DEFAULT_MODEL=grok-3-mini-fast
DEFAULT_TEMPERATURE=0.7
PORT=5007
POSTMARK_API_TOKEN=...       # Postmark transactional email
FROM_EMAIL=info@liquidround.com
TO_EMAIL=...                 # default digest recipient
GOOGLE_CLIENT_ID=...         # Google OAuth (optional)
GOOGLE_CLIENT_SECRET=...
DIGEST_FREQUENCY=daily       # daily | weekly | hourly | off
DIGEST_HOUR_UTC=7            # 0-23, fire hour for daily/weekly
DIGEST_WEEKDAY=1             # 0=Mon...6=Sun, only used when weekly
```

At least one of `XAI_API_KEY` or `OPENAI_API_KEY` must be set or `utils/config.Config` raises at import time.

## Known stale code to leave alone unless touched deliberately

- `Home.py` (if present) and the README's "Streamlit run Home.py" sections -- predate the FastHTML rewrite.
- `routes/home.py` -- defines `ar` but isn't mounted; its routes are superseded by `main.py` + `render_agent.py`.
- `agents/workflow.py` -- has a relative-import bug that breaks `tests/test_integration.py` collection. Not part of the live chat path.
- `agents/base_agent.py` -- the old `BaseAgent` ABC, still used by `scoring_agent.py`, `valuer.py`, `target_finder.py`, `research_agent.py`, `document_agent.py`. The new 22-agent architecture uses `agents/base.py` (`cached_agent`, `build_simple_agent`) -- different file, different pattern, don't confuse them.
- `routes/deals.py`, `routes/market.py` -- exist on disk but are **not mounted** in `main.py`; their endpoints are dead code.
