import os
import re
from dotenv import load_dotenv

# Try importing LangChain components, with a fallback
try:
    from pinecone import Pinecone
except ImportError:
    # Fallback for older pinecone-client package
    import pinecone
    Pinecone = pinecone.Pinecone

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

def get_vector_store():
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY env var is missing.")
    
    # Initialize connection
    pc = Pinecone(api_key=pinecone_api_key)
    if INDEX_NAME not in [idx["name"] for idx in pc.list_indexes()]:
        raise ValueError(f"Index {INDEX_NAME} not found on Pinecone.")
        
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
    return PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)


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


def process_query(user_query: str) -> str:
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
    try:
        vectorstore = get_vector_store()
    except Exception as e:
        return f"Error connecting to vector database: {e}"

    # Fetch top 3 relevant chunks
    docs = vectorstore.similarity_search(user_query, k=3)
    
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
        # Just grab the first primary source URL for simplicity
        primary_source = list(sources)[0]
        answer += f"\n\nSource: [Link]({primary_source})"

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
