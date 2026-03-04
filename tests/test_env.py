"""
Test Environment Configuration
==============================
Validates that all required environment variables are loaded and not empty.
Part of Phase 1: Environment & Project Foundation.
"""

import os
import pytest
from dotenv import load_dotenv

# Load .env file before running tests
load_dotenv()


class TestEnvironmentVariables:
    """Test suite to verify that all required API keys are configured."""

    def test_gemini_api_key_is_set(self):
        """GEMINI_API_KEY must be present and non-empty."""
        api_key = os.getenv("GEMINI_API_KEY")
        assert api_key is not None, "GEMINI_API_KEY is not set in environment"
        assert api_key.strip() != "", "GEMINI_API_KEY is empty"
        assert api_key != "your_gemini_api_key_here", (
            "GEMINI_API_KEY still has placeholder value — update .env with a real key"
        )

    def test_pinecone_api_key_is_set(self):
        """PINECONE_API_KEY must be present and non-empty."""
        api_key = os.getenv("PINECONE_API_KEY")
        assert api_key is not None, "PINECONE_API_KEY is not set in environment"
        assert api_key.strip() != "", "PINECONE_API_KEY is empty"
        assert api_key != "your_pinecone_api_key_here", (
            "PINECONE_API_KEY still has placeholder value — update .env with a real key"
        )
