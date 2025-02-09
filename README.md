# eBay Scraper

A Python script to scrape search results from eBay and output them in a structured CSV format.

## Features
- Search eBay products using keywords from Keywords.csv
- Extract product details including images, titles, and prices
- Categorize products based on search keywords
- Configurable results per keyword and total results limit
- Clean and structured CSV output
- Generates short and full descriptions using Gemini AI for each category

## Development Environment
- Developed and tested on Ubuntu 24.04.1 LTS (Noble Numbat)
- Generated using Windsurf Code Editor

## Installation

1. Clone this repository, activate python environment and install dependencies
Run below command on Linux terminal.
```bash
git clone https://github.com/kadavilrahul/ebay_scraper.git && cd ebay_scraper && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```
2. Create or move a `Keywords.csv` file in the current directory with your search terms (see `Keywords_sample.csv` for format)
Input Format

The script requires a `Keywords.csv` file with the following format:
```csv
Keywords
"term1"
"term2"
"term3"
```
A sample file `Keywords_sample.csv` is provided as a template.

3. Run the script:
```bash
python3 main.py
```

Follow the prompts to:
1. Enter the maximum number of results per keyword (default is 500)
2. Enter the maximum total number of results across all keywords (default is 5000)

The script will:
1. Read keywords from Keywords.csv
2. Search eBay for each keyword
3. Save results in a CSV file with the following columns:
   - Image (product image URL)
   - Title (product title)
   - Regular Price (product price)
   - Category (search keyword used)
   - Short_description (placeholder for future use)
   - description (placeholder for future use)

## Output Format

The output CSV file contains the following columns:
- **Image**: URL to the product image
- **Title**: Product title from the listing
- **Regular Price**: Price of the product
- **Category**: The keyword used to find this product
- **Short_description**: Reserved for future use
- **description**: Reserved for future use

## Note
- The script processes Keywords.csv file for search terms
- Results are limited by both per-keyword and total result limits
- The script will stop when either limit is reached
