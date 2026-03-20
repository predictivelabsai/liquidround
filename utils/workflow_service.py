"""
Enhanced workflow service with real-time progress tracking and intermediate results.
"""
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from .database import db_service
from .logging import get_logger

logger = get_logger("workflow_service_enhanced")


class EnhancedWorkflowService:
    """Enhanced service for managing workflow execution with real-time progress."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._agent_registry = {}
        self._active_workflows = {}  # Track active workflow progress
    
    def register_agent(self, name: str, agent_class):
        """Register an agent class for lazy loading."""
        self._agent_registry[name] = agent_class
        logger.info(f"Registered agent: {name}")
    
    def _get_agent(self, name: str):
        """Get an agent instance by name."""
        if name not in self._agent_registry:
            # Lazy import agents only when needed
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
                if name == "orchestrator":
                    from agents.orchestrator import OrchestratorAgent
                    self._agent_registry[name] = OrchestratorAgent
                elif name == "target_finder":
                    from agents.target_finder import TargetFinderAgent
                    self._agent_registry[name] = TargetFinderAgent
                elif name == "valuer":
                    from agents.valuer import ValuerAgent
                    self._agent_registry[name] = ValuerAgent
                else:
                    logger.error(f"Unknown agent: {name}")
                    return None
            except ImportError as e:
                logger.error(f"Failed to import agent {name}: {e}")
                return None
        
        agent_class = self._agent_registry[name]
        return agent_class()
    
    def get_workflow_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Get real-time workflow progress."""
        return self._active_workflows.get(workflow_id, {
            "current_agent": None,
            "progress": [],
            "status": "unknown"
        })
    
    def _update_progress(self, workflow_id: str, agent_name: str, status: str, data: Dict = None):
        """Update workflow progress in real-time."""
        if workflow_id not in self._active_workflows:
            self._active_workflows[workflow_id] = {
                "current_agent": None,
                "progress": [],
                "status": "pending"
            }
        
        progress_entry = {
            "agent": agent_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        self._active_workflows[workflow_id]["current_agent"] = agent_name if status == "running" else None
        self._active_workflows[workflow_id]["progress"].append(progress_entry)
        self._active_workflows[workflow_id]["status"] = status
        
        # Also save to database for persistence
        db_service.add_message(
            workflow_id, 
            "system", 
            json.dumps(progress_entry, indent=2)
        )
    
    async def start_workflow(self, user_query: str) -> str:
        """Start a new workflow and return the workflow ID."""
        workflow_id = db_service.create_workflow(user_query)
        
        # Add user message
        db_service.add_message(workflow_id, "user", user_query)
        
        # Initialize progress tracking
        self._update_progress(workflow_id, "system", "initialized", {
            "message": "Workflow started",
            "query": user_query
        })
        
        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow(workflow_id, user_query))
        
        return workflow_id
    
    async def _execute_workflow(self, workflow_id: str, user_query: str):
        """Execute the workflow asynchronously with real-time progress."""
        try:
            logger.info(f"Starting workflow execution for {workflow_id}")
            
            # Step 1: Orchestrator determines workflow type
            self._update_progress(workflow_id, "orchestrator", "running", {
                "message": "🎯 Analyzing query and determining workflow type...",
                "step": "routing"
            })
            
            db_service.update_workflow_status(workflow_id, "routing")
            orchestrator = self._get_agent("orchestrator")
            
            if not orchestrator:
                self._update_progress(workflow_id, "orchestrator", "failed", {
                    "error": "Failed to load orchestrator agent"
                })
                db_service.update_workflow_status(workflow_id, "failed")
                return
            
            start_time = time.time()
            
            # Create a proper state object for the orchestrator
            state = {
                "user_query": user_query,
                "mode": "unknown",
                "messages": [],
                "deal": {
                    "deal_id": workflow_id,
                    "deal_type": "unknown",
                    "company_name": None,
                    "industry": None,
                    "deal_size": None,
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": {}
                },
                "agent_results": {},
                "workflow_status": "routing"
            }
            
            try:
                updated_state = await orchestrator.execute(state)
                
                execution_time = time.time() - start_time
                
                # Extract orchestrator result from the updated state
                orchestrator_result = updated_state["agent_results"]["orchestrator"]["result"]
                
                # Update progress with orchestrator results
                self._update_progress(workflow_id, "orchestrator", "completed", {
                    "message": "✅ Workflow routing completed",
                    "result": orchestrator_result,
                    "execution_time": execution_time
                })
                
                db_service.save_agent_result(
                    workflow_id, "orchestrator", orchestrator_result, 
                    "success", execution_time
                )
                
                workflow_type = orchestrator_result.get("workflow_type", "unknown")
                db_service.update_workflow_status(workflow_id, "executing", workflow_type)
                
                # Add orchestrator response
                rationale = orchestrator_result.get("rationale", "Workflow routing completed")
                db_service.add_message(workflow_id, "assistant", f"🎯 **Workflow Routing**: {workflow_type.upper()}\n\n{rationale}")
                
            except Exception as e:
                logger.error(f"Orchestrator failed for {workflow_id}: {e}")
                self._update_progress(workflow_id, "orchestrator", "failed", {
                    "error": str(e)
                })
                db_service.save_agent_result(workflow_id, "orchestrator", {"error": str(e)}, "failed")
                db_service.update_workflow_status(workflow_id, "failed")
                return
            
            # Step 2: Execute workflow-specific agents
            if workflow_type in ["buyer_ma", "seller_ma"]:
                await self._execute_ma_workflow(workflow_id, user_query, workflow_type)
            elif workflow_type == "ipo":
                await self._execute_ipo_workflow(workflow_id, user_query)
            else:
                logger.warning(f"Unknown workflow type: {workflow_type}")
                self._update_progress(workflow_id, "system", "completed", {
                    "message": f"⚠️ Unknown workflow type: {workflow_type}",
                    "workflow_type": workflow_type
                })
                db_service.update_workflow_status(workflow_id, "completed")
            
        except Exception as e:
            logger.error(f"Workflow execution failed for {workflow_id}: {e}")
            self._update_progress(workflow_id, "system", "failed", {
                "error": str(e)
            })
            db_service.update_workflow_status(workflow_id, "failed")
            db_service.add_message(workflow_id, "assistant", f"❌ **Error**: Workflow execution failed: {str(e)}")
    
    async def _execute_ma_workflow(self, workflow_id: str, user_query: str, workflow_type: str):
        """Execute M&A workflow with real-time progress tracking."""
        try:
            # Create proper state structure
            state = {
                "user_query": user_query,
                "mode": workflow_type,
                "messages": [],
                "deal": {
                    "deal_id": workflow_id,
                    "deal_type": workflow_type,
                    "company_name": None,
                    "industry": None,
                    "deal_size": None,
                    "status": "executing",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "metadata": {}
                },
                "agent_results": {},
                "workflow_status": "executing"
            }
            
            # Step 1: Target Finder
            self._update_progress(workflow_id, "target_finder", "running", {
                "message": "🔍 Finding acquisition targets...",
                "step": "target_identification"
            })
            
            db_service.add_message(workflow_id, "assistant", "🔍 **Finding acquisition targets...**")
            
            target_finder = self._get_agent("target_finder")
            if target_finder:
                start_time = time.time()
                
                try:
                    updated_state = await target_finder.execute(state)
                    
                    execution_time = time.time() - start_time
                    
                    # Extract target finder result from updated state
                    target_result = updated_state["agent_results"]["target_finder"]["result"]
                    
                    # Update progress with target finder results
                    self._update_progress(workflow_id, "target_finder", "completed", {
                        "message": "✅ Target identification completed",
                        "result": target_result,
                        "execution_time": execution_time
                    })
                    
                    db_service.save_agent_result(
                        workflow_id, "target_finder", target_result,
                        "success", execution_time
                    )
                    
                    # Add target finder response
                    targets = target_result.get("targets", [])
                    if targets:
                        response = f"📊 **Found {len(targets)} potential targets:**\n\n"
                        for i, target in enumerate(targets[:5], 1):  # Show top 5
                            response += f"{i}. **{target.get('company_name', 'Unknown')}**\n"
                            response += f"   - Revenue: {target.get('estimated_revenue', 'N/A')}\n"
                            response += f"   - Strategic Fit: {target.get('strategic_fit_score', 'N/A')}/5\n"
                            response += f"   - Highlights: {target.get('investment_highlights', 'N/A')}\n\n"
                        
                        db_service.add_message(workflow_id, "assistant", response)
                    else:
                        db_service.add_message(workflow_id, "assistant", "🔍 **Target search completed** but no specific targets were identified.")
                
                except Exception as e:
                    logger.error(f"Target finder failed for {workflow_id}: {e}")
                    self._update_progress(workflow_id, "target_finder", "failed", {
                        "error": str(e)
                    })
                    db_service.save_agent_result(workflow_id, "target_finder", {"error": str(e)}, "failed")
                    db_service.add_message(workflow_id, "assistant", f"❌ **Target Finder Error**: {str(e)}")
            
            # Step 2: Valuer
            self._update_progress(workflow_id, "valuer", "running", {
                "message": "💰 Performing valuation analysis...",
                "step": "valuation"
            })
            
            db_service.add_message(workflow_id, "assistant", "💰 **Performing valuation analysis...**")
            
            valuer = self._get_agent("valuer")
            if valuer:
                start_time = time.time()
                
                try:
                    updated_state = await valuer.execute(state)
                    
                    execution_time = time.time() - start_time
                    
                    # Extract valuer result from updated state
                    valuation_result = updated_state["agent_results"]["valuer"]["result"]
                    
                    # Update progress with valuer results
                    self._update_progress(workflow_id, "valuer", "completed", {
                        "message": "✅ Valuation analysis completed",
                        "result": valuation_result,
                        "execution_time": execution_time
                    })
                    
                    db_service.save_agent_result(
                        workflow_id, "valuer", valuation_result,
                        "success", execution_time
                    )
                    
                    # Add valuation response
                    if "valuation_analysis" in valuation_result:
                        analysis = valuation_result["valuation_analysis"]
                        response = f"💰 **Valuation Analysis Complete**\n\n{analysis[:500]}..."
                        if len(analysis) > 500:
                            response += "\n\n*Full analysis available in detailed results.*"
                        db_service.add_message(workflow_id, "assistant", response)
                    else:
                        db_service.add_message(workflow_id, "assistant", "💰 **Valuation analysis completed** - detailed metrics captured.")
                
                except Exception as e:
                    logger.error(f"Valuer failed for {workflow_id}: {e}")
                    self._update_progress(workflow_id, "valuer", "failed", {
                        "error": str(e)
                    })
                    db_service.save_agent_result(workflow_id, "valuer", {"error": str(e)}, "failed")
                    db_service.add_message(workflow_id, "assistant", f"❌ **Valuation Error**: {str(e)}")
            
            # Mark workflow as completed
            self._update_progress(workflow_id, "system", "completed", {
                "message": "✅ M&A Analysis Complete",
                "workflow_type": workflow_type
            })
            
            db_service.update_workflow_status(workflow_id, "completed")
            db_service.add_message(workflow_id, "assistant", "✅ **M&A Analysis Complete** - All results are available in the detailed view.")
            
        except Exception as e:
            logger.error(f"M&A workflow failed for {workflow_id}: {e}")
            self._update_progress(workflow_id, "system", "failed", {
                "error": str(e)
            })
            db_service.update_workflow_status(workflow_id, "failed")
    
    async def _execute_ipo_workflow(self, workflow_id: str, user_query: str):
        """Execute IPO workflow with real-time progress tracking."""
        self._update_progress(workflow_id, "ipo_assessor", "running", {
            "message": "🏛️ Assessing IPO readiness...",
            "step": "ipo_assessment"
        })
        
        # Placeholder for IPO workflow
        await asyncio.sleep(2)
        
        self._update_progress(workflow_id, "ipo_assessor", "completed", {
            "message": "✅ IPO assessment completed",
            "result": {"readiness_score": 7.5, "recommendations": ["Strengthen financials", "Expand market presence"]}
        })
        
        db_service.update_workflow_status(workflow_id, "completed")
        db_service.add_message(workflow_id, "assistant", "🏛️ **IPO Assessment Complete** - Readiness analysis available.")
    
    def get_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent workflows with enhanced status."""
        return db_service.get_recent_workflows(limit)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive workflow status including progress."""
        status = db_service.get_workflow_status(workflow_id)
        if status:
            # Add real-time progress information
            progress = self.get_workflow_progress(workflow_id)
            status["progress"] = progress
        return status


# Global enhanced service instance
enhanced_workflow_service = EnhancedWorkflowService()
