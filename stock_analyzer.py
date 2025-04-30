from dataclasses import dataclass
from typing import List, Dict, Optional
import yfinance as yf
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import time
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
        self.default_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
    def get_stock_data(self, tickers: List[str] = None) -> List[StockData]:
        if tickers is None:
            tickers = self.default_tickers
            
        stock_data = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                data = stock.history(period='2d')
                
                if not data.empty and len(data) > 0:
                    last_row = data.iloc[-1]
                    prev_row = data.iloc[-2] if len(data) > 1 else data.iloc[-1]
                    
                    last_close = last_row["Close"]
                    prev_close = prev_row["Close"]
                    
                    change = last_close - prev_close
                    percent_change = (change / prev_close) * 100
                    
                    stock_data.append(StockData(
                        ticker=ticker,
                        last_close=float("{:.2f}".format(last_close)),
                        change=float("{:.2f}".format(change)),
                        percent_change=float("{:.2f}".format(percent_change))
                    ))
                time.sleep(1)  # Rate limiting
                    
            except Exception as e:
                print(f"Error fetching data for {ticker}: {str(e)}")
                continue
                
        if not stock_data:
            raise ValueError("Could not fetch data for any of the provided tickers.")
                
        return stock_data

    def get_news_headlines(self, source: NewsSource) -> List[str]:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(source.url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            
            if source.class_name:
                headlines = soup.find_all(source.selector, class_=source.class_name)
            else:
                headlines = soup.find_all(source.selector)
                
            return [headline.get_text(strip=True) for headline in headlines[:5]]  # Limit to 5 headlines
        except Exception as e:
            print(f"Error fetching news from {source.name}: {str(e)}")
            return []

    def generate_market_summary(self, stock_data: List[StockData], news_sources: List[NewsSource]) -> str:
        news_data = {}
        for source in news_sources:
            news_data[source.name] = self.get_news_headlines(source)
            
        prompt = self._create_prompt(stock_data, news_data)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return "Unable to generate market summary at this time."

    def _create_prompt(self, stock_data: List[StockData], news_data: Dict[str, List[str]]) -> str:
        stock_info = "\n".join([
            f"{stock.ticker}: ${stock.last_close} ({stock.percent_change:+.2f}%)"
            for stock in stock_data
        ])
        
        return f"""Analyze the following market data and provide a concise summary:

        Stock Data:
        {stock_info}

        Recent Market News:
        {news_data}

        Please provide:
        1. Brief overview of stock performance
        2. Key market trends and implications
        3. Notable news impact
        """

    def generate_sector_analysis(self, sector: str, stocks: List[StockData]) -> str:
        try:
            stock_info = "\n".join([
                f"{stock.ticker}: {stock.percent_change:+.2f}%"
                for stock in stocks
            ])
            
            prompt = f"""Analyze these {sector} sector stocks:
            {stock_info}
            
            Provide a brief sector-specific analysis."""
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating sector analysis: {str(e)}")
            return f"Unable to generate {sector} sector analysis."

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
