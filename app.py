from flask import Flask, render_template, request, jsonify
from stock_analyzer import StockAnalyzer, NewsSource
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Initialize the stock analyzer
analyzer = StockAnalyzer(os.getenv('GEMINI_API_KEY'))

# Define sectors and their stocks
SECTORS = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META'],
    'Financial': ['JPM', 'BAC', 'GS', 'MS'],
    'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV']
}

# Define news sources
news_sources = [
    NewsSource("Yahoo Finance", "https://finance.yahoo.com/topic/stock-market-news/", "h3"),
    NewsSource("CNBC", "https://www.cnbc.com/markets/", "a", "Card-title")
]

@app.route('/')
def index():
    return render_template('index.html', default_tickers=analyzer.default_tickers)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get tickers from the form
        tickers_input = request.form.get('tickers', '').strip()
        tickers = [ticker.strip().upper() for ticker in tickers_input.split(',')] if tickers_input else None

        # Get stock data
        stock_data = analyzer.get_stock_data(tickers)
        
        # Generate market summary
        summary = analyzer.generate_market_summary(stock_data, news_sources)

        # Generate sector-specific analysis
        sector_analysis = {}
        for sector, sector_tickers in SECTORS.items():
            # Filter the analyzed stocks that belong to this sector
            sector_stocks = [stock for stock in stock_data if stock.ticker in sector_tickers]
            if sector_stocks:
                sector_analysis[sector.lower()] = analyzer.generate_sector_analysis(sector, sector_stocks)

        return jsonify({
            'success': True,
            'stock_data': [
                {
                    'ticker': stock.ticker,
                    'last_close': stock.last_close,
                    'change': stock.change,
                    'percent_change': stock.percent_change
                }
                for stock in stock_data
            ],
            'summary': summary,
            'sector_analysis': sector_analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 