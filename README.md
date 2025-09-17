# Scraper and CSV Processor Suite

A comprehensive toolkit for web scraping and data processing, featuring an eBay product scraper and CSV/Excel file deduplicator.


## 🛠️ Installation

### Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scraper_and_csv_processor.git
```
```bash
cd scraper_and_csv_processor
```


2. Run the setup:
```bash
bash run.sh
```

## 🚀 Features

### eBay Scraper
- Search eBay products using custom keywords
- Extract product details (images, titles, prices)
- Auto-categorize products based on search terms
- Generate AI-powered descriptions using Gemini
- Configurable result limits per keyword
- Clean CSV output format

### CSV Cleaner
- Remove problematic characters like `=-`, `#NAME?`, bracketed worker names
- Clean Unicode artifacts and encoding issues
- Preserve legitimate content like technical specifications
- Excel-style find and replace functionality
- Multiple cleaning methods available
- Works with any CSV file

### CSV/Excel Deduplicator
- Remove duplicate entries from files
- Process both CSV and Excel formats (.csv, .xlsx, .xls)
- Find duplicates within single files and across multiple files
- Automatic backup creation before processing
- Column-based deduplication (uses column B by default)
- Detailed statistics and reporting

### Slug Deduplicator

**Problem Solved:** When importing products into a database with unique slug constraints, products with similar titles can generate identical slugs. For example, "Product Name!" and "Product Name" both generate slug: `product-name`, causing database import failures.

**How it works:**
1. Reads a CSV file and generates slugs for all product titles
2. Identifies duplicate slugs
3. Appends the product ID to duplicate titles to make them unique
4. Outputs a fixed CSV file with unique titles/slugs

**Usage:**
```bash
# Via menu system
./run.sh --fix-slugs

# Direct usage (if in slug_deduplicator directory)
python fix_duplicate_slugs.py products.csv                    # Creates products_fixed.csv
python fix_duplicate_slugs.py products.csv products_deduped.csv  # Custom output name
python test_deduplicator.py                                   # Run test with sample data
```

**Example transformation:**
```csv
# Input CSV:
id,title,description
1001,"Product Name!","Description"
1002,"Product Name","Description"

# Output CSV:
id,title,description
1001,"Product Name!","Description"
1002,"Product Name - 1002","Description"
```

**Files in slug_deduplicator/:**
- `fix_duplicate_slugs.py` - Main deduplication script
- `test_deduplicator.py` - Test script with sample data
- `requirements.txt` - Python dependencies (uses standard library only)

### Slug Deduplicator Output

Creates fixed CSV files in `data/` directory with format:
- Filename: `originalname_slug_fixed_YYYYMMDD_HHMMSS.csv`
- Report file: `originalname_deduplication_report.txt`
- Backup: `originalname_backup_YYYYMMDD_HHMMSS.csv`
- Changes: Appends product IDs to duplicate titles to ensure unique slugs




## 📋 Prerequisites

- **Operating System**: Linux (Ubuntu 24.04.1 LTS recommended)
- **Python**: Version 3.8 or higher
- **Git**: For cloning the repository
- **Internet**: Required for eBay scraping

This will automatically:
- Check Python installation
- Create virtual environments for each tool
- Install all required dependencies

### Manual Setup

If you prefer to set up each tool individually:

#### eBay Scraper:
```bash
cd ebay_scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### CSV Deduplicator:
```bash
cd "excel_csv deduplicator"

#### Slug Deduplicator:
```bash
cd slug_deduplicator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


### Command Line Mode

Run specific operations directly:

```bash
# Setup all projects
./run.sh --setup

# Run eBay scraper
./run.sh --scrape

# Clean CSV files
./run.sh --clean-csv

# Run CSV deduplicator

# Fix duplicate slugs in CSV files
./run.sh --fix-slugs
./run.sh --deduplicate

# View data files
./run.sh --view-data

# Clean temporary files
./run.sh --cleanup

