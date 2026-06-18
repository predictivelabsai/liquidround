"""Hedge fund treemap + filter UI components — LiquidRound palette."""
from __future__ import annotations

from fasthtml.common import *

BG = "#0B1220"
BG_CARD = "#111827"
BORDER = "#1E293B"
INK = "#F8FAFC"
INK_MUTED = "#94A3B8"
AMBER = "#F59E0B"


def hedge_fund_page_content():
    """Full-width hedge fund treemap page rendered inside the chat app shell."""
    return Div(
        # Header
        Div(
            H1("Hedge Fund Treemap", cls="text-xl font-bold", style=f"color:{INK}"),
            P("SEC Form 13F institutional holdings — top positions across funds",
              cls="text-sm mt-1", style=f"color:{INK_MUTED}"),
            cls="mb-4",
        ),
        # Filters row
        Div(
            Div(
                Label("Fund", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
                Input(
                    type="text", name="fund", placeholder="e.g. Bridgewater",
                    id="hf-fund-filter",
                    cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none focus:ring-1",
                    style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}; focus:ring-color:{AMBER}",
                ),
                cls="flex-1",
            ),
            Div(
                Label("Min Value ($)", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
                Select(
                    Option("Any", value="0"),
                    Option("$1M+", value="1000"),
                    Option("$10M+", value="10000"),
                    Option("$100M+", value="100000"),
                    Option("$1B+", value="1000000"),
                    name="min_value",
                    id="hf-min-value",
                    cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none",
                    style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}",
                ),
                cls="w-36",
            ),
            Div(
                Label("Limit", cls="text-xs font-medium block mb-1", style=f"color:{INK_MUTED}"),
                Select(
                    Option("200", value="200"),
                    Option("500", value="500", selected=True),
                    Option("1000", value="1000"),
                    name="limit",
                    id="hf-limit",
                    cls="w-full text-xs rounded px-2 py-1.5 border focus:outline-none",
                    style=f"background:{BG_CARD}; color:{INK}; border-color:{BORDER}",
                ),
                cls="w-24",
            ),
            Button(
                "Apply",
                onclick="loadTreemap()",
                cls="text-xs font-medium px-4 py-1.5 rounded self-end cursor-pointer",
                style=f"background:{AMBER}; color:{BG}",
            ),
            cls="flex gap-3 items-end mb-4",
        ),
        # Treemap container
        Div(
            Div(
                P("Loading treemap...", cls="text-sm", style=f"color:{INK_MUTED}"),
                cls="flex items-center justify-center h-96",
            ),
            id="treemap-container",
            style=f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; min-height:500px; padding:8px;",
        ),
        # Stats row
        Div(id="hf-stats", cls="mt-3 text-xs", style=f"color:{INK_MUTED}"),
        # Plotly CDN + loader script
        Script(src="https://cdn.plot.ly/plotly-2.35.0.min.js"),
        Script("""
        function fmtMoney(v) {
            if (v >= 1e12) return '$' + (v/1e12).toFixed(1) + 'T';
            if (v >= 1e9) return '$' + (v/1e9).toFixed(1) + 'B';
            if (v >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
            if (v >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
            return '$' + v.toFixed(0);
        }
        async function loadTreemap() {
            const fund = document.getElementById('hf-fund-filter').value;
            const minVal = document.getElementById('hf-min-value').value;
            const limit = document.getElementById('hf-limit').value;
            const params = new URLSearchParams({fund, min_value: minVal, limit});
            const container = document.getElementById('treemap-container');
            container.innerHTML = '<div class="flex items-center justify-center h-96"><p style="color:#94A3B8">Loading...</p></div>';
            try {
                const resp = await fetch('/app/hedgefunds/data?' + params);
                const data = await resp.json();
                if (!data.length) {
                    container.innerHTML = '<div class="flex items-center justify-center h-96"><p style="color:#94A3B8">No data matching filters.</p></div>';
                    return;
                }
                const uniqueFunds = [...new Set(data.map(d => d.fund))];
                // ids must be unique — use fund/security composite for children
                const ids = [
                    ...uniqueFunds,
                    ...data.map(d => d.fund + '/' + d.security),
                ];
                const labels = [
                    ...uniqueFunds,
                    ...data.map(d => d.security),
                ];
                const parentIds = [
                    ...uniqueFunds.map(() => ''),
                    ...data.map(d => d.fund),
                ];
                const values = [
                    ...uniqueFunds.map(() => 0),
                    ...data.map(d => d.value),
                ];
                const textLabels = labels.map((l, i) => values[i] > 0 ? l + '\\n' + fmtMoney(values[i]) : l);
                const trace = {
                    type: 'treemap',
                    ids: ids,
                    labels: labels,
                    parents: parentIds,
                    values: values,
                    branchvalues: 'remainder',
                    text: textLabels,
                    textinfo: 'text',
                    hovertemplate: '%{label}<br>%{text}<br>Parent: %{parent}<extra></extra>',
                    marker: {
                        colorscale: [[0, '#1E293B'], [0.5, '#F59E0B'], [1, '#EF4444']],
                        colors: values,
                    },
                    pathbar: {visible: true},
                };
                const layout = {
                    margin: {t: 30, l: 5, r: 5, b: 5},
                    paper_bgcolor: '#111827',
                    font: {color: '#F8FAFC', size: 10},
                    treemapcolorway: ['#F59E0B', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316'],
                };
                Plotly.newPlot(container, [trace], layout, {responsive: true});
                document.getElementById('hf-stats').textContent =
                    `Showing ${data.length} positions across ${uniqueFunds.length} funds`;
            } catch(e) {
                container.innerHTML = '<div class="flex items-center justify-center h-96"><p style="color:#EF4444">Error loading data.</p></div>';
            }
        }
        // Auto-load on page render
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', loadTreemap);
        } else {
            loadTreemap();
        }
        """),
        cls="w-full",
        style=f"color:{INK}",
    )
