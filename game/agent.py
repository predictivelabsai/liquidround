"""LangGraph ReAct agent for the Deal Street game master.

Builds a fresh agent per turn, bound to the current GameState via tool closures.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from game.engine import GameState
from game.tools import build_game_tools
from utils.llm_factory import create_llm


def build_game_agent(state: GameState, system_prompt: str):
    """Build a LangGraph ReAct agent with game tools bound to `state`."""
    tools = build_game_tools(state)
    llm = create_llm(temperature=0.7)
    return create_react_agent(llm, tools, prompt=system_prompt)
