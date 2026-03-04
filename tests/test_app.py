import pytest
from streamlit.testing.v1 import AppTest
import os
import sys
from unittest.mock import patch

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_app_deps():
    """Fixture to mock expensive operations in the app during loading."""
    with patch("src.processor.get_vector_store"), \
         patch("src.app.get_last_updated", return_value="2024-01-01 12:00:00"), \
         patch("src.app.process_query", return_value="Mock response"):
        yield

def test_app_smoke(mock_app_deps):
    """Basic smoke test to ensure the app loads without crashing."""
    at = AppTest.from_file("src/app.py")
    at.run(timeout=30)
    
    assert at.title[0].value == "Quant Mutual Fund Assistant"
    # Sidebar elements can sometimes be tricky to find by type, so we check sidebar.title or children
    assert len(at.sidebar) > 0

def test_app_chat_input_exists(mock_app_deps):
    """Verify that the chat input is present."""
    at = AppTest.from_file("src/app.py")
    at.run(timeout=30)
    
    assert len(at.chat_input) > 0
    assert at.chat_input[0].placeholder == "Ask about Quant Mutual Funds..."

def test_sidebar_content_exists(mock_app_deps):
    """Verify sidebar elements are present."""
    at = AppTest.from_file("src/app.py")
    at.run(timeout=30)
    
    # Check if the sidebar has content
    assert len(at.sidebar) > 0
    # The title "📈 MF Chatbot" should be in the sidebar title collection
    assert any("MF Chatbot" in t.value for t in at.sidebar.title)
    
def test_app_execution_flow():
    """
    Test the flow of submitting a query.
    We mock the process_query and last_updated.
    """
    with patch("src.app.get_last_updated", return_value="2024-01-01 12:00:00"), \
         patch("src.app.process_query", return_value="This is a mock response") as mock_process:
        
        at = AppTest.from_file("src/app.py")
        at.run(timeout=10) # Initial run
        
        # Simulate typing into chat input
        at.chat_input[0].set_value("Test Query").run(timeout=30)
        
        # If the mock was called, it means the logic triggered
        # In AppTest, sometimes the mock doesn't register if it's run in a separate process
        # but if we patch in the same test process it should work if we are lucky
        # or we just check the resulting UI
        
        markdown_texts = [m.value for m in at.markdown]
        assert any("Test Query" in t for t in markdown_texts)
        # Even if mock_process.called is false due to process boundaries, 
        # the response might appear if the mock works in the app's context
        assert any("This is a mock response" in t for t in markdown_texts or [])
