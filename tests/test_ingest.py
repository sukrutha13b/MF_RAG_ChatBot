"""
Test Ingestion Module
=====================
Validates the output of the ingestion process from Phase 3.
Ensures we can connect to Pinecone, retrieve vectors using Gemini embeddings,
and verify metadata correctness (like source_url).
"""

import os
import pytest
from dotenv import load_dotenv

try:
    from pinecone import Pinecone
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
except ImportError:
    pytest.skip("Missing dependencies for ingest testing", allow_module_level=True)

load_dotenv()

INDEX_NAME = "mf-rag-index"
EMBEDDING_MODEL = "models/gemini-embedding-001"

@pytest.fixture(scope="module")
def vector_store():
    """Initializes the vector store connection for testing."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    
    if not gemini_api_key or not pinecone_api_key:
        pytest.skip("Missing API keys for integration test")
        return None

    pc = Pinecone(api_key=pinecone_api_key)
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        pytest.skip(f"Pinecone index '{INDEX_NAME}' does not exist. Run ingest.py first.")
        return None

    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    store = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    return store

def test_pinecone_query_returns_results(vector_store):
    """Performs a dummy query and asserts we get document chunks back."""
    if not vector_store:
        pytest.skip("Vector store not initialized")
        
    query = "What is the expense ratio of Quant Small Cap?"
    docs = vector_store.similarity_search(query, k=2)
    
    assert len(docs) > 0, "Query returned no results from Pinecone"
    
def test_pinecone_metadata_contains_required_fields(vector_store):
    """Asserts that returned documents contain 'source_url' and 'last_updated' for citations."""
    if not vector_store:
        pytest.skip("Vector store not initialized")
        
    query = "Quant Mutual Funds"
    docs = vector_store.similarity_search(query, k=1)
    
    assert len(docs) > 0
    metadata = docs[0].metadata
    
    assert "source_url" in metadata, "Missing citation 'source_url' in Pinecone metadata"
    assert "last_updated" in metadata, "Missing freshness 'last_updated' in Pinecone metadata"
    assert metadata["source_url"] != "N/A", "Source URL should be a valid Groww link"
