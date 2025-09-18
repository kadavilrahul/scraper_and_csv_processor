#!/usr/bin/env python3
"""
Clean URL-Encoded Slugs in Product CSV

This script identifies and cleans products with URL-encoded slugs (containing %xx patterns).
It preserves all other products unchanged.

Author: CSV Slug Cleaner
Date: September 2025
"""

import csv
import re
import sys
import os
from datetime import datetime
import urllib.parse
from typing import Dict, List, Tuple, Optional

def decode_and_clean_slug(encoded_slug: str) -> str:
    """
    Decode URL-encoded slug and clean special characters.
    
    Examples:
    - %e3%80%90save20%ef%bc%85%e3%80%91-shiseido → save20-shiseido
    - product-%f0%9f%8f%85-premium → product-premium
    - %d8%a8%d8%af%d9%8a%d8%b9-arabic-text → arabic-text
    """
    
    # First, decode the URL encoding
    try:
        decoded = urllib.parse.unquote(encoded_slug)
    except:
        # If decoding fails, use original
        decoded = encoded_slug
    
    # Remove Unicode categories:
    # - Emoji & Symbols (including 🏅, ❤️, ✔, ❀, etc.)
    # - CJK characters (Chinese, Japanese, Korean)
    # - Arabic script
    # - Other non-ASCII special characters
    
    # Step 1: Remove emoji and special Unicode symbols
    # This regex removes most emoji and special symbols
    decoded = re.sub(r'[\U0001F000-\U0001F9FF]', '', decoded)  # Emoji
    decoded = re.sub(r'[\U00002600-\U000027BF]', '', decoded)  # Misc symbols
    decoded = re.sub(r'[\U0001F300-\U0001F5FF]', '', decoded)  # Misc symbols & pictographs
    decoded = re.sub(r'[\U0001F900-\U0001F9FF]', '', decoded)  # Supplemental symbols
    decoded = re.sub(r'[\U0001F600-\U0001F64F]', '', decoded)  # Emoticons
    decoded = re.sub(r'[\U0001F680-\U0001F6FF]', '', decoded)  # Transport & map symbols
    
    # Step 2: Remove CJK characters (Chinese, Japanese, Korean)
    decoded = re.sub(r'[\u3000-\u303F]', '', decoded)  # CJK punctuation
    decoded = re.sub(r'[\u3040-\u309F]', '', decoded)  # Hiragana
    decoded = re.sub(r'[\u30A0-\u30FF]', '', decoded)  # Katakana
    decoded = re.sub(r'[\u4E00-\u9FFF]', '', decoded)  # CJK unified ideographs
    decoded = re.sub(r'[\uFF00-\uFFEF]', '', decoded)  # Full-width characters
    decoded = re.sub(r'【|】', '', decoded)  # Special CJK brackets
    
    # Step 3: Remove Arabic script
    decoded = re.sub(r'[\u0600-\u06FF]', '', decoded)  # Arabic
    decoded = re.sub(r'[\u0750-\u077F]', '', decoded)  # Arabic supplement
    
    # Step 4: Remove other special Unicode characters
    decoded = re.sub(r'[^\x00-\x7F]', '', decoded)  # Remove all non-ASCII
    
    # Step 5: Clean up what remains
    # Replace any sequence of non-alphanumeric (except hyphen) with hyphen
    cleaned = re.sub(r'[^a-zA-Z0-9\-]+', '-', decoded)
    
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip('-')
    
    # If the slug becomes empty after cleaning, generate from product ID
    if not cleaned:
        # We'll handle this in the main function with product ID
        return ""
    
    return cleaned.lower()

def has_url_encoding(slug: str) -> bool:
    """
    Check if a slug contains URL encoding patterns (%xx).
    """
    return bool(re.search(r'%[0-9a-fA-F]{2}', slug))