# Show help
./run.sh --help
```

## 📂 Project Structure

```
scraper_and_csv_processor/
├── run.sh                      # Main script with menu interface
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
│
├── ebay_scraper/              # eBay scraping tool
│   ├── main.py                # Scraper implementation
│   ├── requirements.txt       # Python dependencies
│   ├── Keywords_sample.csv    # Sample keywords file
│   ├── Keywords.csv           # Your keywords (create from sample)
│   └── README.md              # Tool documentation
│
├── slug_deduplicator/         # Slug deduplication tool
│   ├── fix_duplicate_slugs.py # Main deduplication script
│   ├── test_deduplicator.py   # Test script with sample data
│   ├── requirements.txt       # Python dependencies
│
├── csv_cleaner/               # CSV cleaning tool
│   ├── clean_csv.py           # Comprehensive CSV cleaner
│   ├── requirements.txt       # Python dependencies
│   └── products.csv           # Sample file for testing
│
├── excel_csv deduplicator/    # Deduplication tool
│   ├── main.py                # Deduplicator implementation
│   ├── requirements.txt       # Python dependencies
│   ├── data_csv/              # Input directory for files
│   │   └── .gitkeep          # Keeps directory in git
│   └── README.md              # Tool documentation
│
├── slug_deduplicator/         # Slug deduplication tool
│   ├── fix_duplicate_slugs.py # Main deduplication script
│   ├── test_deduplicator.py   # Test script with sample data
│   ├── requirements.txt       # Python dependencies
│
├── data/                      # Shared data output directory
└── logs/                      # Application logs

```

## 🔧 Configuration

### eBay Scraper Keywords

1. Copy the sample file:
```bash
cp ebay_scraper/Keywords_sample.csv ebay_scraper/Keywords.csv
```

2. Edit with your keywords:
```csv
Keywords
"gaming laptop"
"wireless mouse"
"mechanical keyboard"
```

3. Run the scraper - you'll be prompted for:
   - Max results per keyword (default: 10)
   - Max total results (default: 20)
   - Price multiplier (default: 200)

### CSV Deduplicator Setup

1. Place your CSV/Excel files in:
```
excel_csv deduplicator/data_csv/
```

2. Run the deduplicator
3. The tool will:
   - Identify the newest file
   - Use column B for deduplication
   - Create backups before processing
   - Show statistics after completion

## 📊 Output Files

### eBay Scraper Output

Creates CSV files in `data/` directory with format:
- Filename: `ebay_products_YYYYMMDD_HHMMSS.csv`
- Columns:
  - Image (product image URL)
  - Title (product title)
  - Regular Price (product price)
  - Category (search keyword)
  - Short_description (AI-generated)
  - description (AI-generated full description)

### CSV Cleaner Output

Creates cleaned CSV files in `data/` directory with format:
- Filename: `originalname_cleaned_YYYYMMDD_HHMMSS.csv`
- Removes: `=-` characters, `(worker names)`, `#NAME?` errors, Unicode artifacts
- Preserves: Technical specs like `(25mm)`, `(USD)`, proper punctuation

**Important**: When viewed on Windows systems, the cleaned files may show en-dashes (–) as garbled characters like `â€"`. This is a Windows display issue - the files are actually clean and correct.



### Deduplicator Output

- Processes files in-place
- Creates backups with format: `original_backup_YYYYMMDD_HHMMSS.ext`
- Backup location: Same directory as original file

## 🧹 Maintenance

### Cleanup Old Files

Remove temporary files and old logs:
```bash
./run.sh --cleanup
```

This will:
- Delete Python cache files (`__pycache__`, `*.pyc`)
- Remove logs older than 30 days
- Show current disk usage

### View Logs

Check application logs through the menu (option 8) or directly in:
```
logs/
```

## 🐛 Troubleshooting

### Common Issues

1. **Python not found**
   - Install Python 3: `sudo apt install python3 python3-venv python3-pip`

2. **Permission denied**
   - Make script executable: `chmod +x run.sh`

3. **Module not found**
   - Run setup again: `./run.sh --setup`

4. **No Keywords.csv file**
   - Copy from sample: `cp ebay_scraper/Keywords_sample.csv ebay_scraper/Keywords.csv`

5. **Empty deduplicator directory**
   - The menu will offer to copy files from the data directory

6. **Garbled characters in cleaned CSV on Windows**
   - This is normal - characters like `â€"` are actually proper en-dashes (–)
   - The files are correct, it's a Windows display encoding issue
   - Use UTF-8 compatible editors or import into Excel properly

### Log Files

Check logs for detailed error information:
```bash
ls -la logs/
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- Developed using Windsurf Code Editor
- Tested on Ubuntu 24.04.1 LTS

## 🙏 Acknowledgments

- eBay for providing product data
- Google Gemini for AI-powered descriptions
- Python community for excellent libraries

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Read tool-specific README files in each directory

---

**Note**: This tool is for educational purposes. Please respect website terms of service and rate limits when scraping.