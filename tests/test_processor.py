import pytest
from src.processor import detect_pii, detect_investment_advice, process_query

# --- Guardrail Tests ---

def test_detect_pii_pan_card():
    assert detect_pii("Can you check my PAN ABCDE1234F?") is True
    assert detect_pii("My pan is abcde1234f, what is the exit load?") is True
    
def test_detect_pii_aadhaar():
    assert detect_pii("Is 1234 5678 9012 a valid number for kyc?") is True
    assert detect_pii("1234-5678-9012 is my aadhaar") is True

def test_detect_pii_clean():
    assert detect_pii("What is the expense ratio for Quant Small Cap?") is False
    assert detect_pii("Tell me the AUM") is False

def test_detect_investment_advice_blocked():
    assert detect_investment_advice("Should I invest in Quant Small Cap?") is True
    assert detect_investment_advice("Can you recommend a good fund?") is True
    assert detect_investment_advice("Where to put my money for 5 years?") is True
    assert detect_investment_advice("Is it safe to buy this right now?") is True

def test_detect_investment_advice_clean():
    assert detect_investment_advice("What is the minimum SIP amount?") is False
    assert detect_investment_advice("Who is the fund manager?") is False
    assert detect_investment_advice("Show me the historic returns") is False

# --- Integration Tests (Requires Env Vars) ---

@pytest.mark.skipif(not pytest.importorskip("dotenv").load_dotenv(), reason="Requires .env setup")
def test_process_query_guardrail_trigger():
    # Test that guardrails intercept before LLM call
    response = process_query("Should I buy Quant Small Cap?")
    assert "cannot provide subjective investment advice" in response.lower()
    
    response2 = process_query("My PAN is ABCDE1234F, tell me about the fund")
    assert "pii" in response2.lower()

@pytest.mark.skipif(not pytest.importorskip("dotenv").load_dotenv(), reason="Requires .env setup")
def test_process_query_valid_factual():
    """
    End-to-end test of the RAG pipeline.
    Warning: This makes real API calls to Pinecone and Gemini.
    """
    response = process_query("What is the expense ratio for Quant Small Cap fund?")
    
    # Ensure it's not a guardrail rejection
    assert "advice" not in response.lower()
    assert "pii" not in response.lower()
    
    # Ensure a source link is appended somewhere
    assert "Source:" in response
    assert "groww.in" in response
