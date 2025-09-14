import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import csv
import time
import json
import sys
import os
from dotenv import load_dotenv

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
        # Remove any whitespace
        price_str = price_str.strip()
        
        # Handle variable prices like "$15.74 - $150.00" or "US $15.74 - US $150.00"
        if " - " in price_str or " to " in price_str:
            # Split and take the higher price
            separator = " - " if " - " in price_str else " to "
            prices = price_str.split(separator)
            price_str = max(prices, key=lambda x: float(x.replace("US $", "").replace("$", "").replace(",", "")))
        
        # Remove US $, $ sign and any commas
        price_float = float(price_str.replace("US $", "").replace("$", "").replace(",", ""))
        
        # Multiply price by the provided multiplier
        final_price = price_float * price_multiplier
        
        # Return formatted price without $ sign
        return f"{final_price:.2f}"
    except (ValueError, AttributeError) as e:
        print(f"Error processing price {price_str}: {e}")
        return price_str  # Return original string if processing fails

class AliExpressSeleniumScraper:
    def __init__(self):
        self.driver = None
        self.search_urls = [
            "https://www.aliexpress.com/w/wholesale-{}.html",
            "https://best.aliexpress.com/?SearchText={}",
        ]
        
    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver with anti-detection options"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is not installed. Run: pip install selenium")
            
        options = Options()
        
        if headless:
            options.add_argument('--headless')
        
        # Anti-detection options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Use webdriver-manager to automatically handle ChromeDriver
            from webdriver_manager.chrome import ChromeDriverManager
            chrome_driver_path = ChromeDriverManager().install()
            self.driver = webdriver.Chrome(options=options)
            # Execute script to hide automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            print(f"❌ Chrome WebDriver setup failed: {e}")
            print("💡 Error details:", str(e))
            return False

    def search(self, query, max_results_per_keyword):
        """Search for products using Selenium"""
        if not self.setup_driver(headless=True):
            print("❌ Cannot initialize WebDriver. Falling back to basic scraping...")
            return self._fallback_search(query, max_results_per_keyword)
        
        all_items = []
        
        try:
            for url_pattern in self.search_urls:
                print(f"🔍 Trying: {url_pattern.split('{}')[0]}...")
                
                url = url_pattern.format(quote_plus(query))
                
                try:
                    self.driver.get(url)
                    print(f"  ✅ Page loaded, waiting for content...")
                    
                    # Wait for page to load
                    time.sleep(3)
                    
                    # Try to scroll to load more content
                    self._scroll_and_load()
                    
                    # Get page source and parse
                    html = self.driver.page_source
                    items = self._parse_selenium_results(html, max_results_per_keyword)
                    
                    if items:
                        print(f"  ✅ Found {len(items)} products with Selenium")
                        all_items.extend(items)
                        if len(all_items) >= max_results_per_keyword:
                            break
                    else:
                        print(f"  ❌ No products found with this URL")
                        
                except Exception as e:
                    print(f"  ❌ Error with URL: {e}")
                    continue
                    
        finally:
            if self.driver:
                self.driver.quit()
                
        return all_items[:max_results_per_keyword]
    
    def _scroll_and_load(self):
        """Scroll page to load dynamic content"""
        try:
            # Scroll down multiple times to load content
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Try to click "load more" buttons if they exist
                try:
                    load_more_button = self.driver.find_element(By.CLASS_NAME, 'more-to-love--action--2gSTocC')
                    if load_more_button.is_displayed():
                        load_more_button.click()
                        time.sleep(2)
                except:
                    pass  # Button not found, continue
                    
        except Exception as e:
            print(f"  Warning: Scroll loading failed: {e}")

    def _parse_selenium_results(self, html, max_results):
        """Parse results from Selenium-rendered HTML"""
        soup = BeautifulSoup(html, 'lxml')
        items = []
        
        # Multiple selectors based on different AliExpress layouts
        selectors = [
            'div.recommend-card--card-wrap--2jjBf6S',  # From reference scraper
            'div[data-widget-cid="widget-common-recommend"]',
            'div.gallery-layout-list-item',
            'div.product-item',
            'a[href*="/item/"]'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                print(f"  Selector '{selector}': found {len(elements)} elements")
                
                if elements:
                    for element in elements[:max_results * 2]:
                        try:
                            item = self._extract_product_data(element)
                            if item and item['title']:
                                items.append(item)
                                if len(items) >= max_results:
                                    break
                        except Exception as e:
                            continue
                    
                    if items:
                        break  # Found products with this selector
                        
            except Exception as e:
                continue
        
        return items[:max_results]
    
    def _extract_product_data(self, element):
        """Extract product data from an element"""
        try:
            title = None
            price = "N/A"
            image = None
            product_id = None
            
            # Extract title - multiple methods
            title_selectors = [
                'div[style*="font-size: 14px"]',  # Reference scraper style
                'h3', 'h4', 'span[title]', 'a[title]'
            ]
            
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get('title') or title_elem.get_text(strip=True)
                    if title and len(title) > 10:
                        break
            
            # Extract price
            price_selectors = [
                'span.rc-modules--price--1NNLjth',  # Reference scraper
                'span[class*="price"]',
                'div[class*="price"]'
            ]
            
            for selector in price_selectors:
                price_elem = element.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if '$' in price_text:
                        price = price_text
                        break
            
            # Extract image
            img_elem = element.select_one('img')
            if img_elem:
                image = img_elem.get('src') or img_elem.get('data-src')
                if image and image.startswith('//'):
                    image = 'https:' + image
            
            # Extract product ID from any links
            link_elem = element.select_one('a[href*="/item/"]')
            if link_elem:
                href = link_elem.get('href', '')
                if '/item/' in href:
                    try:
                        product_id = href.split('/item/')[-1].split('.')[0].split('?')[0]
                    except:
                        pass
            
            if title and len(title.strip()) > 5:
                return {
                    'title': title[:150],
                    'price': price,
                    'imagelink': image or "No image",
                    'prdid': product_id or "N/A"
                }
                
        except Exception as e:
            pass
            
        return None

    def _fallback_search(self, query, max_results):
        """Fallback to requests-based search if Selenium fails"""
        print("🔄 Using fallback method with requests...")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        for url_pattern in self.search_urls:
            try:
                url = url_pattern.format(quote_plus(query))
                response = session.get(url, timeout=15)
                
                if response.status_code == 200 and len(response.text) > 5000:
                    soup = BeautifulSoup(response.text, 'lxml')
                    # Simple fallback parsing
                    links = soup.find_all('a', href=lambda x: x and '/item/' in x if x else False)
                    
                    items = []
                    for link in links[:max_results]:
                        title = link.get_text(strip=True) or link.get('title', '')
                        if title and len(title) > 10:
                            items.append({
                                'title': title[:150],
                                'price': "N/A",
                                'imagelink': "No image",
                                'prdid': "N/A"
                            })
                    
                    if items:
                        print(f"  ✅ Fallback found {len(items)} items")
                        return items
                        
            except Exception as e:
                continue
        
        return []

def main():
    print("=" * 60)
    print("AliExpress Scraper v3.0 (Selenium Edition)")
    print("=" * 60)
    print()
    
    if not SELENIUM_AVAILABLE:
        print("❌ SELENIUM NOT AVAILABLE")
        print("Please install selenium: pip install selenium")
        print("And install ChromeDriver for your Chrome version")
        print()
        proceed = input("Continue with limited functionality? (y/N): ")
        if not proceed.lower().startswith('y'):
            return
    else:
        print("✅ Selenium WebDriver available")
    
    print()
    print("📋 This scraper uses browser automation to bypass AliExpress anti-bot protection")
    print("⚠️  Note: Requires ChromeDriver to be installed and in PATH")
    print()
    
    proceed = input("Do you want to continue? (Y/n): ")
    if proceed.lower().startswith('n'):
        return
    
    print()
    
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
    max_results_per_keyword = input("Enter the maximum number of results per keyword (default is 5): ")
    max_results_per_keyword = int(max_results_per_keyword) if max_results_per_keyword else 5
    
    total_results_limit = input("Enter the maximum total number of results across all keywords (default is 15): ")
    total_results_limit = int(total_results_limit) if total_results_limit else 15
    
    price_multiplier = input("Enter the price multiplier (default is 200.0): ")
    price_multiplier = float(price_multiplier) if price_multiplier else 200.0
    
    print(f"Using max_results_per_keyword: {max_results_per_keyword}")
    print(f"Using total_results_limit: {total_results_limit}")
    print(f"Using price multiplier: {price_multiplier}")
    print()
    
    scraper = AliExpressSeleniumScraper()
    
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
        
        print(f"\n🔍 Searching AliExpress for: {keyword}")
        print("-" * 50)
        
        results = scraper.search(keyword, max_results_per_keyword)
        
        if results:
            print(f"✅ Found {len(results)} results for '{keyword}'")
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
            print(f"❌ No results found for '{keyword}'")
        
        if len(unique_products) >= total_results_limit:
            break
        
        # Delay between searches
        time.sleep(2)
    
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
            print(f"  {i}. {title[:60]}... - {product['price']}")
            
    else:
        # Create empty CSV
        with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Image', 'Title', 'Regular Price', 'Category', 'Short_description', 'description']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        
        print("❌ No products were scraped successfully.")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Ensure ChromeDriver is installed and in PATH")
        print("2. Try running with visible browser (set headless=False)")
        print("3. Check internet connection")
        print("4. Consider using eBay scraper: ./run.sh --scrape-ebay")

if __name__ == "__main__":
    main()