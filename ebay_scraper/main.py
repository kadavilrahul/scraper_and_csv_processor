import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import csv
import time
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()
# Gemini AI configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    GEMINI_API_KEY = input('Please enter your GEMINI_API_KEY: ')

# Get endpoint from environment or use default
GEMINI_ENDPOINT = os.getenv('GEMINI_API_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models/')
# Ensure endpoint ends with /
if not GEMINI_ENDPOINT.endswith('/'):
    GEMINI_ENDPOINT += '/'
GEMINI_BASE_URL = f"{GEMINI_ENDPOINT}gemini-2.0-flash-exp:generateContent"

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

    prompt = f"""You're a woocommerce store owner writing concise yet informative descriptions for a product category.

Please write for the product category '{category}':
1. A short description (maximum 20 words)
2. A full description (maximum 50 words)

Format your response as:
SHORT: [your short description]
FULL: [your full description]

Make the descriptions engaging and suitable for an e-commerce website."""

    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(GEMINI_BASE_URL, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and result['candidates']:
                content = result['candidates'][0].get('content', {})
                if 'parts' in content and content['parts']:
                    text = content['parts'][0].get('text', '')
                    
                    # Parse the response
                    lines = text.strip().split('\n')
                    short_desc = ""
                    full_desc = ""
                    
                    for line in lines:
                        if line.startswith('SHORT:'):
                            short_desc = line.replace('SHORT:', '').strip()
                        elif line.startswith('FULL:'):
                            full_desc = line.replace('FULL:', '').strip()
                    
                    return short_desc, full_desc
        else:
            print(f"Gemini API error: {response.status_code}")
    except Exception as e:
        print(f"Error generating descriptions: {e}")
    
    return f"Quality {category} products", f"Discover our selection of {category} products with competitive prices and excellent quality"

def clean_price(price_str, price_multiplier):
    """
    Clean the price string and multiply by the given price multiplier
    1. Remove currency symbols ($ or £) and commas
    2. Convert to float  
    3. Multiply by the price multiplier
    4. Return as Rs (Indian Rupees)
    """
    try:
        # Remove any whitespace
        price_str = price_str.strip()
        
        # Handle variable prices like "£15.74 to £150.00" or "$15.74 to $150.00"
        if " to " in price_str:
            # Split and take the higher price
            prices = price_str.split(" to ")
            # Remove currency symbols for comparison
            price_str = max(prices, key=lambda x: float(x.replace("£", "").replace("$", "").replace(",", "")))
        
        # Remove currency symbols (£, $) and any commas
        price_float = float(price_str.replace("£", "").replace("$", "").replace(",", ""))
        
        # Multiply price by the provided multiplier to convert to Rs
        final_price = price_float * price_multiplier
        
        # Return formatted price without currency symbol
        return f"{final_price:.2f}"
    except (ValueError, AttributeError) as e:
        print(f"Error processing price {price_str}: {e}")
        return price_str  # Return original string if processing fails

class EbayScraper:
    def __init__(self):
        # Use eBay UK as it's less restrictive
        self.base_url = "https://www.ebay.co.uk/sch/i.html?_nkw={}"
        self.mobile_url = "https://m.ebay.co.uk/sch/i.html?_nkw={}&_sacat=0"
        self.session = requests.Session()
        
        # Standard browser headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session.headers.update(self.headers)

    def search(self, query, max_results_per_keyword):
        # Try eBay UK desktop version first
        desktop_results = self._try_desktop_search(query, max_results_per_keyword)
        if desktop_results:
            return desktop_results
            
        print("Desktop version failed, trying mobile version...")
        return self._try_mobile_search(query, max_results_per_keyword)
    
    def _try_desktop_search(self, query, max_results_per_keyword):
        url = self.base_url.format(quote_plus(query))
        print(f"Trying eBay UK desktop search: {url}")
        
        for attempt in range(3):
            try:
                if attempt > 0:
                    print(f"Desktop retry {attempt + 1}...")
                    time.sleep(2 * attempt)
                
                response = self.session.get(url, timeout=20)
                
                if response.status_code == 200:
                    # Check if we're blocked
                    if "Pardon Our Interruption" in response.text:
                        print("eBay UK desktop is blocking requests")
                        continue
                    return self._parse_results(response.text, max_results_per_keyword)
                else:
                    print(f"Desktop attempt {attempt + 1}: Got status {response.status_code}")
                    
            except Exception as e:
                print(f"Desktop attempt {attempt + 1} error: {e}")
                
        return []
    
    def _try_mobile_search(self, query, max_results_per_keyword):
        url = self.mobile_url.format(quote_plus(query))
        print(f"Trying mobile eBay UK search: {url}")
        
        for attempt in range(2):
            try:
                if attempt > 0:
                    print(f"Mobile retry {attempt + 1}...")
                    time.sleep(3)
                
                response = self.session.get(url, timeout=20)
                
                if response.status_code == 200:
                    return self._parse_mobile_results(response.text, max_results_per_keyword)
                else:
                    print(f"Mobile attempt {attempt + 1}: Got status {response.status_code}")
                    
            except Exception as e:
                print(f"Mobile attempt {attempt + 1} error: {e}")
                
        return []

    def _parse_mobile_results(self, html, max_results_per_keyword):
        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        print("Parsing mobile eBay results...")
        
        # Mobile eBay uses different structure
        # Try multiple selectors for mobile
        mobile_items = soup.find_all('div', class_='s-item')
        if not mobile_items:
            mobile_items = soup.find_all('div', {'data-view': 'mi:1686|iid:1'})
        if not mobile_items:
            mobile_items = soup.find_all('div', class_='item')
        
        print(f"Found {len(mobile_items)} mobile items")
        
        for item in mobile_items[:max_results_per_keyword * 2]:
            try:
                # Mobile title extraction
                title = None
                title_elem = item.find('h3')
                if not title_elem:
                    title_elem = item.find('span', class_='it-ttl')
                if not title_elem:
                    title_elem = item.find('a')
                    
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    
                if not title or len(title) < 5 or "Shop on eBay" in title:
                    continue
                
                # Mobile price extraction
                price = "N/A"
                price_elem = item.find('span', class_='notranslate')
                if not price_elem:
                    price_elem = item.find('span', string=lambda x: x and '$' in str(x) if x else False)
                if price_elem:
                    price = price_elem.get_text(strip=True)
                
                # Mobile image extraction
                imagelink = None
                img_elem = item.find('img')
                if img_elem:
                    imagelink = img_elem.get('src') or img_elem.get('data-src')
                
                # Mobile product link
                link_elem = item.find('a', href=True)
                prdid = "N/A"
                if link_elem:
                    href = link_elem.get('href', '')
                    if '/itm/' in href:
                        try:
                            start = href.find('/itm/') + 5
                            end = href.find('?', start)
                            if end == -1:
                                end = len(href)
                            prdid = href[start:end]
                        except:
                            pass
                
                items.append({
                    'title': title,
                    'prdid': prdid,
                    'price': price,
                    'imagelink': imagelink or "No image"
                })
                
                if len(items) >= max_results_per_keyword:
                    break
                    
            except Exception as e:
                print(f"Error parsing mobile item: {e}")
                continue
        
        print(f"Successfully parsed {len(items)} mobile items")
        return items

    def _parse_results(self, html, max_results_per_keyword):
        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        # Method 1: Try the current eBay structure (ul.srp-results > li)
        results_list = soup.find('ul', class_='srp-results')
        if results_list:
            # Get all li items (can be s-card or other classes)
            list_items = results_list.find_all('li', recursive=False)[:max_results_per_keyword * 2]
            print(f"Found {len(list_items)} items in results list")
            
            for item_li in list_items:
                try:
                    # Skip if it's an ad or sponsored item
                    if 'srp-river-answer' in str(item_li.get('class', [])):
                        continue
                    
                    # Find the main product link (usually has aria-label with title)
                    links = item_li.find_all('a', href=lambda x: x and '/itm/' in x if x else False)
                    
                    title = None
                    prdlink = None
                    prdid = None
                    
                    # Try to find the main product link - prioritize links with actual text content
                    for link in links:
                        link_text = link.get_text(strip=True)
                        aria_label = link.get('aria-label', '')
                        
                        # Skip image-only links and watch buttons
                        if link_text and len(link_text) > 10 and not link_text.lower().startswith('watch'):
                            # Use the text content as title
                            title = link_text
                            prdlink = link.get('href', '')
                            break
                        elif aria_label and len(aria_label) > 10 and not aria_label.lower().startswith('opens in') and not aria_label.lower().startswith('watch'):
                            # Fallback to aria-label if it has meaningful content
                            title = aria_label
                            prdlink = link.get('href', '')
                            break
                    
                    # If no aria-label, try other methods
                    if not title and links:
                        link = links[0]  # Use first link
                        prdlink = link.get('href', '')
                        
                        # Try to find title in h3 or span
                        title_elem = item_li.find('h3', class_=lambda x: x and 's-item__title' in str(x) if x else False)
                        if not title_elem:
                            title_elem = item_li.find('span', {'role': 'heading'})
                        if not title_elem:
                            title_elem = item_li.find('h3')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    
                    # Skip items starting with "watch" (these are watch buttons)
                    if title and title.startswith('watch'):
                        # Look for the actual title link
                        for link in links:
                            aria_label = link.get('aria-label', '')
                            if aria_label and not aria_label.startswith('watch'):
                                title = aria_label
                                prdlink = link.get('href', '')
                                break
                    
                    if not title or "Shop on eBay" in title:
                        continue
                    
                    # Extract product ID from link
                    if prdlink:
                        start_index = prdlink.find("/itm/")
                        end_index = prdlink.find("?")
                        if end_index == -1:
                            end_index = len(prdlink)
                        prdid = prdlink[start_index+5:end_index] if start_index != -1 else None
                    
                    # Find price within the li - look for any text with £ or $
                    price = "N/A"
                    price_elem = item_li.find('span', class_=lambda x: x and 's-item__price' in str(x) if x else False)
                    if not price_elem:
                        # Try finding any span with pound or dollar sign
                        price_spans = item_li.find_all('span', string=lambda x: x and ('£' in str(x) or '$' in str(x)) if x else False)
                        for span in price_spans:
                            text = span.get_text(strip=True)
                            if (text.startswith('£') or text.startswith('$')) and 'shipping' not in text.lower():
                                price_elem = span
                                break
                    
                    if price_elem:
                        price = price_elem.get_text(strip=True)
                    
                    # Find image within the li
                    imagelink = None
                    img_elem = item_li.find('img')
                    if img_elem:
                        imagelink = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-defer-load')
                    
                    items.append({
                        'title': title,
                        'prdid': prdid or "N/A",
                        'price': price,
                        'imagelink': imagelink or "No image"
                    })
                    
                    if len(items) >= max_results_per_keyword:
                        break
                        
                except Exception as e:
                    print(f"Error parsing list item: {e}")
                    continue
        
        # Method 2: Fallback - try old structure div.s-item__wrapper
        if not items:
            old_listings = soup.find_all('div', {'class': 's-item__wrapper'})
            if old_listings:
                print(f"Using fallback method, found {len(old_listings)} items")
                for listing in old_listings[:max_results_per_keyword]:
                    try:
                        # Extract title
                        title_elem = listing.find('div', {'class': 's-item__title'})
                        if not title_elem:
                            title_elem = listing.find('h3', {'class': 's-item__title'})
                        title = title_elem.text.strip() if title_elem else None
                        
                        if not title or "Shop on eBay" in title:
                            continue
                        
                        # Extract price
                        price_elem = listing.find('span', {'class': 's-item__price'})
                        price = price_elem.text.strip() if price_elem else "N/A"
                        price = price.replace("$ ", "$")

                        # Get the product image URL
                        image_elem = listing.find("img")
                        imagelink = image_elem.get('data-defer-load') if image_elem else None

                        # Get the product ID
                        prdlink_elem = listing.find("a")
                        prdid = None
                        if prdlink_elem:
                            prdlink = prdlink_elem.get('href')
                            if prdlink and "/itm/" in prdlink:
                                start_index = prdlink.find("/itm/")
                                end_index = prdlink.find("?")
                                if end_index == -1:
                                    end_index = len(prdlink)
                                prdid = str(prdlink[start_index+5:end_index])

                        items.append({
                            'title': title,
                            'prdid': prdid or "N/A",
                            'price': price,
                            'imagelink': imagelink or "No image"
                        })
                    except Exception as e:
                        print(f"Error parsing item (fallback): {e}")
                        continue
        
        print(f"Parsed {len(items)} items")
        return items

def main():
    # Check for Keywords.csv
    check_keywords_file()
    
    # Read keywords from CSV
    with open('Keywords.csv', 'r') as file:
        reader = csv.DictReader(file)
        keywords = [row['Keywords'].strip() for row in reader]
    
    # Filter out empty keywords
    keywords = [k for k in keywords if k]
    
    print(f"Keywords to search: {keywords}")
    
    # User inputs
    max_results_per_keyword = input("Enter the maximum number of results per keyword (default is 10): ")
    max_results_per_keyword = int(max_results_per_keyword) if max_results_per_keyword else 10
    
    total_results_limit = input("Enter the maximum total number of results across all keywords (default is 20): ")
    total_results_limit = int(total_results_limit) if total_results_limit else 20
    
    price_multiplier = input("Enter the price multiplier (default is 200.0): ")
    price_multiplier = float(price_multiplier) if price_multiplier else 200.0
    
    print(f"Using max_results_per_keyword: {max_results_per_keyword}")
    print(f"Using total_results_limit: {total_results_limit}")
    print(f"Using price multiplier: {price_multiplier}")
    
    scraper = EbayScraper()
    
    # Dictionary to store unique products (using title as key to avoid duplicates)
    unique_products = {}
    
    # Dictionary to store category descriptions
    category_descriptions = {}
    
    for keyword in keywords:
        # Generate descriptions for this category once
        if keyword not in category_descriptions:
            print(f"Generating descriptions for category: {keyword}")
            short_desc, full_desc = generate_category_descriptions(keyword)
            category_descriptions[keyword] = {
                'short': short_desc,
                'full': full_desc
            }
        
        print(f"Searching eBay for - {keyword}")
        results = scraper.search(keyword, max_results_per_keyword)
        
        if results:
            print(f"Found {len(results)} results for {keyword}")
            for item in results:
                # Use title as unique key to avoid duplicates
                unique_key = item['title']
                if unique_key not in unique_products:
                    item['category'] = keyword
                    item['short_description'] = category_descriptions[keyword]['short']
                    item['description'] = category_descriptions[keyword]['full']
                    unique_products[unique_key] = item
                    
                    # Check if we've reached the total limit
                    if len(unique_products) >= total_results_limit:
                        print(f"Reached total results limit of {total_results_limit}")
                        break
        else:
            print("No results found.")
        
        # Stop if we've reached the total limit
        if len(unique_products) >= total_results_limit:
            break
        
        # Small delay between searches
        time.sleep(1)
    
    # Write to CSV
    if unique_products:
        with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in unique_products.values():
                cleaned_price = clean_price(product['price'], price_multiplier)
                writer.writerow({
                    'Image': product['imagelink'],
                    'Title': product['title'],
                    'Regular Price': cleaned_price,
                    'Category': product['category'],
                    'Short_description': product['short_description'],
                    'description': product['description']
                })
        
        print(f"Total results written: {len(unique_products)}")
    else:
        # Still create empty CSV with headers if no results
        with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        print("Total results written: 0")

if __name__ == "__main__":
    main()