from openai import OpenAI
import yfinance as yf
from dicttoxml import dicttoxml
import json
import openai
from fpdf  import FPDF
import html
import markdown
import requests
from bs4 import BeautifulSoup
import asyncio
import unicodedata
import smtplib
# from weasyprint import HTML
from markdown_pdf import MarkdownPdf
from email.message import EmailMessage
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import google.generativeai as genai

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

class FinancialAssistant:
    def __init__(self, gemini_api_key: str, email_config: Dict[str, str]):
        self.gemini_api_key = gemini_api_key
        self.email_config = email_config
        self.default_tickers = ["AAPL", "GOOGL", "MSFT", "AVGO", 'NVDA', 'VOO', 'VXUS']
        # Configure Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
        
    def get_stock_data(self, tickers: List[str] = None) -> List[StockData]:
        """Fetch stock data for given tickers."""
        if tickers is None:
            tickers = self.default_tickers
            
        stock_data = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                data = stock.history(period="1d")
                
                if data.empty:
                    continue
                
                last_close = data["Close"].iloc[-1]
                change = data["Close"].iloc[-1] - data["Open"].iloc[-1]
                percent_change = (change / data["Open"].iloc[-1]) * 100
            
                stock_data.append(StockData(
                    ticker=ticker,
                    last_close=float("{:.2f}".format(last_close)),
                    change=float("{:.2f}".format(change)),
                    percent_change=float("{:.2f}".format(percent_change))
                ))
            except Exception as e:
                print(f"Error fetching data for {ticker}: {str(e)}")
                continue
                
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
        # ... (keep the existing prompt structure but make it more dynamic)
        return f"""
        ## Prompt: Informe de inteligencia de mercado basado en noticias financieras actuales

Eres un asistente experto en análisis financiero y redacción de informes de inteligencia de mercado. Tu tarea es generar un informe completo y actualizado basado en noticias económicas y financieras recientes provenientes de fuentes confiables. El informe debe estar completamente redactado en **español** y estructurado como un documento **listo para imprimirse en PDF**, lo que significa que:

- No se deben utilizar viñetas, listas, tablas ni formatos estructurados.  
- Todo el contenido debe presentarse en forma de párrafos completos, con un lenguaje formal, claro y profesional.
- La narrativa debe fluir de forma coherente y estar orientada al análisis objetivo basado en datos reales.
- Esta prohibido el uso de "" o '', y por tanto de citas textuales.

### Estructura del informe:

1. **Título del informe**: Debe reflejar el enfoque principal del análisis.

2. **Resumen ejecutivo**: Una introducción breve que destaque los desarrollos económicos más importantes del momento y su relevancia para los mercados financieros globales o regionales.

3. **Eventos clave**: Descripción y análisis de entre tres y siete noticias financieras recientes que tengan impacto directo en los mercados. Para cada evento:
   - Resume el hecho principal.
   - Explica la reacción del mercado o posibles implicaciones.
   - Analiza cómo este evento afecta a sectores o empresas específicas.
   - Incluye menciones de empresas relevantes, símbolos bursátiles, movimientos en precios y cambios en la percepción del mercado.

4. **Empresas relevantes**: Selección crítica de entre tres y cinco compañías que tengan un papel significativo en el escenario económico actual, debido a su exposición a factores como inflación, tasas de interés, cambios regulatorios, conflictos geopolíticos, innovación tecnológica u otras variables macroeconómicas. Expón su situación, comportamiento reciente, decisiones estratégicas y evolución de sus acciones.

5. **Análisis macroeconómico**: Descripción de los principales factores económicos que contextualizan los eventos anteriores. Incluye comentarios sobre la política monetaria, datos de inflación, actividad económica, empleo, confianza del consumidor y otras variables clave.

6. **Perspectiva del mercado**: Conclusión con una visión a corto plazo del posible rumbo de los mercados financieros, destacando señales clave, riesgos emergentes, oportunidades potenciales y tendencias que los inversores o analistas deberían seguir.

### Fuentes de información:

A continuación, se incluirán las fuentes de información específicas que deben utilizarse como base para el contenido del informe. Solo se deben considerar artículos, datos o publicaciones provenientes de medios confiables, actualizados y con reconocimiento en el ámbito financiero.

**CNBC: {json.dumps(news_data['CNBC'], indent=4)}, Yahoo Finance: {json.dumps(news_data['Yahoo Finance'], indent=4)}**

### Consideraciones finales:

El informe debe estar redactado de manera concisa, con precisión terminológica, enfoque analítico, y sin ningún formato que impida su correcta conversión y lectura en PDF. Se debe evitar la repetición de informacion previamente dada o redundante, y todos los hechos o proyecciones deben estar respaldados por datos o por análisis provenientes de las fuentes especificadas.
    """

class PDFGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def create_report(self, content: str, filename: str = None) -> str:
        """Create a PDF report with the given content."""
        if filename is None:
            filename = f"market_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            
        pdf_path = os.path.join(self.output_dir, filename)
        
        pdf = FPDF()
        pdf.set_left_margin(20)
        pdf.set_right_margin(20)
        pdf.add_page()
        
        # Add title
        pdf.set_font("Times", "B", 24)
        pdf.cell(0, 20, "Resumen del Mercado de valores", ln=True, align="C")
        pdf.ln(10)  # Add some space after the title
        
        # Add content
        pdf.set_font("Times", "", 13)
        pdf.multi_cell(0, 5, content)
        
        pdf.output(pdf_path)
        return pdf_path

class EmailSender:
    def __init__(self, config: Dict[str, str]):
        self.config = config

    def send_report(self, pdf_path: str, subject: str, body: str) -> bool:
        """Send the report via email."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.config["sender"]
            msg["To"] = self.config["receiver"]
            msg.set_content(body)

            with open(pdf_path, "rb") as pdf_file:
                pdf_data = pdf_file.read()
                msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

            with smtplib.SMTP("smtp.office365.com", 587) as server:
                server.starttls()
                server.login(self.config["sender"], self.config["password"])
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

def main():
    # Configuration
    config = {
        "gemini_api_key": "AIzaSyBfSUsFKpSXpRR9fa04xjXTFbISbVkxTNI",  # Replace with your Gemini API key
        "email": {
            "sender": "sebastian.manco@lineadirecta.com.co",
            "password": "G3rm4ny202507..",
            "receiver": "julian.gaviria@lineadirecta.com.co"
        },
        "output_dir": "reports"
    }

    # Initialize components
    assistant = FinancialAssistant(config["gemini_api_key"], config["email"])
    pdf_generator = PDFGenerator(config["output_dir"])
    email_sender = EmailSender(config["email"])

    # Define news sources
    news_sources = [
        NewsSource("Yahoo Finance", "https://finance.yahoo.com/topic/stock-market-news/", "h3"),
        NewsSource("CNBC", "https://www.cnbc.com/markets/", "a", "Card-title")
    ]

    # Generate report
    stock_data = assistant.get_stock_data()
    summary = assistant.generate_market_summary(stock_data, news_sources)
    
    if summary:
        pdf_path = pdf_generator.create_report(summary)
        email_sender.send_report(
            pdf_path,
            "Reporte del Mercado de Valores",
            "Hola,\n\nAdjunto el archivo PDF con el resumen del mercado de valores.\n\nSaludos cordiales."
        )

if __name__ == "__main__":
    main()
