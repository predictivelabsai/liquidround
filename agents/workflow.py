"""
LangGraph workflow implementation for LiquidRound multi-agent system.
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
# Checkpointing disabled (was SqliteSaver, now using PostgreSQL)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..utils.state import State, create_initial_state, add_message
from ..utils.logging import get_logger
from .orchestrator import OrchestratorAgent
from .target_finder import TargetFinderAgent
from .valuer import ValuerAgent

logger = get_logger("workflow")


class LiquidRoundWorkflow:
    """Main workflow orchestrator for LiquidRound system."""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.target_finder = TargetFinderAgent()
        self.valuer = ValuerAgent()
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        # Create the main workflow graph
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("orchestrator", self._orchestrator_node)
        workflow.add_node("buyer_ma_workflow", self._buyer_ma_workflow)
        workflow.add_node("seller_ma_workflow", self._seller_ma_workflow)
        workflow.add_node("ipo_workflow", self._ipo_workflow)
        
        # Set entry point
        workflow.set_entry_point("orchestrator")
        
        # Add conditional routing from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            self._route_workflow,
            {
                "buyer_ma": "buyer_ma_workflow",
                "seller_ma": "seller_ma_workflow", 
                "ipo": "ipo_workflow"
            }
        )
        
        # All workflows end after completion
        workflow.add_edge("buyer_ma_workflow", END)
        workflow.add_edge("seller_ma_workflow", END)
        workflow.add_edge("ipo_workflow", END)
        
        # Compile the workflow without checkpointing for now
        # TODO: Fix checkpointing implementation later
        return workflow.compile()
    
    async def _orchestrator_node(self, state: State) -> State:
        """Execute the orchestrator agent."""
        logger.log_workflow_step("main", "orchestrator_start", {"mode": state.get("mode")})
        
        result_state = await self.orchestrator.execute(state)
        
        # Update state with orchestrator result
        if "orchestrator" in result_state["agent_results"]:
            orchestrator_result = result_state["agent_results"]["orchestrator"]["result"]
            if orchestrator_result and "workflow_type" in orchestrator_result:
                result_state["mode"] = orchestrator_result["workflow_type"]
        
        logger.log_workflow_step("main", "orchestrator_complete", {"mode": result_state["mode"]})
        return result_state
    
    async def _buyer_ma_workflow(self, state: State) -> State:
        """Execute the buyer-led M&A workflow."""
        logger.log_workflow_step("buyer_ma", "workflow_start")
        
        # Step 1: Find targets
        state = await self.target_finder.execute(state)
        
        # Step 2: Value targets
        state = await self.valuer.execute(state)
        
        # Add completion message
        state = add_message(
            state, 
            "assistant", 
            "Buyer-led M&A analysis completed. Target identification and valuation analysis are ready for review."
        )
        
        state["workflow_status"] = "completed"
        logger.log_workflow_step("buyer_ma", "workflow_complete")
        
        return state
    
    async def _seller_ma_workflow(self, state: State) -> State:
        """Execute the seller-led M&A workflow."""
        logger.log_workflow_step("seller_ma", "workflow_start")
        
        # For now, simplified seller workflow
        # In full implementation, would include seller_prep, market_outreach, etc.
        
        state = add_message(
            state,
            "assistant", 
            "Seller-led M&A workflow initiated. This would include seller preparation, market outreach, and buyer identification."
        )
        
        state["workflow_status"] = "completed"
        logger.log_workflow_step("seller_ma", "workflow_complete")
        
        return state
    
    async def _ipo_workflow(self, state: State) -> State:
        """Execute the IPO workflow."""
        logger.log_workflow_step("ipo", "workflow_start")
        
        # For now, simplified IPO workflow
        # In full implementation, would include readiness assessment, underwriter selection, etc.
        
        state = add_message(
            state,
            "assistant",
            "IPO workflow initiated. This would include readiness assessment, underwriter selection, and S-1 preparation."
        )
        
        state["workflow_status"] = "completed"
        logger.log_workflow_step("ipo", "workflow_complete")
        
        return state
    
    def _route_workflow(self, state: State) -> str:
        """Route to the appropriate workflow based on mode."""
        mode = state.get("mode", "buyer_ma")
        
        if mode == "seller_ma":
            return "seller_ma"
        elif mode == "ipo":
            return "ipo"
        else:
            return "buyer_ma"  # Default
    
    async def run(self, user_query: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the workflow with a user query."""
        if config is None:
            config = {"configurable": {"thread_id": "default"}}
        
        # Create initial state
        initial_state = create_initial_state("buyer_ma", user_query)  # Will be updated by orchestrator
        
        logger.log_user_interaction(
            user_id="default",
            action="workflow_start",
            input_data=user_query,
            session_id=config.get("configurable", {}).get("thread_id")
        )
        
        try:
            # Execute the workflow
            final_state = None
            async for event in self.workflow.astream(initial_state, config):
                final_state = event
                logger.debug(f"Workflow event: {list(event.keys())}")
            
            logger.log_user_interaction(
                user_id="default",
                action="workflow_complete",
                session_id=config.get("configurable", {}).get("thread_id"),
                metadata={"status": final_state.get("workflow_status") if final_state else "unknown"}
            )
            
            return final_state or initial_state
            
        except Exception as e:
            logger.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                context={"user_query": user_query, "config": config}
            )
            
            # Return error state
            error_state = initial_state.copy()
            error_state["workflow_status"] = "error"
            error_state = add_message(error_state, "assistant", f"An error occurred: {str(e)}")
            
            return error_state


# Global workflow instance
workflow_instance = LiquidRoundWorkflow()
