"""Analytics page — natural-language → SQL over liquidround/pehero schema, rendered as a Plotly chart.

/app/analytics           → text input + example prompts
POST /app/analytics/run  → returns the SQL + result table + plotly fig JSON
"""
from __future__ import annotations

import json
import logging
import os
import re

import pandas as pd
import plotly.express as px
from fasthtml.common import (
    Div, Span, H2, H3, P, A, Button, Form, Input, Textarea, Title, Script, Link, NotStr, APIRouter,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

from utils.llm_factory import create_llm
from utils.database import get_conn

log = logging.getLogger(__name__)

ar = APIRouter()

COMPANY_DB_SCHEMA = os.getenv("COMPANY_DB_SCHEMA", "pehero")


def _load_schema_snippet() -> str:
    from pathlib import Path
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.json"
    if not schema_path.exists():
        return "-- schema.json not found"

    schema = json.loads(schema_path.read_text())
    lines = [
        "-- LiquidRound read-only PostgreSQL schema. ONLY SELECT queries.",
        f"-- Use schema-qualified names (liquidround.* or {COMPANY_DB_SCHEMA}.*).\n",
    ]
    for table, info in schema.items():
        cols = info.get("columns", [])
        row_count = info.get("row_count", 0)
        enums = info.get("enums", {})

        col_parts = []
        for c in cols:
            part = c["name"]
            ctype = c.get("type", "")
            if "JSONB" in ctype:
                part += " JSONB"
            elif "DATE" in ctype or "TIMESTAMP" in ctype:
                part += " DATE"
            elif "NUMERIC" in ctype:
                part += f" {ctype}"
            if c["name"] in enums:
                vals = " | ".join(str(v) for v in enums[c["name"]])
                part += f"  -- {vals}"
            col_parts.append(part)

        lines.append(f"{table} ({row_count} rows) (")
        lines.append("    " + ",\n    ".join(col_parts))
        lines.append(")\n")

    return "\n".join(lines)


SCHEMA_SNIPPET = _load_schema_snippet()


SAMPLE_QUERIES = [
    "Top 10 companies by LTM revenue, show sector",
    "Company count by deal stage",
    "Average EBITDA margin by sector",
    "Revenue distribution by sub-sector",
    "Largest healthcare companies by employees",
    "Average revenue by sector, bar chart",
    "Company count by country",
    "Top 20 companies by enterprise value",
]


SYSTEM = f"""You translate plain-English questions into a single PostgreSQL SELECT
query against the schema below, and suggest a chart.

Rules:
- Return ONLY a JSON object with exactly these keys:
  {{ "sql": "...", "chart": "bar|line|scatter|pie|none", "x": "...", "y": "...", "color": "...", "title": "..." }}
- Never modify data. SELECT only.
- Use schema-qualified names (liquidround.*, {COMPANY_DB_SCHEMA}.*).
- Limit results sensibly (≤200 rows) unless a time-series needs more.
- For time series, order by the time column.
- For percentages like margins, already-percent values — leave them, don't multiply.

Schema:
{SCHEMA_SNIPPET}
"""


def _draft_sql(question: str) -> dict:
    llm = create_llm()
    resp = llm.invoke(f"{SYSTEM}\n\nQuestion: {question}\n\nJSON:").content
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON in model response: {resp[:400]}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"Bad JSON from model: {e} — {resp[:400]}")


def _guard_sql(sql: str) -> None:
    s = sql.strip().rstrip(";").strip()
    lowered = s.lower()
    if not lowered.startswith("select") and not lowered.startswith("with"):
        raise ValueError("Only SELECT / WITH queries are allowed.")
    banned = ["insert ", "update ", "delete ", "drop ", "truncate ",
              "alter ", "grant ", "revoke ", "create ", "copy ", ";"]
    for b in banned:
        if b in lowered:
            raise ValueError(f"Disallowed keyword in SQL: {b.strip()}")


def _run_sql(sql: str) -> pd.DataFrame:
    _guard_sql(sql)
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn)


