# LiquidRound — Architecture

LiquidRound is Predictive Labs' AI platform for M&A deal origination,
hedge fund intelligence, and IPO pipeline tracking. It is built on
**FastHTML** (server-rendered hypermedia) with a **LangGraph multi-agent system**
(the "ECM Agent Squad") and a **PostgreSQL** data layer spanning two schemas.

This document covers the system architecture with Mermaid diagrams.
Render these in any Mermaid-compatible viewer (GitHub, VS Code, etc.).

---

## 1. High-Level System Architecture

The platform runs as a single FastHTML process serving both the
public-facing landing site and the authenticated chat application.

```mermaid
flowchart TB
    USER(["User (browser)"])
    SEARCH(["Search engines"])

    subgraph Server["FastHTML Process (port 5007)"]
        LANDING["Landing site<br/>routes/landing.py<br/>/, /agents, /pricing, /contact"]
        BLOG["Public blog<br/>routes/blog.py<br/>/blog, /blog/rss"]
        TOOLS["Public tools<br/>routes/tools.py<br/>/tools/*, /industries/*"]
        APP["Chat application<br/>main.py /app<br/>3-pane shell + SSE streaming"]
        AUTH["Auth routes<br/>routes/auth.py<br/>/signin, /register, /profile"]
        API["REST API<br/>routes/api.py<br/>/api/*"]
        SCHED["Scheduler (daemon threads)<br/>utils/scheduler.py<br/>digest · candidates · returns"]
    end

    subgraph Data["PostgreSQL"]
        LR[("liquidround schema<br/>users, workflows, messages,<br/>ipo_pipeline, deal_candidates,<br/>digest_archive")]
        HF[("hedgefolio schema<br/>submission, coverpage,<br/>infotable, activist_filing<br/>~10K funds, 3.4M holdings")]
    end

    subgraph External["External APIs"]
        XAI[["Grok LLM<br/>api.x.ai (OpenAI-compat)"]]
        TAVILY[["Tavily<br/>web search"]]
        EXA[["EXA<br/>semantic search"]]
        YFINANCE[["yfinance<br/>market data"]]
        POSTMARK[["Postmark<br/>transactional email"]]
        BEEHIIV[["Beehiiv<br/>newsletter syndication"]]
    end

    USER -->|HTTPS| LANDING
    USER -->|HTTPS| APP
    SEARCH -->|crawl| LANDING
    SEARCH -->|crawl| BLOG

    APP -->|SQL| LR
    APP -->|SQLAlchemy| HF
    APP -->|chat + agents| XAI
    APP -->|research| TAVILY
    APP -->|research| EXA
    APP -->|company data| YFINANCE

    SCHED -->|daily digest| POSTMARK
    SCHED -->|syndicate| BEEHIIV
    SCHED -->|build digest| LR
    SCHED -.->|deal candidates| TAVILY
    SCHED -.->|security returns| YFINANCE
```

---

## 2. ECM Agent Squad — Multi-Agent Router

32 specialist agents organised into 7 categories. The typed router uses
prefix match → direct intent → keyword heuristics → context refinement →
LLM fallback.

```mermaid
flowchart TD
    MSG["User Message"] --> ROUTER["Router<br/>(agents/router.py)"]

    ROUTER -->|"scan: triage: intent:<br/>buyer:"| SRC["Deal Sourcing<br/>& Screening"]
    ROUTER -->|"comps: ltm: dcf:<br/>multi: synergy:"| UND["Valuation<br/>& Underwriting"]
    ROUTER -->|"vdr: abstract: legal:<br/>ops: esg:"| DIG["Due Diligence<br/>Stack"]
    ROUTER -->|"memo: teaser: bid:<br/>ipo: score:"| CAP["Deal Execution<br/>& Capital"]
    ROUTER -->|"research: hermes: integrate:"| PORT["Research<br/>& Post-Deal"]
    ROUTER -->|"hedgefunds: filings:<br/>releases: rto:"| PUB["Public Markets<br/>& Hedge Funds"]
    ROUTER -->|"write-release:<br/>ir-*:"| IR["Investor Relations<br/>& Communications"]

    subgraph SRC_AGENTS ["Sourcing (4 agents)"]
        SRC --> TS["target_scanner"]
        SRC --> BS["buyer_scanner"]
        SRC --> DT["deal_triage"]
        SRC --> SI["seller_intent"]
    end

    subgraph UND_AGENTS ["Underwriting (6 agents)"]
        UND --> CP["company_profiler"]
        UND --> CF["comps_finder"]
        UND --> LN["ltm_normalizer"]
        UND --> DV["dcf_valuer"]
        UND --> MV["multiples_valuer"]
        UND --> SA["synergy_analyst"]
    end

    subgraph DIG_AGENTS ["Diligence (5 agents)"]
        DIG --> VA["vdr_auditor"]
        DIG --> CA["contract_abstractor"]
        DIG --> LR2["legal_reviewer"]
        DIG --> OD["operational_dd"]
        DIG --> ER["esg_reviewer"]
    end

    subgraph CAP_AGENTS ["Capital (5 agents)"]
        CAP --> ICM["ic_memo_writer"]
        CAP --> TD["teaser_designer"]
        CAP --> BID["bid_strategist"]
        CAP --> IPO["ipo_readiness"]
        CAP --> MS["match_scorer"]
    end

    subgraph PORT_AGENTS ["Portfolio (3 agents)"]
        PORT --> RA["research_analyst"]
        PORT --> HO["hermes_orchestrator"]
        PORT --> IP["integration_planner"]
    end

    subgraph PUB_AGENTS ["Public Markets (1 agent)"]
        PUB --> HFA["hedge_fund_analyst"]
    end

    style ROUTER fill:#F59E0B,color:#0B1220,stroke:#D97706
    style SRC fill:#3B82F6,color:#fff
    style UND fill:#8B5CF6,color:#fff
    style DIG fill:#EC4899,color:#fff
    style CAP fill:#10B981,color:#fff
    style PORT fill:#F97316,color:#fff
    style PUB fill:#06B6D4,color:#fff
```

