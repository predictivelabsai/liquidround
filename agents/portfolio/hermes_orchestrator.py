"""Hermes Orchestrator — a dedicated LangGraph delegation specialist."""
from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from agents.registry import AGENTS_BY_SLUG
from tools.hermes import hermes_delegate
from utils.hermes_agent import run_hermes

SPEC = AGENTS_BY_SLUG["hermes_orchestrator"]
TOOLS = [hermes_delegate]


def _delegate(state: MessagesState) -> dict:
    messages = state.get("messages", [])
    content = ""
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = str(getattr(message, "content", ""))
            break
    return {"messages": [AIMessage(content=run_hermes(content))]}


@lru_cache(maxsize=1)
def build():
    graph = StateGraph(MessagesState)
    graph.add_node("hermes_delegate", _delegate)
    graph.add_edge(START, "hermes_delegate")
    graph.add_edge("hermes_delegate", END)
    return graph.compile()
