"""SPAC tracker dashboard components — spacanalytics-style layout."""
from __future__ import annotations

from fasthtml.common import *

BG = "#0B1220"
BG_CARD = "#111827"
BORDER = "#1E293B"
INK = "#F8FAFC"
INK_MUTED = "#94A3B8"
AMBER = "#F59E0B"
BLUE = "#3B82F6"
GREEN = "#10B981"
RED = "#EF4444"

STATUS_COLORS = {
    "searching": BLUE,
    "announced": AMBER,
    "completed": GREEN,
    "liquidated": RED,
}


def _fmt_money(v) -> str:
    if not v:
        return "—"
    v = float(v)
    if v >= 1e12:
        return f"${v/1e12:.1f}T"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    if v >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def _kpi_card(label: str, value: str, color: str = INK):
    return Div(
        Div(value, cls="text-2xl font-bold tightest", style=f"color:{color}"),
        Div(label, cls="text-xs mt-1 uppercase tracking-widest",
            style=f"color:{INK_MUTED}"),
        cls="text-center p-4 rounded-lg",
        style=f"background:{BG_CARD}; border:1px solid {BORDER}",
    )


def kpi_row(stats: dict):
    return Div(
        _kpi_card("Active SPACs", str(stats.get("seeking", 0)), BLUE),
        _kpi_card("Total Trust", _fmt_money(stats.get("total_trust", 0)), AMBER),
        _kpi_card("Announced Deals", str(stats.get("announced", 0)), GREEN),
        _kpi_card("Avg Redemption", f"{stats.get('avg_redemption', 0):.1f}%", RED),
        cls="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6",
    )


def filter_bar():
    return Div(
        Div(
            Label("Status", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
            Select(
                Option("All", value=""),
                Option("Searching", value="searching"),
                Option("Announced", value="announced"),
                Option("Completed", value="completed"),
                Option("Liquidated", value="liquidated"),
                name="status", id="spac-status",
                cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none",
                style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}",
            ),
            cls="w-36",
        ),
        Div(
            Label("Min Trust", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
            Select(
                Option("Any", value="0"),
                Option("$50M+", value="50000000"),
                Option("$100M+", value="100000000"),
                Option("$200M+", value="200000000"),
                Option("$500M+", value="500000000"),
                name="min_trust", id="spac-min-trust",
                cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none",
                style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}",
            ),
            cls="w-36",
        ),
        Div(
            Label("Search", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
            Input(
                type="text", name="q", placeholder="Ticker or name...",
                id="spac-search",
                cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none",
                style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}",
            ),
            cls="flex-1",
        ),
        Button(
            "Apply",
            onclick="loadSpacTable()",
            cls="text-xs font-medium px-4 py-1.5 rounded self-end cursor-pointer",
            style=f"background:{AMBER}; color:{BG}",
        ),
        cls="flex flex-wrap gap-3 items-end mb-4",
    )


def _status_badge(status: str):
    color = STATUS_COLORS.get(status, INK_MUTED)
    return Span(
        status.capitalize(),
        cls="text-[10px] font-medium px-2 py-0.5 rounded",
        style=f"color:{color}; border:1px solid {color}",
    )


