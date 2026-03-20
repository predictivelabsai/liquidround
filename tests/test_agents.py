"""
Tests for LiquidRound agents.
"""
import pytest
import json
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents'))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.state import create_initial_state
from orchestrator import OrchestratorAgent
from target_finder import TargetFinderAgent
from valuer import ValuerAgent


@pytest.fixture
def buyer_ma_state():
    """Fixture for buyer-led M&A state."""
    query = "Find me add-on acquisition targets in EU med-tech with EV 50-150 m EUR and >15 % EBITDA margin."
    return create_initial_state("buyer_ma", query)


@pytest.fixture
def seller_ma_state():
    """Fixture for seller-led M&A state."""
    query = "I’m a founder preparing to raise series C; build a buyer list of US PE growth funds."
    return create_initial_state("seller_ma", query)


@pytest.fixture
def ipo_state():
    """Fixture for IPO state."""
    query = "We are a SaaS company planning to go public in 2025. Help us with the IPO process."
    return create_initial_state("ipo", query)


@pytest.mark.asyncio
async def test_orchestrator_agent_buyer_ma(buyer_ma_state):
    """Test orchestrator agent for buyer-led M&A."""
    agent = OrchestratorAgent()
    result_state = await agent.execute(buyer_ma_state)
    
    assert result_state["mode"] == "buyer_ma"
    assert "orchestrator" in result_state["agent_results"]
    orchestrator_result = result_state["agent_results"]["orchestrator"]
    assert orchestrator_result["status"] == "success"
    assert orchestrator_result["result"]["workflow_type"] == "buyer_ma"


@pytest.mark.asyncio
async def test_orchestrator_agent_seller_ma(seller_ma_state):
    """Test orchestrator agent for seller-led M&A."""
    agent = OrchestratorAgent()
    result_state = await agent.execute(seller_ma_state)
    
    assert result_state["mode"] == "seller_ma"
    assert "orchestrator" in result_state["agent_results"]
    orchestrator_result = result_state["agent_results"]["orchestrator"]
    assert orchestrator_result["status"] == "success"
    assert orchestrator_result["result"]["workflow_type"] == "seller_ma"


@pytest.mark.asyncio
async def test_orchestrator_agent_ipo(ipo_state):
    """Test orchestrator agent for IPO."""
    agent = OrchestratorAgent()
    result_state = await agent.execute(ipo_state)
    
    assert result_state["mode"] == "ipo"
    assert "orchestrator" in result_state["agent_results"]
    orchestrator_result = result_state["agent_results"]["orchestrator"]
    assert orchestrator_result["status"] == "success"
    assert orchestrator_result["result"]["workflow_type"] == "ipo"


@pytest.mark.asyncio
async def test_target_finder_agent(buyer_ma_state):
    """Test target finder agent."""
    agent = TargetFinderAgent()
    result_state = await agent.execute(buyer_ma_state)
    
    assert "target_finder" in result_state["agent_results"]
    target_finder_result = result_state["agent_results"]["target_finder"]
    assert target_finder_result["status"] == "success"
    
    result = target_finder_result["result"]
    assert "targets" in result
    assert "target_count" in result
    assert result["target_count"] > 0
    assert len(result["targets"]) == result["target_count"]


@pytest.mark.asyncio
async def test_valuer_agent(buyer_ma_state):
    """Test valuer agent."""
    # First, run target finder to get a target
    target_finder = TargetFinderAgent()
    state_with_target = await target_finder.execute(buyer_ma_state)
    
    # Now, run valuer
    agent = ValuerAgent()
    result_state = await agent.execute(state_with_target)
    
    assert "valuer" in result_state["agent_results"]
    valuer_result = result_state["agent_results"]["valuer"]
    assert valuer_result["status"] == "success"
    
    result = valuer_result["result"]
    assert "valuation_analysis" in result
    assert "key_metrics" in result
    assert "valuation_range" in result
    assert result["valuation_range"]["mid"] > 0
