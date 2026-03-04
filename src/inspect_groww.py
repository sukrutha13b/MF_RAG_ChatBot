from playwright.sync_api import sync_playwright

url = "https://groww.in/mutual-funds/quant-small-cap-fund-direct-plan-growth"

def inspect_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(3000)
        
        # Look for the exact node holding "Expense ratio"
        # Often it's in a grid or table format: label nearby value.
        print("\n--- LOCATING BY TEXT ---")
        
        # 1. Expense ratio
        node = page.locator("text=Expense ratio").first
        if node.count() > 0:
            parent_text = node.evaluate("el => el.parentElement.innerText")
            print(f"Expense Ratio Parent Text:\n{parent_text}")
        else:
            print("Expense ratio text not found")
            
        # 2. NAV
        node = page.locator("text=NAV").first
        if node.count() > 0:
            parent_text = node.evaluate("el => el.parentElement.innerText")
            print(f"NAV Parent Text:\n{parent_text}")
            
        # 3. Fund size
        node = page.locator("text=Fund size").first
        if node.count() > 0:
            parent_text = node.evaluate("el => el.parentElement.innerText")
            print(f"Fund size Parent Text:\n{parent_text}")

        # 4. Exit load (usually contains "Exit load of")
        node = page.locator("text=Exit load of").first
        if node.count() > 0:
            text = node.evaluate("el => el.innerText")
            print(f"Exit load Text:\n{text}")
            
        # 5. AUM (alternate for fund size)
        node = page.locator("text=Total AUM").first
        if node.count() > 0:
            parent_text = node.evaluate("el => el.parentElement.innerText")
            print(f"Total AUM Parent Text:\n{parent_text}")

        browser.close()

if __name__ == "__main__":
    inspect_html()