def spac_table(df):
    if df is None or df.empty:
        return Div(
            P("No SPAC data available. Run sync to populate.",
              cls="text-sm", style=f"color:{INK_MUTED}"),
            cls="flex items-center justify-center py-12",
        )

    rows = []
    for _, r in df.iterrows():
        rows.append(Tr(
            Td(Span(r.get("ticker") or "—", cls="font-medium text-xs",
                     style=f"color:{AMBER}"),
               cls="px-3 py-2"),
            Td(Span(str(r.get("company_name") or "—")[:40], cls="text-xs",
                     style=f"color:{INK}"),
               cls="px-3 py-2"),
            Td(_status_badge(r.get("status", "searching")),
               cls="px-3 py-2"),
            Td(Span(_fmt_money(r.get("trust_size")), cls="text-xs",
                     style=f"color:{INK}"),
               cls="px-3 py-2 text-right"),
            Td(Span(f"${r['current_price']:.2f}" if r.get("current_price") else "—",
                     cls="text-xs", style=f"color:{INK}"),
               cls="px-3 py-2 text-right"),
            Td(Span(f"{r['nav_premium_pct']:+.1f}%" if r.get("nav_premium_pct") else "—",
                     cls="text-xs",
                     style=f"color:{GREEN if (r.get('nav_premium_pct') or 0) >= 0 else RED}"),
               cls="px-3 py-2 text-right"),
            Td(Span(str(r.get("target_name") or "—")[:25], cls="text-xs",
                     style=f"color:{INK_MUTED}"),
               cls="px-3 py-2"),
            Td(Span(str(r.get("ipo_date") or "—")[:10], cls="text-xs",
                     style=f"color:{INK_MUTED}"),
               cls="px-3 py-2"),
            Td(Span(r.get("exchange") or "—", cls="text-xs",
                     style=f"color:{INK_MUTED}"),
               cls="px-3 py-2"),
            cls="border-b", style=f"border-color:{BORDER}",
            hx_get=f"/app/spacs/holders/{r.get('ticker', '')}",
            hx_target=f"#holders-{r.get('ticker', 'x')}",
            hx_swap="innerHTML",
            hx_trigger="click",
            **{"_": f"on click toggle .hidden on #holders-{r.get('ticker', 'x')}"},
        ))
        rows.append(Tr(
            Td(Div(id=f"holders-{r.get('ticker', 'x')}",
                   cls="text-xs py-2", style=f"color:{INK_MUTED}"),
               colspan="9", cls="px-3"),
            cls=f"hidden border-b", id=f"holders-{r.get('ticker', 'x')}",
            style=f"border-color:{BORDER}; background:{BG}",
        ))

    header_cls = "px-3 py-2 text-xs font-medium text-left"
    return Div(
        Table(
            Thead(Tr(
                Th("Ticker", cls=header_cls, style=f"color:{INK_MUTED}"),
                Th("Name", cls=header_cls, style=f"color:{INK_MUTED}"),
                Th("Status", cls=header_cls, style=f"color:{INK_MUTED}"),
                Th("Trust", cls=f"{header_cls} text-right", style=f"color:{INK_MUTED}"),
                Th("Price", cls=f"{header_cls} text-right", style=f"color:{INK_MUTED}"),
                Th("NAV Prem", cls=f"{header_cls} text-right", style=f"color:{INK_MUTED}"),
                Th("Target", cls=header_cls, style=f"color:{INK_MUTED}"),
                Th("IPO Date", cls=header_cls, style=f"color:{INK_MUTED}"),
                Th("Exchange", cls=header_cls, style=f"color:{INK_MUTED}"),
                style=f"border-bottom:2px solid {BORDER}",
            )),
            Tbody(*rows),
            cls="w-full",
        ),
        cls="overflow-x-auto rounded-lg",
        style=f"background:{BG_CARD}; border:1px solid {BORDER}",
    )


