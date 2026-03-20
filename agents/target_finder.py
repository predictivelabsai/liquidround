"""
Target Finder agent for identifying acquisition targets.
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state import State


class TargetFinderAgent(BaseAgent):
    """Agent for finding and evaluating acquisition targets."""
    
    def __init__(self):
        super().__init__("target_finder", "target_finder.md")
    
    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        """Find acquisition targets based on buyer criteria."""
        context = self._extract_context_from_state(state)
        
        # Create prompt for target identification
        prompt = f"""
        Based on the following acquisition criteria, identify potential targets:
        
        Buyer Query: {state['user_query']}
        
        Please provide 8-12 acquisition targets in the following format:
        
        | Company Name | Location | Est. Revenue (USD M) | Est. EBITDA Margin | Strategic Fit Score (1-5) | Key Investment Highlights | Source/Rationale |
        
        Focus on realistic companies that would be genuine strategic fits.
        """
        
        messages = self._create_messages(prompt, context)
        
        try:
            # Get LLM response for target identification
            llm_response = await self._call_llm(messages)
            
            # Parse the response to extract targets
            targets = self._parse_targets_from_response(llm_response)
            
            # Enhance with financial data where possible
            enhanced_targets = await self._enhance_with_financial_data(targets)
            
            return {
                "targets": enhanced_targets,
                "target_count": len(enhanced_targets),
                "analysis_summary": llm_response,
                "search_criteria": state['user_query']
            }
            
        except Exception as e:
            self.logger.error(f"Target finding failed: {e}")
            return {
                "targets": [],
                "target_count": 0,
                "error": str(e),
                "search_criteria": state['user_query']
            }
    
    def _parse_targets_from_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse target companies from LLM response."""
        targets = []
        lines = response.split('\n')
        
        for line in lines:
            if '|' in line and 'Company Name' not in line and '---' not in line:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 6:
                    target = {
                        "company_name": parts[0],
                        "location": parts[1],
                        "estimated_revenue": parts[2],
                        "estimated_ebitda_margin": parts[3],
                        "strategic_fit_score": parts[4],
                        "investment_highlights": parts[5],
                        "source_rationale": parts[6] if len(parts) > 6 else ""
                    }
                    targets.append(target)
        
        return targets
    
    async def _enhance_with_financial_data(self, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance target data with real financial information where available."""
        enhanced_targets = []
        
        for target in targets:
            enhanced_target = target.copy()
            
            try:
                # Try to find ticker symbol and get real data
                company_name = target["company_name"]
                
                # This is a simplified approach - in production, you'd use
                # more sophisticated company/ticker matching
                potential_tickers = self._guess_ticker_symbols(company_name)
                
                for ticker in potential_tickers:
                    try:
                        stock = yf.Ticker(ticker)
                        info = stock.info
                        
                        if info and 'marketCap' in info:
                            enhanced_target.update({
                                "ticker": ticker,
                                "market_cap": info.get('marketCap', 'N/A'),
                                "sector": info.get('sector', 'N/A'),
                                "industry": info.get('industry', 'N/A'),
                                "revenue_ttm": info.get('totalRevenue', 'N/A'),
                                "employees": info.get('fullTimeEmployees', 'N/A'),
                                "website": info.get('website', 'N/A')
                            })
                            break
                    except:
                        continue
                        
            except Exception as e:
                self.logger.debug(f"Could not enhance data for {target['company_name']}: {e}")
            
            enhanced_targets.append(enhanced_target)
        
        return enhanced_targets
    
    def _guess_ticker_symbols(self, company_name: str) -> List[str]:
        """Generate potential ticker symbols for a company name."""
        # This is a very basic implementation
        # In production, you'd use a proper company/ticker database
        
        name_parts = company_name.replace(',', '').replace('.', '').split()
        potential_tickers = []
        
        # Try first letters of words
        if len(name_parts) >= 2:
            ticker = ''.join([part[0] for part in name_parts[:3]]).upper()
            potential_tickers.append(ticker)
        
        # Try first word
        if name_parts:
            potential_tickers.append(name_parts[0].upper())
        
        # Try common abbreviations
        if 'Corporation' in company_name or 'Corp' in company_name:
            base_name = company_name.replace('Corporation', '').replace('Corp', '').strip()
            potential_tickers.append(base_name.replace(' ', '')[:4].upper())
        
        return potential_tickers[:3]  # Limit to 3 attempts
