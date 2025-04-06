import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import json

# --- Configuration ---
BASE_URL = "https://www.shl.com"
CATALOG_URL = f"{BASE_URL}/solutions/products/product-catalog/"
MAX_PAGES_PER_TABLE = 15 # Limit for table 1 (~12 pages expected) + buffer

# --- Selenium Setup ---
def setup_driver():
    """Sets up the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Recommend running VISIBLE first to debug pagination
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu') # Often needed for headless mode on servers
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    options.add_argument("window-size=1920,1080")
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Suppress DevTools messages
    try:
        print("Setting up Chrome driver...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("Driver setup complete.")
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        # Add more specific error hints if common issues occur
        if "permission denied" in str(e).lower():
             print("Hint: WebDriver might lack permissions. Check file paths/permissions.")
        elif "chrome failed to start" in str(e).lower():
             print("Hint: Chrome browser might be missing, incompatible, or crashing. Check installation.")
        return None

# --- Helper: Find Specific Table Wrapper ---
def find_table_wrapper(driver, header_text):
    """Finds the table wrapper div containing the specified header text."""
    print(f"Looking for table wrapper containing header: '{header_text}'")
    try:
        # Wait for *any* table wrapper to show up first
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.custom__table-wrapper'))
        )
        # Get all wrappers
        wrappers = driver.find_elements(By.CSS_SELECTOR, 'div.custom__table-wrapper')
        # Iterate to find the one with the correct header text
        for wrapper in wrappers:
            try:
                # Check for the header text specifically within this wrapper's table header
                header_element = wrapper.find_element(By.XPATH, f".//thead/tr/th[contains(@class, 'custom__table-heading__title') and contains(normalize-space(), '{header_text}')]")
                # Use normalize-space() to handle potential extra whitespace in the header text
                print(f"Found matching wrapper for '{header_text}'.")
                return wrapper # Return the specific wrapper WebElement
            except NoSuchElementException:
                continue # This wrapper doesn't contain the header, check the next one
        # If loop finishes without finding the header
        print(f"Warning: Iterated through {len(wrappers)} wrappers, but none contained the header '{header_text}'.")
        return None
    except TimeoutException:
        print("Warning: Timed out waiting for any table wrappers (div.custom__table-wrapper) to appear on the page.")
        return None
    except Exception as e:
        # Catch other potential errors during find
        print(f"Error finding table wrapper: {e}")
        return None

# --- Helper: Parse Rows from Table Body ---
def parse_table_rows(table_body_html):
    """Parses rows from the given HTML string of a table body."""
    # Pass the HTML string to BeautifulSoup
    soup = BeautifulSoup(table_body_html, 'html.parser')
    # Select rows based on potential attributes directly from the parsed soup
    rows = soup.select('tr[data-entity-id], tr[data-course-id]')
    page_data = []

    for row in rows:
        # Find cells within each row object
        cells = row.find_all('td')
        # Ensure we have enough cells before proceeding
        if len(cells) < 4: continue # Need Name, Remote, Adaptive, Type columns

        # Initialize data dictionary for the row
        data = {
            "Assessment Name": "N/A", "Assessment URL": None,
            "Remote Testing Support": "No", "Adaptive/IRT Support": "No",
            "Test Type": "N/A", "Duration": "N/A" # Duration consistently N/A based on findings
        }

        try:
            # --- Column 1: Assessment Name and URL ---
            name_cell = cells[0]
            link_tag = name_cell.find('a') # Find link within the first cell
            if link_tag:
                data["Assessment Name"] = link_tag.get_text(strip=True) # Get text from link
                if link_tag.has_attr('href'):
                    href = link_tag['href']
                    # Construct absolute URL if relative
                    if href.startswith('/'): data["Assessment URL"] = BASE_URL + href
                    elif href.startswith('http'): data["Assessment URL"] = href
                    # else: handle potentially incomplete URLs if necessary
            else:
                # Fallback if no link tag is found
                data["Assessment Name"] = name_cell.get_text(strip=True)

            # --- Column 2: Remote Testing ---
            remote_cell = cells[1]
            # Check for the specific 'yes' indicator span
            if remote_cell.find('span', class_='catalogue__circle'):
                 data["Remote Testing Support"] = "Yes"

            # --- Column 3: Adaptive/IRT ---
            adaptive_cell = cells[2]
            if adaptive_cell.find('span', class_='catalogue__circle'):
                 data["Adaptive/IRT Support"] = "Yes"

            # --- Column 4: Test Type ---
            test_type_cell = cells[3]
            # Extract text from all key spans within the cell
            key_spans = test_type_cell.find_all('span', class_='product-catalogue__key')
            keys = [span.get_text(strip=True) for span in key_spans]
            if keys:
                data["Test Type"] = "".join(keys) # Concatenate keys like "CPAB", "K"
            else:
                # Fallback if no key spans are found
                data["Test Type"] = test_type_cell.get_text(strip=True)

            # Append data only if an assessment name was found
            if data["Assessment Name"] != "N/A":
                page_data.append(data)

        except Exception as e:
            # Log errors during cell processing but continue with other rows
            print(f"Error parsing row cells (HTML snippet: {str(row)[:100]}...): {e}")
            continue

    return page_data

# --- Main Scraping Function with Pagination ---
def scrape_paginated_table(driver, table_header_text, max_pages=MAX_PAGES_PER_TABLE):
    """Scrapes a specific table identified by its header, handling pagination."""
    all_table_data = []
    page_count = 1

    while page_count <= max_pages:
        print(f"\n--- Scraping Page {page_count} for table '{table_header_text}' ---")

        # --- Find the specific table wrapper for this section ---
        # It's crucial to re-find the wrapper on each page/interaction
        # as the DOM might change significantly after clicks.
        table_wrapper = find_table_wrapper(driver, table_header_text)
        if not table_wrapper:
            # If the wrapper isn't found after the first page, it likely means
            # the table is no longer displayed (as described by user).
            if page_count > 1:
                print(f"Table wrapper for '{table_header_text}' not found on page {page_count}. Assuming end of this table's data.")
            else:
                # If not found even on page 1, something is wrong.
                print(f"Stopping: Could not find table wrapper for '{table_header_text}' on initial page.")
            break # Exit the loop for this table

        try:
            # --- Wait for rows within this specific table wrapper ---
            # Use XPath relative to the found table_wrapper WebElement
            row_locator = (By.XPATH, ".//tbody/tr[@data-entity-id or @data-course-id]")
            print(f"Waiting for rows inside the '{table_header_text}' table wrapper...")
            # Wait up to 15 seconds for rows to appear within the specific table context
            WebDriverWait(table_wrapper, 15).until(
                EC.presence_of_element_located(row_locator),
                message=f"Timeout waiting for rows in table '{table_header_text}' on page {page_count}"
            )
            print("Table rows appear loaded.")
            time.sleep(1.5) # Increased pause for rendering stability after wait

            # --- Scrape rows from the current page ---
            try:
                # Find the tbody element within the confirmed wrapper
                tbody = table_wrapper.find_element(By.TAG_NAME, 'tbody')
                # Get the HTML content of the tbody to parse
                tbody_html = tbody.get_attribute('outerHTML')
                page_rows = parse_table_rows(tbody_html) # Pass HTML to parser
                if page_rows:
                    print(f"Scraped {len(page_rows)} rows from page {page_count}.")
                    all_table_data.extend(page_rows)
                else:
                    # Log if parsing returned no rows, might indicate unexpected HTML
                    print(f"Warning: No rows parsed by BeautifulSoup on page {page_count}, though rows were located by Selenium.")

            except StaleElementReferenceException:
                # Handle cases where the table/tbody element becomes stale after the wait
                print("StaleElementReferenceException getting table body. Page might have reloaded unexpectedly. Retrying loop.")
                time.sleep(2) # Wait before retrying
                continue # Go to the start of the while loop to re-find elements
            except Exception as parse_e:
                # Catch other errors during tbody find or parsing
                print(f"Error finding tbody or parsing rows on page {page_count}: {parse_e}")
                # Depending on the error, might want to break or continue
                break


            # --- Find Pagination Controls (Improved Logic) ---
            pagination_ul = None
            print("Attempting to find pagination controls...")
            try:
                # Method 1: Try finding as direct following sibling (often correct)
                pagination_ul = table_wrapper.find_element(By.XPATH, "./following-sibling::ul[contains(@class, 'pagination')]")
                print("Found pagination controls via following-sibling.")
            except NoSuchElementException:
                print("Pagination not found as direct sibling.")
                try:
                     # Method 2: Try finding within the parent of the wrapper
                     parent = table_wrapper.find_element(By.XPATH, "./parent::*")
                     # Wait briefly for pagination potentially within parent
                     WebDriverWait(parent, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.pagination")))
                     pagination_ul = parent.find_element(By.CSS_SELECTOR, 'ul.pagination')
                     print("Found pagination controls within parent element.")
                except (NoSuchElementException, TimeoutException):
                    print("Pagination not found within parent.")
                    try:
                        # Method 3: Last resort - find the first on the page
                        pagination_ul = driver.find_element(By.CSS_SELECTOR, 'ul.pagination')
                        print("Found first 'ul.pagination' on page as fallback.")
                    except NoSuchElementException:
                         # If no pagination is found using any method, assume it's the end
                         print(f"Warning: Could not find pagination controls using any method on page {page_count}. Assuming single page or end.")
                         break # Exit the while loop

            # --- Find and Check "Next" Button within the located Pagination UL ---
            try:
                # Wait for the 'next' list item to be present within the pagination_ul
                next_li_locator = (By.CSS_SELECTOR, 'li.pagination__item--arrow-next')
                WebDriverWait(pagination_ul, 5).until(EC.presence_of_element_located(next_li_locator))
                # Find the list item itself
                next_li = pagination_ul.find_element(By.CSS_SELECTOR, 'li.pagination__item--arrow-next')

                # Check if the list item has the 'disabled' class attribute
                li_classes = next_li.get_attribute('class') or ""
                if 'disabled' in li_classes:
                    print("Next button's parent li has 'disabled' class. Reached the last page.")
                    break # Exit loop, last page reached
                else:
                    # If not disabled, find the clickable 'a' tag inside
                    try:
                       # Use the selector from the latest image
                       next_button_link = next_li.find_element(By.CSS_SELECTOR, 'a.pagination_arrow')
                       print("Found active Next button link.")
                    except NoSuchElementException:
                       # If the 'li' is present but the 'a' tag isn't, treat as end/disabled
                       print("Next button li found, but no active link (a.pagination_arrow) inside. Assuming last page.")
                       break # Exit loop
            except (NoSuchElementException, TimeoutException):
                # If the 'next' list item itself isn't found after waiting
                print(f"Could not find or wait for Next button li ('li.pagination__item--arrow-next') within pagination controls. Assuming last page.")
                break # Exit loop

            # --- Click "Next" ---
            try:
                print("Attempting to click Next button link...")
                # Scroll element into view for interaction
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});", next_button_link)
                time.sleep(0.5) # Brief pause after scroll
                # Use JavaScript click for reliability
                driver.execute_script("arguments[0].click();", next_button_link)
                print("Clicked Next button link via JavaScript.")
                page_count += 1 # Increment page counter only after successful click
                print("Waiting for page transition/content update...")
                # Increased wait time as page might reload/re-render significantly
                time.sleep(5) # Adjust sleep time as needed

            except Exception as e:
                # Catch potential errors during scroll or click
                print(f"Error clicking Next button: {e}. Stopping pagination.")
                break # Exit loop if click fails

        except TimeoutException as e:
            # Catch timeouts during waits for rows
            print(f"Timeout waiting for table rows on page {page_count}: {e}. Stopping pagination.")
            break
        except StaleElementReferenceException as e:
             # Catch stale elements, often happens if page reloads during processing
             print(f"StaleElementReferenceException occurred on page {page_count}. Retrying loop. ({e})")
             time.sleep(2) # Wait before retrying the loop
             continue # Go back to the start of the while loop
        except Exception as e:
            # Catch any other unexpected errors during page processing
            print(f"An unexpected error occurred processing page {page_count} for table '{table_header_text}': {e}")
            break # Exit loop on other errors

    # Loop finished or broke
    print(f"\nFinished scraping table '{table_header_text}'. Total pages processed: {max(0, page_count-1)}. Total rows found: {len(all_table_data)}.")
    return all_table_data


# --- Main Execution ---
if __name__ == "__main__":
    driver = setup_driver()
    all_data = [] # Initialize list to store results

    if driver:
        try:
            # --- Optional: Clear Cookies ---
            # print("Navigating to base domain to clear cookies...")
            # driver.get(BASE_URL + "/solutions") # Navigate to a page on the domain
            # time.sleep(1)
            # driver.delete_all_cookies()
            # print("Cookies cleared.")
            # time.sleep(1)

            # --- Navigate to Target URL ---
            driver.get(CATALOG_URL)
            print(f"Navigating to {CATALOG_URL}")
            print("Waiting for initial page load and presence of a table wrapper...")
            # Wait for *any* table wrapper to ensure page basics are loaded
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.custom__table-wrapper')),
                message="Timeout waiting for initial table wrapper on page load."
            )
            print("Initial page appears loaded.")
            time.sleep(2) # Extra pause for any JS adjustments

            # --- Scrape Table 1 only ---
            # Define the specific header text for the first table
            table1_header = "Pre-packaged Job Solutions"
            table1_data = scrape_paginated_table(driver, table1_header)
            if table1_data:
                all_data.extend(table1_data) # Add results to the main list

            # --- (Scraping for Table 2 is intentionally omitted as requested) ---

        except Exception as e:
            # Catch any exceptions during the overall process
            print(f"An overall error occurred during execution: {e}")
        finally:
            # Ensure the browser is closed regardless of errors
            if driver:
                print("Closing the browser...")
                driver.quit()

    # --- Process and Save Final Results ---
    if all_data:
        print(f"\nSuccessfully scraped a total of {len(all_data)} assessments from table '{table1_header}'.")
        # Create DataFrame from the collected data
        df = pd.DataFrame(all_data)
        # Ensure desired column order and fill missing values just in case
        df = df.reindex(columns=["Assessment Name", "Assessment URL", "Remote Testing Support", "Adaptive/IRT Support", "Test Type", "Duration"], fill_value="N/A")
        print("\n--- Final DataFrame Output (Sample) ---")
        print(df.head()) # Display the first few rows

        try:
            # Save the DataFrame to a CSV file
            output_filename = "shl_prepackaged_solutions_paginated.csv" # Specific filename
            df.to_csv(output_filename, index=False, encoding='utf-8')
            print(f"\nTable data saved to {output_filename}")
        except Exception as e:
            # Handle potential errors during file saving
            print(f"\nError saving final data to CSV: {e}")
    else:
        # Message if no data was collected
        print(f"\nNo assessment data was scraped for table '{table1_header}'. Check logs for specific errors.")