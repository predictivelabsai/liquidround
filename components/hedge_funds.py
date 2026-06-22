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
                cls="flex-1 min-w-[160px]",
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
                cls="flex-1 min-w-[120px]",
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
                cls="flex-1 min-w-[80px]",
            ),
            Button(
                "Apply",
                onclick="loadTreemap()",
                cls="text-xs font-medium px-4 py-1.5 rounded self-end cursor-pointer w-full sm:w-auto",
                style=f"background:{AMBER}; color:{BG}",
            ),
            Button(
                "Share ↗",
                onclick="copyTreemapUrl()",
                cls="text-xs font-medium px-4 py-1.5 rounded self-end cursor-pointer w-full sm:w-auto",
                style=f"border:1px solid {AMBER}; color:{AMBER}; background:transparent",
                id="hf-share-btn",
            ),
            Button(
                "★ Bookmark",
                onclick="bookmarkCurrentFund()",
                id="hf-bookmark-btn",
                cls="text-xs font-medium px-4 py-1.5 rounded self-end cursor-pointer w-full sm:w-auto",
                style=f"border:1px solid {AMBER}; color:{AMBER}; background:transparent; opacity:0.4",
                disabled=True,
            ),
            cls="flex flex-wrap gap-3 items-end mb-4",
        ),
        # Bookmarks section (hidden until JS populates it)
        Div(
            Span("★ Bookmarks", cls="text-xs font-semibold", style=f"color:{AMBER}"),
            Div(id="hf-bookmarks", cls="flex flex-wrap gap-2 mt-1"),
            id="hf-bookmarks-section",
            cls="mb-3",
            style="display:none",
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
        # Finviz-style gradient legend bar
        Div(
            Div(
                # Gradient bar
                Div(
                    style="height:14px;border-radius:3px;"
                          "background:linear-gradient(90deg,"
                          "#67000d,#a50f15,#cb181d,#ef3b2c,#fb6a4a,"
                          "#374151,"
                          "#74c476,#41ab5d,#238b45,#006d2c,#00441b);"
                          "flex:1;",
                ),
                cls="flex items-center gap-2",
            ),
            # Tick labels
            Div(
                Span("-50%", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span("-25%", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span("0%", cls="text-xs font-semibold", style=f"color:{INK}"),
                Span("+25%", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span("+50%", cls="text-xs", style=f"color:{INK_MUTED}"),
                cls="flex justify-between mt-1",
            ),
            # Description
            Div(
                Span("Color = YTD return", cls="text-xs font-medium", style=f"color:{INK}"),
                Span(" · ", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span("Size = position value (USD)", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span(" · ", cls="text-xs", style=f"color:{INK_MUTED}"),
                Span("Data: SEC 13F filings", cls="text-xs", style=f"color:{INK_MUTED}"),
                cls="mt-1",
            ),
            cls="mt-3 p-3 rounded-lg",
            style=f"background:{BG_CARD}; border:1px solid {BORDER}",
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
        function fmtPct(v) {
            if (v == null) return '';
            return (v >= 0 ? '+' : '') + (v * 100).toFixed(1) + '%';
        }
        // Red-green color scale matching finviz: deep red -> grey -> deep green
        function ytdColor(v) {
            if (v == null) return '#374151'; // grey for unknown
            // Clamp to [-0.5, 0.5] for color mapping
            var t = Math.max(-0.5, Math.min(0.5, v));
            var norm = (t + 0.5); // 0..1
            if (norm < 0.5) {
                // Red side: interpolate from deep red to grey
                var r2 = norm / 0.5;
                var r = Math.round(103 + (55 - 103) * r2);
                var g = Math.round(0 + (65 - 0) * r2);
                var b = Math.round(13 + (81 - 13) * r2);
                return 'rgb(' + r + ',' + g + ',' + b + ')';
            } else {
                // Green side: interpolate from grey to deep green
                var r2 = (norm - 0.5) / 0.5;
                var r = Math.round(55 + (0 - 55) * r2);
                var g = Math.round(65 + (68 - 65) * r2);
                var b = Math.round(81 + (27 - 81) * r2);
                return 'rgb(' + r + ',' + g + ',' + b + ')';
            }
        }
        // ---- Bookmark helpers ----
        async function loadBookmarks() {
            try {
                const resp = await fetch('/app/hedgefunds/bookmarks');
                const names = await resp.json();
                const section = document.getElementById('hf-bookmarks-section');
                const container = document.getElementById('hf-bookmarks');
                if (!names.length) { section.style.display = 'none'; container.innerHTML = ''; return; }
                section.style.display = '';
                container.innerHTML = names.map(function(name) {
                    var safe = name.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                    var enc = encodeURIComponent(name);
                    return '<span style="border:1px solid #F59E0B;color:#F59E0B;border-radius:9999px;padding:2px 10px;font-size:0.75rem;cursor:pointer;display:inline-flex;align-items:center;gap:4px"' +
                        ' onclick="loadFundFromBookmark(decodeURIComponent(' + "'" + enc + "'" + '))">' +
                        safe +
                        '<span onclick="event.stopPropagation();removeBookmark(decodeURIComponent(' + "'" + enc + "'" + '))" ' +
                        'style="cursor:pointer;margin-left:2px;opacity:0.7" title="Remove bookmark">&times;</span></span>';
                }).join('');
            } catch(e) { /* ignore for guests */ }
        }
        function bookmarkCurrentFund() {
            var fund = document.getElementById('hf-fund-filter').value.trim();
            if (!fund) return;
            bookmarkFund(fund);
        }
        async function bookmarkFund(name) {
            try {
                await fetch('/app/hedgefunds/bookmark', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({fund: name}),
                });
                loadBookmarks();
            } catch(e) { console.error('Bookmark error', e); }
        }
        async function removeBookmark(name) {
            try {
                await fetch('/app/hedgefunds/bookmark', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({fund: name}),
                });
                loadBookmarks();
            } catch(e) { console.error('Remove bookmark error', e); }
        }
        function loadFundFromBookmark(name) {
            document.getElementById('hf-fund-filter').value = name;
            updateBookmarkBtn();
            loadTreemap();
        }
        function updateBookmarkBtn() {
            var btn = document.getElementById('hf-bookmark-btn');
            var fund = document.getElementById('hf-fund-filter').value.trim();
            if (fund) { btn.disabled = false; btn.style.opacity = '1'; }
            else { btn.disabled = true; btn.style.opacity = '0.4'; }
        }
        // Track fund filter changes to enable/disable bookmark button
        document.addEventListener('DOMContentLoaded', function() {
            var fi = document.getElementById('hf-fund-filter');
            if (fi) { fi.addEventListener('input', updateBookmarkBtn); }
        });
        // ---- End bookmark helpers ----

        async function loadTreemap() {
            const fund = document.getElementById('hf-fund-filter').value;
            const minVal = document.getElementById('hf-min-value').value;
            const limit = document.getElementById('hf-limit').value;
            const params = new URLSearchParams({fund, min_value: minVal, limit});
            // Push filter state to browser URL so the link is shareable
            const _url = new URL(window.location);
            _url.search = '';
            if (fund) _url.searchParams.set('fund', fund);
            if (minVal !== '0') _url.searchParams.set('min_value', minVal);
            if (limit !== '500') _url.searchParams.set('limit', limit);
            history.replaceState(null, '', _url);
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
                const ids = [
                    ...uniqueFunds,
                    ...data.map(d => d.fund + '/' + d.security),
                ];
                const labels = [
                    ...uniqueFunds,
                    ...data.map(d => d.ticker || d.security),
                ];
                const parentIds = [
                    ...uniqueFunds.map(() => ''),
                    ...data.map(d => d.fund),
                ];
                const values = [
                    ...uniqueFunds.map(() => 0),
                    ...data.map(d => d.value),
                ];
                // Build color array: fund-level grey, leaf-level by YTD return
                const colors = [
                    ...uniqueFunds.map(() => '#1E293B'),
                    ...data.map(d => ytdColor(d.return_ytd)),
                ];
                const textLabels = labels.map((l, i) => {
                    if (values[i] <= 0) return l;
                    const idx = i - uniqueFunds.length;
                    if (idx >= 0 && data[idx].return_ytd != null) {
                        return l + '\\n' + fmtPct(data[idx].return_ytd);
                    }
                    return l + '\\n' + fmtMoney(values[i]);
                });
                const hoverTexts = labels.map((l, i) => {
                    if (i < uniqueFunds.length) return l;
                    const idx = i - uniqueFunds.length;
                    const d = data[idx];
                    var parts = [d.security, fmtMoney(d.value)];
                    if (d.ticker) parts.push(d.ticker);
                    if (d.return_ytd != null) parts.push('YTD: ' + fmtPct(d.return_ytd));
                    return parts.join('<br>');
                });
                const trace = {
                    type: 'treemap',
                    ids: ids,
                    labels: labels,
                    parents: parentIds,
                    values: values,
                    branchvalues: 'remainder',
                    text: textLabels,
                    textinfo: 'text',
                    hovertext: hoverTexts,
                    hoverinfo: 'text',
                    marker: {
                        colors: colors,
                        line: {width: 1, color: '#1E293B'},
                    },
                    textfont: {color: '#F8FAFC'},
                    pathbar: {visible: true},
                };
                const layout = {
                    margin: {t: 30, l: 5, r: 5, b: 5},
                    paper_bgcolor: '#111827',
                    font: {color: '#F8FAFC', size: 10},
                };
                Plotly.newPlot(container, [trace], layout, {responsive: true});
                const withReturns = data.filter(d => d.return_ytd != null).length;
                document.getElementById('hf-stats').textContent =
                    `Showing ${data.length} positions across ${uniqueFunds.length} funds · ${withReturns} with YTD returns`;
            } catch(e) {
                container.innerHTML = '<div class="flex items-center justify-center h-96"><p style="color:#EF4444">Error loading data.</p></div>';
            }
        }
        function copyTreemapUrl() {
            navigator.clipboard.writeText(window.location.href).then(function() {
                var btn = document.getElementById('hf-share-btn');
                var orig = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(function() { btn.textContent = orig; }, 1500);
            });
        }
        // On page load, read URL params and populate filter controls
        (function initFromUrl() {
            const params = new URLSearchParams(window.location.search);
            if (params.get('fund')) document.getElementById('hf-fund-filter').value = params.get('fund');
            if (params.get('min_value')) document.getElementById('hf-min-value').value = params.get('min_value');
            if (params.get('limit')) document.getElementById('hf-limit').value = params.get('limit');
            updateBookmarkBtn();
        })();
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() { loadTreemap(); loadBookmarks(); });
        } else {
            loadTreemap();
            loadBookmarks();
        }
        """),
        cls="w-full",
        style=f"color:{INK}; padding: 1.5rem;",
    )
