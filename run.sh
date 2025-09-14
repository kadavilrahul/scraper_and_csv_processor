#!/bin/bash

# Scraper and CSV Processor Master Script
# Version: 1.0

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
DATA_DIR="$SCRIPT_DIR/data"

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
    echo "  --scrape         Run eBay scraper"
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
    echo "│                                    SCRAPER AND CSV PROCESSOR                                            │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  SETUP & CONFIGURATION                                                                                           │"
    echo "│  1. Setup All Projects         [./run.sh --setup]            # Install Python dependencies for all tools         │"
    echo "│  2. Check Python & Dependencies                              # Verify Python version and virtual environments    │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  SCRAPING OPERATIONS                                                                                             │"
    echo "│  3. Run eBay Scraper          [./run.sh --scrape]            # Scrape products from eBay using keywords          │"
    echo "│  4. Edit Keywords.csv                                        # Modify search keywords for eBay scraper           │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  DATA PROCESSING                                                                                                 │"
    echo "│  5. Run CSV Deduplicator      [./run.sh --deduplicate]       # Remove duplicate rows from CSV/Excel files        │"
    echo "│  6. View Data Files           [./run.sh --view-data]         # List all processed data files with details        │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  MAINTENANCE                                                                                                     │"
    echo "│  7. Clean Temporary Files     [./run.sh --cleanup]           # Remove cache, old logs, and temporary files       │"
    echo "│  8. View Logs                                                # Browse and read application log files             │"
    echo "├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤"
    echo "│  0. Exit                                                                                                         │"
    echo "└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e "${YELLOW}Select option [0-8]: ${NC}\c"
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
    if [ ! -d "$SCRIPT_DIR/ebay_scraper/venv" ] && [ ! -d "$SCRIPT_DIR/excel_csv deduplicator/venv" ]; then
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
        --scrape)
            check_python
            run_ebay_scraper
            ;;
        --deduplicate)
            check_python
            run_csv_deduplicator
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
                        check_python
                        echo ""
                        # Check eBay scraper dependencies
                        if [ -d "$SCRIPT_DIR/ebay_scraper/venv" ]; then
                            log_success "eBay Scraper virtual environment: ✓"
                        else
                            log_warning "eBay Scraper virtual environment: ✗"
                        fi
                        
                        # Check deduplicator dependencies
                        if [ -d "$SCRIPT_DIR/excel_csv deduplicator/venv" ]; then
                            log_success "CSV Deduplicator virtual environment: ✓"
                        else
                            log_warning "CSV Deduplicator virtual environment: ✗"
                        fi
                        ;;
                    3)
                        check_python
                        run_ebay_scraper
                        ;;
                    4)
                        if [ -f "$SCRIPT_DIR/ebay_scraper/Keywords.csv" ]; then
                            ${EDITOR:-nano} "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                        else
                            log_warning "Keywords.csv not found. Creating from sample..."
                            cp "$SCRIPT_DIR/ebay_scraper/Keywords_sample.csv" "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                            ${EDITOR:-nano} "$SCRIPT_DIR/ebay_scraper/Keywords.csv"
                        fi
                        ;;
                    5)
                        check_python
                        run_csv_deduplicator
                        ;;
                    6)
                        view_data_files
                        ;;
                    7)
                        cleanup
                        ;;
                    8)
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