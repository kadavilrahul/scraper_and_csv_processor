#!/bin/bash

# Scraper and CSV Processor Master Script
# Version: 1.0

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
DATA_DIR="$SCRIPT_DIR/data"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Logging functions
log() { echo -e "$1"; }
log_error() { log "${RED}❌ $1${NC}"; }
log_success() { log "${GREEN}✅ $1${NC}"; }
log_warning() { log "${YELLOW}⚠️  $1${NC}"; }
log_info() { log "${BLUE}ℹ️  $1${NC}"; }

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# Check Python installation
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3 to continue."
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
    log_success "Python $PYTHON_VERSION detected"
}

# Install Python dependencies if missing
install_python_deps() {
    local install_needed=false
    
    # Check if venv module is available
    if ! python3 -m venv --help &> /dev/null 2>&1; then
        log_warning "Python venv module is not installed"
        install_needed=true
    fi
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        log_warning "pip is not installed"
        install_needed=true
    fi
    
    if [ "$install_needed" = true ]; then
        log_info "Installing required Python packages..."
        
        # Get Python version
        PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
        
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu system
            log_info "Detected Debian/Ubuntu system"
            
            # Check for sudo access
            if [ "$EUID" -ne 0 ]; then
                log_warning "Root access required. You will be prompted for sudo password..."
            fi
            
            # Update package list and install
            if command -v apt &> /dev/null; then
                log_info "Running: apt install python${PYTHON_VERSION}-venv python3-pip"
                sudo apt update -qq 2>/dev/null
                sudo apt install -y python${PYTHON_VERSION}-venv python3-pip
                
                if [ $? -eq 0 ]; then
                    log_success "Python dependencies installed successfully"
                else
                    log_error "Failed to install Python dependencies"
                    log_info "Please install manually with:"
                    echo "  sudo apt update"
                    echo "  sudo apt install python${PYTHON_VERSION}-venv python3-pip"
                    exit 1
                fi
            fi
        elif [ -f /etc/redhat-release ]; then
            # RHEL/CentOS/Fedora system
            log_info "Detected RHEL/CentOS/Fedora system"
            if command -v yum &> /dev/null; then
                sudo yum install -y python3-virtualenv python3-pip
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3-virtualenv python3-pip
            fi
        else
            log_error "Unsupported system. Please install python3-venv and pip manually"
            exit 1
        fi
    else
        log_info "Python venv and pip are already installed"
    fi
}

# Check and create virtual environment
setup_venv() {
    local project_dir="$1"
    local venv_path="$project_dir/venv"
    
    # First ensure Python dependencies are installed
    install_python_deps
    
    # Check if venv exists and is valid
    if [ -d "$venv_path" ]; then
        if [ ! -f "$venv_path/bin/activate" ]; then
            log_warning "Virtual environment is corrupted. Removing and recreating..."
            rm -rf "$venv_path"
        else
            log_info "Virtual environment already exists in $project_dir"
        fi
    fi
    
    # Create venv if it doesn't exist
    if [ ! -d "$venv_path" ]; then
        log_info "Creating virtual environment in $project_dir..."
        cd "$project_dir"
        
        if python3 -m venv venv; then
            log_success "Virtual environment created"
        else
            log_error "Failed to create virtual environment"
            log_info "Please check your Python installation"
            exit 1
        fi
    fi
    
    # Activate and install requirements
    log_info "Activating virtual environment and installing dependencies..."
    cd "$project_dir"
    
    # Check if activate script exists
    if [ ! -f "venv/bin/activate" ]; then
        log_error "Virtual environment activation script not found"
        log_info "Recreating virtual environment..."
        rm -rf venv
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    if [ -f "requirements.txt" ]; then
        # Upgrade pip first
        python -m pip install --upgrade pip >/dev/null 2>&1
        
        # Install requirements
        log_info "Installing Python packages from requirements.txt..."
        if pip install -r requirements.txt >/dev/null 2>&1; then
            log_success "Dependencies installed"
        else
            log_warning "Some dependencies may have failed. Retrying with verbose output..."
            pip install -r requirements.txt
        fi
    else
        log_warning "No requirements.txt found in $project_dir"
    fi
    
    deactivate
}

