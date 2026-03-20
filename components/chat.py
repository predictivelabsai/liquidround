"""
Chat interface components.
"""
from fasthtml.common import *


def ChatMessage(role: str, content: str, agent_name: str = ""):
    if role == "user":
        return Div(
            Div(
                P(content, cls="text-sm"),
                cls="bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2 max-w-lg",
            ),
            cls="flex justify-end mb-3",
        )
    else:
        label = agent_name.replace("_", " ").title() if agent_name else "LiquidRound"
        return Div(
            Div(
                P(label, cls="text-xs font-medium text-blue-700 mb-1") if agent_name else "",
                Div(NotStr(content), cls="text-sm prose prose-sm max-w-none") if "<" in content else P(content, cls="text-sm text-gray-800"),
                cls="bg-white rounded-2xl rounded-bl-md px-4 py-3 max-w-2xl border border-gray-200 shadow-sm",
            ),
            cls="flex justify-start mb-3",
        )


def ChatInput():
    return Form(
        Div(
            Input(
                name="msg",
                placeholder="Enter your M&A or IPO query...",
                autofocus=True,
                cls="flex-1 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            ),
            Button(
                "Send",
                type="submit",
                cls="bg-blue-600 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors",
            ),
            cls="flex gap-3",
        ),
        hx_post="/chat",
        hx_target="#chat-messages",
        hx_swap="beforeend",
        hx_on__after_request="this.reset(); document.getElementById('right-pane').classList.remove('translate-x-full');",
        cls="mt-4",
    )


def AgentProgress(agent_name: str, status: str, message: str = "", execution_time: float = 0):
    status_styles = {
        "running": ("animate-pulse bg-yellow-50 border-yellow-300", "text-yellow-700"),
        "completed": ("bg-green-50 border-green-300", "text-green-700"),
        "error": ("bg-red-50 border-red-300", "text-red-700"),
        "pending": ("bg-gray-50 border-gray-200", "text-gray-500"),
    }
    card_cls, text_cls = status_styles.get(status, status_styles["pending"])
    icons = {"running": "...", "completed": "Done", "error": "Err", "pending": "Wait"}

    return Div(
        Div(
            Span(icons.get(status, "?"), cls=f"text-xs font-bold {text_cls}"),
            Span(agent_name.replace("_", " ").title(), cls="text-sm font-medium text-gray-800"),
            Span(f"{execution_time:.1f}s", cls="text-xs text-gray-400") if execution_time > 0 else "",
            cls="flex items-center gap-2",
        ),
        P(message, cls=f"text-xs {text_cls} mt-1") if message else "",
        cls=f"rounded-lg px-3 py-2 border {card_cls} mb-2",
    )
