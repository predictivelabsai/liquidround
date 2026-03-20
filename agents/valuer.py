"""
Valuer agent for financial analysis and valuation.
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from agents.base_agent import BaseAgent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.state import State


class ValuerAgent(BaseAgent):
    """Agent for financial valuation and analysis."""
    
    def __init__(self):
        super().__init__("valuer", "valuer.md")
    
    async def _execute_logic(self, state: State) -> Dict[str, Any]:
        """Perform valuation analysis for the target company."""
        context = self._extract_context_from_state(state)
        
        # Extract target information from previous results
        target_info = self._extract_target_info(state)
        
        # Perform financial analysis
        financial_analysis = await self._perform_financial_analysis(target_info)
        
        # Create valuation prompt
        prompt = f"""
        Perform a comprehensive valuation analysis for the following target:
        
        Target: {target_info.get('company_name', 'Target Company')}
        Industry: {target_info.get('industry', state['deal'].get('industry', 'Not specified'))}
        
        Financial Data Available:
        {self._format_financial_data(financial_analysis)}
        
        Previous Analysis:
        {context.get('previous_results', {})}
        
        Please provide:
        1. DCF valuation with 5-year projections
        2. Comparable company analysis
        3. Precedent transaction analysis
        4. Sensitivity analysis on key assumptions
        5. Valuation summary and recommendation
        
        Structure your response with clear sections and supporting rationale.
        """
        
        messages = self._create_messages(prompt, context)
        
        try:
            # Get LLM valuation analysis
            llm_response = await self._call_llm(messages)
            
            # Combine with quantitative analysis
            valuation_result = {
                "target_company": target_info.get('company_name', 'Target Company'),
                "financial_analysis": financial_analysis,
                "valuation_analysis": llm_response,
                "key_metrics": self._extract_key_metrics(financial_analysis),
                "valuation_range": self._estimate_valuation_range(financial_analysis),
                "methodology": "DCF, Comparable Companies, Precedent Transactions"
            }
            
            return valuation_result
            
        except Exception as e:
            self.logger.error(f"Valuation analysis failed: {e}")
            return {
                "target_company": target_info.get('company_name', 'Target Company'),
                "error": str(e),
                "financial_analysis": financial_analysis
            }
    
    def _extract_target_info(self, state: State) -> Dict[str, Any]:
        """Extract target company information from state."""
        target_info = {
            "company_name": state['deal'].get('company_name'),
            "industry": state['deal'].get('industry')
        }
        
        # Look for target information in previous agent results
        if 'target_finder' in state['agent_results']:
            target_result = state['agent_results']['target_finder']
            if target_result['status'] == 'success' and 'targets' in target_result['result']:
                targets = target_result['result']['targets']
                if targets:
                    # Use the first target for detailed analysis
                    target_info.update(targets[0])
        
        return target_info
    
    async def _perform_financial_analysis(self, target_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform quantitative financial analysis."""
        analysis = {
            "data_source": "estimated",
            "metrics": {},
            "comparables": [],
            "market_data": {}
        }
        
        try:
            # If we have a ticker, get real financial data
            if 'ticker' in target_info:
                ticker = target_info['ticker']
                stock = yf.Ticker(ticker)
                
                # Get financial information
                info = stock.info
                financials = stock.financials
                
                if info:
                    analysis.update({
                        "data_source": "yfinance",
                        "metrics": {
                            "market_cap": info.get('marketCap', 0),
                            "enterprise_value": info.get('enterpriseValue', 0),
                            "revenue_ttm": info.get('totalRevenue', 0),
                            "ebitda": info.get('ebitda', 0),
                            "pe_ratio": info.get('trailingPE', 0),
                            "ev_revenue": info.get('enterpriseToRevenue', 0),
                            "ev_ebitda": info.get('enterpriseToEbitda', 0),
                            "profit_margin": info.get('profitMargins', 0),
                            "revenue_growth": info.get('revenueGrowth', 0)
                        }
                    })
                
                # Get comparable companies
                analysis["comparables"] = await self._get_comparable_companies(
                    info.get('sector', ''), info.get('industry', '')
                )
            
            else:
                # Use estimated data from target_finder
                analysis["metrics"] = self._estimate_financial_metrics(target_info)
        
        except Exception as e:
            self.logger.debug(f"Financial analysis error: {e}")
            analysis["metrics"] = self._estimate_financial_metrics(target_info)
        
        return analysis
    
    def _estimate_financial_metrics(self, target_info: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate financial metrics from available information."""
        metrics = {}
        
        # Extract revenue estimate
        revenue_str = target_info.get('estimated_revenue', '0')
        try:
            # Parse revenue (assuming format like "100M" or "1.5B")
            revenue_num = float(revenue_str.replace('M', '').replace('B', '').replace('$', ''))
            if 'B' in revenue_str:
                revenue_num *= 1000  # Convert to millions
            metrics['revenue_estimate'] = revenue_num
        except:
            metrics['revenue_estimate'] = 0
        
        # Extract EBITDA margin
        margin_str = target_info.get('estimated_ebitda_margin', '0%')
        try:
            margin_num = float(margin_str.replace('%', '')) / 100
            metrics['ebitda_margin'] = margin_num
            metrics['ebitda_estimate'] = metrics['revenue_estimate'] * margin_num
        except:
            metrics['ebitda_margin'] = 0.15  # Default 15%
            metrics['ebitda_estimate'] = metrics['revenue_estimate'] * 0.15
        
        return metrics
    
    async def _get_comparable_companies(self, sector: str, industry: str) -> List[Dict[str, Any]]:
        """Get comparable companies for benchmarking."""
        # This is a simplified implementation
        # In production, you'd use a comprehensive database of companies
        
        comparables = []
        
        # Sample tickers by sector (simplified)
        sector_tickers = {
            'Technology': ['MSFT', 'AAPL', 'GOOGL', 'META', 'NVDA'],
            'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO'],
            'Financial Services': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'],
            'Industrials': ['BA', 'CAT', 'GE', 'MMM', 'HON']
        }
        
        tickers = sector_tickers.get(sector, ['SPY'])[:3]  # Limit to 3 for performance
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                if info and 'marketCap' in info:
                    comparable = {
                        "ticker": ticker,
                        "company_name": info.get('longName', ticker),
                        "market_cap": info.get('marketCap', 0),
                        "ev_revenue": info.get('enterpriseToRevenue', 0),
                        "ev_ebitda": info.get('enterpriseToEbitda', 0),
                        "pe_ratio": info.get('trailingPE', 0)
                    }
                    comparables.append(comparable)
            except:
                continue
        
        return comparables
    
    def _format_financial_data(self, analysis: Dict[str, Any]) -> str:
        """Format financial data for LLM prompt."""
        formatted = f"Data Source: {analysis['data_source']}\n\n"
        
        metrics = analysis.get('metrics', {})
        if metrics:
            formatted += "Key Metrics:\n"
            for key, value in metrics.items():
                formatted += f"- {key}: {value}\n"
        
        comparables = analysis.get('comparables', [])
        if comparables:
            formatted += f"\nComparable Companies ({len(comparables)} companies):\n"
            for comp in comparables:
                formatted += f"- {comp.get('company_name', comp.get('ticker'))}: "
                formatted += f"EV/Rev: {comp.get('ev_revenue', 'N/A')}, "
                formatted += f"EV/EBITDA: {comp.get('ev_ebitda', 'N/A')}\n"
        
        return formatted
    
    def _extract_key_metrics(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics for summary."""
        metrics = analysis.get('metrics', {})
        
        return {
            "revenue": metrics.get('revenue_ttm') or metrics.get('revenue_estimate', 0),
            "ebitda": metrics.get('ebitda') or metrics.get('ebitda_estimate', 0),
            "market_cap": metrics.get('market_cap', 0),
            "ev_revenue_multiple": metrics.get('ev_revenue', 0),
            "ev_ebitda_multiple": metrics.get('ev_ebitda', 0)
        }
    
    def _estimate_valuation_range(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate valuation range based on available data."""
        metrics = analysis.get('metrics', {})
        
        revenue = metrics.get('revenue_ttm') or metrics.get('revenue_estimate', 0)
        ebitda = metrics.get('ebitda') or metrics.get('ebitda_estimate', 0)
        
        # Simple multiple-based valuation
        valuation_range = {
            "low": 0,
            "mid": 0,
            "high": 0,
            "methodology": "Multiple-based estimation"
        }
        
        if revenue > 0:
            # Use industry-typical multiples
            rev_multiple_low = 2.0
            rev_multiple_mid = 4.0
            rev_multiple_high = 6.0
            
            valuation_range.update({
                "low": revenue * rev_multiple_low,
                "mid": revenue * rev_multiple_mid,
                "high": revenue * rev_multiple_high
            })
        
        return valuation_range
