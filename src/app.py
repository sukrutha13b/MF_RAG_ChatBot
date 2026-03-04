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

def get_last_updated():
    """Retrieves the last updated timestamp from Pinecone metadata."""
    try:
        vectorstore = get_vector_store()
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
                response = process_query(prompt)
                st.markdown(response)
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"An error occurred: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