### Routing priority

```mermaid
flowchart LR
    INPUT["User input"] --> P{"Starts with<br/>specialist prefix?"}
    P -->|"Yes (e.g. dcf:)"| STRIP["Strip prefix<br/>→ invoke agent"]
    P -->|"No"| KW{"Keyword<br/>heuristics?"}
    KW -->|"Match"| AGENT["Matched agent"]
    KW -->|"No match"| LLM["LLM fallback<br/>classifier"]
    LLM --> AGENT
    LLM -.->|"failure"| DEFAULT["deal_triage<br/>(default)"]

    style P fill:#F59E0B,color:#0B1220
    style LLM fill:#3B82F6,color:#fff
```

---

## 3. Two Chat Entry Paths

The platform has two parallel chat pathways that share the same agent
registry and tool layer.

```mermaid
sequenceDiagram
    participant Browser as Browser (chat.js)
    participant SSE as POST /app/chat (SSE)
    participant HTMX as POST /chat (HTMX)
    participant Router as agents/router.py
    participant Agent as cached_agent(slug)
    participant Tools as tools/*.py
    participant DB as PostgreSQL

    Note over Browser,SSE: Primary path — SSE streaming

    Browser->>SSE: user message (fetch + EventSource)
    SSE->>Router: route(message)
    Router-->>SSE: slug
    SSE->>Agent: cached_agent(slug).astream_events()
    Agent->>Tools: tool calls (search, valuation, etc.)
    Tools-->>Agent: results + __ARTIFACT__ payloads
    Agent-->>SSE: LLM tokens + tool events
    SSE-->>Browser: SSE events (token, tool_start, tool_end, artifact_show, done)
    SSE->>DB: persist messages to workflows

    Note over Browser,HTMX: Legacy path — HTMX partials

    Browser->>HTMX: user message (hx-post)
    HTMX->>HTMX: command_parser.parse_command()
    alt Structured command (profile:, score, etc.)
        HTMX->>HTMX: render_agent built-in handler
    else Specialist prefix or free-form
        HTMX->>Router: route(message)
        Router-->>HTMX: slug
        HTMX->>Agent: cached_agent(slug).ainvoke()
    end
    HTMX-->>Browser: HTML partial (hx-swap)
```

---

## 4. FastHTML 3-Pane Application Shell

The `/app` route renders a responsive 3-pane layout powered by
`components/chat_shell.py` with SSE-driven updates.

```mermaid
flowchart LR
    subgraph Left ["Left Pane"]
        SESS["Sessions<br/>(conversation history)"]
        AGENTS["Agent Directory<br/>(ECM Squad by category)"]
        WORK["Workspace<br/>(Pipeline, Research,<br/>Companies, Data Room)"]
        CONFIG["Configuration<br/>(role, model, language)"]
    end

    subgraph Center ["Center Pane"]
        HEADER["Header bar<br/>(role badge, share, help)"]
        MSGS["Message list<br/>(user + assistant bubbles)"]
        INPUT["Chat input<br/>(textarea + send button)"]
        WELCOME["Welcome cards<br/>(role-specific prompts)"]
    end

    subgraph Right ["Right Pane (Canvas)"]
        DOCS["Documents tab<br/>(uploaded files)"]
        RES["Research tab<br/>(search results)"]
        SCORES["Scores tab<br/>(radar charts)"]
        COMPARE["Compare tab<br/>(side-by-side)"]
        PDF["Memo PDF viewer<br/>(PDF.js iframe)"]
    end

    INPUT -->|SSE stream| MSGS
    MSGS -.->|artifact payloads| Right
    AGENTS -->|click agent chip| INPUT
```

