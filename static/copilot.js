(() => {
    const $ = (sel) => document.querySelector(sel);
    let copilotSid = null;
    let copilotStreaming = false;
    let sessionReady = false;
    let thinker = null;

    function escapeHtml(s) {
        return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function renderMd(text) {
        if (window.marked) return marked.parse(text);
        return escapeHtml(text).replace(/\n/g, "<br>");
    }

    function scrollBottom() {
        const box = $("#copilot-messages");
        if (box) box.scrollTop = box.scrollHeight;
    }

    function addBubble(role, text, agentSlug) {
        const box = $("#copilot-messages");
        if (!box) return null;
        const div = document.createElement("div");
        div.className = "msg msg-" + role;
        if (role === "assistant" && agentSlug) {
            const hdr = document.createElement("div");
            hdr.className = "msg-agent";
            hdr.innerHTML = '<span class="msg-agent-icon">◆</span><span class="msg-agent-label">' +
                escapeHtml(agentSlug) + '</span>';
            div.appendChild(hdr);
        }
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        if (text) bubble.innerHTML = renderMd(text);
        div.appendChild(bubble);
        box.appendChild(div);
        scrollBottom();
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
        const argStr = args ? JSON.stringify(args).slice(0, 100) : "";
        step.innerHTML = '→ <span class="tool-name">' + escapeHtml(name) +
            '</span> <span class="tool-args">' + escapeHtml(argStr) + '</span>';
        log.appendChild(step);
    }

    function showThinking(bubble) {
        if (!bubble) return;
        thinker = {
            started: Date.now(),
            tool: null,
            el: document.createElement("div"),
            timerId: null,
        };
        thinker.el.className = "thinking-indicator";
        thinker.el.innerHTML = '<span class="dot"></span><span class="label">Thinking… <span class="secs">0s</span></span>';
        bubble.parentElement.insertBefore(thinker.el, bubble);
        thinker.timerId = setInterval(updateThinking, 500);
    }

    function updateThinking() {
        if (!thinker) return;
        const secs = Math.floor((Date.now() - thinker.started) / 1000);
        const label = thinker.tool
            ? 'Thinking… <span class="secs">' + secs + 's</span> · calling <code>' + escapeHtml(thinker.tool) + '</code>'
            : 'Thinking… <span class="secs">' + secs + 's</span>';
        const el = thinker.el.querySelector(".label");
        if (el) el.innerHTML = label;
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

    function hideChips() {
        const chips = $("#copilot-chips");
        if (chips) chips.style.display = "none";
    }

    function enhanceTables(container) {
        if (!container || !window.enhanceTables) return;
        window.enhanceTables(container);
    }

    async function initSession() {
        if (sessionReady) return;
        const page = ($("#copilot-page") || {}).value || "";
        const company = ($("#copilot-company") || {}).value || "";
        const params = new URLSearchParams({ page, company });
        try {
            const resp = await fetch("/app/copilot/session?" + params);
            const data = await resp.json();
            copilotSid = data.sid;
            if (data.messages && data.messages.length) {
                data.messages.forEach(m => addBubble(m.role, m.content, m.agent_slug));
                hideChips();
            }
            sessionReady = true;
        } catch (e) {
            console.error("copilot session init failed", e);
        }
    }

    function handleEvent(raw, cb) {
        let type = null, data = "";
        for (const line of raw.split("\n")) {
            if (line.startsWith("event: ")) type = line.slice(7).trim();
            else if (line.startsWith("data: ")) data += line.slice(6);
        }
        if (!type) return;
        try { cb(type, data ? JSON.parse(data) : {}); }
        catch (e) { console.error("copilot sse parse error", raw, e); }
    }

    async function copilotSend(evt) {
        if (evt) evt.preventDefault();
        if (copilotStreaming) return;
        const ta = $("#copilot-input");
        const msg = ta.value.trim();
        if (!msg) return;

        copilotStreaming = true;
        const sendBtn = $("#copilot-send-btn");
        if (sendBtn) sendBtn.disabled = true;

        hideChips();
        addBubble("user", msg);
        ta.value = "";

        if (!copilotSid) {
            const page = ($("#copilot-page") || {}).value || "";
            const company = ($("#copilot-company") || {}).value || "";
            const params = new URLSearchParams({ page, company });
            try {
                const resp = await fetch("/app/copilot/session?" + params);
                const data = await resp.json();
                copilotSid = data.sid;
                sessionReady = true;
            } catch (e) {
                console.error("copilot session create failed", e);
            }
        }

        const context = ($("#copilot-context") || {}).value || "";
        const body = new URLSearchParams({ msg, sid: copilotSid || "", context });

        let bubble = null;
        let accumulated = "";

        try {
            const resp = await fetch("/app/chat", { method: "POST", body });
            if (!resp.ok) {
                addBubble("assistant", "Error: " + resp.status);
                copilotStreaming = false;
                if (sendBtn) sendBtn.disabled = false;
                return;
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

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
                            const name = payload.agent || payload.slug || "";
                            bubble = addBubble("assistant", "", name);
                            bubble.classList.add("streaming");
                            showThinking(bubble);
                        } else if (type === "token") {
                            if (!bubble) { bubble = addBubble("assistant", ""); bubble.classList.add("streaming"); }
                            if (accumulated === "") hideThinking();
                            accumulated += payload.text;
                            bubble.innerHTML = renderMd(accumulated);
                            scrollBottom();
                        } else if (type === "tool_start") {
                            setThinkingTool(payload.name);
                            if (bubble) appendToolLog(bubble, payload.name, payload.args);
                        } else if (type === "tool_end") {
                            // tool finished
                        } else if (type === "session") {
                            if (payload.sid) copilotSid = payload.sid;
                        } else if (type === "done") {
                            hideThinking();
                            if (bubble) {
                                bubble.classList.remove("streaming");
                                enhanceTables(bubble);
                            }
                        } else if (type === "error") {
                            hideThinking();
                            if (!bubble) bubble = addBubble("assistant", "");
                            bubble.textContent = "Error: " + (payload.message || "unknown");
                        }
                    });
                }
            }
        } catch (e) {
            console.error("copilot stream error", e);
            hideThinking();
            addBubble("assistant", "Connection error");
        }

        copilotStreaming = false;
        if (sendBtn) sendBtn.disabled = false;
        accumulated = "";
    }

    window.copilotSend = copilotSend;
    window.copilotFillAndSend = (text) => {
        const ta = $("#copilot-input");
        if (ta) ta.value = text;
        copilotSend(null);
    };
    window.copilotHandleKey = (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); copilotSend(ev); }
    };
    window.toggleCopilotPane = () => {
        const r = $("#right-pane");
        const app = $(".app");
        if (!r || !app) return;
        if (r.classList.contains("open")) {
            r.classList.remove("open");
            app.classList.add("pane-closed");
            const btn = $("#copilot-btn");
            if (btn) { btn.classList.remove("active"); btn.textContent = "«"; }
        } else {
            r.classList.add("open");
            app.classList.remove("pane-closed");
            const btn = $("#copilot-btn");
            if (btn) { btn.classList.add("active"); btn.textContent = "»"; }
            if (!sessionReady) initSession();
        }
    };

    // Auto-init session on page load if copilot is open
    if ($("#right-pane") && $("#right-pane").classList.contains("open")) {
        initSession();
    }
})();
