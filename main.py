import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote_plus
import pandas as pd
import csv
import os

# Default values
MAX_RESULTS_PER_KEYWORD = 10
TOTAL_RESULTS = 20
PRICE_MULTIPLIER = 200  # Default price multiplier

def process_price(price_str):
    """
    Process price string to:
    1. Handle variable prices (take the higher value)
    2. Remove $ sign
    3. Multiply by the price multiplier
    """
    try:
        # Remove any whitespace
        price_str = price_str.strip()
        
        # Handle variable prices like "$15.74 to $150.00"
        if " to " in price_str:
            # Split and take the higher price
            prices = price_str.split(" to ")
            price_str = max(prices, key=lambda x: float(x.replace("$", "").replace(",", "")))
        
        # Remove $ sign and any commas
        price_float = float(price_str.replace("$", "").replace(",", ""))
        
        # Get multiplier from environment variable or use default
        multiplier = float(os.getenv('PRICE_MULTIPLIER', PRICE_MULTIPLIER))
        
        # Multiply price
        final_price = price_float * multiplier
        
        # Return formatted price without $ sign
        return f"{final_price:.2f}"
    except (ValueError, AttributeError) as e:
        print(f"Error processing price {price_str}: {e}")
        return price_str  # Return original string if processing fails

class EbayScraper:
    def __init__(self):
        self.base_url = "https://www.ebay.com/sch/i.html?_nkw={}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search(self, query, max_results_per_keyword):
        url = self.base_url.format(quote_plus(query))
        try:
            response = requests.get(url)
            response.raise_for_status()
            return self._parse_results(response.text, max_results_per_keyword)
        except requests.RequestException as e:
            print(f"Error fetching results: {e}")
            return []

    def _parse_results(self, html, max_results_per_keyword):

        if "s-item__image-img" in html: print("YES")

        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        # Find all product listings
        listings = soup.find_all('div', {'class': 's-item__wrapper'})
        
        for listing in listings[:max_results_per_keyword]:
            try:
                # Extract title
                title = listing.find('div', {'class': 's-item__title'}).text.strip()
                
                # Extract price
                price_elem = listing.find('span', {'class': 's-item__price'})
                price = price_elem.text.strip() if price_elem else "N/A"
                #price = price.replace("NT", "")
                price = price.replace("$ ", "$")

                # Get the product image URL
                image_elem = listing.find("img")
                imagelink = image_elem.get('data-defer-load')#.replace("s-l140", "s-l500")
                #print(new_text)

                # Get the product product Id
                prdlink_elem = listing.find("a")
                prdlink = prdlink_elem.get('href')
                start_index = prdlink.find("/itm/")
                end_index = prdlink.find("?")
                prdid = str(prdlink[start_index+5:end_index])
                #print(prdlink)
                #print(prdid)

                if "Shop on eBay" not in title:
                  items.append({
                      'title': title,
                      'prdid': prdid,
                      'price': price,
                      'imagelink': imagelink
                  })
                #print(items);
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
        return items

def main():
    scraper = EbayScraper()
    output_file = 'output.csv'

    # Get limits from environment variables or use defaults
    max_results_per_keyword = int(os.getenv('MAX_RESULTS_PER_KEYWORD', MAX_RESULTS_PER_KEYWORD))
    total_results_limit = int(os.getenv('TOTAL_RESULTS', TOTAL_RESULTS))
    
    print(f"Using max_results_per_keyword: {max_results_per_keyword}")
    print(f"Using total_results_limit: {total_results_limit}")
    print(f"Using price multiplier: {float(os.getenv('PRICE_MULTIPLIER', PRICE_MULTIPLIER))}")
    
    # Read Keywords.csv file
    words = pd.read_csv('Keywords.csv')
    total_results_count = 0

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        csv_writer = csv.writer(outfile)
        # Write header with new column structure
        headers = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
        csv_writer.writerow(headers)

        for search_query in words["Keywords"]:
            if total_results_count >= total_results_limit:
                print(f"\nReached total results limit of {total_results_limit}. Stopping.")
                break
                
            print(f"\nSearching eBay for - {search_query}")
            results = scraper.search(search_query, max_results_per_keyword)
        
            if results:
                print(f"\nFound {len(results)} results for {search_query}\n")
                for i, item in enumerate(results, 1):
                    if total_results_count >= total_results_limit:
                        break
                    # Process the price before writing to CSV
                    processed_price = process_price(item['price'])
                    # Create row with new structure
                    row = [
                        item['imagelink'],          # Image
                        item['title'],              # Title
                        processed_price,            # Regular Price (processed)
                        search_query,               # Category (using the keyword)
                        '',                         # Short_description (empty for now)
                        ''                          # description (empty for now)
                    ]
                    csv_writer.writerow(row)
                    total_results_count += 1
            else:
                print("No results found.")
        
        print(f"\nTotal results written: {total_results_count}")

if __name__ == "__main__":
    main()
