# Quant Mutual Fund RAG Chatbot

An AI-powered chatbot that provides factual insights about Quant Mutual Funds by scraping data from Groww, storing it in a Pinecone vector database, and using Google Gemini for reasoning and factual response generation.

## Features
- **Accurate Fund Data**: Scrapes expense ratios, AUM, fund managers, and more using Playwright.
- **RAG Architecture**: Uses Pinecone for similarity search and Gemini-1.5-flash for context-aware answering.
- **Safety First**: Implements guardrails for PII detection and prevents investment advice.
- **Clean UI**: Streamlit-based dashboard with chat history and data freshness indicators.

## Tech Stack
- **Languages**: Python
- **LLM**: Google Gemini
- **Vector DB**: Pinecone
- **Scraping**: Playwright
- **Frontend**: Streamlit
- **Testing**: Pytest

## Project Structure
- `src/`: Core logic (scraper, ingestion, processor, app).
- `tests/`: Automated test suites.
- `data/`: Temporary storage for scraped JSON files (ignored in Git).
- `.github/`: Daily ingestion workflows.

## Getting Started
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Configure `.env` with `GEMINI_API_KEY` and `PINECONE_API_KEY`.
4. Run the app: `streamlit run src/app.py`.
