"""
Orchestrator agent for routing workflows in LiquidRound system.
"""
from typing import Dict, Any, Literal
from agents.base_agent import BaseAgent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state import State


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that determines workflow routing."""
    
    def __init__(self):
        super().__init__("orchestrator", "orchestrator.md")
    
    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        """Determine the appropriate workflow based on user input."""
        user_query = state["user_query"].lower()
        
        # Simple keyword-based routing logic
        # In a production system, this could use more sophisticated NLP
        
        if any(keyword in user_query for keyword in [
            "acquire", "acquisition", "buy", "target", "merger", "m&a", "purchase"
        ]):
            if any(keyword in user_query for keyword in [
                "sell", "selling", "divest", "exit", "buyer"
            ]):
                mode = "seller_ma"
                rationale = "Detected seller-side M&A keywords in query"
            else:
                mode = "buyer_ma"
                rationale = "Detected buyer-side M&A keywords in query"
        
        elif any(keyword in user_query for keyword in [
            "ipo", "public", "listing", "public offering", "go public"
        ]):
            mode = "ipo"
            rationale = "Detected IPO-related keywords in query"
        
        elif any(keyword in user_query for keyword in [
            "sell", "selling", "divest", "exit", "sale"
        ]):
            mode = "seller_ma"
            rationale = "Detected seller-side keywords in query"
        
        else:
            # Default to buyer-led M&A if unclear
            mode = "buyer_ma"
            rationale = "Defaulting to buyer-led M&A workflow"
        
        # Use LLM for more sophisticated analysis if needed
        context = self._extract_context_from_state(state)
        messages = self._create_messages(
            f"Analyze this query and confirm the workflow type: {state['user_query']}\n\n"
            f"Initial assessment: {mode} - {rationale}\n\n"
            f"Respond with either 'buyer_ma', 'seller_ma', or 'ipo' and provide a brief rationale.",
            context
        )
        
        try:
            llm_response = await self._call_llm(messages)
            
            # Parse LLM response
            if "seller_ma" in llm_response.lower():
                mode = "seller_ma"
            elif "ipo" in llm_response.lower():
                mode = "ipo"
            elif "buyer_ma" in llm_response.lower():
                mode = "buyer_ma"
            
            rationale = llm_response
            
        except Exception as e:
            self.logger.warning(f"LLM analysis failed, using keyword-based routing: {e}")
        
        # Update state mode
        state["mode"] = mode
        
        return {
            "workflow_type": mode,
            "rationale": rationale,
            "next_step": f"{mode}_workflow"
        }
