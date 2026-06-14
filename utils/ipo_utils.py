import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
import time
from typing import List, Dict, Optional
import logging

# Exchange to country mapping
EXCHANGE_COUNTRY_MAP = {
    # United States
    'NASDAQ': 'United States',
    'NYSE': 'United States',
    'AMEX': 'United States',
    
    # United Kingdom
    'LSE': 'United Kingdom',
    'AIM': 'United Kingdom',
    'LON': 'United Kingdom',
    
    # Germany
    'XETRA': 'Germany',
    'FSE': 'Germany',
    'GETTEX': 'Germany',
    'FRA': 'Germany',
    'BER': 'Germany',
    
    # France
    'EPA': 'France',
    'EURONEXT': 'France',
    'PAR': 'France',
    
    # Netherlands
    'AMS': 'Netherlands',
    
    # Italy
    'BIT': 'Italy',
    'MIL': 'Italy',
    
    # Spain
    'BME': 'Spain',
    'MCE': 'Spain',
    'MAD': 'Spain',
    
    # Switzerland
    'SIX': 'Switzerland',
    'VTX': 'Switzerland',
    
    # Nordic Countries
    'STO': 'Sweden',
    'HEL': 'Finland',
    'CPH': 'Denmark',
    'OSL': 'Norway',
    
    # Other European
    'WSE': 'Poland',
    'BUD': 'Hungary',
    'PRA': 'Czech Republic',
    'ATH': 'Greece',
    'LIS': 'Portugal',
    'BRU': 'Belgium',
    'VIE': 'Austria',
    'TAL': 'Estonia',
    'RIG': 'Latvia',
    'VSE': 'Lithuania'
}

def get_country_from_exchange(exchange: str) -> str:
    """Get country name from exchange code"""
    return EXCHANGE_COUNTRY_MAP.get(exchange, 'Unknown')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IPODataFetcher:
    """Utility class for fetching IPO data"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        
    def get_nasdaq_nyse_ipos(self, year: int = None, max_tickers: int = 80) -> List[Dict]:
        """Fetch real historical IPOs for a calendar year.

        Delegates to ``utils.ipo_scraper`` which pulls the NASDAQ IPO calendar
        (NASDAQ/NYSE/AMEX, US-focused) with a stockanalysis.com fallback, then
        enriches each ticker with yfinance (sector / market cap / performance)
        and tags country + region. Returns dicts ready for
        ``DatabaseService.insert_ipo_data``.
        """
        if year is None:
            year = self.current_year
        from .ipo_scraper import scrape_ipos
        try:
            return scrape_ipos(year, max_tickers=max_tickers)
        except Exception as e:  # noqa: BLE001
            logger.error("IPO scrape failed for %s: %s", year, e)
            return []
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """Get detailed stock information for a single ticker"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            if len(hist) == 0:
                return None
                
            current_price = hist['Close'].iloc[-1]
            
            return {
                'ticker': ticker,
                'company_name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'exchange': info.get('exchange', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'current_price': current_price,
                'volume': hist['Volume'].iloc[-1],
                'pe_ratio': info.get('trailingPE', None),
                'forward_pe': info.get('forwardPE', None),
                'price_to_book': info.get('priceToBook', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'return_on_equity': info.get('returnOnEquity', None),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {str(e)}")
            return None
    
    def calculate_performance_metrics(self, ticker: str, ipo_date: str) -> Dict:
        """Calculate various performance metrics since IPO"""
        try:
            stock = yf.Ticker(ticker)
            ipo_datetime = datetime.fromisoformat(ipo_date)
            
            # Get historical data from IPO date
            hist = stock.history(start=ipo_datetime, end=datetime.now())
            
            if len(hist) == 0:
                return {}
            
            first_price = hist['Close'].iloc[0]
            current_price = hist['Close'].iloc[-1]
            
            # Calculate various metrics
            total_return = (current_price - first_price) / first_price
            
            # Volatility (annualized)
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * (252 ** 0.5)  # Annualized
            
            # Max drawdown
            cumulative_returns = (1 + daily_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            return {
                'total_return': total_return,
                'annualized_volatility': volatility,
                'max_drawdown': max_drawdown,
                'days_since_ipo': (datetime.now().date() - ipo_datetime.date()).days,
                'high_52w': hist['High'].max(),
                'low_52w': hist['Low'].min(),
                'avg_volume': hist['Volume'].mean()
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics for {ticker}: {str(e)}")
            return {}
    
    def get_sector_performance(self, ipo_data: List[Dict]) -> Dict:
        """Calculate sector-wise performance statistics"""
        df = pd.DataFrame(ipo_data)
        
        if df.empty:
            return {}
        
        sector_stats = df.groupby('sector').agg({
            'price_change_since_ipo': ['mean', 'median', 'std', 'count'],
            'market_cap': ['sum', 'mean', 'count']
        }).round(4)
        
        return sector_stats.to_dict()
    
    def filter_by_criteria(self, ipo_data: List[Dict], 
                          min_market_cap: float = None,
                          max_market_cap: float = None,
                          sectors: List[str] = None,
                          exchanges: List[str] = None) -> List[Dict]:
        """Filter IPO data based on various criteria"""
        
        filtered_data = ipo_data.copy()
        
        if min_market_cap:
            filtered_data = [d for d in filtered_data if d['market_cap'] >= min_market_cap]
            
        if max_market_cap:
            filtered_data = [d for d in filtered_data if d['market_cap'] <= max_market_cap]
            
        if sectors:
            filtered_data = [d for d in filtered_data if d['sector'] in sectors]
            
        if exchanges:
            filtered_data = [d for d in filtered_data if d['exchange'] in exchanges]
            
        return filtered_data

# Utility functions for data processing
def format_market_cap(market_cap: float) -> str:
    """Format market cap in human readable format"""
    if market_cap >= 1e12:
        return f"${market_cap/1e12:.1f}T"
    elif market_cap >= 1e9:
        return f"${market_cap/1e9:.1f}B"
    elif market_cap >= 1e6:
        return f"${market_cap/1e6:.1f}M"
    else:
        return f"${market_cap:,.0f}"

def format_percentage(value: float) -> str:
    """Format percentage with appropriate sign and color coding"""
    return f"{value:+.2%}"

def get_color_for_performance(performance: float) -> str:
    """Get color code for performance visualization"""
    if performance > 0.1:  # > 10%
        return "#00ff00"  # Bright green
    elif performance > 0.05:  # 5-10%
        return "#90EE90"  # Light green
    elif performance > 0:  # 0-5%
        return "#FFFFE0"  # Light yellow
    elif performance > -0.05:  # 0 to -5%
        return "#FFE4B5"  # Light orange
    elif performance > -0.1:  # -5% to -10%
        return "#FFA07A"  # Light red
    else:  # < -10%
        return "#FF0000"  # Bright red
