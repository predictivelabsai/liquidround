"""
Right-pane research panel components (EXA, TAVILY, thinking trace).
"""
from fasthtml.common import *


def ResearchEntry(source: str, title: str, url: str, snippet: str, score: float = 0):
    badge_cls = "bg-purple-100 text-purple-700" if source == "exa" else "bg-orange-100 text-orange-700"
    return Div(
        Div(
            Span(source.upper(), cls=f"text-xs font-bold px-2 py-0.5 rounded {badge_cls}"),
            Span(f"{score:.2f}", cls="text-xs text-gray-400") if score else "",
            cls="flex items-center gap-2 mb-1",
        ),
        A(title or url, href=url, target="_blank", cls="text-sm font-medium text-blue-700 hover:underline block"),
        P(snippet[:200], cls="text-xs text-gray-600 mt-1 line-clamp-3") if snippet else "",
        cls="border-b border-gray-100 pb-3 mb-3",
    )


def ThinkingTrace(trace: list):
    steps = []
    for entry in trace:
        step = entry.get("step", "")
        elapsed = entry.get("elapsed", 0)
        count = entry.get("count", "")
        detail = f"{count} results in {elapsed}s" if count else step
        steps.append(
            Div(
                Div(cls="w-2 h-2 rounded-full bg-blue-400 mt-1.5"),
                Div(
                    P(step.replace("_", " ").title(), cls="text-xs font-medium text-gray-700"),
                    P(detail, cls="text-xs text-gray-400"),
                ),
                cls="flex gap-2",
            )
        )
    return Div(
        H3("Thinking Trace", cls="text-sm font-semibold text-gray-700 mb-2"),
        Div(*steps, cls="flex flex-col gap-2 border-l-2 border-blue-200 pl-2"),
        cls="p-4 bg-gray-50 rounded-lg mb-4",
    )


def ResearchPanel(research_data: dict):
    """Full research panel content from deep_research() results."""
    exa = research_data.get("exa", {})
    tavily = research_data.get("tavily", {})
    trace = research_data.get("thinking_trace", [])

    entries = []

    # Thinking trace at top
    if trace:
        entries.append(ThinkingTrace(trace))

    # EXA results
    exa_results = exa.get("results", [])
    if exa_results:
        entries.append(H3(f"EXA Semantic Search ({len(exa_results)})", cls="text-sm font-semibold text-purple-700 mb-2 mt-4"))
        if exa.get("error"):
            entries.append(P(f"Error: {exa['error']}", cls="text-xs text-red-500"))
        for r in exa_results:
            entries.append(ResearchEntry("exa", r.get("title", ""), r.get("url", ""), r.get("snippet", ""), r.get("score", 0)))

    # TAVILY results
    tav_results = tavily.get("results", [])
    if tav_results:
        entries.append(H3(f"Tavily Web Search ({len(tav_results)})", cls="text-sm font-semibold text-orange-700 mb-2 mt-4"))
        if tavily.get("error"):
            entries.append(P(f"Error: {tavily['error']}", cls="text-xs text-red-500"))
        for r in tav_results:
            entries.append(ResearchEntry("tavily", r.get("title", ""), r.get("url", ""), r.get("content", ""), r.get("score", 0)))

    if not entries:
        entries.append(P("No research results yet.", cls="text-sm text-gray-400 italic p-4"))

    return Div(*entries, cls="p-4")
