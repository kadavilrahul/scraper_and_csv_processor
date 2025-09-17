#!/usr/bin/env python3
"""
Test script for the CSV Slug Deduplicator
Creates a sample CSV with duplicate slugs and tests the deduplication
"""

import csv
import os
from pathlib import Path
from fix_duplicate_slugs import find_and_fix_duplicates, generate_slug


def create_test_csv():
    """Create a test CSV file with duplicate slugs."""
    test_file = Path("test_products.csv")
    
    test_data = [
        ["id", "title", "description", "price"],
        ["1001", "Venom Pheromone Perfume Collection, Flower Scent!", "Description 1", "100"],
        ["1002", "Venom Pheromone Perfume Collection, Flower Scent", "Description 2", "100"],
        ["1003", "Valentine's Day Sale Box Rose Phero Perfume Oil~", "Description 3", "150"],
        ["1004", "Valentine's Day Sale Box Rose Phero Perfume Oil❤", "Description 4", "150"],
        ["1005", "USB-C to USB-B Printer Cable", "Description 5", "20"],
        ["1006", "USB-C to USB-B Printer Cable!", "Description 6", "20"],
        ["1007", "Unique Product Name", "Description 7", "50"],
        ["1008", "Another Unique Product", "Description 8", "75"],
    ]
    
    with open(test_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
    
    print(f"✅ Created test file: {test_file}")
    return test_file


def verify_results(fixed_file):
    """Verify that the fixed file has no duplicate slugs."""
    slugs = set()
    duplicates = []
    
    with open(fixed_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        for row in reader:
            if len(row) > 1:
                title = row[1]
                slug = generate_slug(title)
                
                if slug in slugs:
                    duplicates.append((row[0], title, slug))
                else:
                    slugs.add(slug)
    
    if duplicates:
        print("\n❌ VERIFICATION FAILED: Duplicate slugs still found:")
        for product_id, title, slug in duplicates:
            print(f"  ID: {product_id}, Title: {title}, Slug: {slug}")
        return False
    else:
        print("\n✅ VERIFICATION PASSED: No duplicate slugs found!")
        print(f"  Total unique slugs: {len(slugs)}")
        return True


def main():
    """Run the test."""
    print("="*60)
    print("CSV SLUG DEDUPLICATOR TEST")
    print("="*60)
    
    # Create test CSV
    test_file = create_test_csv()
    
    # Show original slugs
    print("\nOriginal slugs:")
    with open(test_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) > 1:
                print(f"  ID: {row[0]:4} Slug: {generate_slug(row[1]):50} Title: {row[1][:40]}...")
    
    # Run deduplication
    print("\n" + "-"*60)
    print("Running deduplication...")
    print("-"*60)
    
    fixed_file = Path("test_products_fixed.csv")
    stats = find_and_fix_duplicates(test_file, fixed_file, backup=False)
    
    # Show fixed slugs
    print("\nFixed slugs:")
    with open(fixed_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) > 1:
                print(f"  ID: {row[0]:4} Slug: {generate_slug(row[1]):50} Title: {row[1][:40]}...")
    
    # Verify results
    print("\n" + "-"*60)
    print("Verifying results...")
    print("-"*60)
    
    if verify_results(fixed_file):
        print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ TEST FAILED!")
    
    # Cleanup
    print("\nCleaning up test files...")
    for file in ["test_products.csv", "test_products_fixed.csv", "test_products_fixed_report.txt"]:
        if Path(file).exists():
            os.remove(file)
            print(f"  Removed: {file}")


if __name__ == "__main__":
    main()
