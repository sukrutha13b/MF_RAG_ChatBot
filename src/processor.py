import os
import re
import time
from dotenv import load_dotenv

# Set this BEFORE importing pinecone to skip plugin check
os.environ["PINECONE_SKIP_PLUGIN_CHECK"] = "true"
os.environ["PINECONE_DISABLE_DEPRECATION_WARNINGS"] = "true"

from pinecone import Pinecone

try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from langchain_core.prompts import PromptTemplate
except ImportError as e:
    print(f"Missing dependency: {e}")
    exit(1)

load_dotenv()

# Constants
INDEX_NAME = "mf-rag-index"
EMBEDDING_MODEL = "models/gemini-embedding-001"
LLM_MODEL = "gemini-2.5-flash"  # Flash is fast and cheap for reasoning/RAG
# or gemini-1.5-pro

# --- Guardrails ---

def detect_pii(query: str) -> bool:
    """
    Returns True if the query appears to contain PII (like a PAN card or Aadhaar number).
    PAN format: 5 letters, 4 numbers, 1 letter.
    Aadhaar rough format: 12 digits.
    """
    # Simple PAN card regex
    if re.search(r'[A-Za-z]{5}\d{4}[A-Za-z]{1}', query):
        return True
    # Simple Aadhaar regex (12 consecutive digits, or hyphenated/spaced)
    if re.search(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', query):
        return True
    return False

def detect_investment_advice(query: str) -> bool:
    """
    Returns True if the user seems to be asking for subjective investment advice.
    """
    advice_keywords = [
        "should i invest",
        "should i buy",
        "should i sell",
        "recommend",
        "good investment",
        "where to put my money",
        "is it safe to"
    ]
    query_lower = query.lower()
    for kw in advice_keywords:
        if kw in query_lower:
            return True
    return False

# --- RAG Setup ---

def get_vector_store(max_retries=3, test_connection=False):
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY env var is missing.")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY env var is missing.")
    
    # Initialize connection
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Basic check for index existence (fast)
    if INDEX_NAME not in [idx["name"] for idx in pc.list_indexes()]:
        raise ValueError(f"Index {INDEX_NAME} not found on Pinecone.")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=EMBEDDING_MODEL,
                google_api_key=gemini_api_key,  # Explicitly pass API key
                request_options={"timeout": 60}
            )
            
            if test_connection:
                # Only test if explicitly requested (e.g., during startup)
                _ = embeddings.embed_query("test")
                
            return PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise last_error


def build_qa_prompt() -> PromptTemplate:
    """Creates a strict system prompt to ensure factual replies."""
    template = """You are a helpful and factual Mutual Funds assistant.
Use the following pieces of retrieved context to answer the user's question.

Rules:
1. If you don't know the answer based strictly on the context, just say "I don't know based on the available data." Do not try to make up an answer.
2. Keep the answer concise (maximum 3 sentences).
3. Under no circumstances should you provide investment advice.
4. If context is provided, you must append the 'source_url' from the context metadata at the end of your response, formatted as: "\n\nSource: [Link](url)"

Context:
{context}

Question: {question}

Helpful Answer:"""
    return PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )


def _is_list_all_query(query: str) -> bool:
    """
    Detects if the user is asking for a list of all funds or all items.
    These queries need to retrieve more documents (k=10) instead of default (k=3).
    """
    query_lower = query.lower()
    list_keywords = [
        "list all", "all funds", "give a list", "show all", "what are all",
        "tell me all", "list of", "all available", "minimum sip for all",
        "expense ratio of all", "aum of all", "fund manager of all"
    ]
    return any(kw in query_lower for kw in list_keywords)


def process_query(user_query: str, vectorstore=None) -> str:
    """
    Main entry point for handling a user query.
    Applies guardrails, retrieves context, and queries the LLM.
    """
    # 1. Evaluate Guardrails
    if detect_pii(user_query):
        return "I cannot process this request. PII (Personal Identifiable Information) detected."
        
    if detect_investment_advice(user_query):
        return "I am an informational bot and cannot provide subjective investment advice or recommendations."

    # 2. Retrieve Context
    if vectorstore is None:
        try:
            vectorstore = get_vector_store()
        except Exception as e:
            return f"Error connecting to vector database: {e}"

    # Determine how many documents to retrieve
    # Use k=10 for "list all" queries, k=3 for specific queries
    k_value = 10 if _is_list_all_query(user_query) else 3
    
    # Fetch relevant chunks with retry for embedding timeouts
    docs = []
    max_search_retries = 3
    for attempt in range(max_search_retries):
        try:
            docs = vectorstore.similarity_search(user_query, k=k_value)
            break
        except Exception as e:
            if "504" in str(e) or "Deadline Exceeded" in str(e):
                if attempt < max_search_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            return f"Error retrieving context: {e}"
    
    if not docs:
        return "I don't know based on the available data. (No context retrieved)"

    # Format context and extract unique sources
    context_texts = []
    sources = set()
    for doc in docs:
        context_texts.append(doc.page_content)
        url = doc.metadata.get("source_url", "N/A")
        if url != "N/A":
            sources.add(url)
            
    context_block = "\n---\n".join(context_texts)

    # 3. Generate Answer
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model=LLM_MODEL, 
        temperature=0,  # Zero temperature for maximum factual consistency
        api_key=gemini_api_key
    )
    
    prompt = build_qa_prompt()
    chain = prompt | llm
    
    response = chain.invoke({
        "context": context_block,
        "question": user_query
    })
    
    answer = response.content
    
    # 4. Enforce Source Appending if LLM missed it or failed
    if "Source:" not in answer and sources:
        sources_list = list(sources)
        if len(sources_list) == 1:
            # Single source - simple format
            answer += f"\n\nSource: [Link]({sources_list[0]})"
        else:
            # Multiple sources - list them all
            answer += "\n\nSources:\n"
            for i, source in enumerate(sources_list, 1):
                answer += f"{i}. [Link]({source})\n"

    return answer


if __name__ == "__main__":
    # Small test shell for manual verification
    print("Welcome to MF Bot (Type 'quit' to exit)")
    while True:
        q = input("\nYou: ")
        if q.lower() in ['quit', 'exit']:
            break
        ans = process_query(q)
        print(f"Bot: {ans}")
