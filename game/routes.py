"""Deal Street game routes — IB training RPG at /app/training.

Uses LangGraph ReAct agent with game-state mutation tools.
The agent reasons about the player's action, calls tools to update state
(win mandates, close deals, adjust resources, advance stages), then generates narrative.

All responses are SSE-streamed using the same event protocol as the main chat.
"""

from __future__ import annotations

import json
import logging

from fasthtml.common import (
    Html, Head, Body, Meta, Title, Link, Script, NotStr,
    Div, Span, Button, Form, Input,
)
from fasthtml.core import APIRouter
from langchain_core.messages import HumanMessage
from starlette.responses import StreamingResponse, JSONResponse

import chat_sse as sse
from game.engine import (
    CHARACTERS, LEVELS, GameState, new_game, draw_event, format_status,
    STAGES, calculate_score, load_deal_pipeline,
)
from game.prompts import (
    GAME_MASTER_SYSTEM, WELCOME, CHARACTER_SELECT_ROW,
    GAME_OVER,
)

log = logging.getLogger(__name__)
ar = APIRouter()

CHAR_MAP = {}
for k, v in CHARACTERS.items():
    CHAR_MAP[k] = k
    CHAR_MAP[v["name"].lower()] = k
    CHAR_MAP[v["title"].lower().lstrip("the ")] = k

CHAR_MAP.update({
    "1": "rainmaker", "2": "modeler", "3": "bull",
    "4": "strategist", "5": "grinder", "6": "insider",
    "alex": "rainmaker", "priya": "modeler", "marcus": "bull",
    "sophie": "strategist", "derek": "grinder", "elena": "insider",
    "alex voss": "rainmaker", "priya sharma": "modeler",
    "marcus reynolds": "bull", "sophie laurent": "strategist",
    "derek chen": "grinder", "elena petrova": "insider",
    "dr. elena petrova": "insider",
})


def _get_game_state(sess) -> GameState | None:
    raw = sess.get("deal_street_state")
    if raw:
        try:
            return GameState.from_dict(json.loads(raw) if isinstance(raw, str) else raw)
        except Exception:
            pass
    return None


def _save_game_state(sess, state: GameState):
    sess["deal_street_state"] = json.dumps(state.to_dict())


def _build_system_prompt(state: GameState) -> str:
    char = CHARACTERS.get(state.character, {})
    lvl = LEVELS.get(state.level, {})
    event = draw_event()
    state.events_history.append(event["name"])

    char_info = (
        f"**{char['name']}** — {char['title']} ({char['icon']})\n"
        f"Role: {char['role']}\n"
        f"Ability: {char['ability']}\n"
        f"Background: {char['description']}"
    )

    return GAME_MASTER_SYSTEM.replace("{{total_rounds}}", str(state.total_rounds)).replace(
        "{{status}}", format_status(state)
    ).replace(
        "{{event}}", f"**{event['name']}**: {event['effect']}"
    ).replace(
        "{{character_info}}", char_info
    ).replace(
        "{{level_title}}", lvl.get("title", "Analyst")
    ).replace(
        "{{level_complexity}}", lvl.get("complexity", "")
    )


def _welcome_text() -> str:
    text = WELCOME
    for key, char in CHARACTERS.items():
        text += CHARACTER_SELECT_ROW.format(
            icon=char["icon"],
            name=char["name"],
            role=char["role"],
            knowledge=char["start_knowledge"],
            network=char["start_network"],
            reputation=char["start_reputation"],
            ability_short=char["ability"][:55] + "...",
        )
    text += "\n*Type a character name or number (1-6) to begin.*\n"
    return text


def _game_over_text(state: GameState) -> str:
    char = CHARACTERS.get(state.character, {})
    score = calculate_score(state)
    state.score = score
    lvl = LEVELS.get(state.level, {})
    fee_target = lvl.get("fee_target", 500_000)

    if state.fees_earned >= fee_target * 1.5:
        result_tone = "WHAT A PERFORMANCE! You absolutely DOMINATED the league table!"
    elif state.fees_earned >= fee_target:
        result_tone = "Solid run! You hit your fee target. Now push for the top of the table."
    elif state.fees_earned >= fee_target * 0.5:
        result_tone = "Not bad, but the MD is NOT impressed. You need to close harder next time."
    else:
        result_tone = "Tough quarter. But every great banker has a deal drought. Learn and come back STRONGER."

    current_lvl = LEVELS[state.level]
    level_keys = list(LEVELS.keys())
    current_idx = level_keys.index(state.level)

    if current_idx < len(level_keys) - 1 and score >= LEVELS[level_keys[current_idx + 1]]["unlock"]:
        next_key = level_keys[current_idx + 1]
        next_lvl = LEVELS[next_key]
        next_level_msg = (
            f"\n**PROMOTED: {next_lvl['title']}** — {next_lvl['description']}\n\n"
            f"1. **Level up** to {next_lvl['title']} — let's GO!\n"
            f"2. **Replay** {current_lvl['title']} with a different character\n"
            f"3. **New game** — start fresh\n"
        )
    else:
        next_level_msg = (
            f"\nScore {LEVELS[level_keys[min(current_idx + 1, len(level_keys)-1)]]['unlock']:,} to unlock the next level.\n\n"
            f"1. **Replay** {current_lvl['title']} — come back stronger!\n"
            f"2. **New character** — try a different role\n"
            f"3. **New game** — start fresh\n"
        )

    return GAME_OVER.format(
        result_tone=result_tone,
        player_name=state.player_name,
        character_name=state.character_name,
        character_title=char.get("title", ""),
        fees_earned=state.fees_earned,
        deals_closed=state.deals_closed,
        deals_advised=state.deals_advised,
        mandates_won=state.mandates_won,
        knowledge=state.knowledge,
        network=state.network,
        reputation=state.reputation,
        score=score,
        next_level_msg=next_level_msg,
    )


