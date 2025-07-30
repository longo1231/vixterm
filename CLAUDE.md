# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core System Architecture

This is a VIX term structure monitoring system with automated daily execution via GitHub Actions. The system follows a modular pipeline architecture:

**Data Pipeline**: `vix_scraper.py` → `term_structure.py` → `visualizer.py` → `email_sender.py`

**Key Components**:
- `main.py` - Central orchestrator with CLI interface
- `vix_scraper.py` - CBOE web scraping using Selenium (handles JavaScript-rendered pages)  
- `term_structure.py` - Mathematical analysis engine (contango/backwardation, roll carry, trading signals)
- `visualizer.py` - Chart generation with dual x-axis (days + expiry dates) and aligned contango grid
- `email_sender.py` - HTML email delivery with chart/data attachments
- `alerts.py` - Market condition monitoring and alert generation
- `file_manager.py` - Output organization with timestamped files

**Automation**: `.github/workflows/daily-vix-monitor.yml` runs Mon-Fri at 4:45 PM EST via GitHub Actions, requiring email credentials in repository secrets.

## Common Commands

**Development and Testing**:
```bash
# Basic analysis with live data
python main.py --save-plots --save-data

# Testing with fake data (no web scraping)
python main.py --fake-data --save-plots

# Quick market overview without plots
python main.py --info

# File cleanup (remove files older than N days)
python main.py --cleanup 30

# Test email system locally (requires environment variables)
python email_sender.py
```

**Dependencies**:
```bash
pip install -r requirements.txt
```

## Analysis Logic and Data Flow

**Web Scraping Strategy**: Uses Selenium with Chrome WebDriver to handle CBOE's JavaScript-rendered futures table. Filters out weekly contracts, keeping only monthly VIX futures (VX/Q5, VX/U5, etc.).

**Mathematical Analysis**: 
- Roll carry calculation uses time-weighted interpolation between F1/F2 contracts to create synthetic 30-day index
- Trading signals based on curve shape classification (Steep Contango, Normal, Inversion)
- Contango percentages calculated between consecutive contracts starting from spot VIX

**Visualization Design**: Single comprehensive dashboard with spot VIX at day 0, futures curve, secondary x-axis showing MM/DD expiry dates, and aligned contango/difference grid positioned under corresponding contracts.

**Output Structure**: 
- `outputs/charts/` - Timestamped PNG dashboard files
- `outputs/data/` - TXT summaries and JSON analysis results  
- `outputs/logs/` - Alert history and system logs

## GitHub Actions Integration

The automation requires these repository secrets:
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `RECIPIENT_EMAIL`

Manual workflow triggering available via GitHub Actions web interface for testing.

## Development Notes

**CBOE Data Handling**: The scraper accommodates both settlement prices (after hours) and live prices (market hours). Contract expiration parsing handles the VX + month code + year format.

**Error Resilience**: System includes robust error handling for market holidays, stale data, and web scraping failures with fallback mechanisms.

**File Organization**: All outputs use timestamp prefixes (YYYY-MM-DD_HHMMSS) for chronological organization and easy identification of latest results.