#!/usr/bin/env python3
"""
CSV Slug Deduplicator
Fixes duplicate slugs in CSV files by appending product IDs to duplicate titles
"""

import csv
import re
import sys
import os
from collections import defaultdict
from pathlib import Path
from datetime import datetime


def generate_slug(title):
    """Generate a slug from a title string."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def find_and_fix_duplicates(input_file, output_file=None, backup=True):
    """
    Find and fix duplicate slugs in a CSV file.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (optional, defaults to input_file_fixed.csv)
        backup: Whether to create a backup of the original file
    
    Returns:
        Dictionary with statistics about the deduplication process
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Set output file name if not provided
    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_fixed{input_path.suffix}"
    else:
        output_file = Path(output_file)
    
    # Create backup if requested
    if backup:
        backup_file = input_path.parent / f"{input_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{input_path.suffix}"
        print(f"Creating backup: {backup_file}")
        import shutil
        shutil.copy2(input_path, backup_file)
    
    # Read CSV and process
    rows = []
    slug_count = defaultdict(int)
    slug_to_products = defaultdict(list)
    duplicates_fixed = []
    
    print(f"Reading CSV file: {input_file}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        row_count = 0
        for row in reader:
            row_count += 1
            if len(row) > 1:
                product_id = row[0]
                title = row[1]
                slug = generate_slug(title)
                
                slug_count[slug] += 1
                slug_to_products[slug].append((product_id, title))
                
                # If this slug has been seen before, modify the title
                if slug_count[slug] > 1:
                    # Add product ID to title to make it unique
                    new_title = f"{title} - {product_id}"
                    row[1] = new_title
                    duplicates_fixed.append({
                        'product_id': product_id,
                        'original_title': title,
                        'new_title': new_title,
                        'slug': slug,
                        'occurrence': slug_count[slug]
                    })
                    print(f"  Fixed duplicate #{len(duplicates_fixed)}: {title[:50]}... -> ...{product_id}")
                
                rows.append(row)
    
    # Write fixed CSV
    print(f"\nWriting fixed CSV to: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    # Prepare statistics
    total_unique_slugs = len(slug_count)
    duplicate_slugs = [slug for slug, count in slug_count.items() if count > 1]
    total_duplicate_occurrences = sum(count - 1 for count in slug_count.values() if count > 1)
    
    stats = {
        'total_rows': row_count,
        'total_unique_slugs': total_unique_slugs,
        'duplicate_slugs': len(duplicate_slugs),
        'total_fixes_applied': len(duplicates_fixed),
        'output_file': str(output_file)
    }
    
    # Print summary
    print("\n" + "="*60)
    print("DEDUPLICATION SUMMARY")
    print("="*60)
    print(f"Total rows processed: {stats['total_rows']:,}")
    print(f"Unique slugs found: {stats['total_unique_slugs']:,}")
    print(f"Duplicate slugs found: {stats['duplicate_slugs']:,}")
    print(f"Fixes applied: {stats['total_fixes_applied']:,}")
    print(f"Output file: {stats['output_file']}")
    
    # Show most common duplicates
    if duplicate_slugs:
        print("\n" + "-"*60)
        print("TOP DUPLICATE SLUGS (showing first 10):")
        print("-"*60)
        
        sorted_duplicates = sorted(
            [(slug, count) for slug, count in slug_count.items() if count > 1],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        for slug, count in sorted_duplicates:
            print(f"  {count}x: {slug[:60]}...")
            products = slug_to_products[slug][:3]  # Show first 3 products
            for pid, title in products:
                print(f"      - ID: {pid}, Title: {title[:50]}...")
            if len(slug_to_products[slug]) > 3:
                print(f"      ... and {len(slug_to_products[slug]) - 3} more")
    
    # Write detailed report
    report_file = output_file.parent / f"{output_file.stem}_report.txt"
    print(f"\nWriting detailed report to: {report_file}")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("CSV SLUG DEDUPLICATION REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*80 + "\n\n")
        
        f.write("STATISTICS:\n")
        f.write("-"*40 + "\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
        
        f.write("\n\nDUPLICATES FIXED:\n")
        f.write("-"*40 + "\n")
        for fix in duplicates_fixed:
            f.write(f"\nProduct ID: {fix['product_id']}\n")
            f.write(f"Original: {fix['original_title']}\n")
            f.write(f"Modified: {fix['new_title']}\n")
            f.write(f"Slug: {fix['slug']}\n")
            f.write(f"Occurrence #: {fix['occurrence']}\n")
    
    return stats


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python fix_duplicate_slugs.py <input_csv> [output_csv]")
        print("\nExample:")
        print("  python fix_duplicate_slugs.py products.csv")
        print("  python fix_duplicate_slugs.py products.csv products_deduped.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        stats = find_and_fix_duplicates(input_file, output_file)
        print("\n✅ Deduplication completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
