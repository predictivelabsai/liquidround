"""
Research Agent — deep research via EXA + TAVILY with thinking trace.
"""
import json
from typing import Dict, Any

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from utils.state import State
from utils.research_tools import research_tools


class ResearchAgent(BaseAgent):
    """Runs parallel EXA + TAVILY searches and synthesizes into a research brief."""

    def __init__(self):
        super().__init__("research")

    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        query = state["user_query"]
        company = state["deal"].get("company_name", "")
        industry = state["deal"].get("industry", "")

        # Build research query
        search_query = query
        if company:
            search_query = f"{company} {industry} M&A acquisition"
        elif "ipo" in query.lower():
            search_query = f"{query} IPO market readiness"

        # Run deep research (parallel EXA + TAVILY)
        research = await research_tools.deep_research(search_query)

        # Synthesize with LLM
        exa_snippets = "\n".join(
            f"- [{r['title']}]({r['url']}): {r['snippet']}"
            for r in research.get("exa", {}).get("results", [])[:5]
        )
        tavily_snippets = "\n".join(
            f"- [{r['title']}]({r['url']}): {r['content']}"
            for r in research.get("tavily", {}).get("results", [])[:5]
        )

        synthesis_prompt = f"""Based on the following research results, provide a concise M&A research brief.

User Query: {query}

EXA Semantic Search Results:
{exa_snippets or "No results"}

Tavily Web Search Results:
{tavily_snippets or "No results"}

Provide:
1. Key findings (3-5 bullet points)
2. Relevant companies or targets mentioned
3. Market context and trends
4. Risks or concerns identified
5. Recommended next steps

Keep it concise and actionable."""

        messages = self._create_messages(synthesis_prompt)
        summary = await self._call_llm(messages)

        research["summary"] = summary
        research["query"] = search_query

        return research