def _chart_for(df: pd.DataFrame, spec: dict) -> dict | None:
    if df.empty:
        return None
    kind = (spec.get("chart") or "").lower()
    x = spec.get("x")
    y = spec.get("y")
    color = spec.get("color") or None
    title = spec.get("title") or ""

    cols = list(df.columns)
    if x and x not in cols:
        x = cols[0]
    if y and y not in cols:
        y = next((c for c in cols[1:] if pd.api.types.is_numeric_dtype(df[c])), cols[-1])
    if color and color not in cols:
        color = None
    if not x:
        x = cols[0]
    if not y and len(cols) > 1:
        y = cols[1]

    try:
        if kind == "bar":
            fig = px.bar(df, x=x, y=y, color=color, title=title, barmode="group")
        elif kind == "line":
            fig = px.line(df, x=x, y=y, color=color, title=title, markers=True)
        elif kind == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, title=title)
        elif kind == "pie":
            fig = px.pie(df, names=x, values=y, title=title)
        else:
            return None
    except Exception as e:
        log.warning("plotly failed: %s", e)
        return None

    fig.update_layout(
        paper_bgcolor="#111A2E", plot_bgcolor="#0B1220",
        font=dict(family="Inter, system-ui", color="#E5E7EB"),
        margin=dict(l=40, r=20, t=50, b=40),
        title=dict(font=dict(size=15, color="#E5E7EB")),
        xaxis=dict(gridcolor="#1E293B", zerolinecolor="#1E293B"),
        yaxis=dict(gridcolor="#1E293B", zerolinecolor="#1E293B"),
        legend=dict(font=dict(color="#94A3B8")),
        colorway=["#F59E0B", "#3B82F6", "#10B981", "#EF4444", "#8B5CF6",
                   "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16"],
    )
    return json.loads(fig.to_json())


# ─── Routes ────────────────────────────────────────────────────────

@ar("/app/analytics")
def analytics_page(session):
    from components.chat_shell import left_pane, right_pane

    user = session.get("user")
    user_email = user.get("email") if user else None
    current_currency = session.get("currency", "EUR")
    current_role = session.get("role", "buyer")

    sessions_list = []
    if user and user.get("user_id"):
        try:
            from utils.database import db_service
            convs = db_service.get_user_conversations(user["user_id"], limit=20) or []
            sessions_list = [{"id": c["id"], "title": c.get("conversation_title") or c.get("user_query", "Untitled")}
                             for c in convs]
        except Exception:
            pass

    suggestions = Div(
        *[Button(q, cls="analytics-sugg", onclick=f"runAnalytics({q!r})")
          for q in SAMPLE_QUERIES],
        cls="analytics-suggestions",
    )

    return (
        Title("Analytics · LiquidRound"),
        Div(cls="left-overlay", id="left-overlay", onclick="toggleLeftPane()"),
        Div(
            left_pane(
                user_email=user_email,
                sessions=sessions_list,
                current_sid="",
                current_currency=current_currency,
                current_role=current_role,
                current_path="/app/analytics",
            ),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()", type="button"),
                        Span("Analytics", cls="chat-header-title"),
                        Span("·", cls="chat-header-dot"),
                        Span("Text-to-SQL", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    Div(
                        copilot_toggle_btn(),
                        cls="chat-header-actions",
                    ),
                    cls="chat-header",
                ),
                Div(
                    Div(
                        H2("Ask anything about your data", cls="text-ink"),
                        P("Type a question in plain English — the AI writes SQL, runs it, and charts the results.",
                          cls="text-ink-muted"),
                        cls="analytics-hero",
                    ),
                    Form(
                        Input(type="text", id="analytics-q", name="q",
                              placeholder="e.g. Top 10 companies by EV/EBITDA, grouped by sector",
                              onkeydown="if(event.key==='Enter'){event.preventDefault();runAnalytics()}"),
                        Button("Run", type="button", onclick="runAnalytics()"),
                        cls="analytics-form",
                    ),
                    suggestions,
                    Div(id="analytics-result"),
                    cls="analytics-wrap",
                ),
                cls="center-pane",
            ),
            copilot_pane(
                page_name="Analytics",
                page_context={
                    "page": "Analytics",
                    "capabilities": "text-to-SQL against LiquidRound/pehero schema, Plotly charts",
                    "sample_queries": list(SAMPLE_QUERIES[:4]),
                },
            ),
            cls="app pane-closed",
        ),
        Script(NotStr("""
            async function runAnalytics(q) {
                if (q) document.getElementById('analytics-q').value = q;
                const question = document.getElementById('analytics-q').value.trim();
                const out = document.getElementById('analytics-result');
                if (!question) return;
                out.innerHTML = '<div class="analytics-result"><div style="color:var(--ink-muted)">Thinking…</div></div>';
                const r = await fetch('/app/analytics/run', {
                    method: 'POST',
                    body: new URLSearchParams({ q: question })
                });
                const data = await r.json();
                if (data.error) {
                    out.innerHTML = `<div class="analytics-error"><strong>Error:</strong> ${data.error}<br><pre style="margin-top:.5rem;font-size:.7rem;overflow-x:auto">${data.sql || ''}</pre></div>`;
                    return;
                }
                const chartId = 'chart-' + Math.random().toString(36).slice(2, 8);
                const tableHtml = data.table
                    ? `<div class="analytics-table-wrap">${data.table}</div>` : '';
                out.innerHTML = `
                    <div class="analytics-result">
                        <h3>${data.title || question}</h3>
                        <div class="sql">${data.sql}</div>
                        <div id="${chartId}" class="analytics-chart"></div>
                        ${tableHtml}
                    </div>`;
                if (data.figure) {
                    Plotly.newPlot(chartId, data.figure.data, data.figure.layout, {responsive: true});
                } else {
                    document.getElementById(chartId).innerHTML = '<p style="color:var(--ink-muted);font-size:.82rem">(No chart — showing table only.)</p>';
                }
            }
            window.runAnalytics = runAnalytics;
        """)),
        Script(src="/chat.js"),
        Script(src="/copilot.js"),
    )


