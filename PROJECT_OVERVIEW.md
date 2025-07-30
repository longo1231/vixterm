# VIX Term Structure Monitor - Project Overview

## 🎯 Project Purpose
Automated daily monitoring system for VIX term structure analysis with beautiful visualizations and email delivery. Built to track volatility market conditions, identify trading opportunities, and deliver professional analysis reports via GitHub Actions automation.

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Cloud)                   │
├─────────────────────────────────────────────────────────────┤
│  Daily Schedule: Mon-Fri 4:45 PM EST                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    Setup    │→ │   Analysis  │→ │   Email & Archive   │ │
│  │ Environment │  │   Pipeline  │  │      Results        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Analysis Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│  VIX Data        Term Structure    Dashboard      Email     │
│  Scraping   →    Analysis      →   Generation  → Delivery  │
│  (CBOE Web)      (Mathematics)     (Matplotlib)  (SMTP)    │
└─────────────────────────────────────────────────────────────┘
```

## 📁 File Structure & Components

### Core Analysis Engine
```
main.py                 # Entry point & orchestration
├── vix_scraper.py      # CBOE web scraping (Selenium)
├── term_structure.py   # Mathematical analysis & signals  
├── visualizer.py       # Chart generation & formatting
└── alerts.py           # Market condition monitoring
```

### Automation & Delivery
```
.github/workflows/
└── daily-vix-monitor.yml    # GitHub Actions workflow

email_sender.py              # HTML email with attachments
file_manager.py             # Output organization & cleanup
```

### Configuration & Dependencies
```
requirements.txt            # Python package dependencies
outputs/                   # Generated files (charts, data, logs)
├── charts/               # PNG dashboard files  
├── data/                 # TXT/JSON analysis summaries
└── logs/                 # Alert history & system logs
```

## 🔄 Data Flow Process

### 1. **Data Collection** (`vix_scraper.py`)
- Scrapes live VIX spot price from CBOE website
- Extracts VIX futures contracts with expiration dates
- Handles both settlement prices and live market data
- Filters weekly contracts, keeps monthly contracts only
- Returns structured DataFrame with pricing and timing data

### 2. **Market Analysis** (`term_structure.py`)
- **Contango/Backwardation Detection**: Compares spot vs futures pricing
- **Roll Carry Calculation**: Estimates 30-day synthetic index and roll costs
- **Curve Shape Analysis**: Classifies as Steep/Normal/Flat/Inverted
- **Trading Signal Generation**: Provides actionable market recommendations
- **Inversion Detection**: Identifies pricing anomalies between contracts

### 3. **Visualization** (`visualizer.py`)  
- **Main Dashboard**: Clean term structure curve with spot + 9 futures
- **Dual X-Axis**: Days to expiration (bottom) + actual expiry dates (top)
- **Contango Grid**: Aligned percentage differences under each contract
- **Roll Carry Box**: Prominent display of synthetic index and carry metrics
- **Market Commentary**: Trading signals and curve health status

### 4. **Email Delivery** (`email_sender.py`)
- **HTML Formatting**: Professional email template with market colors
- **Dynamic Subjects**: Include spot VIX and trading signal
- **Dual Attachments**: PNG chart + TXT summary data
- **Market Sentiment**: Color-coded signals (red/yellow/green)
- **Key Metrics Display**: Spot VIX, roll carry, curve status

## ⚙️ Automation Workflow

### GitHub Actions Pipeline (`.github/workflows/daily-vix-monitor.yml`)

1. **Schedule Trigger**: Runs Monday-Friday at 4:45 PM EST (after market close)
2. **Environment Setup**: Ubuntu + Python 3.11 + Chrome browser
3. **Dependency Installation**: pip requirements + Chrome webdriver
4. **Analysis Execution**: `python main.py --save-plots --save-data`
5. **Email Delivery**: `python email_sender.py` with SMTP authentication
6. **Artifact Storage**: Backup charts/data to GitHub (30-day retention)

### Configuration via GitHub Secrets
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587  
EMAIL_USER=your.email@gmail.com
EMAIL_PASSWORD=your-app-password
RECIPIENT_EMAIL=your.email@gmail.com
```

## 📊 Analysis Outputs

### Visual Dashboard Features
- **Spot VIX**: Red dot with label annotation at day 0
- **Term Structure Curve**: Blue line connecting all contract prices  
- **Contract Labels**: Symbol + price above each point
- **Expiry Dates**: MM/DD format on secondary x-axis
- **Contango Metrics**: Percentage differences aligned under each contract
- **Roll Carry Analysis**: Prominent box with synthetic index calculation
- **Trading Commentary**: Signal interpretation with market health status

### Data Summary Format
```
VIX MARKET OVERVIEW
VIX Spot: 15.85
Curve Shape: Steep Contango  
Trading Signal: Strong Contango - Consider Short Vol

ROLL CARRY ANALYSIS
Synthetic 30-Day Index: 18.44
Roll Points: -0.0667
Roll Carry: -0.36%

FUTURES CONTRACTS  
VX/Q5    17.84  ( 21 days)
VX/U5    19.71  ( 49 days)
[... additional contracts ...]
```

## 🚀 Key Features

### Market Intelligence
- **Real-time CBOE data** with robust web scraping
- **Professional trading signals** based on term structure shape
- **Roll carry calculations** for VIX ETF analysis  
- **Inversion detection** for market stress identification

### Visual Excellence  
- **Publication-ready charts** with clean, professional styling
- **Dual-axis design** showing both time and expiry dates
- **Aligned contango grid** for precise contract comparison
- **Color-coded signals** for immediate market assessment

### Reliable Automation
- **GitHub Actions hosting** - runs regardless of local machine status
- **Email delivery system** with beautiful HTML formatting and attachments
- **Error handling** with detailed logging and backup artifact storage
- **Manual trigger option** for testing and ad-hoc analysis

## 🛠️ Usage & Maintenance

### Manual Execution (Local)
```bash
python main.py --save-plots --save-data    # Full analysis with outputs
python main.py --info                      # Quick market overview
python main.py --cleanup --days 30         # Clean old files  
```

### GitHub Actions Testing
- Navigate to repository **Actions** tab
- Select **"Daily VIX Monitor"** workflow  
- Click **"Run workflow"** for manual trigger
- Monitor logs for debugging any issues

### Email Configuration
- Uses Gmail SMTP with App Password authentication
- Requires 2FA enabled on Gmail account
- App password generated at: https://myaccount.google.com/apppasswords
- All credentials stored securely in GitHub repository secrets

## 📈 Market Analysis Logic

### Trading Signal Generation
- **Strong Contango**: Spot significantly below front month (consider short vol)
- **Contango**: Normal upward sloping curve (neutral to bearish vol)  
- **Backwardation**: Inverted curve with spot above futures (bullish vol)
- **Mixed Structure**: Complex curve requiring careful analysis

### Roll Carry Methodology
- Calculates synthetic 30-day constant maturity index
- Uses time-weighted interpolation between F1 and F2 contracts
- Expresses as percentage carry cost for VIX ETF holders
- Negative values indicate contango (cost to hold), positive indicate backwardation

## 🎯 Business Value

This system provides:
- **Daily market intelligence** delivered automatically via email
- **Professional-grade analysis** comparable to institutional research  
- **Zero-maintenance automation** running reliably in the cloud
- **Historical tracking** via archived outputs and email records
- **Actionable trading insights** for volatility-based strategies

Built with modern Python stack, cloud-native automation, and institutional-quality analysis methodologies.