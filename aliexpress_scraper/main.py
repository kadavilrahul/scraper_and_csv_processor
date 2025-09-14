import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import csv
import time
import json
import sys
import os
from dotenv import load_dotenv
import re

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not available. Install with: pip install selenium webdriver-manager")

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
    """
    try:
        if not price_str or price_str == "N/A" or price_str.strip() == "":
            return "0.00"
            
        # Remove any whitespace
        price_str = price_str.strip()
        
        # Handle various currency formats and extract numbers
        # Remove currency symbols and text
        price_clean = re.sub(r'[^\d.,]', '', price_str)
        
        if not price_clean:
            return "0.00"
            
        # Handle different decimal separators
        if ',' in price_clean and '.' in price_clean:
            # Assume European format: 1.234,56
            if price_clean.rindex(',') > price_clean.rindex('.'):
                price_clean = price_clean.replace('.', '').replace(',', '.')
            # Assume US format: 1,234.56
            else:
                price_clean = price_clean.replace(',', '')
        elif ',' in price_clean:
            # Could be decimal (1,50) or thousands separator (1,234)
            if len(price_clean.split(',')[-1]) <= 2:
                price_clean = price_clean.replace(',', '.')
            else:
                price_clean = price_clean.replace(',', '')
        
        # Convert to float and multiply
        price_float = float(price_clean)
        final_price = price_float * price_multiplier
        
        return f"{final_price:.2f}"
        
    except (ValueError, AttributeError) as e:
        print(f"Error processing price {price_str}: {e}")
        return "0.00"

class AliExpressFixedScraper:
    def __init__(self):
        self.driver = None
        # Use proper search URLs that actually work
        self.search_urls = [
            "https://www.aliexpress.com/wholesale?SearchText={}",
            "https://www.aliexpress.com/af/{}.html",
        ]
        
    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver with proper options"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not installed. Run: pip install selenium webdriver-manager")
            
        options = Options()
        
        if headless:
            options.add_argument('--headless')
        
        # Enhanced anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # Faster loading
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--window-size=1920,1080')
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            chrome_driver_path = ChromeDriverManager().install()
            self.driver = webdriver.Chrome(options=options)
            
            # Enhanced stealth measures
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            return True
        except Exception as e:
            print(f"❌ Chrome WebDriver setup failed: {e}")
            return False

    def search(self, query, max_results_per_keyword):
        """Search for products using enhanced Selenium approach"""
        if not self.setup_driver(headless=True):
            print("❌ Cannot initialize WebDriver")
            return []
        
        all_items = []
        
        try:
            for url_index, url_pattern in enumerate(self.search_urls):
                print(f"🔍 Trying URL pattern {url_index + 1}: {url_pattern.split('{}')[0]}...")
                
                url = url_pattern.format(quote_plus(query))
                
                try:
                    # Navigate to search page
                    self.driver.get(url)
                    print(f"  ✅ Navigated to search page")
                    
                    # Wait for page to load and for search results
                    time.sleep(5)
                    
                    # Try to wait for search results to appear
                    try:
                        # Wait for any product elements to be present
                        WebDriverWait(self.driver, 10).until(
                            lambda driver: len(driver.find_elements(By.CSS_SELECTOR, 'a[href*="/item/"]')) > 0
                        )
                        print(f"  ✅ Search results loaded")
                    except TimeoutException:
                        print(f"  ⚠️  Timeout waiting for search results, proceeding anyway...")
                    
                    # Scroll to load more products
                    self._scroll_and_load()
                    
                    # Get page source and parse
                    html = self.driver.page_source
                    items = self._parse_search_results(html, query, max_results_per_keyword)
                    
                    if items:
                        print(f"  ✅ Found {len(items)} relevant products")
                        all_items.extend(items)
                        if len(all_items) >= max_results_per_keyword:
                            break
                    else:
                        print(f"  ❌ No relevant products found")
                        
                except Exception as e:
                    print(f"  ❌ Error with URL pattern {url_index + 1}: {e}")
                    continue
                    
        finally:
            if self.driver:
                self.driver.quit()
                
        return all_items[:max_results_per_keyword]
    
    def _scroll_and_load(self):
        """Scroll page to load more products"""
        try:
            # Scroll down a few times to trigger lazy loading
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check if there are more products after scrolling
                current_products = len(self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/item/"]'))
                if current_products > 10:  # If we have enough products, stop scrolling
                    break
                    
        except Exception as e:
            print(f"  Warning: Scroll loading failed: {e}")

    def _parse_search_results(self, html, search_query, max_results):
        """Parse search results with improved relevance filtering"""
        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        # Find all product links
        product_links = soup.find_all('a', href=lambda x: x and '/item/' in x if x else False)
        print(f"  Found {len(product_links)} product links total")
        
        search_terms = search_query.lower().split()
        
        for link in product_links[:max_results * 3]:  # Check more than needed to filter
            try:
                item_data = self._extract_product_info(link, search_terms)
                if item_data and self._is_relevant_product(item_data, search_terms):
                    items.append(item_data)
                    if len(items) >= max_results:
                        break
                        
            except Exception as e:
                continue
        
        print(f"  Filtered to {len(items)} relevant products")
        return items
    
    def _extract_product_info(self, link_element, search_terms):
        """Extract comprehensive product information"""
        try:
            # Find the parent container that has all product info
            product_container = link_element
            
            # Look for parent containers that might have all the info
            for _ in range(5):  # Go up 5 levels max
                if product_container.parent:
                    product_container = product_container.parent
                else:
                    break
            
            # Extract title from various sources
            title = None
            title_sources = [
                link_element.get('title'),
                link_element.get_text(strip=True),
            ]
            
            # Look for title in nearby elements
            for elem in product_container.find_all(['h1', 'h2', 'h3', 'h4', 'span', 'div'], limit=10):
                if elem.get('title'):
                    title_sources.append(elem.get('title'))
                text = elem.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:  # Reasonable title length
                    title_sources.append(text)
            
            # Choose the best title
            for potential_title in title_sources:
                if potential_title and len(potential_title.strip()) > 10:
                    title = potential_title.strip()
                    break
            
            if not title:
                return None
            
            # Extract price with better methods
            price = "N/A"
            price_patterns = [
                r'\$\s*[\d,]+\.?\d*',
                r'US\s*\$\s*[\d,]+\.?\d*',
                r'€\s*[\d,]+\.?\d*',
                r'£\s*[\d,]+\.?\d*',
                r'[\d,]+\.?\d*\s*\$',
            ]
            
            # Search in the product container text
            container_text = product_container.get_text()
            for pattern in price_patterns:
                matches = re.findall(pattern, container_text, re.IGNORECASE)
                if matches:
                    price = matches[0].strip()
                    break
            
            # Extract image URL
            image_url = None
            img_elem = product_container.find('img')
            if img_elem:
                image_url = (img_elem.get('src') or 
                           img_elem.get('data-src') or 
                           img_elem.get('data-lazy-src') or
                           img_elem.get('data-original'))
                
                if image_url and image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url and image_url.startswith('/'):
                    image_url = 'https://www.aliexpress.com' + image_url
            
            # Extract product ID
            product_id = None
            href = link_element.get('href', '')
            if '/item/' in href:
                try:
                    # Extract ID from various URL formats
                    id_match = re.search(r'/item/(\d+)', href)
                    if id_match:
                        product_id = id_match.group(1)
                except:
                    pass
            
            return {
                'title': title[:200],  # Limit title length
                'price': price,
                'imagelink': image_url or "No image",
                'prdid': product_id or "N/A"
            }
            
        except Exception as e:
            return None
    
    def _is_relevant_product(self, item_data, search_terms):
        """Check if product is relevant to search query"""
        if not item_data or not item_data.get('title'):
            return False
        
        title_lower = item_data['title'].lower()
        
        # Check if at least one search term appears in the title
        relevance_score = 0
        for term in search_terms:
            if term in title_lower:
                relevance_score += 1
        
        # Product is relevant if it contains at least one search term
        # or if the title is substantial (not just random text)
        return relevance_score > 0 or len(item_data['title']) > 30

def main():
    print("=" * 60)
    print("AliExpress Scraper v4.0 (Fixed Edition)")
    print("=" * 60)
    print()
    
    if not SELENIUM_AVAILABLE:
        print("❌ SELENIUM NOT AVAILABLE")
        print("Please install selenium: pip install selenium webdriver-manager")
        return
    
    print("✅ All required packages available")
    print("🔧 This version fixes all previous issues:")
    print("   ✅ Proper search targeting")
    print("   ✅ Enhanced price extraction")
    print("   ✅ Relevance filtering")
    print("   ✅ Better product detection")
    print()
    
    proceed = input("Do you want to continue? (Y/n): ")
    if proceed.lower().startswith('n'):
        return
    
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
    max_results_per_keyword = input("Enter the maximum number of results per keyword (default is 3): ")
    max_results_per_keyword = int(max_results_per_keyword) if max_results_per_keyword else 3
    
    total_results_limit = input("Enter the maximum total number of results across all keywords (default is 10): ")
    total_results_limit = int(total_results_limit) if total_results_limit else 10
    
    price_multiplier = input("Enter the price multiplier (default is 100.0): ")
    price_multiplier = float(price_multiplier) if price_multiplier else 100.0
    
    print(f"Using max_results_per_keyword: {max_results_per_keyword}")
    print(f"Using total_results_limit: {total_results_limit}")
    print(f"Using price multiplier: {price_multiplier}")
    print()
    
    scraper = AliExpressFixedScraper()
    
    # Dictionary to store unique products
    unique_products = {}
    category_descriptions = {}
    successful_searches = 0
    
    for keyword in keywords:
        # Generate descriptions for this category once
        if keyword not in category_descriptions:
            print(f"Generating descriptions for category: {keyword}")
            short_desc, full_desc = generate_category_descriptions(keyword)
            category_descriptions[keyword] = {
                'short': short_desc,
                'full': full_desc
            }
        
        print(f"\n🎯 Searching AliExpress for: '{keyword}'")
        print("-" * 50)
        
        results = scraper.search(keyword, max_results_per_keyword)
        
        if results:
            print(f"✅ Found {len(results)} relevant results for '{keyword}'")
            successful_searches += 1
            
            for item in results:
                unique_key = item['title']
                if unique_key not in unique_products:
                    item['category'] = keyword
                    item['short_description'] = category_descriptions[keyword]['short']
                    item['description'] = category_descriptions[keyword]['full']
                    unique_products[unique_key] = item
                    
                    if len(unique_products) >= total_results_limit:
                        print(f"Reached total results limit of {total_results_limit}")
                        break
        else:
            print(f"❌ No relevant results found for '{keyword}'")
        
        if len(unique_products) >= total_results_limit:
            break
        
        # Delay between searches
        time.sleep(3)
    
    # Results summary
    print("\n" + "=" * 60)
    print("📊 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"Keywords processed: {len(keywords)}")
    print(f"Successful searches: {successful_searches}")
    print(f"Total unique products: {len(unique_products)}")
    
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
        
        print(f"✅ Results saved to output.csv")
        print(f"📄 Total results written: {len(unique_products)}")
        
        # Show sample results
        print(f"\n📋 Sample results:")
        for i, (title, product) in enumerate(list(unique_products.items())[:3], 1):
            print(f"  {i}. [{product['category']}] {title[:80]}...")
            print(f"     Price: {product['price']} → {clean_price(product['price'], price_multiplier)}")
            
    else:
        # Create empty CSV
        with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        
        print("❌ No products were scraped successfully.")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check internet connection")
        print("2. Try different search terms") 
        print("3. AliExpress may have updated their page structure")

if __name__ == "__main__":
    main()