async def _stream_agent_turn(state: GameState, user_content: str):
    """Run the LangGraph game agent and yield SSE events."""
    from game.agent import build_game_agent

    system = _build_system_prompt(state)
    graph = build_game_agent(state, system)
    messages = [HumanMessage(content=user_content)]

    async for event in graph.astream_events({"messages": messages}, version="v2"):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                if not getattr(chunk, "tool_call_chunks", None):
                    yield sse.event(sse.TOKEN, {"text": chunk.content})
        elif kind == "on_tool_start":
            name = event.get("name", "unknown")
            args = event["data"].get("input", {})
            yield sse.event(sse.TOOL_START, {"name": name, "args": args})
        elif kind == "on_tool_end":
            name = event.get("name", "unknown")
            raw = event["data"].get("output", "")
            output = getattr(raw, "content", None) or (raw if isinstance(raw, str) else str(raw))
            yield sse.event(sse.TOOL_END, {"name": name, "output": output[:2000]})


@ar("/app/training")
def training_page(sess):
    from components.chat_shell import left_pane

    user_email = sess.get("email") if sess else None
    current_role = sess.get("role", "buyer") if sess else "buyer"

    body = Body(
        Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
        left_pane(user_email=user_email, current_path="/app/training",
                  current_role=current_role),
        Div(
            Div(
                Div(
                    Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                    Span("Deal Street", cls="chat-header-title"),
                    cls="chat-header-left",
                ),
                Div(
                    Button("Reset Game", cls="news-toggle-btn",
                           style="font-size:.7rem; padding:.25rem .6rem;",
                           onclick="fetch('/app/training/reset',{method:'POST'}).then(()=>location.reload())"),
                    cls="chat-header-actions",
                ),
                cls="chat-header",
            ),
            Div(
                Div(id="messages", cls="messages",
                    style="flex:1; overflow-y:auto; padding:1rem;"),
                Div(
                    Form(
                        Input(type="text", id="training-input",
                              placeholder="Type your choice or action...",
                              cls="chat-textarea", style="flex:1; min-height:auto; resize:none;",
                              autocomplete="off"),
                        Button("Send", type="submit", cls="chat-send"),
                        id="training-form",
                        cls="chat-form",
                    ),
                    cls="chat-input-wrap",
                ),
                cls="chat-body",
                style="display:flex; flex-direction:column; height:calc(100vh - 48px);",
            ),
            cls="center-pane pipeline-center",
            style="overflow:hidden;",
        ),
        Script(src="/chat.js"),
        Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
        Script(src="/training.js"),
        cls="app pipeline-app",
    )

    head = Head(
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Title("Deal Street · LiquidRound"),
        Link(rel="icon", type="image/svg+xml", href="/favicon.svg"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(rel="stylesheet",
             href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"),
        Script(src="https://cdn.tailwindcss.com"),
        Link(rel="stylesheet", href="/app.css"),
    )
    return Html(head, body)


@ar("/app/training/chat", methods=["POST"])
async def training_chat(request):
    sess = request.session
    form = await request.form()
    user_msg = (form.get("msg") or "").strip()

    if not user_msg:
        return JSONResponse({"error": "empty message"}, status_code=400)

    state = _get_game_state(sess)

    async def event_stream():
        nonlocal state

        yield sse.event(sse.SESSION, {"sid": "training"})
        yield sse.event(sse.AGENT_ROUTE, {
            "slug": "deal_street_game",
            "agent": "The Desk",
            "icon": "\U0001f3e6",
        })

        if state is None:
            choice = user_msg.lower().strip().rstrip(".")
            char_key = CHAR_MAP.get(choice)

            if choice in ("level up", "next level"):
                yield sse.event(sse.TOKEN, {"text": _welcome_text()})
                yield sse.event(sse.DONE, {"slug": "deal_street_game"})
                return

            if not char_key:
                yield sse.event(sse.TOKEN, {"text": _welcome_text()})
                yield sse.event(sse.DONE, {"slug": "deal_street_game"})
                return

            level = sess.get("deal_street_level", "analyst")
            state = new_game(char_key, level=level, player_name=sess.get("email", "Player"))
            try:
                state.deal_pipeline = load_deal_pipeline(limit=40)
            except Exception:
                state.deal_pipeline = []
            _save_game_state(sess, state)

            char = CHARACTERS[char_key]
            lvl = LEVELS[level]
            intro = (
                f"## {char['icon']} You are **{char['name']}** — {char['title']}\n"
                f"*{char['description']}*\n\n"
                f"**{char['start_knowledge']}** knowledge | "
                f"**{char['start_network']}** network | "
                f"**{char['start_reputation']}** reputation\n\n"
                f"Special: *{char['ability']}*\n\n"
                f"**Level: {lvl['title']}** — {lvl['description']}\n"
                f"Fee target: ${lvl['fee_target']:,}\n\n"
                f"---\n\n"
            )
            yield sse.event(sse.TOKEN, {"text": intro})

            try:
                async for evt in _stream_agent_turn(
                    state,
                    f"The game begins! Present Round 1, Stage 1: Pitch & Origination.\n"
                    f"Set the scene — the player just joined an investment bank. "
                    f"Call browse_pipeline to see REAL companies that could be advisory clients. "
                    f"Present 3-4 of them as potential mandates with their actual "
                    f"financials (revenue, EBITDA, EV, multiple).\n"
                    f"Frame them as: exploring a sale, looking to raise capital, or considering an IPO.\n"
                    f"Give your coaching intro — fire them up! "
                    f"Then end with 3 choices.",
                ):
                    yield evt
            except Exception as e:
                log.exception("Game agent failed on intro")
                yield sse.event(sse.ERROR, {"message": str(e)})

            _save_game_state(sess, state)
            yield sse.event(sse.DONE, {"slug": "deal_street_game"})
            return

        lower = user_msg.lower().strip()
        if lower in ("new game", "restart", "reset"):
            sess.pop("deal_street_state", None)
            yield sse.event(sse.TOKEN, {"text": "Game reset! Let's go again.\n\n" + _welcome_text()})
            yield sse.event(sse.DONE, {"slug": "deal_street_game"})
            return

        if lower in ("level up", "next level"):
            level_keys = list(LEVELS.keys())
            current_idx = level_keys.index(state.level)
            if current_idx < len(level_keys) - 1:
                next_key = level_keys[current_idx + 1]
                if state.score >= LEVELS[next_key]["unlock"]:
                    sess["deal_street_level"] = next_key
                    sess.pop("deal_street_state", None)
                    next_lvl = LEVELS[next_key]
                    yield sse.event(sse.TOKEN, {
                        "text": (
                            f"## PROMOTED!\n\n"
                            f"Welcome to **{next_lvl['title']}** — {next_lvl['description']}\n\n"
                            f"*{next_lvl['complexity']}*\n\n"
                            f"Pick your banker for this level:\n\n" + _welcome_text()
                        ),
                    })
                    yield sse.event(sse.DONE, {"slug": "deal_street_game"})
                    return
            yield sse.event(sse.TOKEN, {"text": "You haven't unlocked the next level yet. Keep closing!\n"})
            yield sse.event(sse.DONE, {"slug": "deal_street_game"})
            return

        if state.game_over:
            if lower in ("replay", "new character", "new game"):
                sess.pop("deal_street_state", None)
                yield sse.event(sse.TOKEN, {"text": _welcome_text()})
            else:
                yield sse.event(sse.TOKEN, {"text": _game_over_text(state)})
            yield sse.event(sse.DONE, {"slug": "deal_street_game"})
            return

        try:
            async for evt in _stream_agent_turn(
                state,
                f"Player action: {user_msg}\n\n"
                f"Process this for {state.current_stage()} "
                f"(Round {state.round}/{state.total_rounds}).\n"
                f"React to their choice — give coaching feedback "
                f"(praise great moves, roast bad ones).\n"
                f"Show the outcome with updated resource numbers.\n"
                f"Then present 3 new choices for the next action.",
            ):
                yield evt
        except Exception as e:
            log.exception("Game agent failed")
            yield sse.event(sse.ERROR, {"message": str(e)})

        _save_game_state(sess, state)

        if state.game_over:
            yield sse.event(sse.TOKEN, {"text": "\n\n---\n\n" + _game_over_text(state)})

        yield sse.event(sse.DONE, {"slug": "deal_street_game"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@ar("/app/training/reset", methods=["POST"])
async def training_reset(request):
    request.session.pop("deal_street_state", None)
    request.session.pop("deal_street_level", None)
    return JSONResponse({"ok": True})
