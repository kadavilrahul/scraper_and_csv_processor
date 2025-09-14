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

### CSV/Excel Deduplicator
- Remove duplicate entries from files
- Process both CSV and Excel formats (.csv, .xlsx, .xls)
- Find duplicates within single files and across multiple files
- Automatic backup creation before processing
- Column-based deduplication (uses column B by default)
- Detailed statistics and reporting

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

# Run CSV deduplicator
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
├── excel_csv deduplicator/    # Deduplication tool
│   ├── main.py                # Deduplicator implementation
│   ├── requirements.txt       # Python dependencies
│   ├── data_csv/              # Input directory for files
│   │   └── .gitkeep          # Keeps directory in git
│   └── README.md              # Tool documentation
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