@ar("/app/analytics/run", methods=["POST"])
async def analytics_run(request: Request):
    form = await request.form()
    q = (form.get("q") or "").strip()
    if not q:
        return JSONResponse({"error": "Empty question."})

    try:
        spec = _draft_sql(q)
        sql = spec.get("sql", "").strip().rstrip(";")
    except Exception as e:
        return JSONResponse({"error": f"LLM couldn't draft SQL: {e}"})

    try:
        df = _run_sql(sql)
    except Exception as e:
        return JSONResponse({"error": f"SQL failed: {e}", "sql": sql})

    fig = _chart_for(df, spec)
    table_html = df.head(50).to_html(
        index=False, classes="artifact-table", border=0,
        float_format=lambda x: f"{x:,.2f}" if isinstance(x, float) else str(x),
    )

    return JSONResponse({
        "sql": sql,
        "title": spec.get("title") or q,
        "figure": fig,
        "rows": len(df),
        "table": table_html,
    })


# ─── Copilot helpers (used by analytics + other workspace pages) ───

COPILOT_PROMPTS: dict[str, list[str]] = {
    "Analytics": [
        "Revenue distribution by sector",
        "Company count by deal stage",
        "Average EBITDA margin by sector",
        "Top 20 companies by enterprise value",
    ],
    "Companies": [
        "Top 10 companies by revenue in healthcare",
        "Find software companies above €5M revenue",
        "Compare EBITDA margins across sectors",
        "Which companies have the highest growth rate?",
    ],
    "Valuation": [
        "What's a fair EV/EBITDA multiple for this sector?",
        "Build a 5-year DCF model at 12% revenue growth",
        "What are the key risks for this acquisition?",
        "How should I structure the deal financing?",
    ],
    "Pipeline": [
        "Which companies should I move to screening?",
        "Show me healthcare deals above €10M revenue",
        "What's the average EBITDA margin across the pipeline?",
        "Draft an outreach email for the top logistics company",
    ],
    "Training": [
        "What character should I pick for my first game?",
        "How do I win mandates faster?",
        "What's the best strategy for due diligence?",
        "How does the scoring work?",
    ],
}


def copilot_pane(*, page_name: str, page_context: dict | None = None,
                 company_slug: str = ""):
    context_json = json.dumps(page_context or {})
    prompts = COPILOT_PROMPTS.get(page_name, COPILOT_PROMPTS.get("Pipeline", []))
    sample_chips = [
        Button(
            Span(p, cls="copilot-chip-text"),
            cls="copilot-chip",
            onclick=f"copilotFillAndSend({p!r})",
        )
        for p in prompts
    ]

    return Div(
        Div(
            Div(H3("Copilot", cls="right-title"),
                Span(page_name, id="copilot-subtitle", cls="right-subtitle"),
                cls="right-header-left"),
            Button("»", cls="right-close copilot-collapse", onclick="toggleCopilotPane()"),
            cls="right-header",
        ),
        Div(
            Div(id="copilot-messages", cls="copilot-messages"),
            cls="right-body copilot-body",
        ),
        Form(
            Input(type="hidden", id="copilot-context", value=context_json),
            Input(type="hidden", id="copilot-page", value=page_name),
            Input(type="hidden", id="copilot-company", value=company_slug),
            Div(
                Textarea(
                    id="copilot-input", name="msg",
                    cls="copilot-textarea",
                    placeholder=f"Ask about {page_name.lower()}...",
                    rows="2",
                    onkeydown="copilotHandleKey(event)",
                ),
                Button("Send", type="submit", cls="copilot-send", id="copilot-send-btn"),
                cls="copilot-input-row",
            ),
            Div(*sample_chips, id="copilot-chips", cls="copilot-chips"),
            id="copilot-form",
            cls="copilot-form",
            onsubmit="copilotSend(event)",
        ),
        id="right-pane", cls="right-pane copilot-pane open",
    )


def copilot_toggle_btn():
    return Button("«", id="copilot-btn", cls="copilot-expand-btn",
                  onclick="toggleCopilotPane()", title="Open Copilot")
