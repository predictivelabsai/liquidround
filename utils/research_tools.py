"""
EXA + TAVILY research tool wrappers.
"""
import asyncio, time, json
from typing import Optional
from utils.config import config


class ResearchTools:
    """Combined EXA semantic search + TAVILY web search."""

    def __init__(self):
        self._exa = None
        self._tavily = None

    def _get_exa(self):
        if self._exa is None:
            from exa_py import Exa
            self._exa = Exa(api_key=config.exa_api_key)
        return self._exa

    def _get_tavily(self):
        if self._tavily is None:
            from tavily import TavilyClient
            self._tavily = TavilyClient(api_key=config.tavily_api_key)
        return self._tavily

    async def exa_search(self, query: str, num_results: int = 8) -> dict:
        ts = time.time()
        try:
            exa = self._get_exa()
            resp = await asyncio.to_thread(
                exa.search_and_contents,
                query,
                num_results=num_results,
                text={"max_characters": 500},
                use_autoprompt=True,
            )
            results = [
                {
                    "title": r.title or "",
                    "url": r.url or "",
                    "snippet": (r.text or "")[:400],
                    "score": getattr(r, "score", 0),
                    "published_date": getattr(r, "published_date", ""),
                }
                for r in resp.results
            ]
            return {"source": "exa", "results": results, "elapsed": round(time.time() - ts, 2)}
        except Exception as e:
            return {"source": "exa", "results": [], "error": str(e), "elapsed": round(time.time() - ts, 2)}

    async def tavily_search(self, query: str, search_depth: str = "advanced") -> dict:
        ts = time.time()
        try:
            tavily = self._get_tavily()
            resp = await asyncio.to_thread(
                tavily.search,
                query=query,
                search_depth=search_depth,
                max_results=8,
            )
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": (r.get("content", ""))[:400],
                    "score": r.get("score", 0),
                }
                for r in resp.get("results", [])
            ]
            return {"source": "tavily", "results": results, "elapsed": round(time.time() - ts, 2)}
        except Exception as e:
            return {"source": "tavily", "results": [], "error": str(e), "elapsed": round(time.time() - ts, 2)}

    async def deep_research(self, query: str) -> dict:
        """Run EXA + TAVILY in parallel, return combined results with trace."""
        trace = []
        trace.append({"step": "start", "query": query, "ts": time.time()})

        exa_task = self.exa_search(query)
        tavily_task = self.tavily_search(query)
        exa_res, tavily_res = await asyncio.gather(exa_task, tavily_task)

        trace.append({"step": "exa_done", "count": len(exa_res["results"]), "elapsed": exa_res["elapsed"], "ts": time.time()})
        trace.append({"step": "tavily_done", "count": len(tavily_res["results"]), "elapsed": tavily_res["elapsed"], "ts": time.time()})

        return {
            "exa": exa_res,
            "tavily": tavily_res,
            "thinking_trace": trace,
        }


research_tools = ResearchTools()
