"""
Individual agent tests with real API calls to get actual company data.
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


class TestIndividualAgents:
    """Test each agent individually with real API calls."""
    
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
        
        print(f"Agent test result saved to: {filepath}")
        return filepath

    def test_orchestrator_buyer_queries(self):
        """Test orchestrator with various buyer M&A queries."""
        print("\n=== Testing Orchestrator with Buyer M&A Queries ===")
        
        queries = [
            "Find fintech companies to acquire with $20-100M revenue",
            "Looking for SaaS acquisition targets in healthcare",
            "Want to buy a cybersecurity company",
            "Identify AI/ML startups for strategic acquisition",
            "Find manufacturing companies for acquisition"
        ]
        
        orchestrator = OrchestratorAgent()
        results = []
        
        for query in queries:
            print(f"\nTesting query: {query}")
            state = create_initial_state("unknown", query)
            
            try:
                result_state = asyncio.run(orchestrator.execute(state))
                
                result = {
                    "query": query,
                    "success": True,
                    "workflow_type": result_state["agent_results"]["orchestrator"]["result"]["workflow_type"],
                    "rationale": result_state["agent_results"]["orchestrator"]["result"]["rationale"],
                    "execution_time": result_state["agent_results"]["orchestrator"]["execution_time"]
                }
                
                print(f"✅ Detected: {result['workflow_type']}")
                results.append(result)
                
            except Exception as e:
                result = {
                    "query": query,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Failed: {e}")
                results.append(result)
        
        test_result = {
            "test": "orchestrator_buyer_queries",
            "total_queries": len(queries),
            "successful": len([r for r in results if r["success"]]),
            "results": results
        }
        
        self.save_test_result("orchestrator_buyer_queries", test_result)

    def test_orchestrator_seller_queries(self):
        """Test orchestrator with seller M&A queries."""
        print("\n=== Testing Orchestrator with Seller M&A Queries ===")
        
        queries = [
            "Preparing to sell our B2B software company",
            "Need help finding buyers for our logistics business",
            "Planning to divest our retail division",
            "Looking for strategic buyers in the energy sector",
            "Want to sell our fintech startup"
        ]
        
        orchestrator = OrchestratorAgent()
        results = []
        
        for query in queries:
            print(f"\nTesting query: {query}")
            state = create_initial_state("unknown", query)
            
            try:
                result_state = asyncio.run(orchestrator.execute(state))
                
                result = {
                    "query": query,
                    "success": True,
                    "workflow_type": result_state["agent_results"]["orchestrator"]["result"]["workflow_type"],
                    "rationale": result_state["agent_results"]["orchestrator"]["result"]["rationale"]
                }
                
                print(f"✅ Detected: {result['workflow_type']}")
                results.append(result)
                
            except Exception as e:
                result = {
                    "query": query,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Failed: {e}")
                results.append(result)
        
        test_result = {
            "test": "orchestrator_seller_queries",
            "results": results
        }
        
        self.save_test_result("orchestrator_seller_queries", test_result)

    def test_target_finder_specific_sectors(self):
        """Test target finder with specific sector queries."""
        print("\n=== Testing Target Finder with Specific Sectors ===")
        
        sector_queries = [
            {
                "query": "Find fintech companies with $50-200M revenue for acquisition",
                "expected_sector": "fintech"
            },
            {
                "query": "Looking for healthcare SaaS companies to acquire",
                "expected_sector": "healthcare"
            },
            {
                "query": "Find cybersecurity companies with strong cloud offerings",
                "expected_sector": "cybersecurity"
            },
            {
                "query": "Identify AI/ML companies for strategic acquisition",
                "expected_sector": "artificial intelligence"
            },
            {
                "query": "Find e-commerce platform companies to buy",
                "expected_sector": "e-commerce"
            }
        ]
        
        target_finder = TargetFinderAgent()
        results = []
        
        for test_case in sector_queries:
            query = test_case["query"]
            expected_sector = test_case["expected_sector"]
            
            print(f"\nTesting: {query}")
            state = create_initial_state("buyer_ma", query)
            
            try:
                result_state = asyncio.run(target_finder.execute(state))
                
                target_result = result_state["agent_results"]["target_finder"]
                if target_result["status"] == "success":
                    targets = target_result["result"]["targets"]
                    
                    result = {
                        "query": query,
                        "expected_sector": expected_sector,
                        "success": True,
                        "targets_found": len(targets),
                        "sample_targets": targets[:3],  # First 3 targets
                        "execution_time": target_result["execution_time"]
                    }
                    
                    print(f"✅ Found {len(targets)} targets")
                    for i, target in enumerate(targets[:3]):
                        print(f"  {i+1}. {target.get('company_name', 'Unknown')} - {target.get('estimated_revenue', 'N/A')}")
                    
                else:
                    result = {
                        "query": query,
                        "expected_sector": expected_sector,
                        "success": False,
                        "error": target_result.get("error_message", "Unknown error")
                    }
                    print(f"❌ Failed: {result['error']}")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "query": query,
                    "expected_sector": expected_sector,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Exception: {e}")
                results.append(result)
        
        test_result = {
            "test": "target_finder_specific_sectors",
            "results": results
        }
        
        self.save_test_result("target_finder_specific_sectors", test_result)

    def test_valuer_real_companies(self):
        """Test valuer with real public companies."""
        print("\n=== Testing Valuer with Real Public Companies ===")
        
        # Test with real public companies
        test_companies = [
            {
                "name": "Snowflake Inc.",
                "ticker": "SNOW",
                "sector": "Technology"
            },
            {
                "name": "CrowdStrike Holdings",
                "ticker": "CRWD", 
                "sector": "Cybersecurity"
            },
            {
                "name": "Palantir Technologies",
                "ticker": "PLTR",
                "sector": "Data Analytics"
            },
            {
                "name": "Zoom Video Communications",
                "ticker": "ZM",
                "sector": "Communications"
            },
            {
                "name": "DocuSign Inc.",
                "ticker": "DOCU",
                "sector": "SaaS"
            }
        ]
        
        valuer = ValuerAgent()
        results = []
        
        for company in test_companies:
            print(f"\nTesting valuation for: {company['name']} ({company['ticker']})")
            
            # Create state with target company data
            state = create_initial_state("buyer_ma", f"Value {company['name']}")
            state["agent_results"]["target_finder"] = {
                "status": "success",
                "result": {
                    "targets": [
                        {
                            "company_name": company["name"],
                            "ticker": company["ticker"],
                            "sector": company["sector"],
                            "estimated_revenue": "Unknown",
                            "description": f"Public company in {company['sector']} sector"
                        }
                    ]
                }
            }
            
            try:
                result_state = asyncio.run(valuer.execute(state))
                
                valuer_result = result_state["agent_results"]["valuer"]
                if valuer_result["status"] == "success":
                    valuation_data = valuer_result["result"]
                    
                    result = {
                        "company": company,
                        "success": True,
                        "valuation_data": valuation_data,
                        "execution_time": valuer_result["execution_time"]
                    }
                    
                    # Extract key metrics if available
                    financial_analysis = valuation_data.get("financial_analysis", {})
                    metrics = financial_analysis.get("metrics", {})
                    
                    print(f"✅ Valuation completed")
                    print(f"  Market Cap: ${metrics.get('market_cap', 'N/A'):,}" if metrics.get('market_cap') else "  Market Cap: N/A")
                    print(f"  Revenue TTM: ${metrics.get('revenue_ttm', 'N/A'):,}" if metrics.get('revenue_ttm') else "  Revenue TTM: N/A")
                    print(f"  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}")
                    
                else:
                    result = {
                        "company": company,
                        "success": False,
                        "error": valuer_result.get("error_message", "Unknown error")
                    }
                    print(f"❌ Failed: {result['error']}")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "company": company,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Exception: {e}")
                results.append(result)
        
        test_result = {
            "test": "valuer_real_companies",
            "results": results
        }
        
        self.save_test_result("valuer_real_companies", test_result)

    def test_target_finder_with_revenue_filters(self):
        """Test target finder with specific revenue ranges."""
        print("\n=== Testing Target Finder with Revenue Filters ===")
        
        revenue_queries = [
            "Find SaaS companies with $10-50M annual revenue",
            "Looking for fintech companies with $50-200M revenue",
            "Identify cybersecurity companies with $100-500M revenue",
            "Find healthcare companies with $20-100M revenue",
            "Looking for AI companies with $5-25M revenue"
        ]
        
        target_finder = TargetFinderAgent()
        results = []
        
        for query in revenue_queries:
            print(f"\nTesting: {query}")
            state = create_initial_state("buyer_ma", query)
            
            try:
                result_state = asyncio.run(target_finder.execute(state))
                
                target_result = result_state["agent_results"]["target_finder"]
                if target_result["status"] == "success":
                    targets = target_result["result"]["targets"]
                    
                    # Analyze revenue data in targets
                    revenue_analysis = []
                    for target in targets:
                        revenue_analysis.append({
                            "company": target.get("company_name", "Unknown"),
                            "estimated_revenue": target.get("estimated_revenue", "N/A"),
                            "ticker": target.get("ticker", "N/A"),
                            "market_cap": target.get("market_cap", "N/A"),
                            "revenue_ttm": target.get("revenue_ttm", "N/A")
                        })
                    
                    result = {
                        "query": query,
                        "success": True,
                        "targets_found": len(targets),
                        "revenue_analysis": revenue_analysis,
                        "execution_time": target_result["execution_time"]
                    }
                    
                    print(f"✅ Found {len(targets)} targets with revenue data")
                    
                else:
                    result = {
                        "query": query,
                        "success": False,
                        "error": target_result.get("error_message", "Unknown error")
                    }
                    print(f"❌ Failed: {result['error']}")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "query": query,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Exception: {e}")
                results.append(result)
        
        test_result = {
            "test": "target_finder_revenue_filters",
            "results": results
        }
        
        self.save_test_result("target_finder_revenue_filters", test_result)

    def test_exa_search_integration(self):
        """Test direct Exa.ai search integration for company discovery."""
        print("\n=== Testing Exa.ai Search Integration ===")
        
        import requests
        
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            print("❌ EXA_API_KEY not found")
            return
        
        search_queries = [
            "fintech companies funding acquisition 2024",
            "healthcare SaaS companies revenue growth",
            "cybersecurity startups Series B funding",
            "AI machine learning companies acquisition",
            "B2B software companies IPO ready"
        ]
        
        results = []
        
        for query in search_queries:
            print(f"\nSearching: {query}")
            
            try:
                url = "https://api.exa.ai/search"
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-api-key": api_key
                }
                
                payload = {
                    "query": query,
                    "num_results": 5,
                    "include_domains": ["techcrunch.com", "reuters.com", "bloomberg.com", "crunchbase.com"],
                    "include_text": True
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "query": query,
                        "success": True,
                        "results_count": len(data.get("results", [])),
                        "articles": [
                            {
                                "title": article.get("title", "No title"),
                                "url": article.get("url", "No URL"),
                                "text_preview": article.get("text", "No text")[:200] + "..." if article.get("text") else "No text"
                            }
                            for article in data.get("results", [])
                        ]
                    }
                    
                    print(f"✅ Found {len(data.get('results', []))} articles")
                    for i, article in enumerate(data.get("results", [])[:2]):
                        print(f"  {i+1}. {article.get('title', 'No title')}")
                    
                else:
                    result = {
                        "query": query,
                        "success": False,
                        "error": f"API returned {response.status_code}: {response.text}"
                    }
                    print(f"❌ API error: {response.status_code}")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "query": query,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Exception: {e}")
                results.append(result)
        
        test_result = {
            "test": "exa_search_integration",
            "results": results
        }
        
        self.save_test_result("exa_search_integration", test_result)


if __name__ == "__main__":
    # Run individual agent tests
    test_instance = TestIndividualAgents()
    test_instance.setup_method()
    
    print("🔬 Starting Individual Agent Tests with Real APIs")
    print("=" * 60)
    
    try:
        test_instance.test_orchestrator_buyer_queries()
        test_instance.test_orchestrator_seller_queries()
        test_instance.test_target_finder_specific_sectors()
        test_instance.test_valuer_real_companies()
        test_instance.test_target_finder_with_revenue_filters()
        test_instance.test_exa_search_integration()
        
        print("\n🎉 All individual agent tests completed!")
        print(f"Test results saved to: {test_instance.test_data_dir}")
        
    except Exception as e:
        print(f"\n💥 Individual agent tests failed: {e}")
        raise
