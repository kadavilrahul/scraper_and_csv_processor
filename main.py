import os
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote_plus
import pandas as pd
import csv
import sys

# Gemini AI configuration
GEMINI_API_KEY = "AIzaSyA5bfenANZwEDV5vfSWWaFWuX4cD2ejJSQ"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

def check_keywords_file():
    """Check if Keywords.csv exists in the current directory"""
    if not os.path.exists('Keywords.csv'):
        print("Error: Keywords.csv file not found in the current directory.")
        print("Please ensure Keywords.csv is present before running the script.")
        sys.exit(1)
    return True

def generate_category_descriptions(category):
    """
    Generate short description and full description for a category using Gemini AI
    """
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': GEMINI_API_KEY
    }
    
    # Prompt for short description
    short_prompt = f"Give SEO based short description (Who needs it, features, durability, and options, highlight any additional features) in maximum five sentences. The answer should start with the short description, no comments, no suggestions, nothing except the content. Use bullet point as much as possible but not other formats. The item is - : '{category}'"
    
    # Prompt for full description
    full_prompt = f"""Give SEO based detailed description (With focus on benefits, mentioning what is it used for, all features, list key selling points like easy installation, durability, and color options etc, Include keywords: Includes relevant terms for search engine optimization, detailed specifications in bullet points, highlight any additional features. The answer should start with the description without any introduction no comments, no suggestions, nothing except the content. Use headings, bullet points and tables as much as possile. The item is - : '{category}'
    Keep it professional and informative."""
    
    try:
        # Generate short description
        short_response = requests.post(
            GEMINI_BASE_URL,
            headers=headers,
            json={
                "contents": [{"parts":[{"text": short_prompt}]}]
            }
        )
        short_response.raise_for_status()
        short_description = short_response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Generate full description
        full_response = requests.post(
            GEMINI_BASE_URL,
            headers=headers,
            json={
                "contents": [{"parts":[{"text": full_prompt}]}]
            }
        )
        full_response.raise_for_status()
        full_description = full_response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        return short_description, full_description
    except Exception as e:
        print(f"Error generating descriptions for category {category}: {e}")
        return "", ""

def process_price(price_str, price_multiplier):
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
        
        # Multiply price by the provided multiplier
        final_price = price_float * price_multiplier
        
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
                price = price.replace("$ ", "$")

                # Get the product image URL
                image_elem = listing.find("img")
                imagelink = image_elem.get('data-defer-load')

                # Get the product ID
                prdlink_elem = listing.find("a")
                prdlink = prdlink_elem.get('href')
                start_index = prdlink.find("/itm/")
                end_index = prdlink.find("?")
                prdid = str(prdlink[start_index+5:end_index])

                if "Shop on eBay" not in title:
                    items.append({
                        'title': title,
                        'prdid': prdid,
                        'price': price,
                        'imagelink': imagelink
                    })
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
        return items

def main():
    # First check if Keywords.csv exists
    check_keywords_file()
    
    # Get default values from environment variables
    default_max_results = int(os.getenv('MAX_RESULTS_PER_KEYWORD', 10))
    default_total_results = int(os.getenv('TOTAL_RESULTS', 20))
    default_price_multiplier = float(os.getenv('PRICE_MULTIPLIER', 200))

    # Prompt user for input with defaults from environment variables
    max_results_per_keyword = int(input(f"Enter the maximum number of results per keyword (default is {default_max_results}): ") or default_max_results)
    total_results_limit = int(input(f"Enter the maximum total number of results across all keywords (default is {default_total_results}): ") or default_total_results)
    price_multiplier = float(input(f"Enter the price multiplier (default is {default_price_multiplier}): ") or default_price_multiplier)

    scraper = EbayScraper()
    output_file = 'output.csv'
    
    print(f"Using max_results_per_keyword: {max_results_per_keyword}")
    print(f"Using total_results_limit: {total_results_limit}")
    print(f"Using price multiplier: {price_multiplier}")
    
    # Read Keywords.csv file
    words = pd.read_csv('Keywords.csv')
    total_results_count = 0

    # Dictionary to store category descriptions
    category_descriptions = {}

    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        csv_writer = csv.writer(outfile)
        # Write header with new column structure
        headers = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
        csv_writer.writerow(headers)

        for search_query in words["Keywords"]:
            if total_results_count >= total_results_limit:
                print(f"\nReached total results limit of {total_results_limit}. Stopping.")
                break
            
            # Generate descriptions for this category if not already generated
            if search_query not in category_descriptions:
                print(f"\nGenerating descriptions for category: {search_query}")
                short_desc, full_desc = generate_category_descriptions(search_query)
                category_descriptions[search_query] = (short_desc, full_desc)
                
            print(f"\nSearching eBay for - {search_query}")
            results = scraper.search(search_query, max_results_per_keyword)
        
            if results:
                print(f"\nFound {len(results)} results for {search_query}\n")
                for i, item in enumerate(results, 1):
                    if total_results_count >= total_results_limit:
                        break
                    
                    # Process the price using the user-specified multiplier
                    processed_price = process_price(item['price'], price_multiplier)
                    
                    # Get the cached descriptions for this category
                    short_desc, full_desc = category_descriptions[search_query]
                    
                    # Create row with new structure
                    row = [
                        item['imagelink'],          # Image
                        item['title'],              # Title
                        processed_price,            # Regular Price (processed)
                        search_query,               # Category (using the keyword)
                        short_desc,                 # Short_description
                        full_desc                   # description
                    ]
                    csv_writer.writerow(row)
                    total_results_count += 1
                    print(f"Processed item {i} of {len(results)} for {search_query}")
            else:
                print("No results found.")
        
        print(f"\nTotal results written: {total_results_count}")

if __name__ == "__main__":
    main()