# Gemini API Key Management
setup_gemini_api_key() {
    log_info "Setting up Gemini API configuration..."
    echo ""
    
    # Check if .env file exists and has API key
    if [ -f "$ENV_FILE" ]; then
        if grep -q "GEMINI_API_KEY=" "$ENV_FILE"; then
            local current_key=$(grep "GEMINI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
            if [ -n "$current_key" ]; then
                log_success "Gemini API key already configured"
                echo -e "${YELLOW}Current key: ${NC}${current_key:0:10}...${current_key: -4}"
                echo -e "${YELLOW}Update API configuration? (y/N): ${NC}\c"
                read update_key
                if [[ ! "$update_key" =~ ^[Yy]$ ]]; then
                    return 0
                fi
            fi
        fi
    fi
    
    # Prompt for new API key
    echo -e "${YELLOW}Enter your Gemini API key: ${NC}\c"
    read -s api_key
    echo ""
    
    if [ -z "$api_key" ]; then
        log_warning "No API key provided"
        return 1
    fi
    
    # Ask for custom endpoint or use default
    local endpoint="https://generativelanguage.googleapis.com/v1beta/models/"
    echo -e "${YELLOW}Use default endpoint? (Y/n): ${NC}\c"
    read use_default
    
    if [[ "$use_default" =~ ^[Nn]$ ]]; then
        echo -e "${YELLOW}Enter custom Gemini API endpoint: ${NC}\c"
        read custom_endpoint
        if [ -n "$custom_endpoint" ]; then
            endpoint="$custom_endpoint"
        fi
    fi
    
    log_info "Endpoint: $endpoint"
    
    # Test the API key
    log_info "Testing API key..."
    if test_gemini_api_key "$api_key" "$endpoint"; then
        # Save to .env file
        if [ -f "$ENV_FILE" ]; then
            # Remove old config if exists
            grep -v -E "GEMINI_API_KEY=|GEMINI_API_ENDPOINT=" "$ENV_FILE" > "$ENV_FILE.tmp" || true
            mv "$ENV_FILE.tmp" "$ENV_FILE"
        fi
        echo "GEMINI_API_KEY=$api_key" >> "$ENV_FILE"
        echo "GEMINI_API_ENDPOINT=$endpoint" >> "$ENV_FILE"
        log_success "API configuration saved to .env file"
        
        # Set permission for security
        chmod 600 "$ENV_FILE"
        
        # Export for current session
        export GEMINI_API_KEY="$api_key"
        export GEMINI_API_ENDPOINT="$endpoint"
        log_success "API configuration complete!"
    else
        log_error "API key validation failed"
        return 1
    fi
}

# Test Gemini API key
test_gemini_api_key() {
    local api_key="$1"
    local endpoint="${2:-https://generativelanguage.googleapis.com/v1beta/models/}"
    
    # Ensure endpoint ends with /
    [[ "$endpoint" != */ ]] && endpoint="$endpoint/"
    
    # Test with a simple request
    local test_url="${endpoint}gemini-2.0-flash-exp:generateContent"
    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$test_url" \
        -H "Content-Type: application/json" \
        -H "x-goog-api-key: $api_key" \
        -d '{
            "contents": [{
                "parts": [{
                    "text": "Reply with OK"
                }]
            }]
        }' \
        --max-time 10)
    
    if [ "$response" = "200" ]; then
        log_success "API key is valid"
        return 0
    elif [ "$response" = "403" ]; then
        log_error "API key is invalid or lacks permissions"
        return 1
    elif [ "$response" = "429" ]; then
        log_warning "API key is valid but rate limited"
        return 0
    else
        log_error "Unexpected response code: $response"
        return 1
    fi
}

# Test current API configuration with detailed output
test_api_configuration() {
    log_info "Testing Gemini API Configuration..."
    echo ""
    
    # Check if configuration exists
    if ! load_gemini_api_key; then
        log_error "No API configuration found"
        echo -e "${YELLOW}Run option 2 to configure Gemini API${NC}"
        return 1
    fi
    
    # Display current configuration
    echo "Current Configuration:"
    echo "────────────────────────────────────────────"
    echo "API Key: ${GEMINI_API_KEY:0:15}...${GEMINI_API_KEY: -4}"
    echo "Endpoint: ${GEMINI_API_ENDPOINT}"
    echo "────────────────────────────────────────────"
    echo ""
    
    # Test the configuration
    log_info "Sending test request to Gemini API..."
    
    local test_url="${GEMINI_API_ENDPOINT}gemini-2.0-flash-exp:generateContent"
    local response_file="/tmp/gemini_test_$$.json"
    
    # Make test request and capture full response
    local http_code=$(curl -s -w "%{http_code}" \
        -X POST "$test_url" \
        -H "Content-Type: application/json" \
        -H "x-goog-api-key: $GEMINI_API_KEY" \
        -d '{
            "contents": [{
                "parts": [{
                    "text": "Say hello and confirm you are working"
                }]
            }]
        }' \
        -o "$response_file" \
        --max-time 10)
    
    echo ""
    echo "Response Status: $http_code"
    
    if [ "$http_code" = "200" ]; then
        log_success "✅ API test successful!"
        
        # Try to extract and show the response
        if [ -f "$response_file" ]; then
            if command -v python3 &> /dev/null; then
                echo ""
                echo "API Response:"
                python3 -c "
import json
try:
    with open('$response_file', 'r') as f:
        data = json.load(f)
        if 'candidates' in data and data['candidates']:
            text = data['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', 'No text')
            print('  ' + text[:200])
except:
    print('  (Could not parse response)')
"
            else
                echo "Response received (install python3 to see details)"
            fi
        fi
        echo ""
        log_success "Your Gemini API is working correctly!"
        
    elif [ "$http_code" = "403" ]; then
        log_error "❌ API key is invalid or doesn't have proper permissions"
        echo ""
        echo "Please check:"
        echo "  1. Your API key is correct"
        echo "  2. The API key has Gemini API enabled in Google Cloud Console"
        echo "  3. The project has billing enabled"
        
    elif [ "$http_code" = "429" ]; then
        log_warning "⚠️ Rate limit exceeded"
        echo ""
        echo "The API key is valid but you've exceeded the rate limit."
        echo "Wait a moment and try again."
        
    elif [ "$http_code" = "404" ]; then
        log_error "❌ Endpoint or model not found"
        echo ""
        echo "The endpoint URL might be incorrect or the model might not exist."
        echo "Current endpoint: $GEMINI_API_ENDPOINT"
        
    else
        log_error "❌ Unexpected error (HTTP $http_code)"
        if [ -f "$response_file" ] && [ -s "$response_file" ]; then
            echo ""
            echo "Error details:"
            head -3 "$response_file" | sed 's/^/  /'
        fi
    fi
    
    # Cleanup
    rm -f "$response_file"
    
    echo ""
    return 0
}