def process_csv(input_file: str, output_file: Optional[str] = None) -> Dict:
    """
    Process CSV file and clean only products with URL-encoded slugs.
    
    Returns statistics about the cleaning process.
    """
    
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found.")
        return {}
    
    # Generate output filename if not provided
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base}_cleaned_slugs_{timestamp}{ext}"
    
    print(f"🔍 Analyzing CSV for URL-encoded slugs...")
    print(f"📂 Input: {input_file}")
    print(f"📂 Output: {output_file}")
    print()
    
    # Statistics
    stats = {
        'total_products': 0,
        'encoded_slugs': 0,
        'cleaned_slugs': 0,
        'empty_slugs': 0,
        'unchanged_slugs': 0,
        'samples': []
    }
    
    # Read and process CSV
    with open(input_file, 'r', encoding='utf-8', newline='') as infile:
        # Detect delimiter
        sample = infile.read(1024)
        infile.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        
        reader = csv.DictReader(infile, delimiter=delimiter)
        
        # Check if slug column exists
        fieldnames = reader.fieldnames
        if not fieldnames or 'slug' not in fieldnames:
            print("❌ Error: No 'slug' column found in CSV!")
            if fieldnames:
                print(f"   Available columns: {', '.join(fieldnames)}")
            return {}
        
        # Prepare output
        with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            
            # Process each row
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                stats['total_products'] += 1
                
                original_slug = row.get('slug', '')
                
                # Check if slug has URL encoding
                if has_url_encoding(original_slug):
                    stats['encoded_slugs'] += 1
                    
                    # Clean the slug
                    cleaned_slug = decode_and_clean_slug(original_slug)
                    
                    # If slug is empty after cleaning, use product ID
                    if not cleaned_slug:
                        product_id = row.get('product_id', row.get('id', ''))
                        if product_id:
                            cleaned_slug = f"product-{product_id}"
                        else:
                            cleaned_slug = f"product-{row_num}"
                        stats['empty_slugs'] += 1
                    
                    # Update the row with cleaned slug
                    row['slug'] = cleaned_slug
                    stats['cleaned_slugs'] += 1
                    
                    # Collect samples for reporting
                    if len(stats['samples']) < 10:
                        stats['samples'].append({
                            'original': original_slug,
                            'cleaned': cleaned_slug,
                            'product_id': row.get('product_id', ''),
                            'title': row.get('post_title', row.get('title', ''))[:50]
                        })
                    
                    # Progress indicator
                    if stats['cleaned_slugs'] % 100 == 0:
                        print(f"  ✓ Cleaned {stats['cleaned_slugs']} encoded slugs...")
                else:
                    stats['unchanged_slugs'] += 1
                
                # Write the row (modified or unchanged)
                writer.writerow(row)
                
                # Progress for large files
                if stats['total_products'] % 10000 == 0:
                    print(f"  ⚙️ Processed {stats['total_products']:,} products...")
    
    return stats

def print_statistics(stats: Dict):
    """
    Print detailed statistics about the cleaning process.
    """
    print("\n" + "=" * 70)
    print("📊 CLEANING STATISTICS")
    print("=" * 70)
    print(f"Total products processed:     {stats['total_products']:,}")
    print(f"Products with encoded slugs:  {stats['encoded_slugs']:,}")
    print(f"Successfully cleaned:         {stats['cleaned_slugs']:,}")
    print(f"Empty after cleaning:         {stats['empty_slugs']:,}")
    print(f"Unchanged products:           {stats['unchanged_slugs']:,}")
    print()
    
    if stats['samples']:
        print("=" * 70)
        print("📝 SAMPLE CLEANED SLUGS (First 10)")
        print("=" * 70)
        for i, sample in enumerate(stats['samples'], 1):
            print(f"\n{i}. Product ID: {sample['product_id']}")
            print(f"   Title: {sample['title']}...")
            print(f"   Original: {sample['original'][:60]}...")
            print(f"   Cleaned:  {sample['cleaned']}")
    
    print("\n" + "=" * 70)

def main():
    """
    Main function to run the slug cleaning process.
    """
    print("=" * 70)
    print("🧹 URL-ENCODED SLUG CLEANER")
    print("=" * 70)
    print("This tool cleans products with URL-encoded slugs")
    print("while preserving all other products unchanged.")
    print()
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python clean_encoded_slugs.py <input_csv> [output_csv]")
        print()
        print("Examples:")
        print("  python clean_encoded_slugs.py products.csv")
        print("  python clean_encoded_slugs.py products.csv products_clean.csv")
        print()
        print("Description:")
        print("  - Identifies products with %xx URL encoding in slugs")
        print("  - Decodes and cleans special characters")
        print("  - Preserves all other products unchanged")
        print("  - Creates a backup with timestamp if output not specified")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Process the CSV
    stats = process_csv(input_file, output_file)
    
    if stats:
        # Print statistics
        print_statistics(stats)
        
        # Final summary
        print(f"✅ Successfully cleaned {stats['cleaned_slugs']:,} encoded slugs")
        print(f"💾 Output saved to: {output_file or 'auto-generated filename'}")
        print()
        print("Next steps:")
        print("1. Review the cleaned slugs in the output file")
        print("2. Copy to generator/input/ directory")
        print("3. Regenerate products with clean slugs")
        print()
    else:
        print("❌ Processing failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()