import streamlit as st
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add src to path if needed for local development
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.processor import process_query, get_vector_store

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Quant Mutual Fund Assistant",
    page_icon="📈",
    layout="centered"
)

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stChatMessage.user {
        background-color: #f0f2f6;
    }
    .stChatMessage.assistant {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_cached_vector_store():
    """Caches the vector store connection."""
    return get_vector_store()

@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes to show fresh updates
def get_last_updated():
    """Retrieves and caches the last updated timestamp from Pinecone metadata."""
    try:
        vectorstore = get_cached_vector_store()
        # Querying for a common term to get some metadata
        results = vectorstore.similarity_search("Quant", k=1)
        if results:
            timestamp = results[0].metadata.get("last_updated", "Unknown")
            return timestamp
    except Exception as e:
        return f"Error: {e}"
    return "N/A"

# Sidebar
with st.sidebar:
    st.title("📈 MF Chatbot")
    st.markdown("---")
    st.markdown("### Bot Info")
    st.info("I'm an AI assistant trained on Quant Mutual Fund data from Groww. I can answer questions about expense ratios, fund managers, AUM, and more.")
    
    last_updated = get_last_updated()
    st.markdown(f"**Data Freshness:**")
    st.code(last_updated)
    
    # Debug mode toggle
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    debug_mode = st.checkbox("Debug Mode", value=st.session_state.debug_mode)
    st.session_state.debug_mode = debug_mode
    
    st.markdown("---")
    st.markdown("### Guardrails")
    st.warning("• No PII (PAN/Aadhaar)\n• No Investment Advice")
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Main UI
st.title("Quant Mutual Fund Assistant")
st.subheader("Factual insights from the latest fund data")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about Quant Mutual Funds..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data..."):
            try:
                # Use cached vector store to speed up response
                vectorstore = get_cached_vector_store()
                
                # Debug mode: show retrieved context
                if st.session_state.get("debug_mode", False):
                    docs = vectorstore.similarity_search(prompt, k=3)
                    st.write("**Debug - Retrieved Context:**")
                    for i, doc in enumerate(docs, 1):
                        st.write(f"{i}. {doc.metadata.get('fund_name', 'Unknown')} - {doc.page_content[:150]}...")
                
                response = process_query(prompt, vectorstore=vectorstore)
                st.markdown(response)
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                import traceback
                error_msg = f"An error occurred: {e}\n\n{traceback.format_exc()}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": f"An error occurred: {e}"})