# Load API key from .env file
load_gemini_api_key() {
    if [ -f "$ENV_FILE" ]; then
        if grep -q "GEMINI_API_KEY=" "$ENV_FILE"; then
            export GEMINI_API_KEY=$(grep "GEMINI_API_KEY=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
            # Also load endpoint if present
            if grep -q "GEMINI_API_ENDPOINT=" "$ENV_FILE"; then
                export GEMINI_API_ENDPOINT=$(grep "GEMINI_API_ENDPOINT=" "$ENV_FILE" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
            else
                export GEMINI_API_ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models/"
            fi
            return 0
        fi
    fi
    return 1
}



# Test AliExpress Scraper with single keyword
test_aliexpress_scraper() {
    log_info "Testing AliExpress Scraper with 'laptop' keyword..."
    echo ""
    
    local scraper_dir="$SCRIPT_DIR/aliexpress_scraper"
    
    if [ ! -d "$scraper_dir" ]; then
        log_error "AliExpress scraper directory not found"
        return 1
    fi
    
    # Check virtual environment
    if [ ! -d "$scraper_dir/venv" ] || [ ! -f "$scraper_dir/venv/bin/activate" ]; then
        log_warning "Virtual environment not found. Setting up..."
        setup_venv "$scraper_dir"
    fi
    
    # Load API key
    if load_gemini_api_key; then
        log_success "API key loaded"
    else
        log_warning "No API key configured - descriptions will not be generated"
    fi
    
    # Create test keywords file
    echo "Keywords" > "$scraper_dir/test_keywords.csv"
    echo "laptop" >> "$scraper_dir/test_keywords.csv"
    
    cd "$scraper_dir"
    source venv/bin/activate
    
    log_info "Running test scrape..."
    echo "Testing with parameters: max_results=3, total_limit=3"
    echo ""
    
    # Run Python test directly
    python3 -c "
import sys
sys.path.insert(0, '.')
from main import AliExpressSeleniumScraper
import os

# Set test parameters
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')
os.environ['GEMINI_API_ENDPOINT'] = os.getenv('GEMINI_API_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models/')

print('Testing AliExpress scraper...')
scraper = AliExpressSeleniumScraper()

# Test search
print('\\nSearching for: laptop')
results = scraper.search('laptop', 3)

if results:
    print(f'✅ Found {len(results)} results!')
    for i, item in enumerate(results[:3], 1):
        print(f'\\n--- Item {i} ---')
        print(f\"Title: {item.get('title', 'N/A')[:80]}...\")
        print(f\"Price: {item.get('price', 'N/A')}\")
        print(f\"Image: {'Yes' if item.get('imagelink') and item.get('imagelink') != 'No image' else 'No'}\")
        print(f\"ID: {item.get('prdid', 'N/A')[:20]}...\")
else:
    print('❌ No results found')
    print('\\nPossible issues:')
    print('- AliExpress may have changed their HTML structure')
    print('- Network connectivity issues')
    print('- Rate limiting from AliExpress')
    
    # Try to debug
    import requests
    from bs4 import BeautifulSoup
    
    print('\\nDebug info:')
    url = 'https://www.aliexpress.com/wholesale?SearchText=laptop'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f'HTTP Status: {response.status_code}')
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            # Check for product links
            links = soup.find_all('a', href=lambda x: x and '/item/' in x if x else False)
            print(f'Product links found in page: {len(links)}')
            
            # Check page title
            title = soup.find('title')
            if title:
                print(f'Page title: {title.text[:50]}')
    except Exception as e:
        print(f'Debug failed: {e}')
"
    
    deactivate
    
    # Cleanup test file
    rm -f "$scraper_dir/test_keywords.csv"
    
    echo ""
    log_info "Test complete!"
    return 0
}

# eBay Scraper functions
run_ebay_scraper() {
    log_info "Starting eBay Scraper..."
    echo ""
    
    local scraper_dir="$SCRIPT_DIR/ebay_scraper"
    
    if [ ! -d "$scraper_dir" ]; then
        log_error "eBay scraper directory not found at $scraper_dir"
        return 1
    fi
    
    # Check if venv exists, if not set it up
    if [ ! -d "$scraper_dir/venv" ] || [ ! -f "$scraper_dir/venv/bin/activate" ]; then
        log_info "Virtual environment not found. Setting up..."
        setup_venv "$scraper_dir"
    fi
    
    # Check and load Gemini API key
    if ! load_gemini_api_key; then
        log_warning "Gemini API key not configured"
        echo -e "${YELLOW}The eBay scraper requires a Gemini API key for generating descriptions.${NC}"
        echo -e "${YELLOW}Would you like to set it up now? (Y/n): ${NC}\c"
        read setup_api
        if [[ ! "$setup_api" =~ ^[Nn]$ ]]; then
            setup_gemini_api_key
        else
            log_warning "Proceeding without API key. You'll be prompted to enter it during scraping."
        fi
    else
        log_success "Gemini API key loaded from .env file"
    fi
    
    # Check for Keywords.csv
    if [ ! -f "$scraper_dir/Keywords.csv" ]; then
        log_warning "Keywords.csv not found. Creating from sample..."
        if [ -f "$scraper_dir/Keywords_sample.csv" ]; then
            cp "$scraper_dir/Keywords_sample.csv" "$scraper_dir/Keywords.csv"
            log_info "Created Keywords.csv from sample. Please edit it with your keywords."
            echo -e "${YELLOW}Edit Keywords.csv? (y/N): ${NC}\c"
            read edit_keywords
            if [[ "$edit_keywords" =~ ^[Yy]$ ]]; then
                ${EDITOR:-nano} "$scraper_dir/Keywords.csv"
            fi
        else
            log_error "Keywords_sample.csv not found. Please create Keywords.csv manually."
            return 1
        fi
    fi
    
    # Run the scraper
    cd "$scraper_dir"
    source venv/bin/activate
    log_info "Running eBay scraper..."
    python3 main.py
    
    # Move output to data directory
    if [ -f "$scraper_dir/output.csv" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local output_file="$DATA_DIR/ebay_products_${timestamp}.csv"
        mv "$scraper_dir/output.csv" "$output_file"
        log_success "Output saved to: $output_file"
        
        # Show file info
        local row_count=$(tail -n +2 "$output_file" | wc -l)
        log_info "Scraped $row_count products"
    fi
    
    deactivate
}

# AliExpress Scraper functions
run_aliexpress_scraper() {
    log_info "Starting AliExpress Scraper..."
    echo ""
    
    local scraper_dir="$SCRIPT_DIR/aliexpress_scraper"
    
    if [ ! -d "$scraper_dir" ]; then
        log_error "AliExpress scraper directory not found at $scraper_dir"
        return 1
    fi
    
    # Check if venv exists, if not set it up
    if [ ! -d "$scraper_dir/venv" ] || [ ! -f "$scraper_dir/venv/bin/activate" ]; then
        log_info "Virtual environment not found. Setting up..."
        setup_venv "$scraper_dir"
    fi
    
    # Check and load Gemini API key
    if ! load_gemini_api_key; then
        log_warning "Gemini API key not configured"
        echo -e "${YELLOW}The AliExpress scraper requires a Gemini API key for generating descriptions.${NC}"
        echo -e "${YELLOW}Would you like to set it up now? (Y/n): ${NC}\c"
        read setup_api
        if [[ ! "$setup_api" =~ ^[Nn]$ ]]; then
            setup_gemini_api_key
        else
            log_warning "Proceeding without API key. You'll be prompted to enter it during scraping."
        fi
    else
        log_success "Gemini API key loaded from .env file"
    fi
    
    # Check for Keywords.csv
    if [ ! -f "$scraper_dir/Keywords.csv" ]; then
        log_warning "Keywords.csv not found. Creating from sample..."
        if [ -f "$scraper_dir/Keywords_sample.csv" ]; then
            cp "$scraper_dir/Keywords_sample.csv" "$scraper_dir/Keywords.csv"
            log_info "Created Keywords.csv from sample. Please edit it with your keywords."
            echo -e "${YELLOW}Edit Keywords.csv? (y/N): ${NC}\c"
            read edit_keywords
            if [[ "$edit_keywords" =~ ^[Yy]$ ]]; then
                ${EDITOR:-nano} "$scraper_dir/Keywords.csv"
            fi
        else
            log_error "Keywords_sample.csv not found. Please create Keywords.csv manually."
            return 1
        fi
    fi
    
    # Run the scraper
    cd "$scraper_dir"
    source venv/bin/activate
    log_info "Running AliExpress scraper..."
    python3 main.py
    
    # Move output to data directory
    if [ -f "$scraper_dir/output.csv" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local output_file="$DATA_DIR/aliexpress_products_${timestamp}.csv"
        mv "$scraper_dir/output.csv" "$output_file"
        log_success "Output saved to: $output_file"
        
        # Show file info
        local row_count=$(tail -n +2 "$output_file" | wc -l)
        log_info "Scraped $row_count products"
    fi
    
    deactivate
}


# CSV Cleaner functions
run_csv_cleaner() {
    log_info "Starting CSV Cleaner..."
    echo ""
    
    local cleaner_dir="$SCRIPT_DIR/csv_cleaner"
    
    if [ ! -d "$cleaner_dir" ]; then
        log_error "CSV cleaner directory not found at $cleaner_dir"
        return 1
    fi
    
    # Check for CSV files in the cleaner directory or data directory
    local csv_files=($(find "$DATA_DIR" "$cleaner_dir" -type f -name "*.csv" 2>/dev/null | head -10))
    
    if [ ${#csv_files[@]} -eq 0 ]; then
        log_warning "No CSV files found in data or csv_cleaner directories"
        echo -e "${YELLOW}Please place your CSV file in the csv_cleaner directory and try again${NC}"
        return 1
    fi
    
    echo "Available CSV files:"
    echo "────────────────────────────────────────────"
    for i in "${!csv_files[@]}"; do
        local filename=$(basename "${csv_files[$i]}")
        local filepath=$(dirname "${csv_files[$i]}")
        echo "  $((i+1)). $filename (in $(basename "$filepath"))"
    done
    echo "────────────────────────────────────────────"
    
    echo -e "${YELLOW}Select file to clean [1-${#csv_files[@]}]: ${NC}\c"
    read file_choice
    
    if [[ ! "$file_choice" =~ ^[0-9]+$ ]] || [ "$file_choice" -lt 1 ] || [ "$file_choice" -gt ${#csv_files[@]} ]; then
        log_error "Invalid selection"
        return 1
    fi
    
    local selected_file="${csv_files[$((file_choice-1))]}"
    local filename=$(basename "$selected_file")
    local base_name="${filename%.*}"
    
    log_info "Cleaning file: $filename"
    echo ""
    
    # Run the cleaner
    cd "$cleaner_dir"
    
    # Copy file to cleaner directory if it's not already there
    if [[ "$selected_file" != "$cleaner_dir"* ]]; then
        cp "$selected_file" "$cleaner_dir/"
        selected_file="$cleaner_dir/$(basename "$selected_file")"
    fi
    
    log_info "Running CSV cleaner..."
    python3 clean_csv.py "$selected_file"
    
    # Move cleaned output to data directory with timestamp
    local cleaned_file=$(find "$cleaner_dir" -name "*cleaned*.csv" -newer "$selected_file" 2>/dev/null | head -1)
    if [ -f "$cleaned_file" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local output_file="$DATA_DIR/${base_name}_cleaned_${timestamp}.csv"
        mv "$cleaned_file" "$output_file"
        log_success "Cleaned file saved to: $output_file"
        
        # Show file info
        local original_rows=$(tail -n +2 "$selected_file" | wc -l)
        local cleaned_rows=$(tail -n +2 "$output_file" | wc -l)
        log_info "Original: $original_rows rows → Cleaned: $cleaned_rows rows"
        
        # Show sample of changes
        # Show Windows display warning
        echo ""
        log_warning "Important: When viewed on Windows systems, the cleaned files may show en-dashes as garbled characters. This is a Windows display issue - the files are actually clean and correct."
    else
        log_error "Cleaned file not found. Check for errors above."
    fi
}

# Slug Deduplicator functions
run_slug_deduplicator() {
    log_info "Starting Slug Deduplicator..."
    echo ""
    
    local slug_dir="$SCRIPT_DIR/slug_deduplicator"
    
    if [ ! -d "$slug_dir" ]; then
        log_error "Slug deduplicator directory not found at $slug_dir"
        return 1
    fi
    
    # Check if venv exists, if not set it up
    if [ ! -d "$slug_dir/venv" ] || [ ! -f "$slug_dir/venv/bin/activate" ]; then
        log_info "Virtual environment not found. Setting up..."
        setup_venv "$slug_dir"
    fi
    
    # Check for CSV files in the data directory
    local csv_files=($(find "$DATA_DIR" "$slug_dir" -type f -name "*.csv" 2>/dev/null | head -10))
    
    if [ ${#csv_files[@]} -eq 0 ]; then
        log_warning "No CSV files found in data or slug_deduplicator directories"
        echo -e "${YELLOW}Please place your CSV file in the data directory and try again${NC}"
        return 1
    fi
    
    echo "Available CSV files:"
    echo "────────────────────────────────────────────"
    for i in "${!csv_files[@]}"; do
        local filename=$(basename "${csv_files[$i]}")
        local filepath=$(dirname "${csv_files[$i]}")
        echo "  $((i+1)). $filename (in $(basename "$filepath"))"
    done
    echo "────────────────────────────────────────────"
    
    echo -e "${YELLOW}Select file to fix duplicate slugs [1-${#csv_files[@]}]: ${NC}\c"
    read file_choice
    
    if [[ ! "$file_choice" =~ ^[0-9]+$ ]] || [ "$file_choice" -lt 1 ] || [ "$file_choice" -gt ${#csv_files[@]} ]; then
        log_error "Invalid selection"
        return 1
    fi
    
    local selected_file="${csv_files[$((file_choice-1))]}"
    local filename=$(basename "$selected_file")
    
    log_info "Processing file: $filename"
    echo ""
    
    # Run the slug deduplicator
    cd "$slug_dir"
    source venv/bin/activate
    log_info "Running slug deduplicator..."
    python3 fix_duplicate_slugs.py "$selected_file"
    
    # Move output to data directory
    local fixed_file="${selected_file%.*}_fixed.csv"
    if [ -f "$fixed_file" ]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local output_file="$DATA_DIR/$(basename "${selected_file%.*}")_slug_fixed_${timestamp}.csv"
        mv "$fixed_file" "$output_file"
        log_success "Fixed file saved to: $output_file"
        
        # Show statistics
        local original_rows=$(tail -n +2 "$selected_file" | wc -l)
        local fixed_rows=$(tail -n +2 "$output_file" | wc -l)
        log_info "Processed $original_rows products"
        
        # Check for report file
        local report_file="${selected_file%.*}_deduplication_report.txt"
        if [ -f "$report_file" ]; then
            log_info "Report saved to: $report_file"
            echo ""
            echo "Changes made:"
            head -20 "$report_file"
        fi
    else
        log_error "Fixed file not found. Check for errors above."
    fi
    
    deactivate
}


# CSV Deduplicator functions
run_csv_deduplicator() {
    log_info "Starting CSV/Excel Deduplicator..."
    echo ""
    
    local dedup_dir="$SCRIPT_DIR/excel_csv deduplicator"
    
    if [ ! -d "$dedup_dir" ]; then
        log_error "CSV deduplicator directory not found at $dedup_dir"
        return 1
    fi
    
    # Check if venv exists, if not set it up
    if [ ! -d "$dedup_dir/venv" ] || [ ! -f "$dedup_dir/venv/bin/activate" ]; then
        log_info "Virtual environment not found. Setting up..."
        setup_venv "$dedup_dir"
    fi
    
    # Check for CSV files in data_csv directory
    local csv_count=$(find "$dedup_dir/data_csv" -type f \( -name "*.csv" -o -name "*.xlsx" -o -name "*.xls" \) 2>/dev/null | wc -l)
    
    if [ "$csv_count" -eq 0 ]; then
        log_warning "No CSV/Excel files found in data_csv directory"
        echo -e "${YELLOW}Would you like to copy files from the data directory? (y/N): ${NC}\c"
        read copy_files
        
        if [[ "$copy_files" =~ ^[Yy]$ ]]; then
            # Show available files
            echo "Available files in data directory:"
            local files=($(find "$DATA_DIR" -type f \( -name "*.csv" -o -name "*.xlsx" -o -name "*.xls" \) 2>/dev/null))
            
            if [ ${#files[@]} -eq 0 ]; then
                log_warning "No CSV/Excel files found in data directory either"
                return 1
            fi
            
            for i in "${!files[@]}"; do
                echo "  $((i+1)). $(basename "${files[$i]}")"
            done
            
            echo -e "${YELLOW}Select files to copy (comma-separated numbers, or 'all'): ${NC}\c"
            read file_selection
            
            if [ "$file_selection" == "all" ]; then
                cp "${files[@]}" "$dedup_dir/data_csv/"
                log_success "All files copied to data_csv directory"
            else
                IFS=',' read -ra selections <<< "$file_selection"
                for selection in "${selections[@]}"; do
                    selection=$(echo "$selection" | tr -d ' ')
                    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#files[@]} ]; then
                        cp "${files[$((selection-1))]}" "$dedup_dir/data_csv/"
                        log_success "Copied: $(basename "${files[$((selection-1))]}")"
                    fi
                done
            fi
        fi
    else
        log_info "Found $csv_count file(s) in data_csv directory"
    fi
    
    # Run the deduplicator
    cd "$dedup_dir"
    source venv/bin/activate
    log_info "Running deduplicator..."
    python3 main.py
    
    deactivate
}

# Setup both projects
setup_all() {
    log_info "Setting up all projects..."
    echo ""
    
    # First check Python
    check_python
    
    # Install Python dependencies if needed
    install_python_deps
    
    # Setup eBay scraper
    if [ -d "$SCRIPT_DIR/ebay_scraper" ]; then
        log_info "Setting up eBay Scraper..."
        setup_venv "$SCRIPT_DIR/ebay_scraper"
        log_success "eBay Scraper setup complete"
    else
        log_warning "eBay scraper directory not found"
    fi
    
    # Setup AliExpress scraper
    if [ -d "$SCRIPT_DIR/aliexpress_scraper" ]; then
        log_info "Setting up AliExpress Scraper..."
        setup_venv "$SCRIPT_DIR/aliexpress_scraper"
        log_success "AliExpress Scraper setup complete"
    else
        log_warning "AliExpress scraper directory not found"
    fi
    
    echo ""
    
    # Setup Slug deduplicator
    if [ -d "$SCRIPT_DIR/slug_deduplicator" ]; then
        log_info "Setting up Slug Deduplicator..."
        setup_venv "$SCRIPT_DIR/slug_deduplicator"
        log_success "Slug Deduplicator setup complete"
    else
        log_warning "Slug deduplicator directory not found"
    fi
    
    echo ""
    

    # Setup CSV deduplicator
    if [ -d "$SCRIPT_DIR/excel_csv deduplicator" ]; then
        log_info "Setting up CSV Deduplicator..."
        setup_venv "$SCRIPT_DIR/excel_csv deduplicator"
        log_success "CSV Deduplicator setup complete"
    else
        log_warning "CSV deduplicator directory not found"
    fi
    
    echo ""
    log_success "All projects setup complete!"
    log_info "You can now use the menu options to run the tools"
}

# Clean temporary files
cleanup() {
    log_info "Cleaning up temporary files and virtual environments..."
    
    # Clean Python cache
    find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    log_success "Cleaned Python cache files"
    
    # Clean old logs (older than 30 days)
    if [ -d "$LOG_DIR" ]; then
        find "$LOG_DIR" -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
        log_success "Removed logs older than 30 days"
    fi
    
    # Ask about virtual environments
    echo ""
    echo -e "${YELLOW}Would you like to remove virtual environments? (y/N): ${NC}\c"
    read remove_venv
    
    if [[ "$remove_venv" =~ ^[Yy]$ ]]; then
        log_info "Removing virtual environments..."
        
        # Remove eBay scraper venv
        if [ -d "$SCRIPT_DIR/ebay_scraper/venv" ]; then
            rm -rf "$SCRIPT_DIR/ebay_scraper/venv"
            log_success "Removed eBay scraper virtual environment"
        fi
        
        # Remove AliExpress scraper venv
        if [ -d "$SCRIPT_DIR/aliexpress_scraper/venv" ]; then
            rm -rf "$SCRIPT_DIR/aliexpress_scraper/venv"
            log_success "Removed AliExpress scraper virtual environment"
        fi
        
        # Remove CSV deduplicator venv
        if [ -d "$SCRIPT_DIR/excel_csv deduplicator/venv" ]; then
            rm -rf "$SCRIPT_DIR/excel_csv deduplicator/venv"
            log_success "Removed CSV deduplicator virtual environment"
        fi
        
        log_warning "Virtual environments removed. Run './run.sh --setup' to reinstall them."
    fi
    
    # Show disk usage
    echo ""
    echo "Current disk usage:"
    echo "  Data directory: $(du -sh "$DATA_DIR" 2>/dev/null | cut -f1)"
    echo "  Logs directory: $(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)"
    echo "  Total project: $(du -sh "$SCRIPT_DIR" 2>/dev/null | cut -f1)"
    
    log_success "Cleanup complete"
}

# View data files
view_data_files() {
    log_info "Data files in $DATA_DIR:"
    echo ""
    
    if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
        log_warning "No data files found"
        return
    fi
    
    # List all CSV files with details
    local files=($(find "$DATA_DIR" -type f -name "*.csv" -o -name "*.xlsx" -o -name "*.xls" 2>/dev/null | sort -r))
    
    if [ ${#files[@]} -eq 0 ]; then
        log_warning "No CSV/Excel files found"
        return
    fi
    
    echo "Found ${#files[@]} file(s):"
    echo "────────────────────────────────────────────"
    for file in "${files[@]}"; do
        local filename=$(basename "$file")
        local filesize=$(du -h "$file" | cut -f1)
        local filedate=$(stat -c "%y" "$file" 2>/dev/null | cut -d' ' -f1)
        
        if [[ "$file" == *.csv ]]; then
            local rows=$(tail -n +2 "$file" | wc -l)
            echo "  📄 $filename"
            echo "     Size: $filesize | Date: $filedate | Rows: $rows"
        else
            echo "  📊 $filename"
            echo "     Size: $filesize | Date: $filedate"
        fi
    done
    echo "────────────────────────────────────────────"
}

# Usage function
usage() {
    echo "Scraper and CSV Processor Tool"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --setup          Setup all projects (install dependencies)"
    echo "  --api-key        Configure Gemini API key for AI descriptions"
    echo "  --test-api       Test Gemini API configuration"

    echo "  --test-aliexpress Quick test of AliExpress scraper with 'laptop' keyword"
    echo "  --scrape-ebay    Run eBay scraper"
    echo "  --scrape-aliexpress Run AliExpress scraper"
    echo "  --clean-csv      Run CSV cleaner (remove bracketed names and unwanted chars)"
    echo "  --deduplicate    Run CSV/Excel deduplicator"
    echo "  --view-data      View data files"
    echo "  --cleanup        Clean temporary files and old logs"
    echo "  --help           Show this help message"
    echo ""
    echo "Default: Interactive mode with menu"
}

# Interactive menu
show_menu() {
    echo ""
    echo "┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐"
    echo "│                                    SCRAPER AND CSV PROCESSOR                                                     │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  SETUP & CONFIGURATION                                                                                           │"
    echo "│  1. Setup All Projects           [./run.sh --setup]             # Install Python dependencies for all tools      │"
    echo "│  2. Configure Gemini API Key     [./run.sh --api-key]           # Set up API key for AI descriptions             │"
    echo "│  3. Test API Configuration       [./run.sh --test-api]          # Test if Gemini API is working                  │"
    echo "│  4. Check Python & Dependencies                                 # Verify Python version and virtual environments │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  SCRAPING OPERATIONS                                                                                             │"
    echo "│  5. Run eBay Scraper             [./run.sh --scrape-ebay]       # Scrape products from eBay using keywords       │"
    echo "│  6. Run AliExpress Scraper       [./run.sh --scrape-aliexpress] # Scrape products from AliExpress using keywords │"
    echo "│  7. Edit Keywords.csv (eBay)                                    # Modify search keywords for eBay scraper        │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  DATA PROCESSING                                                                                                 │"
    echo "│  8. Run CSV Cleaner              [./run.sh --clean-csv]         # Clean CSV files (remove names, unwanted chars) │"
    echo "│  9. Run CSV Deduplicator         [./run.sh --deduplicate]       # Remove duplicate rows from CSV/Excel files     │"
    echo "│  10. Fix Duplicate Slugs         [./run.sh --fix-slugs]         # Fix duplicate slugs in product CSV files       │"
    echo "│  11. View Data Files             [./run.sh --view-data]         # List all processed data files with details     │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  MAINTENANCE                                                                                                     │"
    echo "│  12. Clean Temporary Files       [./run.sh --cleanup]           # Remove cache, old logs, and temporary files    │"
    echo "│  13. View Logs                                                  # Browse and read application log files          │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  0. Exit                                                                                                         │"
    echo "└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e "${YELLOW}Select option [0-12]: ${NC}\c"
    read choice
    echo ""
}

# View logs
view_logs() {
    if [ ! -d "$LOG_DIR" ] || [ -z "$(ls -A "$LOG_DIR" 2>/dev/null)" ]; then
        log_warning "No log files found"
        return
    fi
    
    log_info "Recent log files:"
    ls -lht "$LOG_DIR" | head -10
    
    echo ""
    echo -e "${YELLOW}View a specific log file? (y/N): ${NC}\c"
    read view_log
    
    if [[ "$view_log" =~ ^[Yy]$ ]]; then
        local logs=($(find "$LOG_DIR" -type f -name "*.log" | sort -r))
        
        if [ ${#logs[@]} -eq 0 ]; then
            log_warning "No log files available"
            return
        fi
        
        echo "Available logs:"
        for i in "${!logs[@]}"; do
            echo "  $((i+1)). $(basename "${logs[$i]}")"
        done
        
        echo -e "${YELLOW}Select log [1-${#logs[@]}]: ${NC}\c"
        read log_choice
        
        if [[ "$log_choice" =~ ^[0-9]+$ ]] && [ "$log_choice" -ge 1 ] && [ "$log_choice" -le ${#logs[@]} ]; then
            less "${logs[$((log_choice-1))]}"
        fi
    fi
}

# Check first-time setup
check_first_time_setup() {
    local first_run=false
    
    # Check if virtual environments exist
    if [ ! -d "$SCRIPT_DIR/ebay_scraper/venv" ] && [ ! -d "$SCRIPT_DIR/aliexpress_scraper/venv" ] && [ ! -d "$SCRIPT_DIR/excel_csv deduplicator/venv" ]; then
        first_run=true
    fi
    
    # Check if Python venv module is available
    if ! python3 -m venv --help &> /dev/null 2>&1; then
        first_run=true
    fi
    
    if [ "$first_run" = true ]; then
        echo ""
        log_warning "First-time setup detected"
        log_info "This script needs to install Python dependencies and set up virtual environments"
        echo ""
        echo -e "${YELLOW}Would you like to run the automatic setup now? (Y/n): ${NC}\c"
        read setup_choice
        
        if [[ ! "$setup_choice" =~ ^[Nn]$ ]]; then
            setup_all
            echo ""
            log_success "Setup complete! You can now use the tools."
            echo ""
        else
            log_warning "Setup skipped. Some features may not work until setup is complete."
            log_info "Run './run.sh --setup' when ready to install dependencies."
        fi
    fi
}

# Main execution
main() {
    # Check for first-time setup if not running setup command
    if [ "${1:-}" != "--setup" ] && [ "${1:-}" != "--help" ] && [ "${1:-}" != "-h" ]; then
        check_first_time_setup
    fi
    
    case "${1:-}" in
        --setup)
            setup_all
            ;;
        --api-key)
            setup_gemini_api_key
            ;;
        --test-api)
            test_api_configuration
            ;;

        --test-aliexpress)
            check_python
            test_aliexpress_scraper
            ;;
        --scrape-ebay)
            check_python
            run_ebay_scraper
            ;;
        --scrape-aliexpress)
            check_python
            run_aliexpress_scraper
            ;;

        --scrape)
            # Backward compatibility
            check_python
            run_ebay_scraper
            ;;
        --clean-csv)
            check_python
            run_csv_cleaner
            ;;
        --deduplicate)
            check_python
            run_csv_deduplicator
            exit 0
            ;;
        --fix-slugs)
            check_python
            run_slug_deduplicator
            exit 0
            ;;
        --view-data)
            view_data_files
            ;;
        --cleanup)
            cleanup
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        "")
            # Interactive mode
            while true; do
                show_menu
                case $choice in
                    1)
                        setup_all
                        ;;
                    2)
                        setup_gemini_api_key
                        ;;
                    3)
                        test_api_configuration
                        ;;
                    4)
                        check_python
                        echo ""
                        # Check eBay scraper dependencies
                        if [ -d "$SCRIPT_DIR/ebay_scraper/venv" ]; then
                            log_success "eBay Scraper virtual environment: ✓"
                        else
                            log_warning "eBay Scraper virtual environment: ✗"
                        fi
                        
                        # Check AliExpress scraper dependencies
                        if [ -d "$SCRIPT_DIR/aliexpress_scraper/venv" ]; then
                            log_success "AliExpress Scraper virtual environment: ✓"
                        else
                            log_warning "AliExpress Scraper virtual environment: ✗"
                        fi
                        
                        # Check deduplicator dependencies
                        if [ -d "$SCRIPT_DIR/excel_csv deduplicator/venv" ]; then
                            log_success "CSV Deduplicator virtual environment: ✓"
                        else
                            log_warning "CSV Deduplicator virtual environment: ✗"
                        fi
                        
                        # Check API key
                        if load_gemini_api_key; then
                            log_success "Gemini API key: ✓"
                            echo "  Endpoint: ${GEMINI_API_ENDPOINT}"
                        else
                            log_warning "Gemini API key: ✗"
                        fi
                        ;;
                    5)
                        check_python
                        run_ebay_scraper
                        ;;
                    6)
                        check_python
                        run_aliexpress_scraper
                        ;;
                    7)
                        if [ -f "$SCRIPT_DIR/ebay_scraper/Keywords.csv" ]; then
                            ${EDITOR:-nano} "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                        else
                            log_warning "Keywords.csv not found. Creating from sample..."
                            cp "$SCRIPT_DIR/ebay_scraper/Keywords_sample.csv" "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                            ${EDITOR:-nano} "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                        fi
                        ;;
                    8)
                        check_python
                        run_csv_cleaner
                        ;;
                    9)
                        check_python
                        run_csv_deduplicator
                        ;;
                    10)
                        check_python
                        run_slug_deduplicator
                        ;;
                    11)
                        view_data_files
                        ;;
                    11)
                        cleanup
                        ;;
                    12)
                        view_logs
                        ;;
                    0)
                        log_info "Exiting..."
                        exit 0
                        ;;
                    *)
                        log_error "Invalid option: $choice"
                        ;;
                esac
                echo ""
                read -p "Press Enter to continue..."
                echo ""
            done
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
}

# Execute main with all arguments
main "$@"