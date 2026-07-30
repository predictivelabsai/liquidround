"""LangChain tool adapter for bounded Hermes delegation."""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from utils.hermes_agent import run_hermes


class HermesArgs(BaseModel):
    task: str = Field(description="A complete, self-contained analysis task for Hermes.")


hermes_delegate = StructuredTool.from_function(
    func=run_hermes,
    name="hermes_delegate",
    description=(
        "Delegate a bounded, self-contained reasoning task to the configured Hermes "
        "Agent. Hermes may be disabled or unavailable; report that state plainly."
    ),
    args_schema=HermesArgs,
)
