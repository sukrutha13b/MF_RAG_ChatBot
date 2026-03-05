import os
import json
import time
from dotenv import load_dotenv

# Provide a fallback if user is running this directly without pip installing the module properly
try:
    from pinecone import Pinecone, ServerlessSpec
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install langchain-google-genai langchain-pinecone pinecone-client")
    exit(1)

# Load environment variables
load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INDEX_NAME = "mf-rag-index"
EMBEDDING_MODEL = "models/gemini-embedding-001"

def _format_fund_data_as_text(data):
    """
    Converts the structured JSON into a rich, dense text block for optimal embedding.
    We inject the fund name repeatedly so the vector strongly associates with it.
    """
    fund_name = data.get("fund_name", "Unknown Fund")
    
    if "description" in data:
        # AMC layout
        return f"{fund_name} is a Mutual Fund AMC. Description: {data.get('description', '')}"
    
    # Scheme layout
    lines = [
        f"The Mutual Fund scheme is called {fund_name}.",
        f"The NAV (Net Asset Value) of {fund_name} is {data.get('nav', 'N/A')}.",
        f"The Expense Ratio of {fund_name} is {data.get('expense_ratio', 'N/A')}.",
        f"The Total Assets Under Management (AUM) or Fund Size of {fund_name} is {data.get('aum', 'N/A')}.",
        f"The Minimum SIP amount for {fund_name} is {data.get('min_sip', 'N/A')}.",
        f"The Exit Load for {fund_name} is: {data.get('exit_load', 'N/A')}.",
        f"The Inception Date or Launch Date of {fund_name} is {data.get('inception_date', 'N/A')}.",
        f"The Riskometer rating for {fund_name} is {data.get('riskometer', 'N/A')}.",
        f"The Fund Manager for {fund_name} is {data.get('fund_manager', 'N/A')}."
    ]
    
    # Add top holdings information
    holdings = data.get("holdings", [])
    if holdings and len(holdings) > 0:
        lines.append(f"The Top Holdings of {fund_name} are:")
        for i, holding in enumerate(holdings[:5], 1):  # Top 5 holdings
            name = holding.get('name', 'N/A')
            sector = holding.get('sector', 'N/A')
            assets = holding.get('assets', 'N/A')
            lines.append(f"  {i}. {name} ({sector}) - {assets} of assets")
    
    # Add sector allocation information
    sector_allocation = data.get("sector_allocation", {})
    if sector_allocation and len(sector_allocation) > 0:
        lines.append(f"The Sector Allocation for {fund_name} is:")
        for sector, allocation in sector_allocation.items():
            lines.append(f"  {sector}: {allocation}")
    
    return " ".join(lines)


def run_ingestion():
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")

    if not gemini_api_key or not pinecone_api_key:
        print("ERROR: GEMINI_API_KEY and PINECONE_API_KEY must be set in .env")
        return

    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=pinecone_api_key)

    # Check if index exists, create if not
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Index '{INDEX_NAME}' not found. Creating it ...")
        # Google's gemini-embedding-001 outputs 3072 dimensions
        pc.create_index(
            name=INDEX_NAME,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            print("  Waiting for index to be ready...")
            time.sleep(2)
        print("Index created successfully.")
    else:
        print(f"Index '{INDEX_NAME}' already exists.")

    print("Initializing Google Generative AI Embeddings...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    
    print("Loading data files...")
    if not os.path.exists(DATA_DIR):
        print(f"Data directory {DATA_DIR} not found. Run scraper first.")
        return

    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    
    texts = []
    metadatas = []
    ids = []
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")

    for filename in json_files:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        text_chunk = _format_fund_data_as_text(data)
        
        # We use a slugified fund_name as the Pinecone vector ID to overwrite daily
        # rather than append duplicates
        fund_name = data.get("fund_name", filename)
        vector_id = fund_name.lower().replace(" ", "-").replace("/", "-")
        
        texts.append(text_chunk)
        ids.append(vector_id)
        
        metadatas.append({
            "source_url": data.get("url", "N/A"),
            "fund_name": fund_name,
            "last_updated": current_time,
            "filename": filename
        })
        print(f"  Prepared: {fund_name}")

    if not texts:
        print("No valid JSON data to ingest.")
        return

    print(f"Upserting {len(texts)} documents to Pinecone index '{INDEX_NAME}'...")
    
    # Using Langchain's Pinecone wrapper to automatically embed and upsert
    vectorstore = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings
    )
    
    # Overwrites existing vectors with the same ID
    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    
    print("Ingestion complete!")

if __name__ == "__main__":
    run_ingestion()
