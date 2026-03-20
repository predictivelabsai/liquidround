"""
Tests for state management utilities.
"""
import pytest
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.state import (
    create_initial_state,
    add_message,
    update_agent_result,
    update_deal_info,
    serialize_state,
    deserialize_state
)


def test_create_initial_state():
    """Test creating an initial state."""
    state = create_initial_state("buyer_ma", "Find tech companies")
    
    assert state["mode"] == "buyer_ma"
    assert state["user_query"] == "Find tech companies"
    assert state["workflow_status"] == "initialized"
    assert "deal_id" in state["deal"]
    assert state["deal"]["deal_type"] == "buyer_ma"


def test_add_message():
    """Test adding a message to state."""
    state = create_initial_state("buyer_ma", "Test query")
    state = add_message(state, "user", "Hello")
    
    assert len(state["messages"]) == 1
    assert state["messages"][0]["role"] == "user"
    assert state["messages"][0]["content"] == "Hello"


def test_update_agent_result():
    """Test updating agent results in state."""
    state = create_initial_state("buyer_ma", "Test query")
    state = update_agent_result(
        state, "test_agent", "success", {"data": "value"}, 1.23
    )
    
    assert "test_agent" in state["agent_results"]
    result = state["agent_results"]["test_agent"]
    assert result["status"] == "success"
    assert result["result"] == {"data": "value"}
    assert result["execution_time"] == 1.23


def test_update_deal_info():
    """Test updating deal information in state."""
    state = create_initial_state("buyer_ma", "Test query")
    state = update_deal_info(state, company_name="TestCo", deal_size="100M")
    
    assert state["deal"]["company_name"] == "TestCo"
    assert state["deal"]["deal_size"] == "100M"


def test_serialize_deserialize_state():
    """Test serialization and deserialization of state."""
    state = create_initial_state("buyer_ma", "Test query")
    state = add_message(state, "user", "Test message")
    
    serialized_state = serialize_state(state)
    deserialized_state = deserialize_state(serialized_state)
    
    assert isinstance(serialized_state, str)
    assert deserialized_state == state
