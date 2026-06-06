/* Deal Street Training game — SSE chat client */

function streamGame(msg) {
    var messages = document.getElementById("messages");
    var formData = new FormData();
    formData.append("msg", msg);

    fetch("/app/training/chat", { method: "POST", body: formData })
        .then(function(r) { return r.body.getReader(); })
        .then(function(reader) {
            var decoder = new TextDecoder();
            var agentDiv = null;
            var bubble = null;
            var accumulated = "";

            function read() {
                reader.read().then(function(result) {
                    if (result.done) return;
                    var text = decoder.decode(result.value, { stream: true });
                    var lines = text.split("\n");
                    var eventName = "";
                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i];
                        if (line.indexOf("event: ") === 0) {
                            eventName = line.slice(7);
                        } else if (line.indexOf("data: ") === 0) {
                            try {
                                var data = JSON.parse(line.slice(6));
                                if (eventName === "token") {
                                    if (!agentDiv) {
                                        agentDiv = document.createElement("div");
                                        agentDiv.className = "msg msg-assistant";
                                        bubble = document.createElement("div");
                                        bubble.className = "msg-bubble";
                                        agentDiv.appendChild(bubble);
                                        messages.appendChild(agentDiv);
                                    }
                                    accumulated += data.text;
                                    if (window.marked) {
                                        bubble.innerHTML = marked.parse(accumulated);
                                    } else {
                                        bubble.textContent = accumulated;
                                    }
                                    messages.scrollTop = messages.scrollHeight;
                                } else if (eventName === "tool_start") {
                                    var thinking = document.createElement("div");
                                    thinking.className = "thinking-line";
                                    thinking.id = "game-thinking";
                                    thinking.innerHTML = '<span class="thinking-dot"></span> The Desk is thinking...';
                                    messages.appendChild(thinking);
                                    messages.scrollTop = messages.scrollHeight;
                                } else if (eventName === "tool_end") {
                                    var th = document.getElementById("game-thinking");
                                    if (th) th.remove();
                                } else if (eventName === "error") {
                                    var errDiv = document.createElement("div");
                                    errDiv.className = "msg msg-assistant";
                                    errDiv.innerHTML = '<div class="msg-bubble" style="color:#ef4444;">Error: ' +
                                        (data.message || "Something went wrong") + '</div>';
                                    messages.appendChild(errDiv);
                                    messages.scrollTop = messages.scrollHeight;
                                }
                            } catch (e) { /* skip malformed */ }
                        }
                    }
                    read();
                });
            }
            read();
        });
}

document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("training-form");
    var input = document.getElementById("training-input");
    var messages = document.getElementById("messages");

    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var msg = input.value.trim();
        if (!msg) return;
        input.value = "";

        var msgDiv = document.createElement("div");
        msgDiv.className = "msg msg-user";
        msgDiv.innerHTML = '<div class="msg-bubble">' + msg.replace(/</g, "&lt;") + "</div>";
        messages.appendChild(msgDiv);
        messages.scrollTop = messages.scrollHeight;

        streamGame(msg);
    });

    // Also handle Enter key on the input
    input.addEventListener("keydown", function(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event("submit"));
        }
    });

    // Auto-start: show character select
    streamGame("start");
});
