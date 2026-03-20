"""
Base agent class for LiquidRound multi-agent system.
Uses LangChain with swappable LLM providers (XAI/OpenAI/Anthropic).
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.state import State, update_agent_result
from utils.logging import get_logger
from utils.llm_factory import create_llm


class BaseAgent(ABC):
    """Base class for all LiquidRound agents."""

    def __init__(self, name: str, prompt_file: Optional[str] = None):
        self.name = name
        self.logger = get_logger(f"agent_{name}")
        self.system_prompt = self._load_prompt(prompt_file) if prompt_file else ""
        self.llm = create_llm()

    def _load_prompt(self, prompt_file: str) -> str:
        current_dir = Path(__file__).parent
        prompt_path = current_dir.parent / "prompts" / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text().strip()
        self.logger.warning(f"Prompt file not found: {prompt_path}")
        return ""

    async def execute(self, state: State) -> State:
        start_time = time.time()
        try:
            self.logger.log_agent_execution(
                agent_name=self.name, action="start",
                input_data={"user_query": state["user_query"]},
                metadata={"deal_id": state["deal"]["deal_id"]},
            )
            state = update_agent_result(state, self.name, "in_progress")
            result = await self._execute_logic(state)
            execution_time = time.time() - start_time
            state = update_agent_result(state, self.name, "success", result, execution_time)
            self.logger.log_agent_execution(
                agent_name=self.name, action="complete",
                output_data=result, execution_time=execution_time,
                metadata={"deal_id": state["deal"]["deal_id"]},
            )
            return state
        except Exception as e:
            execution_time = time.time() - start_time
            state = update_agent_result(state, self.name, "error", None, execution_time, str(e))
            self.logger.log_error(
                error_type=type(e).__name__, error_message=str(e),
                context={"agent_name": self.name, "deal_id": state["deal"]["deal_id"], "execution_time": execution_time},
            )
            return state

    @abstractmethod
    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        pass

    def _create_messages(self, user_input: str, context: Dict[str, Any] = None) -> List:
        messages = []
        if self.system_prompt:
            formatted = self.system_prompt
            if context:
                try:
                    formatted = self.system_prompt.format(**context)
                except KeyError:
                    pass
            messages.append(SystemMessage(content=formatted))
        messages.append(HumanMessage(content=user_input))
        return messages

    async def _call_llm(self, messages: List, **kwargs) -> str:
        response = await self.llm.ainvoke(messages, **kwargs)
        return response.content

    def _extract_context_from_state(self, state: State) -> Dict[str, Any]:
        return {
            "user_query": state["user_query"],
            "mode": state.get("mode", "unknown"),
            "deal_type": state["deal"]["deal_type"],
            "company_name": state["deal"].get("company_name", ""),
            "industry": state["deal"].get("industry", ""),
            "deal_size": state["deal"].get("deal_size", ""),
            "previous_results": {
                name: result["result"]
                for name, result in state["agent_results"].items()
                if result["status"] == "success"
            },
        }
