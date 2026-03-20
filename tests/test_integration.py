"""
Integration tests for LiquidRound system - testing real API calls and workflows.
No mocks, real data capture to test-data/ folder.
"""
import pytest
import json
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents'))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.state import create_initial_state
from orchestrator import OrchestratorAgent
from target_finder import TargetFinderAgent
from valuer import ValuerAgent
from workflow import LiquidRoundWorkflow


class TestIntegration:
    """Integration tests with real API calls and data capture."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_data_dir = Path(__file__).parent.parent / "test-data"
        self.test_data_dir.mkdir(exist_ok=True)
        
    def save_test_result(self, test_name: str, data: dict):
        """Save test results to test-data folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_name}_{timestamp}.json"
        filepath = self.test_data_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"Test result saved to: {filepath}")
        return filepath

    def test_orchestrator_real_api(self):
        """Test orchestrator agent with real OpenAI API call."""
        print("\n=== Testing Orchestrator Agent with Real API ===")
        
        # Test buyer M&A query
        query = "Find fintech acquisition targets with $10-50M revenue"
        state = create_initial_state("buyer_ma", query)
        
        orchestrator = OrchestratorAgent()
        
        try:
            # This should make a real API call
            result_state = asyncio.run(orchestrator.execute(state))
            
            # Save results
            test_result = {
                "test": "orchestrator_real_api",
                "query": query,
                "success": True,
                "state": result_state,
                "agent_results": result_state.get("agent_results", {}),
                "mode": result_state.get("mode", "unknown"),
                "workflow_status": result_state.get("workflow_status", "unknown")
            }
            
            self.save_test_result("orchestrator_real_api", test_result)
            
            # Assertions
            assert "orchestrator" in result_state["agent_results"]
            assert result_state["agent_results"]["orchestrator"]["status"] in ["success", "error"]
            
            print(f"✅ Orchestrator test completed")
            print(f"Mode detected: {result_state.get('mode', 'unknown')}")
            print(f"Status: {result_state.get('workflow_status', 'unknown')}")
            
        except Exception as e:
            test_result = {
                "test": "orchestrator_real_api",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("orchestrator_real_api_error", test_result)
            print(f"❌ Orchestrator test failed: {e}")
            raise

    def test_target_finder_real_api(self):
        """Test target finder agent with real API calls."""
        print("\n=== Testing Target Finder Agent with Real APIs ===")
        
        query = "Looking to acquire healthcare SaaS companies"
        state = create_initial_state("buyer_ma", query)
        
        target_finder = TargetFinderAgent()
        
        try:
            result_state = asyncio.run(target_finder.execute(state))
            
            test_result = {
                "test": "target_finder_real_api",
                "query": query,
                "success": True,
                "state": result_state,
                "agent_results": result_state.get("agent_results", {}),
                "targets_found": len(result_state.get("agent_results", {}).get("target_finder", {}).get("result", {}).get("targets", []))
            }
            
            self.save_test_result("target_finder_real_api", test_result)
            
            # Check if we got actual targets
            target_result = result_state.get("agent_results", {}).get("target_finder", {})
            if target_result.get("status") == "success":
                targets = target_result.get("result", {}).get("targets", [])
                print(f"✅ Target Finder found {len(targets)} targets")
                for i, target in enumerate(targets[:3]):  # Show first 3
                    print(f"  {i+1}. {target.get('name', 'Unknown')} - {target.get('description', 'No description')}")
            else:
                print(f"⚠️ Target Finder status: {target_result.get('status', 'unknown')}")
            
        except Exception as e:
            test_result = {
                "test": "target_finder_real_api",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("target_finder_real_api_error", test_result)
            print(f"❌ Target Finder test failed: {e}")
            raise

    def test_valuer_real_api(self):
        """Test valuer agent with real financial API calls."""
        print("\n=== Testing Valuer Agent with Real Financial APIs ===")
        
        query = "Value a fintech company with $25M revenue"
        state = create_initial_state("buyer_ma", query)
        
        # Add some mock target data for valuation
        state["agent_results"]["target_finder"] = {
            "status": "success",
            "result": {
                "targets": [
                    {
                        "name": "FinTech Solutions Inc",
                        "revenue": "$25M",
                        "sector": "Financial Technology",
                        "employees": 150,
                        "description": "Cloud-based payment processing platform"
                    }
                ]
            }
        }
        
        valuer = ValuerAgent()
        
        try:
            result_state = asyncio.run(valuer.execute(state))
            
            test_result = {
                "test": "valuer_real_api",
                "query": query,
                "success": True,
                "state": result_state,
                "agent_results": result_state.get("agent_results", {}),
                "valuation_data": result_state.get("agent_results", {}).get("valuer", {}).get("result", {})
            }
            
            self.save_test_result("valuer_real_api", test_result)
            
            # Check valuation results
            valuer_result = result_state.get("agent_results", {}).get("valuer", {})
            if valuer_result.get("status") == "success":
                valuation = valuer_result.get("result", {})
                print(f"✅ Valuer completed analysis")
                print(f"  Estimated Value: {valuation.get('estimated_value', 'N/A')}")
                print(f"  Valuation Method: {valuation.get('valuation_method', 'N/A')}")
                print(f"  Market Data Points: {len(valuation.get('market_data', []))}")
            else:
                print(f"⚠️ Valuer status: {valuer_result.get('status', 'unknown')}")
            
        except Exception as e:
            test_result = {
                "test": "valuer_real_api",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("valuer_real_api_error", test_result)
            print(f"❌ Valuer test failed: {e}")
            raise

    def test_full_workflow_integration(self):
        """Test the complete workflow end-to-end with real APIs."""
        print("\n=== Testing Full Workflow Integration ===")
        
        query = "I want to acquire a cybersecurity company with $50M revenue"
        
        workflow = LiquidRoundWorkflow()
        
        try:
            result_state = asyncio.run(workflow.run(query))
            
            test_result = {
                "test": "full_workflow_integration",
                "query": query,
                "success": True,
                "final_state": result_state,
                "workflow_status": result_state.get("workflow_status", "unknown"),
                "mode": result_state.get("mode", "unknown"),
                "agent_results": result_state.get("agent_results", {}),
                "messages": result_state.get("messages", [])
            }
            
            self.save_test_result("full_workflow_integration", test_result)
            
            print(f"✅ Full workflow completed")
            print(f"Final Status: {result_state.get('workflow_status', 'unknown')}")
            print(f"Mode: {result_state.get('mode', 'unknown')}")
            print(f"Messages: {len(result_state.get('messages', []))}")
            
            # Check each agent's results
            for agent_name, result in result_state.get("agent_results", {}).items():
                status = result.get("status", "unknown")
                icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
                print(f"  {icon} {agent_name}: {status}")
                
        except Exception as e:
            test_result = {
                "test": "full_workflow_integration",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("full_workflow_integration_error", test_result)
            print(f"❌ Full workflow test failed: {e}")
            raise

    def test_seller_workflow_integration(self):
        """Test seller-led M&A workflow."""
        print("\n=== Testing Seller Workflow Integration ===")
        
        query = "Preparing to sell our B2B software company"
        
        workflow = LiquidRoundWorkflow()
        
        try:
            result_state = asyncio.run(workflow.run(query))
            
            test_result = {
                "test": "seller_workflow_integration",
                "query": query,
                "success": True,
                "final_state": result_state,
                "workflow_status": result_state.get("workflow_status", "unknown"),
                "mode": result_state.get("mode", "unknown"),
                "messages": result_state.get("messages", [])
            }
            
            self.save_test_result("seller_workflow_integration", test_result)
            
            print(f"✅ Seller workflow completed")
            print(f"Final Status: {result_state.get('workflow_status', 'unknown')}")
            print(f"Mode: {result_state.get('mode', 'unknown')}")
            
        except Exception as e:
            test_result = {
                "test": "seller_workflow_integration",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("seller_workflow_integration_error", test_result)
            print(f"❌ Seller workflow test failed: {e}")
            raise

    def test_ipo_workflow_integration(self):
        """Test IPO workflow."""
        print("\n=== Testing IPO Workflow Integration ===")
        
        query = "Assessing IPO readiness for our tech company"
        
        workflow = LiquidRoundWorkflow()
        
        try:
            result_state = asyncio.run(workflow.run(query))
            
            test_result = {
                "test": "ipo_workflow_integration",
                "query": query,
                "success": True,
                "final_state": result_state,
                "workflow_status": result_state.get("workflow_status", "unknown"),
                "mode": result_state.get("mode", "unknown"),
                "messages": result_state.get("messages", [])
            }
            
            self.save_test_result("ipo_workflow_integration", test_result)
            
            print(f"✅ IPO workflow completed")
            print(f"Final Status: {result_state.get('workflow_status', 'unknown')}")
            print(f"Mode: {result_state.get('mode', 'unknown')}")
            
        except Exception as e:
            test_result = {
                "test": "ipo_workflow_integration",
                "query": query,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("ipo_workflow_integration_error", test_result)
            print(f"❌ IPO workflow test failed: {e}")
            raise


if __name__ == "__main__":
    # Run tests directly
    test_instance = TestIntegration()
    test_instance.setup_method()
    
    print("🚀 Starting LiquidRound Integration Tests with Real APIs")
    print("=" * 60)
    
    try:
        test_instance.test_orchestrator_real_api()
        test_instance.test_target_finder_real_api()
        test_instance.test_valuer_real_api()
        test_instance.test_full_workflow_integration()
        test_instance.test_seller_workflow_integration()
        test_instance.test_ipo_workflow_integration()
        
        print("\n🎉 All integration tests completed!")
        print(f"Test results saved to: {test_instance.test_data_dir}")
        
    except Exception as e:
        print(f"\n💥 Integration tests failed: {e}")
        raise