def spac_page_content(stats: dict, df, timeline: list, breakdown: list):
    return Div(
        # Header
        Div(
            H1("SPAC Tracker", cls="text-xl font-bold", style=f"color:{INK}"),
            P("Special Purpose Acquisition Companies — lifecycle tracking, trust data, and institutional holdings",
              cls="text-sm mt-1", style=f"color:{INK_MUTED}"),
            cls="mb-6",
        ),
        # KPIs
        kpi_row(stats),
        # Charts row
        Div(
            Div(id="spac-timeline-chart",
                style=f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; min-height:300px; padding:8px;"),
            Div(id="spac-status-chart",
                style=f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; min-height:300px; padding:8px;"),
            cls="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6",
        ),
        # Filters
        filter_bar(),
        # Table
        Div(spac_table(df), id="spac-table-container"),
        # Plotly + scripts
        Script(src="https://cdn.plot.ly/plotly-2.35.0.min.js"),
        _chart_script(timeline, breakdown),
        _table_script(),
        cls="w-full",
        style=f"color:{INK}; padding: 1.5rem;",
    )


def _chart_script(timeline: list, breakdown: list):
    import json
    tl_json = json.dumps(timeline)
    bd_json = json.dumps(breakdown)
    return Script(f"""
    (function() {{
        const timeline = {tl_json};
        const breakdown = {bd_json};
        const dark = {{paper_bgcolor:'#111827', plot_bgcolor:'#111827',
                       font:{{color:'#F8FAFC', size:11}},
                       margin:{{t:40, l:50, r:20, b:40}}}};
        const statusColors = {{'searching':'#3B82F6','announced':'#F59E0B',
                               'completed':'#10B981','liquidated':'#EF4444'}};

        // Timeline bar chart
        if (timeline.length) {{
            const years = timeline.map(t => t.year);
            const counts = timeline.map(t => t.ipo_count);
            const proceeds = timeline.map(t => t.total_proceeds);
            Plotly.newPlot('spac-timeline-chart', [
                {{x:years, y:counts, type:'bar', name:'SPAC IPOs',
                  marker:{{color:'#3B82F6'}}, yaxis:'y'}},
                {{x:years, y:proceeds.map(p => p/1e9), type:'scatter', mode:'lines+markers',
                  name:'Proceeds ($B)', line:{{color:'#F59E0B', width:2}}, yaxis:'y2'}},
            ], {{
                ...dark,
                title:{{text:'Annual SPAC IPOs & Proceeds', font:{{size:14}}}},
                yaxis:{{title:'IPO Count', gridcolor:'#1E293B'}},
                yaxis2:{{title:'Proceeds ($B)', overlaying:'y', side:'right', gridcolor:'#1E293B'}},
                xaxis:{{gridcolor:'#1E293B'}},
                legend:{{x:0.01, y:0.99, bgcolor:'transparent'}},
                barmode:'group',
            }}, {{responsive:true}});
        }} else {{
            document.getElementById('spac-timeline-chart').innerHTML =
                '<div style="display:flex;align-items:center;justify-content:center;height:280px;color:#94A3B8">No timeline data</div>';
        }}

        // Status donut
        if (breakdown.length) {{
            const labels = breakdown.map(b => b.status.charAt(0).toUpperCase() + b.status.slice(1));
            const values = breakdown.map(b => b.count);
            const colors = breakdown.map(b => statusColors[b.status] || '#94A3B8');
            Plotly.newPlot('spac-status-chart', [{{
                type:'pie', labels:labels, values:values,
                hole:0.5, marker:{{colors:colors}},
                textinfo:'label+value', textfont:{{size:11}},
                hovertemplate:'%{{label}}: %{{value}} SPACs<extra></extra>',
            }}], {{
                ...dark,
                title:{{text:'SPACs by Status', font:{{size:14}}}},
                showlegend:true,
                legend:{{font:{{size:10}}}},
            }}, {{responsive:true}});
        }} else {{
            document.getElementById('spac-status-chart').innerHTML =
                '<div style="display:flex;align-items:center;justify-content:center;height:280px;color:#94A3B8">No breakdown data</div>';
        }}
    }})();
    """)


def _table_script():
    return Script("""
    async function loadSpacTable() {
        const status = document.getElementById('spac-status').value;
        const minTrust = document.getElementById('spac-min-trust').value;
        const q = document.getElementById('spac-search').value;
        const params = new URLSearchParams({status, min_trust: minTrust, q});
        const container = document.getElementById('spac-table-container');
        container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;padding:3rem;color:#94A3B8">Loading...</div>';
        try {
            const resp = await fetch('/app/spacs/body?' + params);
            container.innerHTML = await resp.text();
        } catch(e) {
            container.innerHTML = '<div style="color:#EF4444;padding:2rem;text-align:center">Error loading data</div>';
        }
    }
    """)