---

## 5. Tools Layer

LangChain `StructuredTool` wrappers consumed by the 23 LangGraph agents.
Tools emit structured data + `__ARTIFACT__` payloads for the canvas pane.

```mermaid
flowchart TD
    subgraph Agents ["LangGraph ReAct Agents"]
        A1["target_scanner<br/>buyer_scanner<br/>deal_triage<br/>…"]
        A2["dcf_valuer<br/>multiples_valuer<br/>synergy_analyst<br/>…"]
        A3["vdr_auditor<br/>contract_abstractor<br/>legal_reviewer<br/>…"]
        A4["hedge_fund_analyst"]
        A5["research_analyst"]
    end

    subgraph Tools ["tools/"]
        TC["companies.py<br/>get_company_profile<br/>get_financials<br/>get_peer_companies"]
        TV["valuation.py<br/>dcf_valuer<br/>multiples_valuer"]
        TR["research.py<br/>exa_search<br/>tavily_search<br/>deep_research"]
        TD2["documents.py<br/>read_document<br/>extract_key_terms"]
        TS["scoring.py<br/>score_match"]
        TH["hedge_funds.py<br/>search_funds<br/>get_holdings<br/>get_activist_filings"]
        TA["artifact.py<br/>emit() → __ARTIFACT__"]
    end

    subgraph Utils ["utils/"]
        UY["yfinance_util.py"]
        UR["research_tools.py<br/>(EXA + Tavily)"]
        UD["document_parser.py<br/>(PDF, XLSX, PPTX)"]
        UH["hedge_fund_db.py<br/>(SQLAlchemy)"]
    end

    A1 --> TC
    A1 --> TR
    A2 --> TV
    A2 --> TC
    A3 --> TD2
    A4 --> TH
    A5 --> TR

    TC --> UY
    TV --> UY
    TR --> UR
    TD2 --> UD
    TH --> UH

    style TA fill:#F59E0B,color:#0B1220
```

---

## 6. Data Model

Two PostgreSQL schemas on the same database instance.

```mermaid
graph LR
    subgraph liquidround ["Schema: liquidround"]
        U["users<br/>email, display_name,<br/>password_hash, google_id"]
        W["workflows<br/>(= conversations)<br/>user_id, workflow_type,<br/>status, share_token"]
        M["messages<br/>workflow_id, role,<br/>content, agent_slug"]
        UP["user_preferences<br/>user_id, default_role,<br/>notify_weekly_digest"]
        DC["deal_candidates<br/>company_name, country,<br/>sector, last_featured"]
        DA["digest_archive<br/>digest_date, slug,<br/>digest_json, blog_html"]
        IPO["ipo_pipeline<br/>company_name, kind,<br/>last_valuation, expected_date"]
        SR["security_returns<br/>cusip, return_ytd, ticker"]
    end

    subgraph hedgefolio ["Schema: hedgefolio"]
        SUB["submission<br/>accession_number, cik,<br/>filing_date"]
        COV["coverpage<br/>filingmanager_name,<br/>report_type"]
        INF["infotable<br/>name_of_issuer, cusip,<br/>value, ssh_prn_amt"]
        ACT["activist_filing<br/>filer_name, subject_company,<br/>filing_type (13D/13G)"]
    end

    U -- has --> W
    W -- contains --> M
    U -- has --> UP
    SUB -- has --> COV
    SUB -- has --> INF
    INF -.->|"JOIN on cusip"| SR

    style U fill:#3B82F6,color:#fff
    style SUB fill:#06B6D4,color:#fff
```

---

## 7. Daily Digest Pipeline

The digest runs as a scheduled job (07:00 UTC daily). It builds
an email with 5 deal candidates, a deep dive, hedge fund leaderboard,
and IPO snapshot — then archives to the blog and syndicates to Beehiiv.

