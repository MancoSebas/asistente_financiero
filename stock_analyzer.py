from dataclasses import dataclass
from typing import List, Dict, Optional
import yfinance as yf
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import time
from random import uniform
from datetime import datetime, timedelta

@dataclass
class StockData:
    ticker: str
    last_close: float
    change: float
    percent_change: float

@dataclass
class NewsSource:
    name: str
    url: str
    selector: str
    class_name: Optional[str] = None

class StockAnalyzer:
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        # Updated default tickers with the most reliable major stocks
        self.default_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "JPM"]
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        
    def get_stock_data(self, tickers: List[str] = None) -> List[StockData]:
        """Fetch stock data for given tickers."""
        if tickers is None:
            tickers = self.default_tickers
            
        stock_data = []
        
        # Calculate dates
        end = datetime.now() - timedelta(days=1)
        if end.month < 6:
            start = end.replace(year=end.year-1, month=12+(end.month-6))
        else:
            start = end.replace(month=end.month-6)
        
        print(tickers)
        for ticker in tickers:
            try:
                # Create ticker object
                stock = yf.Ticker(ticker)
                
                try:
                    # Get data with explicit start and end dates
                    print(start, end)
                    # data = stock.history(start=start, end=end, interval='1d')
                    data = stock.history(period='3d')
                    print(data)
                    
                    if data.empty or len(data) == 0:
                        print(f"Warning: No data available for {ticker}")
                        continue

                    # Get the most recent data point
                    last_row = data.iloc[-1]
                    if len(data) > 1:
                        prev_row = data.iloc[-2]
                        last_close = last_row["Close"]
                        prev_close = prev_row["Close"]
                    else:
                        last_close = last_row["Close"]
                        prev_close = last_row["Open"]

                    change = last_close - prev_close
                    percent_change = (change / prev_close) * 100

                    stock_data.append(StockData(
                        ticker=ticker,
                        last_close=float("{:.2f}".format(last_close)),
                        change=float("{:.2f}".format(change)),
                        percent_change=float("{:.2f}".format(percent_change))
                    ))
                    
                except Exception as e:
                    print(f"Error fetching history for {ticker}: {str(e)}")
                    continue
                    
            except Exception as e:
                print(f"Error creating ticker object for {ticker}: {str(e)}")
                continue
                
        if not stock_data:
            raise ValueError("Could not fetch data for any of the provided tickers. Please try different symbols.")
                
        return stock_data

    def get_news_headlines(self, source: NewsSource) -> List[str]:
        """Fetch news headlines from a given source."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(source.url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            
            if source.class_name:
                headlines = soup.find_all(source.selector, class_=source.class_name)
            else:
                headlines = soup.find_all(source.selector)
                
            return [headline.get_text(strip=True) for headline in headlines]
        except Exception as e:
            print(f"Error fetching news from {source.name}: {str(e)}")
            return []

    def generate_market_summary(self, stock_data: List[StockData], news_sources: List[NewsSource]) -> str:
        """Generate a market summary using Gemini."""
        news_data = {}
        for source in news_sources:
            news_data[source.name] = self.get_news_headlines(source)
            
        prompt = self._create_prompt(stock_data, news_data)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating summary with Gemini: {str(e)}")
            return ""

    def _create_prompt(self, stock_data: List[StockData], news_data: Dict[str, List[str]]) -> str:
        """Create the prompt for the AI model."""
        stock_info = "\n".join([
            f"{stock.ticker}: ${stock.last_close} ({stock.percent_change:+.2f}%)"
            for stock in stock_data
        ])
        
        return f"""You are a senior financial analyst. Create a detailed yet clear market analysis based on the following data. Write in plain text with clear paragraph breaks between sections. Avoid any special formatting.

        Stock Data:
        {stock_info}

        Recent Market News:
        {news_data}

        Structure your response in the following sections, providing thorough analysis while maintaining clarity:

        1. Stock Performance Overview (1-2 paragraphs)
        - Detailed analysis of key stock movements and their significance
        - Sector-specific trends and their broader market implications
        - Performance comparison with relevant sector benchmarks
        - Notable technical indicators or price patterns

        2. Market Context (1-2 paragraphs)
        - Comprehensive current market sentiment analysis
        - Major market-moving factors and their impacts
        - Market breadth and trading volume analysis
        - Key support and resistance levels in relevant indices

        3. Economic Environment (1-2 paragraphs)
        - Detailed analysis of macroeconomic influences (inflation, interest rates, GDP)
        - Global economic conditions affecting markets
        - Central bank policies and their market impact
        - Currency movements and international trade factors

        4. News Analysis & Impact (1-2 paragraphs)
        - In-depth analysis of how recent headlines are affecting market sentiment
        - Short and medium-term implications of major news events
        - Potential policy changes or corporate actions
        - Industry-specific news impact

        5. Forward Outlook & Strategy (1-2 paragraphs)
        - Comprehensive analysis of opportunities and risks
        - Specific trends and factors to monitor
        - Sector-specific opportunities
        - Risk management considerations

        For each section:
        - Provide specific examples and data points to support your analysis
        - Include relevant quantitative and qualitative factors
        - Connect individual factors to their broader market implications
        - Maintain clear paragraph breaks between topics

        Write in a professional tone, using clear language while providing substantial analysis. Separate major sections with line breaks for readability."""

def main():
    # Configuration
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with your actual API key

    # Initialize analyzer
    analyzer = StockAnalyzer(GEMINI_API_KEY)

    # Define news sources
    news_sources = [
        NewsSource("Yahoo Finance", "https://finance.yahoo.com/topic/stock-market-news/", "h3"),
        NewsSource("CNBC", "https://www.cnbc.com/markets/", "a", "Card-title")
    ]

    # Get user input for stock tickers
    print("Enter stock tickers (comma-separated) or press Enter for default stocks:")
    user_input = input().strip()
    tickers = [ticker.strip().upper() for ticker in user_input.split(",")] if user_input else None

    # Generate report
    stock_data = analyzer.get_stock_data(tickers)
    summary = analyzer.generate_market_summary(stock_data, news_sources)
    
    print("\nStock Data:")
    for stock in stock_data:
        print(f"{stock.ticker}: ${stock.last_close} ({stock.percent_change:+.2f}%)")
    
    print("\nMarket Analysis:")
    print(summary)

if __name__ == "__main__":
    main() 