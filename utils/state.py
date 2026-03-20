"""
State management for LiquidRound multi-agent system.
"""
from typing import TypedDict, List, Dict, Any, Literal, Optional
from datetime import datetime
import json


class Message(TypedDict):
    """Message structure for conversation history."""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str]


class DealInfo(TypedDict):
    """Deal information structure."""
    deal_id: str
    deal_type: Literal["buyer_ma", "seller_ma", "ipo"]
    company_name: Optional[str]
    industry: Optional[str]
    deal_size: Optional[str]
    status: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class AgentResult(TypedDict):
    """Agent execution result structure."""
    agent_name: str
    status: Literal["success", "error", "in_progress"]
    result: Any
    execution_time: float
    timestamp: str
    error_message: Optional[str]


class State(TypedDict):
    """Main state object for the LangGraph workflow."""
    # Core workflow state
    mode: Literal["buyer_ma", "seller_ma", "ipo"]
    messages: List[Message]
    deal: DealInfo
    
    # Agent execution tracking
    current_agent: Optional[str]
    agent_results: Dict[str, AgentResult]
    workflow_status: Literal["initialized", "in_progress", "completed", "error"]
    
    # User input and context
    user_query: str
    context: Dict[str, Any]
    
    # Configuration
    config: Dict[str, Any]


def create_initial_state(
    mode: Literal["buyer_ma", "seller_ma", "ipo"],
    user_query: str,
    deal_id: Optional[str] = None
) -> State:
    """Create an initial state object."""
    timestamp = datetime.now().isoformat()
    
    if not deal_id:
        deal_id = f"{mode}_{timestamp.replace(':', '-').replace('.', '-')}"
    
    return State(
        mode=mode,
        messages=[],
        deal=DealInfo(
            deal_id=deal_id,
            deal_type=mode,
            company_name=None,
            industry=None,
            deal_size=None,
            status="initialized",
            created_at=timestamp,
            updated_at=timestamp,
            metadata={}
        ),
        current_agent=None,
        agent_results={},
        workflow_status="initialized",
        user_query=user_query,
        context={},
        config={
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    )


def add_message(state: State, role: str, content: str) -> State:
    """Add a message to the conversation history."""
    message = Message(
        role=role,
        content=content,
        timestamp=datetime.now().isoformat()
    )
    state["messages"].append(message)
    return state


def update_agent_result(
    state: State,
    agent_name: str,
    status: str,
    result: Any = None,
    execution_time: float = 0.0,
    error_message: str = None
) -> State:
    """Update the result of an agent execution."""
    agent_result = AgentResult(
        agent_name=agent_name,
        status=status,
        result=result,
        execution_time=execution_time,
        timestamp=datetime.now().isoformat(),
        error_message=error_message
    )
    state["agent_results"][agent_name] = agent_result
    state["current_agent"] = agent_name if status == "in_progress" else None
    return state


def update_deal_info(state: State, **kwargs) -> State:
    """Update deal information."""
    for key, value in kwargs.items():
        if key in state["deal"]:
            state["deal"][key] = value
    state["deal"]["updated_at"] = datetime.now().isoformat()
    return state


def serialize_state(state: State) -> str:
    """Serialize state to JSON string."""
    return json.dumps(state, indent=2, default=str)


def deserialize_state(state_json: str) -> State:
    """Deserialize state from JSON string."""
    return json.loads(state_json)