```mermaid
sequenceDiagram
    participant Sched as Scheduler (07:00 UTC)
    participant Lock as pg_advisory_xact_lock
    participant Pool as deal_candidates table
    participant Tavily as Tavily API
    participant LLM as Grok LLM
    participant YF as yfinance
    participant HF as hedgefolio schema
    participant IPO as ipo_pipeline table
    participant PM as Postmark
    participant BH as Beehiiv
    participant DB as digest_archive

    Sched->>Lock: acquire lock for today
    alt Lock acquired
        Sched->>Pool: SELECT eligible candidates (14-day cooldown)
        alt Pool has ≥ 5 candidates
            Pool-->>Sched: 5 companies from pool
        else Pool too small
            Sched->>Tavily: research Baltic M&A deals
            Tavily-->>Sched: raw results
            Sched->>LLM: extract companies (up to 8)
            LLM-->>Sched: structured company list
        end
        Sched->>YF: fetch Baltic comps (13 tickers)
        YF-->>Sched: comps context
        loop Each company
            Sched->>LLM: generate thesis
        end
        Sched->>LLM: pick featured company
        Sched->>LLM: generate deep dive (300-400 words)
        Sched->>HF: get_fund_returns_ranked(top 10)
        Sched->>HF: get_fund_holdings(daily spotlight)
        Sched->>IPO: upcoming IPOs + pre-IPO mega-caps
        Sched->>LLM: render email HTML
        Sched->>DB: archive digest + blog HTML
        Sched->>BH: syndicate to Beehiiv (optional)
        loop Each opted-in subscriber
            Sched->>PM: send email
        end
    else Already sent today
        Sched-->>Sched: skip (dedup)
    end
```

### Deal candidate sync (05:00 UTC)

```mermaid
flowchart LR
    TAVILY(["Tavily API<br/>8 query angles"]) --> RESEARCH["Raw research<br/>results"]
    RESEARCH --> LLM["Grok LLM<br/>extract companies"]
    LLM --> UPSERT["UPSERT into<br/>deal_candidates<br/>(ON CONFLICT update)"]
    UPSERT --> POOL[("deal_candidates<br/>pool table<br/>14-day cooldown")]
    POOL --> DIGEST["Daily digest<br/>draws 5 companies"]

    style POOL fill:#3B82F6,color:#fff
    style DIGEST fill:#10B981,color:#fff
```

---

## 8. Route Map

All routes served by the FastHTML process, grouped by access level.

```mermaid
flowchart TB
    subgraph Public ["Public (no auth)"]
        L["/ — Landing page"]
        AG["/agents, /agents/{slug}"]
        PR["/pricing, /contact"]
        HW["/how-it-works, /industries/*"]
        TL["/tools/*"]
        BL["/blog, /blog/{slug}, /blog/rss"]
        SI["/signin, /register"]
        SM["/sitemap.xml, /robots.txt"]
    end

    subgraph Authenticated ["Authenticated (/app/*)"]
        SHELL["/app — 3-pane chat shell"]
        CHAT["/app/chat — SSE streaming"]
        SHARE["/app/s/{token} — shared chat (read-only)"]
        HFP["/app/hedgefunds — treemap"]
        IPOP["/app/ipo-pipeline"]
        COMP["/app/companies"]
        DR["/app/dataroom"]
        AN["/app/analytics"]
        DG["/app/digest — preview + send"]
        HELP["/app/help — user guide"]
        MEMO["/app/memo-pdf/*"]
        PROF["/profile — preferences"]
    end

    subgraph API ["REST API"]
        API1["/api/company-profile"]
        API2["/api/score-match"]
        API3["/api/research"]
    end

    style Public fill:#0B1220,color:#E5E7EB
    style Authenticated fill:#1E293B,color:#E5E7EB
    style API fill:#111A2E,color:#E5E7EB
```

---

## 9. Deployment

The app runs as a Docker container on Coolify (self-hosted PaaS) with
auto-deploy on push to `main`. Zero-downtime deploys overlap old and new
containers briefly — a `pg_advisory_xact_lock`-based dedup lock prevents
the scheduler from double-firing during the overlap window.

```mermaid
flowchart LR
    GH["GitHub<br/>predictivelabsai/<br/>liquidround"] -->|"push to main"| COOL["Coolify<br/>coolify.predictivelabs.ai"]
    COOL -->|"build + deploy"| C1["Container (new)"]
    COOL -.->|"drain + stop"| C0["Container (old)"]
    C1 -->|"SQL"| PG[("PostgreSQL<br/>liquidround + hedgefolio")]
    C1 -->|"API calls"| EXT["External APIs<br/>(Grok, Tavily, EXA,<br/>Postmark, Beehiiv)"]
    C1 -->|"scheduler threads"| JOBS["digest (07:00)<br/>deal_candidates (05:00)<br/>security_returns (07:00)"]

    style GH fill:#333,color:#fff
    style COOL fill:#6366F1,color:#fff
    style C1 fill:#10B981,color:#fff
    style C0 fill:#6B7280,color:#fff,stroke-dasharray: 5 5
```
