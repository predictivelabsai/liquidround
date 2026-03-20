"""
API connectivity tests - verify all external services are working.
"""
import pytest
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import requests
import yfinance as yf
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.config import config


class TestAPIConnectivity:
    """Test connectivity to all external APIs."""
    
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
        
        print(f"API test result saved to: {filepath}")
        return filepath

    def test_openai_api_connectivity(self):
        """Test OpenAI API connectivity and basic functionality."""
        print("\n=== Testing OpenAI API Connectivity ===")
        
        try:
            from langchain_openai import ChatOpenAI
            
            # Initialize OpenAI client
            llm = ChatOpenAI(
                model="gpt-4.1-mini",
                temperature=0.7,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # Test basic completion
            test_prompt = "What is M&A? Provide a brief 2-sentence answer."
            response = llm.invoke(test_prompt)
            
            test_result = {
                "test": "openai_api_connectivity",
                "success": True,
                "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
                "model": "gpt-4.1-mini",
                "test_prompt": test_prompt,
                "response": response.content,
                "response_length": len(response.content)
            }
            
            self.save_test_result("openai_api_connectivity", test_result)
            
            print(f"✅ OpenAI API working")
            print(f"Response: {response.content[:100]}...")
            
            assert response.content
            assert len(response.content) > 10
            
        except Exception as e:
            test_result = {
                "test": "openai_api_connectivity",
                "success": False,
                "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("openai_api_connectivity_error", test_result)
            print(f"❌ OpenAI API failed: {e}")
            raise

    def test_polygon_api_connectivity(self):
        """Test Polygon.io API connectivity."""
        print("\n=== Testing Polygon.io API Connectivity ===")
        
        try:
            api_key = os.getenv("POLYGON_API_KEY")
            if not api_key:
                raise ValueError("POLYGON_API_KEY not found in environment")
            
            # Test basic stock data retrieval
            url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?adjusted=true&apikey={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                test_result = {
                    "test": "polygon_api_connectivity",
                    "success": True,
                    "api_key_present": bool(api_key),
                    "status_code": response.status_code,
                    "data": data,
                    "results_count": len(data.get("results", []))
                }
                
                self.save_test_result("polygon_api_connectivity", test_result)
                
                print(f"✅ Polygon.io API working")
                print(f"Retrieved data for AAPL: {len(data.get('results', []))} results")
                
            else:
                raise Exception(f"API returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            test_result = {
                "test": "polygon_api_connectivity",
                "success": False,
                "api_key_present": bool(os.getenv("POLYGON_API_KEY")),
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("polygon_api_connectivity_error", test_result)
            print(f"❌ Polygon.io API failed: {e}")
            raise

    def test_exa_api_connectivity(self):
        """Test Exa.ai API connectivity."""
        print("\n=== Testing Exa.ai API Connectivity ===")
        
        try:
            api_key = os.getenv("EXA_API_KEY")
            if not api_key:
                raise ValueError("EXA_API_KEY not found in environment")
            
            # Test basic search functionality
            url = "https://api.exa.ai/search"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "x-api-key": api_key
            }
            
            payload = {
                "query": "fintech companies acquisition",
                "num_results": 3,
                "include_domains": ["techcrunch.com", "reuters.com", "bloomberg.com"]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                test_result = {
                    "test": "exa_api_connectivity",
                    "success": True,
                    "api_key_present": bool(api_key),
                    "status_code": response.status_code,
                    "query": payload["query"],
                    "results_count": len(data.get("results", [])),
                    "results": data.get("results", [])
                }
                
                self.save_test_result("exa_api_connectivity", test_result)
                
                print(f"✅ Exa.ai API working")
                print(f"Search results: {len(data.get('results', []))} articles found")
                
                for i, result in enumerate(data.get("results", [])[:2]):
                    print(f"  {i+1}. {result.get('title', 'No title')}")
                
            else:
                raise Exception(f"API returned status {response.status_code}: {response.text}")
                
        except Exception as e:
            test_result = {
                "test": "exa_api_connectivity",
                "success": False,
                "api_key_present": bool(os.getenv("EXA_API_KEY")),
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("exa_api_connectivity_error", test_result)
            print(f"❌ Exa.ai API failed: {e}")
            raise

    def test_yfinance_connectivity(self):
        """Test Yahoo Finance connectivity via yfinance."""
        print("\n=== Testing Yahoo Finance (yfinance) Connectivity ===")
        
        try:
            # Test basic stock data retrieval
            ticker = yf.Ticker("MSFT")
            info = ticker.info
            history = ticker.history(period="5d")
            
            test_result = {
                "test": "yfinance_connectivity",
                "success": True,
                "ticker": "MSFT",
                "company_name": info.get("longName", "Unknown"),
                "market_cap": info.get("marketCap", "N/A"),
                "sector": info.get("sector", "Unknown"),
                "history_days": len(history),
                "latest_price": float(history['Close'].iloc[-1]) if not history.empty else None,
                "sample_info": {k: v for k, v in list(info.items())[:10]}  # First 10 items
            }
            
            self.save_test_result("yfinance_connectivity", test_result)
            
            print(f"✅ Yahoo Finance (yfinance) working")
            print(f"Company: {info.get('longName', 'Unknown')}")
            print(f"Market Cap: ${info.get('marketCap', 'N/A'):,}" if info.get('marketCap') else "Market Cap: N/A")
            print(f"History: {len(history)} days of data")
            
        except Exception as e:
            test_result = {
                "test": "yfinance_connectivity",
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.save_test_result("yfinance_connectivity_error", test_result)
            print(f"❌ Yahoo Finance failed: {e}")
            raise

    def test_all_environment_variables(self):
        """Test that all required environment variables are present."""
        print("\n=== Testing Environment Variables ===")
        
        required_vars = [
            "OPENAI_API_KEY",
            "POLYGON_API_KEY", 
            "EXA_API_KEY"
        ]
        
        results = {}
        all_present = True
        
        for var in required_vars:
            value = os.getenv(var)
            present = bool(value)
            results[var] = {
                "present": present,
                "length": len(value) if value else 0,
                "starts_with": value[:10] + "..." if value and len(value) > 10 else value
            }
            
            if present:
                print(f"✅ {var}: Present ({len(value)} chars)")
            else:
                print(f"❌ {var}: Missing")
                all_present = False
        
        test_result = {
            "test": "environment_variables",
            "success": all_present,
            "variables": results,
            "all_present": all_present
        }
        
        self.save_test_result("environment_variables", test_result)
        
        if not all_present:
            raise ValueError("Some required environment variables are missing")


if __name__ == "__main__":
    # Run connectivity tests directly
    test_instance = TestAPIConnectivity()
    test_instance.setup_method()
    
    print("🔌 Starting API Connectivity Tests")
    print("=" * 50)
    
    try:
        test_instance.test_all_environment_variables()
        test_instance.test_openai_api_connectivity()
        test_instance.test_polygon_api_connectivity()
        test_instance.test_exa_api_connectivity()
        test_instance.test_yfinance_connectivity()
        
        print("\n🎉 All API connectivity tests passed!")
        print(f"Test results saved to: {test_instance.test_data_dir}")
        
    except Exception as e:
        print(f"\n💥 API connectivity tests failed: {e}")
        raise
