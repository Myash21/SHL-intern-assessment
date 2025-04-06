import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import json
import re

# --- Configuration ---
BASE_URL = "https://www.shl.com"
CATALOG_URL = f"{BASE_URL}/solutions/products/product-catalog/"

# --- Selenium Setup ---
def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    options.add_argument("window-size=1920,1080")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    try:
        print("Setting up Chrome driver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("Driver setup complete.")
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        return None

def scrape_individual_test_solutions():
    driver = setup_driver()
    if not driver:
        return []

    results = []
    page_offset = 0
    items_per_page = 12

    while True:
        url = f"{BASE_URL}/solutions/products/product-catalog/?start={page_offset}&type=1"
        print(f"\nVisiting: {url}")
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # --- Step 1: Locate Table 2 Heading ---
        heading_th = soup.find("th", string=re.compile(r"Individual Test Solutions", re.I))
        if not heading_th:
            print("Table 2 heading not found. Skipping page.")
            break

        # --- Step 2: Go to Parent Table or Section ---
        table_container = heading_th.find_parent("table") or heading_th.find_parent("div", class_="custom__table-responsive")
        if not table_container:
            print("Could not locate table container for Table 2.")
            break

        # --- Step 3: Find Relevant Rows ---
        rows = table_container.select("tr[data-entity-id], tr[data-course-id]")
        print(f"Found {len(rows)} Table 2 rows on this page.")

        if not rows:
            print("No rows found on this page. Exiting pagination loop.")
            break

        for i, row in enumerate(rows):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            data = {
                "Assessment Name": "N/A",
                "Assessment URL": None,
                "Remote Testing Support": "No",
                "Adaptive/IRT Support": "No",
                "Duration": "N/A",
                "Test Type": "N/A"
            }

            try:
                name_cell = cells[0]
                link_tag = name_cell.find("a")
                if link_tag:
                    data["Assessment Name"] = link_tag.get_text(strip=True)
                    href = link_tag.get("href", "")
                    data["Assessment URL"] = BASE_URL + href if href.startswith("/") else href
                else:
                    data["Assessment Name"] = name_cell.get_text(strip=True)

                if cells[1].find("span", class_="catalogue__circle"):
                    data["Remote Testing Support"] = "Yes"
                if cells[2].find("span", class_="catalogue__circle"):
                    data["Adaptive/IRT Support"] = "Yes"

                key_spans = cells[3].find_all("span", class_="product-catalogue__key")
                keys = [span.get_text(strip=True) for span in key_spans]
                data["Test Type"] = "".join(keys) if keys else cells[3].get_text(strip=True)

                if data["Assessment Name"] != "N/A":
                    results.append(data)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue

        # --- Step 4: Check for Pagination ---
        try:
            next_li = soup.select_one("li.pagination__item.-next a.pagination__arrow")
            if next_li and "start=" in next_li.get("href", ""):
                page_offset += items_per_page
                print("Next page detected. Moving to next offset.")
            else:
                print("No more pagination link. Done.")
                break
        except Exception as e:
            print("Error checking pagination:", e)
            break

    driver.quit()
    return results


if __name__ == "__main__":
    table2_data = scrape_individual_test_solutions()
    if table2_data:
        df = pd.DataFrame(table2_data)
        df.to_csv("shl_table2_individual_test_solutions.csv", index=False)
        print(f"\n✅ Scraped {len(df)} rows and saved to CSV.")
    else:
        print("\n⚠️ No data scraped from Table 2.")

