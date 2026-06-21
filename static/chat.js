/* LiquidRound — chat client (SSE streaming, 3-pane interactions).
   Ported from pehero/static/chat.js; endpoints adapted for LiquidRound. */

(() => {
    const $ = (sel) => document.querySelector(sel);

    let currentSessionId = getSidFromURL();
    let currentAgentSlug = null;
    let streaming = false;

    const AGENT_PROMPTS = readJsonScript("agent-prompts-data") || {};
    const AGENT_NAMES = readJsonScript("agent-names-data") || {};

    function readJsonScript(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try { return JSON.parse(el.textContent); }
        catch (e) { console.warn("bad JSON in #" + id, e); return null; }
    }

    function getSidFromURL() {
        const p = new URLSearchParams(window.location.search);
        return p.get("sid") || "";
    }
    window.setSid = function(sid) {
        currentSessionId = sid;
        const u = new URL(window.location);
        u.searchParams.set("sid", sid);
        history.replaceState(null, "", u);
    };

    /* ── Message rendering ───────────────────────────────────────── */

    function addBubble(role, text, agentSlug) {
        const wrap = document.createElement("div");
        wrap.className = `msg msg-${role}`;
        if (role === "assistant" && agentSlug) {
            const hdr = document.createElement("div");
            hdr.className = "msg-agent";
            const nice = AGENT_NAMES[agentSlug] || agentSlug;
            hdr.innerHTML = `<span class="msg-agent-icon">◆</span><span class="msg-agent-label"></span>`;
            hdr.querySelector(".msg-agent-label").textContent = nice;
            wrap.appendChild(hdr);
        }
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.textContent = text;
        wrap.appendChild(bubble);
        $("#messages").appendChild(wrap);
        scrollMessagesBottom();
        return bubble;
    }

    function appendToolLog(bubble, name, args) {
        if (!bubble) return;
        let log = bubble.parentElement.querySelector(".tool-log");
        if (!log) {
            log = document.createElement("div");
            log.className = "tool-log";
            bubble.parentElement.appendChild(log);
        }
        const step = document.createElement("div");
        step.className = "tool-step";
        const argStr = args ? JSON.stringify(args).slice(0, 140) : "";
        step.innerHTML = `→ <span class="tool-name"></span> <span class="tool-args"></span>`;
        step.querySelector(".tool-name").textContent = name;
        step.querySelector(".tool-args").textContent = argStr;
        log.appendChild(step);
    }

    function scrollMessagesBottom() {
        const m = $("#messages");
        if (m) m.scrollTop = m.scrollHeight;
    }

    function renderMarkdownLite(text) {
        let out = text
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/```([\s\S]*?)```/g, "<pre>$1</pre>")
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
        // Auto-link URLs (SEC/EDGAR, etc.) — open in new tab
        out = out.replace(
            /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener" style="color:#F59E0B;text-decoration:underline;">$1</a>'
        );
        out = out.replace(
            /(^|[\s(])(https?:\/\/[^\s<)]+)/g,
            '$1<a href="$2" target="_blank" rel="noopener" style="color:#F59E0B;text-decoration:underline;">$2</a>'
        );
        const lines = out.split("\n");
        const html = [];
        let inList = false;
        let inTable = false;
        let tableRows = [];
        for (const l of lines) {
            const trimmed = l.trim();
            // Markdown table row detection
            if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
                if (inList) { html.push("</ul>"); inList = false; }
                // Skip separator rows (|---|---|)
                if (/^\|[\s\-:|]+\|$/.test(trimmed)) continue;
                const cells = trimmed.slice(1, -1).split("|").map(c => c.trim());
                tableRows.push(cells);
                inTable = true;
                continue;
            }
            // Flush table if we were in one
            if (inTable) {
                html.push(_renderMarkdownTable(tableRows));
                tableRows = [];
                inTable = false;
            }
            if (l.match(/^- /)) {
                if (!inList) { html.push("<ul>"); inList = true; }
                html.push(`<li>${l.slice(2)}</li>`);
            } else {
                if (inList) { html.push("</ul>"); inList = false; }
                html.push(l || "<br>");
            }
        }
        if (inTable) html.push(_renderMarkdownTable(tableRows));
        if (inList) html.push("</ul>");
        return html.join("\n");
    }

    function _renderMarkdownTable(rows) {
        if (!rows.length) return "";
        const header = rows[0];
        const body = rows.slice(1);
        let h = '<div class="table-scroll"><table class="artifact-table"><thead><tr>' +
            header.map(c => `<th>${c}</th>`).join("") + '</tr></thead><tbody>';
        for (const row of body) {
            h += '<tr>' + row.map(c => `<td>${c}</td>`).join("") + '</tr>';
        }
        h += '</tbody></table></div>';
        return h;
    }

    /* ── Thinking indicator ────────────────────────────────────── */

    let thinker = null;
    function showThinking(bubble) {
        if (!bubble) return;
        thinker = { started: Date.now(), tool: null, el: document.createElement("div"), timerId: null };
        thinker.el.className = "thinking-indicator";
        thinker.el.innerHTML = `<span class="dot"></span><span class="label">Thinking… <span class="secs">0s</span></span>`;
        bubble.parentElement.insertBefore(thinker.el, bubble);
        thinker.timerId = setInterval(updateThinking, 500);
    }
    function updateThinking() {
        if (!thinker) return;
        const secs = Math.floor((Date.now() - thinker.started) / 1000);
        const label = thinker.tool
            ? `Thinking… <span class="secs">${secs}s</span> · calling <code>${thinker.tool}</code>`
            : `Thinking… <span class="secs">${secs}s</span>`;
        thinker.el.querySelector(".label").innerHTML = label;
    }
    function setThinkingTool(name) {
        if (!thinker) return;
        thinker.tool = name;
        updateThinking();
    }
    function hideThinking() {
        if (!thinker) return;
        clearInterval(thinker.timerId);
        if (thinker.el && thinker.el.parentElement) thinker.el.parentElement.removeChild(thinker.el);
        thinker = null;
    }

    /* ── Sample cards ──────────────────────────────────────────── */

    window.updateSampleCards = (slug) => {
        const row = $("#sample-cards-row");
        const label = $("#sample-cards-label");
        if (!row) return;
        let prompts = (slug && AGENT_PROMPTS[slug]) || [];
        if (!prompts.length) {
            prompts = [
                "triage: Baltic vet chain, EUR 4M EBITDA, 25% growth",
                "profile: GRG1L.VS",
                "dcf: Grigeo at 9% WACC, 2.5% terminal growth",
                "memo: draft the IC memo for InMedica",
                "vdr: audit the data room for Lietuvos Veterinarija",
                "research: Baltic healthcare consolidation",
            ];
        }
        row.innerHTML = "";
        prompts.slice(0, 6).forEach(p => {
            const b = document.createElement("button");
            b.className = "sample-card";
            b.title = p;
            b.innerHTML = `<span class="sample-card-text"></span>`;
            b.querySelector(".sample-card-text").textContent = p;
            b.onclick = () => { fillChat(p); sendMessage(null); };
            row.appendChild(b);
        });
        if (label) {
            label.textContent = slug && AGENT_NAMES[slug]
                ? `Try with ${AGENT_NAMES[slug]}`
                : `Try a prompt`;
        }
    };

    window.onInputChange = (ta) => {
        const v = (ta.value || "").trim().toLowerCase();
        const m = v.match(/^(\w{2,10}):/);
        if (!m) return;
        const prefix = m[1] + ":";
        for (const slug of Object.keys(AGENT_PROMPTS)) {
            const first = (AGENT_PROMPTS[slug][0] || "").toLowerCase();
            if (first.startsWith(prefix)) { updateSampleCards(slug); return; }
        }
    };

    /* ── Memo → PDF preview + highlight ────────────────────────── */

    // Agents whose responses can be previewed as a PDF memo.
    const MEMO_AGENTS = new Set(["ic_memo_writer", "teaser_designer", "bid_strategist", "ipo_readiness"]);
    let lastMemoFileId = null;

    async function renderMemoPdf(markdown, title) {
        const body = new URLSearchParams({ markdown, title: title || "IC memo" });
        const r = await fetch("/app/memo-pdf/render", { method: "POST", body });
        if (!r.ok) throw new Error("render failed " + r.status);
        const data = await r.json();
        if (data.error) throw new Error(data.error);
        lastMemoFileId = data.file_id;
        openPdfInPane(data.file_url, null, data.title);
        return data;
    }

    function openPdfInPane(fileUrl, searchText, title) {
        const abs = fileUrl.startsWith("http") ? fileUrl : (window.location.origin + fileUrl);
        let viewer = "https://mozilla.github.io/pdf.js/web/viewer.html?file=" + encodeURIComponent(abs);
        if (searchText) {
            viewer += "#search=" + encodeURIComponent(String(searchText).slice(0, 120)) + "&phrase=true";
        }
        const body = $("#artifact-body");
        const empty = $("#artifact-empty");
        if (empty) empty.style.display = "none";
        body.style.display = "block";
        body.innerHTML = `
            <div class="pdf-wrap">
              <div class="pdf-caption"></div>
              <iframe id="pdf-frame" class="pdf-iframe" src="${viewer}" allow="fullscreen"></iframe>
            </div>`;
        const cap = body.querySelector(".pdf-caption");
        cap.innerHTML = (title ? escapeHtml(title) : "Memo preview") +
            (searchText ? ' · <i>highlighting "' + escapeHtml(String(searchText).slice(0, 40)) + '"</i>' : "");
        const sub = $("#artifact-subtitle");
        if (sub) sub.textContent = title || "PDF preview";
        document.querySelector(".app").classList.remove("pane-closed");
        $("#right-pane").classList.add("open");
        $("#artifact-btn").classList.add("active");
    }

    async function highlightInLastPdf(searchText) {
        if (!lastMemoFileId) return false;
        const body = new URLSearchParams({ search: searchText, file_id: lastMemoFileId });
        const r = await fetch("/app/memo-pdf/highlight", { method: "POST", body });
        if (!r.ok) return false;
        const data = await r.json();
        if (data.error) return false;
        const frame = document.getElementById("pdf-frame");
        if (frame) frame.src = data.viewer_url;
        const cap = document.querySelector(".pdf-caption");
        if (cap) cap.innerHTML = 'Memo preview · <i>highlighting "' + escapeHtml(String(searchText).slice(0, 40)) + '"</i>';
        return true;
    }

    function maybeAppendMemoPreviewButton(bubble, text, agentSlug) {
        if (!bubble || !text) return;
        if (!MEMO_AGENTS.has(agentSlug)) return;
        // Heuristic: a memo needs a couple of markdown headers + some length.
        const looksMemo = text.length > 400 && /(^|\n)##?\s+\w/.test(text);
        if (!looksMemo) return;
        const existing = bubble.parentElement.querySelector(".memo-preview-row");
        if (existing) return;
        const row = document.createElement("div");
        row.className = "memo-preview-row";
        row.innerHTML = `
            <button class="memo-preview-btn">📄 Preview PDF</button>
            <span class="memo-preview-hint">Renders this memo as a PDF in the right pane — then ask "show me the deal size" to jump to it.</span>`;
        bubble.parentElement.appendChild(row);
        const btn = row.querySelector(".memo-preview-btn");
        btn.onclick = async () => {
            btn.disabled = true; btn.textContent = "Rendering…";
            try {
                const title = (AGENT_NAMES[agentSlug] || "Memo") + " — " + new Date().toLocaleDateString();
                await renderMemoPdf(text, title);
                btn.textContent = "✓ PDF open in the right pane";
            } catch (e) {
                btn.textContent = "Render failed";
                console.error(e);
            }
        };
    }

    // If the user's last message looks like a PDF-highlight intent AND a memo
    // PDF is already rendered, intercept and navigate the iframe — no SSE roundtrip.
    function tryHighlightIntent(msg) {
        if (!lastMemoFileId) return false;
        const m = msg.match(/^\s*(?:show|find|highlight|jump to|where (?:is|does))\s+(?:me\s+)?(?:the\s+)?(.+?)[?.!]?\s*$/i);
        if (!m) return false;
        const term = m[1].trim();
        if (term.length < 3 || term.length > 60) return false;
        highlightInLastPdf(term);
        addBubble("user", msg);
        addBubble("assistant", `Highlighted "${term}" in the memo PDF →`, null);
        return true;
    }
    window.renderMemoPdf = renderMemoPdf;
    window.openPdfInPane = openPdfInPane;
    window.highlightInLastPdf = highlightInLastPdf;
    window.tryHighlightIntent = tryHighlightIntent;

    /* ── Follow-up ("Next step") detection ─────────────────────── */

    function maybeAppendFollowUp(bubble, text) {
        if (!bubble || !text) return;
        const m = text.match(/\*?\*?Next step\*?\*?[\s]*[—–:-][\s]*([^\n]+)/i);
        if (!m) return;
        const action = m[1].trim().replace(/\*+$/, "");
        const row = document.createElement("div");
        row.className = "followup-row";
        row.innerHTML = `
            <div class="followup-prompt"></div>
            <button class="followup-btn followup-yes">Yes, do that</button>
            <button class="followup-btn followup-no">No thanks</button>`;
        row.querySelector(".followup-prompt").textContent = action;
        bubble.parentElement.appendChild(row);
        row.querySelector(".followup-yes").onclick = () => {
            row.remove();
            fillChat("Yes — do that: " + action);
            sendMessage(null);
        };
        row.querySelector(".followup-no").onclick = () => row.remove();
    }

    /* ── SSE send ──────────────────────────────────────────────── */

    async function sendMessage(evt) {
        if (evt) evt.preventDefault();
        if (streaming) return;
        const ta = $("#chat-input");
        const msg = ta.value.trim();
        if (!msg) return;

        // Client-side fast path: if a memo PDF is already open and the user
        // asks "show me the deal size", highlight directly in the iframe
        // and skip the round-trip.
        if (tryHighlightIntent(msg)) {
            ta.value = "";
            ta.style.height = "";
            return;
        }

        streaming = true;
        const sendBtn = $("#send-btn");
        if (sendBtn) sendBtn.disabled = true;

        const wh = $("#welcome-hero");
        if (wh) wh.style.display = "none";

        addBubble("user", msg);
        ta.value = "";
        ta.style.height = "";

        const body = new URLSearchParams({ msg, sid: currentSessionId || "" });

        let resp;
        try {
            resp = await fetch("/app/chat", { method: "POST", body });
        } catch (e) {
            addBubble("assistant", "Network error: " + e.message);
            streaming = false; if (sendBtn) sendBtn.disabled = false;
            return;
        }
        if (!resp.ok) {
            addBubble("assistant", "Error: " + resp.status);
            streaming = false; if (sendBtn) sendBtn.disabled = false;
            return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let bubble = null;
        let accumulated = "";
        let pendingArtifacts = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            let idx;
            while ((idx = buffer.indexOf("\n\n")) !== -1) {
                const raw = buffer.slice(0, idx);
                buffer = buffer.slice(idx + 2);
                handleEvent(raw, (type, payload) => {
                    if (type === "agent_route") {
                        const nice = payload.agent || AGENT_NAMES[payload.slug] || payload.slug;
                        const lbl = $("#current-agent-label");
                        if (lbl) lbl.textContent = nice;
                        currentAgentSlug = payload.slug;
                        updateSampleCards(payload.slug);
                        bubble = addBubble("assistant", "", payload.slug);
                        bubble.classList.add("streaming");
                        showThinking(bubble);
                    } else if (type === "token") {
                        if (!bubble) bubble = addBubble("assistant", "", "");
                        if (accumulated === "") hideThinking();
                        accumulated += payload.text;
                        bubble.innerHTML = renderMarkdownLite(accumulated);
                        scrollMessagesBottom();
                    } else if (type === "tool_start") {
                        setThinkingTool(payload.name);
                        appendToolLog(bubble || addBubble("assistant", "", ""), payload.name, payload.args);
                    } else if (type === "tool_end") {
                        // no-op for now (thinking label stays on tool name)
                    } else if (type === "artifact_show") {
                        showArtifact(payload);
                        if (!bubble) bubble = addBubble("assistant", "", currentAgentSlug || "");
                        // Queue table artifacts for inline rendering after all tokens
                        if (payload.kind === "table" && Array.isArray(payload.rows) && payload.rows.length) {
                            if (!pendingArtifacts) pendingArtifacts = [];
                            pendingArtifacts.push(payload);
                        }
                    } else if (type === "error") {
                        hideThinking();
                        if (!bubble) bubble = addBubble("assistant", "", "");
                        bubble.textContent = "Error: " + (payload.message || "unknown");
                    } else if (type === "session") {
                        if (payload.sid) setSid(payload.sid);
                    } else if (type === "done") {
                        hideThinking();
                        if (bubble) bubble.classList.remove("streaming");
                        if (bubble && pendingArtifacts) {
                            for (const art of pendingArtifacts) {
                                const tbl = document.createElement("div");
                                tbl.className = "inline-artifact";
                                tbl.innerHTML = '<div class="inline-artifact-title">' + escapeHtml(art.title || "") + '</div>' + renderArtifactHTML(art);
                                tbl.appendChild(_exportButtons(art));
                                bubble.appendChild(tbl);
                            }
                            scrollMessagesBottom();
                        }
                        maybeAppendFollowUp(bubble, accumulated);
                        maybeAppendMemoPreviewButton(bubble, accumulated, payload.slug || currentAgentSlug);
                    }
                });
            }
        }
        streaming = false; if (sendBtn) sendBtn.disabled = false;
    }

    function handleEvent(raw, cb) {
        let type = null; let data = "";
        for (const line of raw.split("\n")) {
            if (line.startsWith("event: ")) type = line.slice(7).trim();
            else if (line.startsWith("data: ")) data += line.slice(6);
        }
        if (!type) return;
        try { cb(type, data ? JSON.parse(data) : {}); }
        catch (e) { console.error("bad sse line", raw, e); }
    }

    /* ── Artifact pane ─────────────────────────────────────────── */

    function showArtifact(payload) {
        const body = $("#artifact-body");
        const empty = $("#artifact-empty");
        if (!body) return;
        empty.style.display = "none";
        body.style.display = "block";

        const sub = $("#artifact-subtitle");
        if (sub) sub.textContent = payload.subtitle || "";

        const card = document.createElement("div");
        card.className = "artifact-card";
        const title = payload.title || "Artifact";
        const kind = payload.kind || "note";
        card.innerHTML = `
            <div class="meta kind-${kind}"></div>
            <h4></h4>
            <div class="body"></div>`;
        card.querySelector(".meta").textContent = kind;
        card.querySelector("h4").textContent = title;
        card.querySelector(".body").innerHTML = renderArtifactHTML(payload);
        if (kind === "table" && Array.isArray(payload.rows) && payload.rows.length) {
            card.querySelector(".body").appendChild(_exportButtons(payload));
        }
        body.prepend(card);

        document.querySelector(".app").classList.remove("pane-closed");
        $("#right-pane").classList.add("open");
        $("#artifact-btn").classList.add("active");
    }

    function _exportButtons(payload) {
        const wrap = document.createElement("div");
        wrap.style.cssText = "display:flex;gap:6px;margin-top:8px;";
        const cols = payload.columns || Object.keys(payload.rows[0] || {});
        const dataJson = JSON.stringify({columns: cols, rows: payload.rows, title: payload.title || "export"});

        function makeBtn(label, format) {
            const btn = document.createElement("button");
            btn.textContent = label;
            btn.style.cssText = "font-size:11px;padding:3px 10px;border-radius:4px;border:1px solid #1E293B;background:#111827;color:#94A3B8;cursor:pointer;";
            btn.onmouseenter = () => btn.style.color = "#F59E0B";
            btn.onmouseleave = () => btn.style.color = "#94A3B8";
            btn.onclick = () => _downloadExport(dataJson, format, payload.title || "export");
            return btn;
        }
        wrap.appendChild(makeBtn("⬇ XLSX", "xlsx"));
        wrap.appendChild(makeBtn("⬇ CSV", "csv"));
        return wrap;
    }

    async function _downloadExport(dataJson, format, title) {
        if (format === "csv") {
            const parsed = JSON.parse(dataJson);
            const cols = parsed.columns;
            const rows = parsed.rows;
            const csvLines = [cols.join(",")];
            for (const r of rows) {
                csvLines.push(cols.map(c => {
                    let v = r[c];
                    if (v === null || v === undefined) v = "";
                    v = String(v).replace(/"/g, '""');
                    return v.includes(",") || v.includes('"') || v.includes("\n") ? `"${v}"` : v;
                }).join(","));
            }
            const blob = new Blob([csvLines.join("\n")], {type: "text/csv"});
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = (title || "export").replace(/[^a-zA-Z0-9]/g, "_") + ".csv";
            a.click();
            return;
        }
        // XLSX via server endpoint
        const form = new FormData();
        form.append("data", dataJson);
        const resp = await fetch("/app/export/xlsx", {method: "POST", body: form});
        if (!resp.ok) { alert("Export failed"); return; }
        const blob = await resp.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = (title || "export").replace(/[^a-zA-Z0-9]/g, "_") + ".xlsx";
        a.click();
    }

    function renderArtifactHTML(p) {
        if (p.kind === "table" && Array.isArray(p.rows)) {
            if (!p.rows.length) return "<p><em>No rows.</em></p>";
            const cols = p.columns || Object.keys(p.rows[0]);
            const head = "<tr>" + cols.map(c => `<th>${c}</th>`).join("") + "</tr>";
            const body = p.rows.map(r => "<tr>" + cols.map(c => `<td>${formatCell(r[c])}</td>`).join("") + "</tr>").join("");
            return `<table class="artifact-table">${head}${body}</table>`;
        }
        if (p.kind === "citations" && Array.isArray(p.items)) {
            return p.items.map(it => `
                <div style="margin-bottom:.6rem;">
                    <div style="color:var(--ink); font-size:.8rem; font-weight:500;">${escapeHtml(it.title || "")}</div>
                    <div style="color:var(--ink-dim); font-size:.68rem; font-family:'JetBrains Mono',monospace;">${(it.doc_type || "").toUpperCase()}${it.url ? ` · <a href="${it.url}" target="_blank">link</a>` : ""} · score ${(it.score || 0).toFixed(2)}</div>
                    <div style="color:var(--ink-muted); font-size:.75rem; margin-top:.25rem;">${escapeHtml(it.snippet || "").replace(/\n/g, "<br>")}</div>
                </div>`).join("");
        }
        if (p.body_md) return renderMarkdownLite(p.body_md);
        return `<pre>${escapeHtml(JSON.stringify(p, null, 2))}</pre>`;
    }

    function formatCell(v) {
        if (v === null || v === undefined) return "—";
        if (typeof v === "number") return v.toLocaleString();
        if (typeof v === "object") return JSON.stringify(v);
        const s = String(v);
        if (/^https?:\/\//.test(s)) {
            return `<a href="${s}" target="_blank" rel="noopener" style="color:#F59E0B;">link ↗</a>`;
        }
        return s;
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    /* ── UI helpers ─────────────────────────────────────────────── */

    window.toggleLeftPane = () => {
        document.querySelector(".left-pane").classList.toggle("open");
        document.querySelector(".left-overlay").classList.toggle("visible");
    };
    window.toggleArtifactPane = () => {
        const r = $("#right-pane");
        const app = document.querySelector(".app");
        if (r.classList.contains("open")) {
            r.classList.remove("open");
            app.classList.add("pane-closed");
            $("#artifact-btn").classList.remove("active");
        } else {
            switchRightTab("artifact");
            r.classList.add("open");
            app.classList.remove("pane-closed");
            $("#artifact-btn").classList.add("active");
        }
    };
    window.toggleNewsPane = () => {
        const r = $("#right-pane");
        const app = document.querySelector(".app");
        if (r.classList.contains("open") && $("#rpane-content-news") && $("#rpane-content-news").style.display !== "none") {
            r.classList.remove("open");
            app.classList.add("pane-closed");
            const nb = $("#news-btn"); if (nb) nb.classList.remove("active");
        } else {
            switchRightTab("news");
            r.classList.add("open");
            app.classList.remove("pane-closed");
            const nb = $("#news-btn"); if (nb) nb.classList.add("active");
            const ab = $("#artifact-btn"); if (ab) ab.classList.remove("active");
        }
    };
    window.switchRightTab = (tab) => {
        const artifact = $("#rpane-content-artifact");
        const news = $("#rpane-content-news");
        const tabArt = $("#rpane-tab-artifact");
        const tabNews = $("#rpane-tab-news");
        if (tab === "news") {
            if (artifact) artifact.style.display = "none";
            if (news) news.style.display = "";
            if (tabArt) tabArt.classList.remove("active");
            if (tabNews) tabNews.classList.add("active");
        } else {
            if (artifact) artifact.style.display = "";
            if (news) news.style.display = "none";
            if (tabArt) tabArt.classList.add("active");
            if (tabNews) tabNews.classList.remove("active");
        }
    };
    window.closeRightPane = () => {
        const r = $("#right-pane");
        const app = document.querySelector(".app");
        r.classList.remove("open");
        app.classList.add("pane-closed");
        const ab = $("#artifact-btn"); if (ab) ab.classList.remove("active");
        const nb = $("#news-btn"); if (nb) nb.classList.remove("active");
    };
    window.toggleGroup = (id) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.toggle("open");
        const btn = document.getElementById("btn-" + id);
        if (btn) btn.classList.toggle("open");
    };
    window.handleKey = (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); sendMessage(ev); }
    };
    window.autoResize = (el) => {
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 240) + "px";
    };
    window.fillChat = (text) => {
        const ta = $("#chat-input");
        ta.value = text;
        ta.focus();
        autoResize(ta);
        onInputChange(ta);
    };
    window.newChat = () => { window.location.href = "/app"; };
    window.showSignIn = () => { window.location.href = "/signin"; };
    window.signOut = () => { window.location.href = "/logout"; };

    window.setCurrency = async (code) => {
        const r = await fetch("/app/config", {
            method: "POST",
            body: new URLSearchParams({ currency: code }),
        });
        if (r.ok) {
            document.querySelectorAll(".cfg-chip").forEach(el => {
                el.classList.toggle("active", el.dataset.code === code);
            });
        }
    };
    window.setRole = async (role) => {
        const r = await fetch("/settings/save", {
            method: "POST",
            headers: { "HX-Request": "true" },
            body: new URLSearchParams({ role }),
        });
        if (r.ok) {
            document.querySelectorAll(".cfg-role-chip").forEach(el => {
                el.classList.toggle("active", el.dataset.role === role);
            });
            // Role affects the welcome prompts — reload the center pane by nav
            window.location.reload();
        }
    };

    window.sendMessage = sendMessage;

    // ── Auto-send from ?q= query param (used by nav links) ──────────
    const _qParam = new URLSearchParams(window.location.search).get("q");
    if (_qParam) {
        const u = new URL(window.location);
        u.searchParams.delete("q");
        history.replaceState(null, "", u);
        setTimeout(() => { fillChat(_qParam); sendMessage(null); }, 300);
    }

    // ── SVG icons for copy/share feedback ────────────────────────────
    const _svgClipboard = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
    const _svgCheck = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    const _svgShare = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
    const _svgShareSmall = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
    const _svgCheckSmall = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';

    function _flashBtn(btn, checkSvg, origSvg, label, doneLabel, cls) {
        const lbl = btn.querySelector('.action-label');
        btn.innerHTML = checkSvg;
        if (lbl) { lbl.textContent = doneLabel; btn.appendChild(lbl); }
        btn.classList.add(cls);
        setTimeout(() => {
            btn.innerHTML = origSvg;
            if (lbl) { lbl.textContent = label; btn.appendChild(lbl); }
            btn.classList.remove(cls);
        }, 1800);
    }

    // ── Copy / share chat ──────────────────────────────────────────
    window.copyChat = () => {
        const msgs = document.querySelectorAll(".msg");
        const lines = [];
        msgs.forEach(m => {
            const role = m.classList.contains("msg-user") ? "You" : "LiquidRound";
            const bubble = m.querySelector(".msg-bubble");
            if (bubble) lines.push(`${role}: ${bubble.textContent.trim()}`);
        });
        const text = lines.join("\n\n");
        navigator.clipboard.writeText(text).then(() => {
            const btn = document.getElementById("copy-chat-btn");
            if (btn) _flashBtn(btn, _svgCheck, _svgClipboard, "Copy", "Copied!", "copied");
        });
    };
    window.shareChat = async () => {
        const btn = document.getElementById("share-chat-btn");
        if (!currentSessionId) {
            if (btn) {
                const lbl = btn.querySelector('.action-label');
                if (lbl) { lbl.textContent = "No session"; setTimeout(() => { lbl.textContent = "Share"; }, 1500); }
            }
            return;
        }
        try {
            const r = await fetch("/app/share", {
                method: "POST",
                body: new URLSearchParams({ sid: currentSessionId }),
            });
            const data = await r.json();
            if (data.ok && data.url) {
                const url = window.location.origin + data.url;
                await navigator.clipboard.writeText(url);
                if (btn) _flashBtn(btn, _svgCheck, _svgShare, "Share", "Copied!", "copied");
            } else {
                if (btn) {
                    const lbl = btn.querySelector('.action-label');
                    if (lbl) { lbl.textContent = "Error"; setTimeout(() => { lbl.textContent = "Share"; }, 1500); }
                }
            }
        } catch (e) {
            console.error("share failed", e);
            if (btn) {
                const lbl = btn.querySelector('.action-label');
                if (lbl) { lbl.textContent = "Error"; setTimeout(() => { lbl.textContent = "Share"; }, 1500); }
            }
        }
    };

    // ── Sidebar session share button ─────────────────────────────────
    window.shareSession = async (event, sid, btn) => {
        event.stopPropagation();
        if (!sid) return;
        try {
            const r = await fetch("/app/share", {
                method: "POST",
                body: new URLSearchParams({ sid }),
            });
            const data = await r.json();
            if (data.ok && data.url) {
                const url = window.location.origin + data.url;
                await navigator.clipboard.writeText(url);
                btn.innerHTML = _svgCheckSmall;
                btn.classList.add("copied");
                setTimeout(() => {
                    btn.innerHTML = _svgShareSmall;
                    btn.classList.remove("copied");
                }, 1800);
            }
        } catch (e) {
            console.error("session share failed", e);
        }
    };
})();
