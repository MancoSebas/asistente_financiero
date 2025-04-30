from flask import Flask, render_template, request, jsonify, send_file
from stock_analyzer import StockAnalyzer, NewsSource
import os
from dotenv import load_dotenv
from datetime import datetime
import tempfile
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.json
        stock_data = data.get('stock_data', [])
        summary = data.get('summary', '')

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Create the PDF document
            doc = SimpleDocTemplate(
                tmp.name,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )

            # Create styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Custom paragraph style for the summary
            summary_style = ParagraphStyle(
                'SummaryStyle',
                parent=normal_style,
                spaceBefore=12,
                spaceAfter=12,
                leading=14
            )

            # Create the document content
            content = []

            # Add title
            content.append(Paragraph("Market Analysis Report", title_style))
            content.append(Spacer(1, 20))

            # Add timestamp
            content.append(Paragraph(
                f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                normal_style
            ))
            content.append(Spacer(1, 20))

            # Add stock data section
            content.append(Paragraph("Stock Data", heading_style))
            content.append(Spacer(1, 12))

            # Create stock data table
            table_data = [['Ticker', 'Last Close', 'Change', '% Change']]
            for stock in stock_data:
                table_data.append([
                    stock['ticker'],
                    stock['last_close'],
                    stock['change'],
                    stock['percent_change']
                ])

            # Create table style
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ])

            # Create table and add to content
            table = Table(table_data)
            table.setStyle(table_style)
            content.append(table)
            content.append(Spacer(1, 20))

            # Add market analysis section
            content.append(Paragraph("Market Analysis", heading_style))
            content.append(Spacer(1, 12))

            # Split summary into paragraphs and add them
            paragraphs = summary.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    content.append(Paragraph(para.strip(), summary_style))
                    content.append(Spacer(1, 12))

            # Build the PDF document
            doc.build(content)
            
            # Return the PDF file
            return send_file(
                tmp.name,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'market_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Use environment variable for port with a default value
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 