# Volatility Analysis Tool - User Guide

## Overview
This tool analyzes stock volatility from JSON data files and generates visual reports showing how current volatility compares to historical quartiles.

## Setup with Virtual Environment (venv)

### 1. Create a Virtual Environment
```bash
# Navigate to your project folder
cd "/Users/lukas/Desktop/Python projects/Financial Enlightenment"

# Create virtual environment
python3 -m venv venv
```

### 2. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

You'll see `(venv)` appear in your terminal prompt.

### 3. Install Required Packages
```bash
pip install pandas numpy matplotlib
```

### 4. Run the Tool
```bash
python volatility_analysis.py indices_10years.json
```

### 5. Deactivate When Done
```bash
deactivate
```

## Quick Start (with venv)
```bash
# One-time setup
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy matplotlib

# Every time you use it
source venv/bin/activate
python volatility_analysis.py indices_10years.json
deactivate
```

## What It Does
- Calculates rolling volatility for 1-month, 3-month, 6-month, and 1-year periods
- Shows volatility quartiles (low, medium-low, medium-high, high)
- Creates visual charts with color-coded volatility bands
- Generates text reports showing current volatility levels

## Basic Usage

### 1. Analyze All Stocks in a JSON File
```bash
python volatility_analysis.py indices_10years.json
```
This will:
- Analyze all tickers in the file
- Save plots to the `data/` folder
- Print volatility reports to the console

### 2. Analyze Specific Stocks
```bash
python volatility_analysis.py indices_10years.json --tickers ^GSPC AAXJ
```
This analyzes only the S&P 500 (^GSPC) and Asia ETF (AAXJ).

### 3. Save to a Custom Output Directory
```bash
python volatility_analysis.py indices_10years.json --output-dir results
```
This saves all plots to the `results/` folder instead of `data/`.

### 4. Combine Options
```bash
python volatility_analysis.py output.json --tickers AAPL MSFT TSLA --output-dir my_analysis
```

## Command-Line Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `json_file` | - | JSON file to analyze (required) | `indices_10years.json` |
| `--tickers` | `-t` | Specific tickers to analyze | `--tickers AAPL MSFT` |
| `--output-dir` | `-o` | Directory for output plots | `--output-dir results` |

## JSON File Format

Your JSON file should have this structure:
```json
{
  "metadata": {
    "tickers": ["AAPL", "MSFT", "TSLA"],
    "start_date": "2020-01-01",
    "end_date": "2025-12-25",
    "interval": "1d"
  },
  "data": {
    "AAPL": [
      {
        "Date": "2020-01-01 00:00:00",
        "Close": 150.25,
        "High": 152.00,
        "Low": 149.50,
        "Open": 151.00,
        "Volume": 1000000
      },
      ...
    ],
    "MSFT": [...],
    "TSLA": [...]
  }
}
```

## Understanding the Output

### Console Report Example
```
============================================================
VOLATILITY REPORT: AAPL
============================================================

1M Rolling Volatility:
  Current: 18.50% [Q2 (Medium-Low)]
  Q1 (25th percentile): 15.20%
  Q2 (50th percentile): 19.80%
  Q3 (75th percentile): 25.40%
  Min: 10.50%
  Max: 45.30%
```

### Volatility Quartiles Explained
- **Q1 (Low)**: Bottom 25% - Very calm market conditions
- **Q2 (Medium-Low)**: 25-50% - Below average volatility
- **Q3 (Medium-High)**: 50-75% - Above average volatility
- **Q4 (High)**: Top 25% - Elevated volatility, higher risk

### Chart Colors
- 🟢 **Green**: Q1 - Low volatility zone
- 🟡 **Yellow**: Q2 - Medium-low volatility
- 🟠 **Orange**: Q3 - Medium-high volatility
- 🔴 **Red**: Q4 - High volatility zone

## Examples with Different Files

### Example 1: Analyze Index Data
```bash
python volatility_analysis.py indices_10years.json
```

### Example 2: Analyze Your Custom Stocks
```bash
python volatility_analysis.py output.json --tickers AAPL TSLA NVDA
```

### Example 3: Quick Analysis of One Stock
```bash
python volatility_analysis.py indices_10years.json --tickers ^GSPC --output-dir quick_check
```

## Tips
- The tool requires at least 252 trading days (1 year) for meaningful 1-year volatility calculations
- Shorter periods (1M, 3M) will have data earlier in the time series
- Charts are saved as high-resolution PNG files (300 DPI)
- The tool uses annualized volatility (standard deviation × √252)

## Troubleshooting

**Error: JSON file not found**
- Check the file path is correct
- Use quotes if filename has spaces: `"my data.json"`

**Error: No data for ticker**
- The ticker isn't in the JSON file's metadata.tickers list
- Check ticker spelling matches exactly (case-sensitive)

**Warning: Not enough data**
- Need at least 21 days for 1M, 63 for 3M, 126 for 6M, 252 for 1Y volatility
