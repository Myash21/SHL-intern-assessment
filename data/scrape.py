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
import re # Import regex for cleaning test type

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

# --- Main Scraping Logic ---
def scrape_shl_table_data_selenium(catalog_url):
    """Scrapes paginated SHL assessment data using Selenium and BeautifulSoup."""
    driver = setup_driver()
    if not driver:
        return []

    assessments_data = []
    try:
        print(f"Navigating to URL: {catalog_url}")
        driver.get(catalog_url)
        wait_timeout = 30
        row_css_selector = 'div.custom__table-responsive tr[data-entity-id], div.custom__table-responsive tr[data-course-id]'

        page_number = 1
        while True:
            print(f"\n--- Scraping Page {page_number} ---")
            try:
                WebDriverWait(driver, wait_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, row_css_selector))
                )
            except Exception as e:
                print(f"Timeout on page {page_number}: {e}")
                break

            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            rows = soup.select(row_css_selector)
            print(f"Found {len(rows)} rows on page {page_number}.")

            if not rows:
                print(f"No data rows found on page {page_number}, stopping.")
                break

            for i, row in enumerate(rows):
                cells = row.find_all('td')
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
                    link_tag = name_cell.find('a')
                    if link_tag:
                        data["Assessment Name"] = link_tag.get_text(strip=True)
                        href = link_tag.get('href', '')
                        data["Assessment URL"] = BASE_URL + href if href.startswith('/') else href
                    else:
                        data["Assessment Name"] = name_cell.get_text(strip=True)

                    if cells[1].find('span', class_='catalogue__circle'):
                        data["Remote Testing Support"] = "Yes"
                    if cells[2].find('span', class_='catalogue__circle'):
                        data["Adaptive/IRT Support"] = "Yes"

                    key_spans = cells[3].find_all('span', class_='product-catalogue__key')
                    keys = [span.get_text(strip=True) for span in key_spans]
                    data["Test Type"] = "".join(keys) if keys else cells[3].get_text(strip=True)

                    if data["Assessment Name"] != "N/A":
                        assessments_data.append(data)
                except Exception as e:
                    print(f"Error parsing row {i+1} on page {page_number}: {e}")
                    continue

            # --- Pagination Logic ---
            # --- Updated Pagination Logic ---
            try:
                next_li = driver.find_element(By.CSS_SELECTOR, "li.pagination__item.-next")
                next_link = next_li.find_element(By.CSS_SELECTOR, "a.pagination__arrow")
                next_href = next_link.get_attribute("href")

                if next_href:
                    print(f"Next page URL: {next_href}")
                    driver.get(next_href)
                    time.sleep(2)
                    page_number += 1
                else:
                    print("No href found in next button. Reached last page.")
                    break
            except Exception as e:
                print("Next button not found or error while navigating:", e)
                break


    except Exception as e:
        print(f"Unexpected error during scraping: {e}")
    finally:
        if driver:
            driver.quit()

    return assessments_data

def scrape_second_table():
    driver = setup_driver()
    if not driver:
        return []

    results = []
    page_offset = 0
    items_per_page = 12  # SHL seems to paginate in 12s
    base_table_url = f"{BASE_URL}/solutions/products/product-catalog/?start={page_offset}&type=1"

    while True:
        url = f"{BASE_URL}/solutions/products/product-catalog/?start={page_offset}&type=1"
        print(f"Visiting: {url}")
        driver.get(url)
        time.sleep(2)

        # Parse table content
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select('div.custom__table-responsive tr[data-entity-id], div.custom__table-responsive tr[data-course-id]')
        print(f"Found {len(rows)} rows on this page.")

        if not rows:
            break  # Stop if no new rows found

        for i, row in enumerate(rows):
            # Same row extraction logic as before
            cells = row.find_all('td')
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
                link_tag = name_cell.find('a')
                if link_tag:
                    data["Assessment Name"] = link_tag.get_text(strip=True)
                    href = link_tag.get("href", "")
                    data["Assessment URL"] = BASE_URL + href if href.startswith('/') else href

                if cells[1].find('span', class_='catalogue__circle'):
                    data["Remote Testing Support"] = "Yes"

                if cells[2].find('span', class_='catalogue__circle'):
                    data["Adaptive/IRT Support"] = "Yes"

                key_spans = cells[3].find_all('span', class_='product-catalogue__key')
                keys = [span.get_text(strip=True) for span in key_spans]
                data["Test Type"] = "".join(keys) if keys else cells[3].get_text(strip=True)

                if data["Assessment Name"] != "N/A":
                    results.append(data)

            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                continue

        # Check for next page by checking presence of updated next link
        try:
            next_li = driver.find_element(By.CSS_SELECTOR, "li.pagination__item.-next")
            next_link = next_li.find_element(By.CSS_SELECTOR, "a.pagination__arrow")
            next_href = next_link.get_attribute("href")

            if not next_href or f"type=1" not in next_href:
                print("No more pages for table 2.")
                break

            page_offset += items_per_page

        except Exception as e:
            print("Next button not found or error while navigating:", e)
            break

    driver.quit()
    return results

# --- Execution ---
if __name__ == "__main__":
    scraped_data = scrape_shl_table_data_selenium(CATALOG_URL)

    if scraped_data:
        print(f"\nSuccessfully scraped {len(scraped_data)} assessments.")
        df = pd.DataFrame(scraped_data)
        # Reorder columns for clarity if desired
        df = df[["Assessment Name", "Assessment URL", "Remote Testing Support", "Adaptive/IRT Support", "Test Type", "Duration"]]
        print("\n--- DataFrame Output ---")
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)
        print(df)

        try:
            output_filename = "shl_table_assessments_selenium_v4.csv"
            df.to_csv(output_filename, index=False, encoding='utf-8')
            print(f"\nData saved to {output_filename}")
        except Exception as e:
            print(f"\nError saving data to CSV: {e}")
    else:
        print("\nNo assessment data was scraped. Review the logs above for errors or warnings.")