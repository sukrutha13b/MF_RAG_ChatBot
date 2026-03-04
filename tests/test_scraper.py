"""
Test Scraper Module
===================
Validates the output of the Playwright scraper from Phase 2.
Ensures JSON files exist and contain required keys.
"""

import os
import json
import pytest

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def test_data_directory_exists():
    assert os.path.exists(DATA_DIR), "Data directory does not exist"

def test_scraped_json_files_exist():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    assert len(files) > 0, "No JSON files were scraped"

def test_json_schema():
    """Verify that at least one mutual fund JSON has the expected schema."""
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and "quant-mutual-funds" not in f]
    
    if not files:
        pytest.skip("No mutual fund JSON files found to test schema")
        
    for filename in files:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Core fields that must exist
        assert "fund_name" in data
        assert "url" in data
        
        # Test that we actually scraped some values (not all N/A)
        # Even if some fail, AUM and Expense ratio almost always exist on Groww.
        assert data.get("aum") != "N/A" and data.get("aum") is not None, f"AUM missing in {filename}"
        assert data.get("expense_ratio") != "N/A" and data.get("expense_ratio") is not None, f"Expense ratio missing in {filename}"
