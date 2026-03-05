import json
import os
from tempfile import tempdir
from playwright.sync_api import sync_playwright

# The deployment plan lists these URIs:
URLS = [
    "https://groww.in/mutual-funds/quant-flexi-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/quant-small-cap-fund-direct-plan-growth",
    "https://groww.in/mutual-funds/quant-large-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/quant-mid-cap-fund-direct-growth",
    "https://groww.in/mutual-funds/quant-liquid-direct-plan-growth",
    "https://groww.in/mutual-funds/quant-multi-asset-allocation-fund-direct-growth",
    "https://groww.in/mutual-funds/amc/quant-mutual-funds"
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def extract_label_value(page, label_text):
    """
    Extracts the value associated with a label using DOM structure.
    Groww usually places label and value under a single parent div.
    """
    try:
        # We look for the exact or partial text match
        loc = page.locator(f"text='{label_text}'").first
        if loc.count() > 0:
            parent_text = loc.evaluate("el => el.parentElement.innerText")
            # e.g., "Expense ratio\n0.81%"
            lines = [line.strip() for line in parent_text.split("\n") if line.strip()]
            if len(lines) >= 2:
                # Value is usually the next line after the label
                for i, line in enumerate(lines):
                    if label_text.lower() in line.lower() and i + 1 < len(lines):
                        return lines[i + 1]
                return lines[-1] # fallback to last line
            
            # If not split by newline, maybe it's the exact text of a span next to it
            return parent_text.replace(label_text, "").strip()
    except Exception as e:
        print(f"  Warning: failed to extract '{label_text}': {e}")
    return "N/A"

def extract_contains_text(page, match_text):
    """Extracts the first element containing the given text."""
    try:
        loc = page.locator(f"text={match_text}").first
        if loc.count() > 0:
            return loc.inner_text().strip()
    except Exception as e:
        pass
    return "N/A"

def extract_fund_manager(page):
    """Specific extraction for fund manager block."""
    try:
        # 'Fund management' header usually precedes the manager list.
        # Find first manager name:
        loc = page.locator("text=Fund management").first
        if loc.count() > 0:
             manager_text = page.evaluate('''() => {
                 let header = Array.from(document.querySelectorAll('div, h2')).find(el => el.innerText === 'Fund management');
                 if(header && header.nextElementSibling) {
                     return header.nextElementSibling.innerText;
                 }
                 return "N/A";
             }''')
             if manager_text and manager_text != "N/A":
                 # Usually the first line of the block is initials, second is name.
                 lines = [line.strip() for line in manager_text.split("\n") if line.strip()]
                 if len(lines) > 1:
                     return lines[1] # e.g., "Sanjeev Sharma"
    except Exception as e:
        pass
    return "N/A"


def extract_holdings(page):
    """
    Extracts top holdings from the Holdings table.
    Returns a list of dictionaries with stock name, sector, and assets percentage.
    """
    holdings = []
    try:
        # Look for the Holdings section header
        holdings_header = page.locator("text=Holdings").first
        if holdings_header.count() == 0:
            return holdings
        
        # Extract holdings table data using JavaScript evaluation
        holdings_data = page.evaluate('''() => {
            const holdings = [];
            // Try to find the holdings table - usually has headers: Name, Sector, Instruments, Assets
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const headers = table.querySelectorAll('th');
                const headerTexts = Array.from(headers).map(h => h.innerText.trim());
                
                // Check if this is the holdings table
                if (headerTexts.includes('Name') && headerTexts.includes('Sector') && headerTexts.includes('Assets')) {
                    const rows = Array.from(table.querySelectorAll('tbody tr'));
                    const topRows = rows.slice(0, 10);  // Get top 10 holdings
                    for (const row of topRows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 4) {
                            holdings.push({
                                name: cells[0]?.innerText?.trim() || '',
                                sector: cells[1]?.innerText?.trim() || '',
                                instrument: cells[2]?.innerText?.trim() || '',
                                assets: cells[3]?.innerText?.trim() || ''
                            });
                        }
                    }
                    break;
                }
            }
            return holdings;
        }''')
        
        if holdings_data and len(holdings_data) > 0:
            holdings = holdings_data
    except Exception as e:
        print(f"  Warning: failed to extract holdings: {e}")
    
    return holdings


def extract_sector_allocation(page):
    """
    Extracts sector allocation data if available on the page.
    Returns a dictionary with sector names and their allocation percentages.
    """
    sectors = {}
    try:
        # Try to find sector allocation section
        sector_data = page.evaluate('''() => {
            const sectors = {};
            // Look for elements containing sector names and percentages
            const sectorElements = document.querySelectorAll('[class*="sector"], [class*="allocation"]');
            
            // Common sector keywords to look for
            const sectorKeywords = [
                'Financial', 'Technology', 'Healthcare', 'Energy', 'Consumer', 
                'Industrials', 'Materials', 'Communication', 'Utilities', 'Real Estate',
                'Services', 'Construction', 'Automobile', 'Chemicals', 'Metals',
                'Textiles', 'Capital Goods', 'Consumer Staples', 'Consumer Discretionary'
            ];
            
            // Try to extract from table or list elements
            const allText = document.body.innerText;
            for (const sector of sectorKeywords) {
                // Look for pattern like "Financial 25.5%" or "Financial: 25.5%"
                const regex = new RegExp(sector + '\\s*[:\\-]?\\s*(\\d+\\.?\\d*)\\s*%', 'i');
                const match = allText.match(regex);
                if (match) {
                    sectors[sector] = match[1] + '%';
                }
            }
            
            return sectors;
        }''')
        
        if sector_data and len(sector_data) > 0:
            sectors = sector_data
    except Exception as e:
        print(f"  Warning: failed to extract sector allocation: {e}")
    
    return sectors

def scrape_fund_page(page, url):
    """Scrapes a single mutual fund scheme page."""
    print(f"Scraping: {url}")
    page.goto(url, wait_until="networkidle")
    # Wait extra to ensure dynamic blocks (like Peer funds/Holdings) load
    page.wait_for_timeout(3000)
    
    # Extract basics
    fund_name = page.locator("h1").first.inner_text() if page.locator("h1").count() > 0 else url.split('/')[-1]
    
    # AUM / Fund Size
    aum = extract_label_value(page, "Total AUM")
    if aum == "N/A":
        aum = extract_label_value(page, "Fund size")
        
    # Launch / Inception
    inception = extract_label_value(page, "Launch Date")
    if inception == "N/A":
        inception = extract_label_value(page, "Date of Incorporation")
        
    # NAV extraction - usually displayed prominently on the page
    nav = extract_label_value(page, "NAV")
    if nav == "N/A":
        nav = extract_label_value(page, "Net Asset Value")
    
    # Extract holdings and sector allocation
    holdings = extract_holdings(page)
    sector_allocation = extract_sector_allocation(page)
    
    data = {
        "fund_name": fund_name.strip(),
        "url": url,
        "nav": nav,
        "expense_ratio": extract_label_value(page, "Expense ratio"),
        "aum": aum,
        "min_sip": extract_label_value(page, "Min. for SIP"),
        "exit_load": extract_contains_text(page, "Exit load of"),
        "inception_date": inception,
        "riskometer": extract_contains_text(page, "Risk"), # E.g., "Very High Risk"
        "fund_manager": extract_fund_manager(page),
        "category_average_returns": extract_label_value(page, "Category average"),
        "holdings": holdings,
        "sector_allocation": sector_allocation,
    }
    
    # Handle specific fields like Exit Load and Riskometer if N/A
    if data["exit_load"] == "N/A":
        # Fallback for AMC pages or variations
        data["exit_load"] = extract_label_value(page, "Exit load")
        
    if data["riskometer"] == "N/A":
         # Fallback, check if text contains "Risk" in the hero section
         hero_text = page.locator("body").inner_text()
         if "Very High Risk" in hero_text:
             data["riskometer"] = "Very High Risk"
         elif "High Risk" in hero_text:
             data["riskometer"] = "High Risk"

    return data

def scrape_amc_page(page, url):
    """Scrapes the AMC profile page. Data structure differs from scheme pages."""
    print(f"Scraping AMC Profile: {url}")
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(3000)
    
    fund_house = page.locator("h1").first.inner_text() if page.locator("h1").count() > 0 else "Quant Mutual Funds"
    
    data = {
        "fund_name": fund_house.strip(),
        "url": url,
        "description": extract_label_value(page, "About Quant Mutual Fund") # Just grabbing the next block
    }
    
    if data["description"] == "N/A":
        # If the specific label didn't work, grab the first heavy paragraph block after header
        try:
            data["description"] = page.locator("text=About").first.evaluate("el => el.parentElement.innerText")
        except:
            pass

    return data

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for url in URLS:
            try:
                if "/amc/" in url:
                    data = scrape_amc_page(page, url)
                else:
                    data = scrape_fund_page(page, url)
                
                # Create a file-system safe name
                filename = url.split('/')[-1] + ".json"
                filepath = os.path.join(DATA_DIR, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    
                print(f"  -> Saved {filename}")
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        browser.close()
        print("Scraping completed!")

if __name__ == "__main__":
    main()
