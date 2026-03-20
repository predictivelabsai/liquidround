"""
Test real company data retrieval using known public companies.
"""
import json
import os
import sys
import yfinance as yf
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class TestRealCompanyData:
    """Test real company data retrieval from various APIs."""
    
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
        
        print(f"Real company data saved to: {filepath}")
        return filepath

    def test_yfinance_real_companies(self):
        """Test Yahoo Finance data for real public companies."""
        print("\n=== Testing Yahoo Finance with Real Public Companies ===")
        
        # Known public companies with good data
        test_companies = [
            {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary"},
            {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
            {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
            {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services"},
            {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
            {"ticker": "SNOW", "name": "Snowflake Inc.", "sector": "Technology"}
        ]
        
        results = []
        
        for company in test_companies:
            print(f"\nTesting: {company['name']} ({company['ticker']})")
            
            try:
                ticker = yf.Ticker(company["ticker"])
                info = ticker.info
                history = ticker.history(period="5d")
                
                # Extract key financial metrics
                financial_data = {
                    "ticker": company["ticker"],
                    "company_name": info.get("longName", company["name"]),
                    "sector": info.get("sector", company["sector"]),
                    "industry": info.get("industry", "Unknown"),
                    "market_cap": info.get("marketCap", "N/A"),
                    "enterprise_value": info.get("enterpriseValue", "N/A"),
                    "revenue_ttm": info.get("totalRevenue", "N/A"),
                    "ebitda": info.get("ebitda", "N/A"),
                    "pe_ratio": info.get("trailingPE", "N/A"),
                    "profit_margin": info.get("profitMargins", "N/A"),
                    "revenue_growth": info.get("revenueGrowth", "N/A"),
                    "employees": info.get("fullTimeEmployees", "N/A"),
                    "website": info.get("website", "N/A"),
                    "business_summary": info.get("businessSummary", "N/A")[:200] + "..." if info.get("businessSummary") else "N/A",
                    "current_price": float(history['Close'].iloc[-1]) if not history.empty else "N/A",
                    "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                    "52_week_low": info.get("fiftyTwoWeekLow", "N/A")
                }
                
                result = {
                    "company": company,
                    "success": True,
                    "financial_data": financial_data
                }
                
                print(f"✅ Success")
                print(f"  Market Cap: ${financial_data['market_cap']:,}" if financial_data['market_cap'] != 'N/A' else "  Market Cap: N/A")
                print(f"  Revenue TTM: ${financial_data['revenue_ttm']:,}" if financial_data['revenue_ttm'] != 'N/A' else "  Revenue TTM: N/A")
                print(f"  Employees: {financial_data['employees']:,}" if financial_data['employees'] != 'N/A' else "  Employees: N/A")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "company": company,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Failed: {e}")
                results.append(result)
        
        test_result = {
            "test": "yfinance_real_companies",
            "total_companies": len(test_companies),
            "successful": len([r for r in results if r["success"]]),
            "results": results
        }
        
        self.save_test_result("yfinance_real_companies", test_result)

    def test_polygon_real_stock_data(self):
        """Test Polygon.io with real stock data."""
        print("\n=== Testing Polygon.io with Real Stock Data ===")
        
        api_key = os.getenv("POLYGON_API_KEY")
        if not api_key:
            print("❌ POLYGON_API_KEY not found")
            return
        
        # Test with real stock tickers
        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        results = []
        
        for ticker in test_tickers:
            print(f"\nTesting: {ticker}")
            
            try:
                # Get previous day's data
                url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?adjusted=true&apikey={api_key}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("results") and len(data["results"]) > 0:
                        stock_data = data["results"][0]
                        
                        result = {
                            "ticker": ticker,
                            "success": True,
                            "data": {
                                "open": stock_data.get("o"),
                                "high": stock_data.get("h"),
                                "low": stock_data.get("l"),
                                "close": stock_data.get("c"),
                                "volume": stock_data.get("v"),
                                "timestamp": stock_data.get("t")
                            }
                        }
                        
                        print(f"✅ Success")
                        print(f"  Close: ${result['data']['close']}")
                        print(f"  Volume: {result['data']['volume']:,}")
                        
                    else:
                        result = {
                            "ticker": ticker,
                            "success": False,
                            "error": "No results in response"
                        }
                        print(f"❌ No data available")
                
                else:
                    result = {
                        "ticker": ticker,
                        "success": False,
                        "error": f"API returned {response.status_code}: {response.text}"
                    }
                    print(f"❌ API error: {response.status_code}")
                
                results.append(result)
                
            except Exception as e:
                result = {
                    "ticker": ticker,
                    "success": False,
                    "error": str(e)
                }
                print(f"❌ Exception: {e}")
                results.append(result)
        
        test_result = {
            "test": "polygon_real_stock_data",
            "results": results
        }
        
        self.save_test_result("polygon_real_stock_data", test_result)

    def test_exa_real_company_search(self):
        """Test Exa.ai with real company searches."""
        print("\n=== Testing Exa.ai with Real Company Searches ===")
        
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            print("❌ EXA_API_KEY not found")
            return
        
        # Test searches for real companies and sectors
        search_queries = [
            "Apple Inc financial results 2024",
            "Microsoft Azure cloud revenue growth",
            "Tesla electric vehicle sales data",
            "Amazon AWS market share",
            "Google Alphabet advertising revenue"
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
                    "num_results": 3,
                    "include_domains": ["sec.gov", "investor.apple.com", "microsoft.com", "tesla.com", "amazon.com", "abc.xyz"],
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
                                "text_preview": article.get("text", "No text")[:300] + "..." if article.get("text") else "No text"
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
            "test": "exa_real_company_search",
            "results": results
        }
        
        self.save_test_result("exa_real_company_search", test_result)

    def test_comprehensive_company_profile(self):
        """Create comprehensive profiles for real companies using all APIs."""
        print("\n=== Creating Comprehensive Company Profiles ===")
        
        # Focus on a few companies for detailed analysis
        target_companies = [
            {"ticker": "CRM", "name": "Salesforce Inc."},
            {"ticker": "SNOW", "name": "Snowflake Inc."},
            {"ticker": "CRWD", "name": "CrowdStrike Holdings"}
        ]
        
        results = []
        
        for company in target_companies:
            print(f"\nCreating profile for: {company['name']} ({company['ticker']})")
            
            profile = {
                "company": company,
                "yfinance_data": None,
                "polygon_data": None,
                "exa_search_data": None
            }
            
            # Get Yahoo Finance data
            try:
                ticker = yf.Ticker(company["ticker"])
                info = ticker.info
                
                profile["yfinance_data"] = {
                    "market_cap": info.get("marketCap"),
                    "revenue_ttm": info.get("totalRevenue"),
                    "employees": info.get("fullTimeEmployees"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "business_summary": info.get("businessSummary"),
                    "website": info.get("website")
                }
                print(f"  ✅ Yahoo Finance data retrieved")
                
            except Exception as e:
                print(f"  ❌ Yahoo Finance failed: {e}")
            
            # Get Polygon data
            try:
                api_key = os.getenv("POLYGON_API_KEY")
                if api_key:
                    url = f"https://api.polygon.io/v2/aggs/ticker/{company['ticker']}/prev?adjusted=true&apikey={api_key}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("results"):
                            profile["polygon_data"] = data["results"][0]
                            print(f"  ✅ Polygon data retrieved")
                    
            except Exception as e:
                print(f"  ❌ Polygon failed: {e}")
            
            # Search for recent news/data
            try:
                api_key = os.getenv("EXA_API_KEY")
                if api_key:
                    url = "https://api.exa.ai/search"
                    headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "x-api-key": api_key
                    }
                    
                    payload = {
                        "query": f"{company['name']} financial results earnings",
                        "num_results": 2,
                        "include_text": True
                    }
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        profile["exa_search_data"] = data.get("results", [])
                        print(f"  ✅ Exa search data retrieved")
                    
            except Exception as e:
                print(f"  ❌ Exa search failed: {e}")
            
            results.append(profile)
        
        test_result = {
            "test": "comprehensive_company_profiles",
            "results": results
        }
        
        self.save_test_result("comprehensive_company_profiles", test_result)


if __name__ == "__main__":
    # Run real company data tests
    test_instance = TestRealCompanyData()
    test_instance.setup_method()
    
    print("📊 Starting Real Company Data Tests")
    print("=" * 50)
    
    try:
        test_instance.test_yfinance_real_companies()
        test_instance.test_polygon_real_stock_data()
        test_instance.test_exa_real_company_search()
        test_instance.test_comprehensive_company_profile()
        
        print("\n🎉 All real company data tests completed!")
        print(f"Test results saved to: {test_instance.test_data_dir}")
        
    except Exception as e:
        print(f"\n💥 Real company data tests failed: {e}")
        raise
