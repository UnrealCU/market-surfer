# Financial Enlightenment - Stock Analysis Toolkit

A comprehensive Python toolkit for collecting and analyzing stock market data. This toolkit enables you to fetch historical stock prices, analyze volatility patterns, and generate visual reports.

---

## 📋 Table of Contents
- [Setup](#setup)
- [get_quotes.py - Data Collection](#get_quotespy---data-collection)
- [edgar_filings_collector.py - SEC Filings](#edgar_filings_collectorpy---sec-filings)
- [edgar_financial_parser.py - XBRL Parser](#edgar_financial_parserpy---xbrl-parser)
- [example_usage.py - Quick Start](#example_usagepy---quick-start)
- [volatility_analysis.py - Volatility Analysis](#volatility_analysispy---volatility-analysis)
- [mahalanobis_regime.py - Multivariate Stress Detection](#mahalanobis_regimepy---multivariate-stress-detection)
- [Output Files](#output-files)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Setup

### 1. Activate Virtual Environment
```bash
cd "/Users/lukas/Desktop/Python projects/Financial Enlightenment"
source .venv/bin/activate
```
You'll see `(.venv)` in your terminal prompt.

### 2. Install Required Packages (if not already installed)
```bash
pip install yfinance pandas numpy matplotlib scipy edgartools
```

### 3. Deactivate When Done
```bash
deactivate
```

---

## 📥 get_quotes.py - Data Collection

### What It Does
Downloads historical stock price data from Yahoo Finance and saves it as JSON/CSV. This is your data collection tool that fetches OHLCV (Open, High, Low, Close, Volume) data for any stock or index.

### Basic Usage

#### Method 1: Command Line (Interactive)
```bash
python get_quotes.py
```
Follow the prompts to enter:
- Tickers (e.g., `AAPL MSFT TSLA`)
 - Start/End dates and interval (`1d` or `1mo`)
 - Optional columns (e.g., `Close Volume`)
 - Which data to fetch: `price`, `options`, and/or `financial`
   - If `options` is selected, choose type: `calls`, `puts`, or `both`
   - Optionally limit how many upcoming expirations to include (e.g., `3`)

Interactive saves produce JSON in a type-first folder layout:

```
Yahoo_extracted/
  price/YYYY-MM-DD/{TICKER}.json
  options/YYYY-MM-DD/{TICKER}.json
  financial/YYYY-MM-DD/{TICKER}.json
```

Notes:
- Price files are per-ticker JSON with records and metadata.
- Options files are per-ticker JSON with filtered expirations and `calls`/`puts` arrays.
- Financial files are per-ticker JSON with earnings, balance sheet, income, and cashflow (annual + quarterly).
### Yahoo_extracted folder structures

There are two saver behaviors:

1) Date-first (CSV + bundled fundamentals) — CLI `--save` uses this:
```
Yahoo_extracted/
  YYYY-MM-DD/
    price_data/
      AAPL.csv
      MSFT.csv
      ...
    financial_data/
      financial_info.json   # options/earnings/balance-sheet/financials (if fetched via flags)
```

2) Type-first (JSON per ticker) — Interactive mode uses this:
```
Yahoo_extracted/
  price/YYYY-MM-DD/{TICKER}.json
  options/YYYY-MM-DD/{TICKER}.json
  financial/YYYY-MM-DD/{TICKER}.json
```

Tips:
- Use Interactive mode for clean, per-ticker JSON by type.
- Use CLI `--save` when you want CSVs plus a single bundled fundamentals JSON.

### New: Options, Earnings, and Financials

You can now pull option chains, earnings history/dates, balance sheet, and key financial statements directly from `yfinance` via `get_quotes.py`.

#### Command-line examples

Fetch prices and option chains for all expirations, then save fundamentals JSON:
```bash
python get_quotes.py -t AAPL MSFT -s 2024-01-01 -e 2024-12-31 --options --save-info --info-output-dir Fundamentals_output
```

Fetch specific option expirations:
```bash
python get_quotes.py -t AAPL -s 2024-01-01 -e 2024-12-31 --options --options-expirations 2025-01-17 2025-03-21
```

Include earnings (yearly/quarterly and earnings dates) and balance sheet/financials:
```bash
python get_quotes.py -t AAPL MSFT -s 2023-01-01 -e 2025-12-31 \
  --earnings --balance-sheet --financials --save-info
```

Interactive mode example flow:
- Choose `price options financial` to fetch all types
- Pick `options` type as `calls` or `both`
- Set “Number of upcoming expirations” to `3` for near-term chains
- Confirm and save — files are written under the type-first JSON layout

#### Flags
- `--options`: Fetch option chains
- `--options-expirations YYYY-MM-DD ...`: Specific expirations (otherwise pulls all available)
- `--earnings`: Fetch earnings (yearly, quarterly, and earnings dates)
- `--balance-sheet`: Fetch balance sheet (annual + quarterly)
- `--financials`: Fetch income and cashflow statements (annual + quarterly)
- `--save-info`: Save fetched fundamentals/options to a single JSON file
- `--info-output-dir DIR`: Where to save the info JSON (default: `Fundamentals_output`)

#### Output structure (JSON)
When using `--save-info`, a file like `Fundamentals_output/info_YYYY-MM-DD_to_YYYY-MM-DD.json` is created.
It contains:
```json
{
  "metadata": { "tickers": ["AAPL"], "start_date": "2024-01-01", "end_date": "2024-12-31", "interval": "1d" },
  "options": { "AAPL": { "2025-01-17": { "calls": [...], "puts": [...] } } },
  "earnings": { "AAPL": { "yearly": [...], "quarterly": [...], "earnings_dates": [...] } },
  "balance_sheet": { "AAPL": { "balance_sheet": [...], "quarterly_balance_sheet": [...] } },
  "financials": { "AAPL": { "income_statement": [...], "cashflow": [...], "quarterly_income_statement": [...], "quarterly_cashflow": [...] } }
}
```

Notes:
- Some assets (indexes, ETFs, crypto) may not have options or complete fundamentals.
- Earnings date API may return limited history; use `--earnings` to include what’s available.

- Start date (e.g., `2024-01-01`)
- End date (e.g., `2025-12-26`)
- Interval (`1d` for daily, `1mo` for monthly)
- Columns (press Enter for all, or specify like `Close Volume`)

#### Method 2: Command Line (Direct)
```bash
# Single stock
python get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26

# Multiple stocks
python get_quotes.py --tickers AAPL MSFT TSLA --start 2024-01-01 --end 2025-12-26

# Specific columns only
python get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26 --columns Close Volume

# Monthly data instead of daily
python get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26 --interval 1mo

# Custom output file
python get_quotes.py --tickers AAPL MSFT --start 2024-01-01 --end 2025-12-26 --output my_stocks.json
```

#### Method 3: Import in Python Code
```python
from get_quotes import get_quotes

# Get data as JSON string
json_data = get_quotes('AAPL', '2024-01-01', '2025-12-26')

# Get data as Python dictionary
data = get_quotes(['AAPL', 'MSFT', 'TSLA'], 
                  '2024-01-01', 
                  '2025-12-26',
                  return_format='dict')

# Access the data
print(data['summary']['AAPL'])
for record in data['data']['AAPL']:
    print(record['Date'], record['Close'])
```

### Command-Line Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--tickers` | `-t` | Stock symbols (space-separated) | `--tickers AAPL MSFT` |
| `--start` | `-s` | Start date (YYYY-MM-DD) | `--start 2024-01-01` |
| `--end` | `-e` | End date (YYYY-MM-DD) | `--end 2025-12-26` |
| `--interval` | `-i` | Time interval (1d/1mo) | `--interval 1d` |
| `--columns` | `-c` | Specific columns | `--columns Close Volume` |
| `--output` | `-o` | Output filename | `--output stocks.json` |

### Common Stock Tickers
- **Stocks**: `AAPL` (Apple), `MSFT` (Microsoft), `GOOGL` (Google), `TSLA` (Tesla), `NVDA` (NVIDIA)
- **Indices**: `^GSPC` (S&P 500), `^DJI` (Dow Jones), `^IXIC` (NASDAQ), `^STOXX` (STOXX Europe)
- **ETFs**: `SPY` (S&P 500 ETF), `AAXJ` (Asia ex-Japan), `EWT` (Taiwan)

### Output Format
Creates a JSON file with:
```json
{
  "metadata": {
    "tickers": ["AAPL", "MSFT"],
    "start_date": "2024-01-01",
    "end_date": "2025-12-26",
    "interval": "1d"
  },
  "data": {
    "AAPL": [
      {
        "Date": "2024-01-01",
        "Open": 150.25,
        "High": 152.00,
        "Low": 149.50,
        "Close": 151.00,
        "Volume": 50000000
      }
    ]
  },
  "summary": {
    "AAPL": {
      "records": 252,
      "start_price": 150.25,
      "end_price": 175.50,
      "min_price": 145.00,
      "max_price": 180.00,
      "avg_price": 162.50
    }
  }
}
```

---

## 📑 edgar_filings_collector.py - SEC Filings

### What It Does
Fetches official SEC filings (10-K, 10-Q, 8-K, etc.) from the EDGAR database using the edgartools library. Extracts financial statements (balance sheet, income statement, cash flow) and company information directly from regulatory filings.

### Key Features
- Accepts both stock tickers (e.g., `AAPL`) and CIK numbers (e.g., `0000320193`)
- Fetches 10-K (annual), 10-Q (quarterly), 8-K (current events) reports
- Extracts structured financial statements when available
- Date range filtering
- Saves to JSON organized by date

### Basic Usage

#### Interactive Mode
```bash
python edgar_filings_collector.py
```
Follow the prompts:
- Tickers or CIK numbers (e.g., `AAPL MSFT` or `0000320193 0000789019`)
- Form types (`10-K 10-Q 8-K`)
- Date range (optional)
- Max filings per form type

#### Command-Line Mode

Get latest 10-K filings:
```bash
python edgar_filings_collector.py -t AAPL -f 10-K --limit 5 --save
```

Multiple companies and forms:
```bash
python edgar_filings_collector.py -t AAPL MSFT GOOGL -f 10-K 10-Q --limit 3 --save
```

With date range:
```bash
python edgar_filings_collector.py -t TSLA -f 10-K -s 2020-01-01 -e 2024-12-31 --save
```

Using CIK numbers instead of tickers:
```bash
python edgar_filings_collector.py -t 0000320193 -f 10-K 10-Q --limit 5 --save
```

### Command-Line Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--tickers` | `-t` | Stock tickers or CIK numbers | `-t AAPL MSFT` |
| `--forms` | `-f` | Form types (default: 10-K 10-Q 8-K) | `-f 10-K 10-Q` |
| `--start-date` | `-s` | Start date filter | `-s 2020-01-01` |
| `--end-date` | `-e` | End date filter | `-e 2024-12-31` |
| `--limit` | - | Max filings per form (default: 10) | `--limit 5` |
| `--save` | - | Save to SEC_filings folder | `--save` |
| `--output-dir` | - | Custom output directory | `--output-dir my_filings` |

### Output Structure

Files are saved to `SEC_filings/YYYY-MM-DD/{TICKER}_filings.json`:

```json
{
  "metadata": {
    "ticker": "AAPL",
    "extraction_date": "2025-12-27T14:30:00",
    "total_filings": 5
  },
  "company_info": {
    "name": "Apple Inc.",
    "cik": "0000320193",
    "ticker": "AAPL",
    "sic_code": "3571",
    "industry": "Computer Hardware"
  },
  "filings": [
    {
      "form": "10-K",
      "filing_date": "2024-11-01",
      "accession_number": "0000320193-24-000123",
      "period_of_report": "2024-09-30",
      "balance_sheet": {...},
      "income_statement": {...},
      "cash_flow": {...}
    }
  ]
}
```

### Common Form Types
- **10-K**: Annual report with comprehensive financial statements
- **10-Q**: Quarterly report with unaudited financials
- **8-K**: Current report for major events (earnings, acquisitions, etc.)
- **S-1**: Initial registration statement for IPOs
- **DEF 14A**: Proxy statement (executive compensation, voting matters)

### Tips
- edgartools automatically converts tickers to CIK numbers internally
- Some filings may not have structured financials (especially older ones or 8-Ks)
- 10-K and 10-Q filings are most reliable for extracting financial statements
- The tool uses your Columbia email (ld3179@columbia.edu) as identity per SEC requirements

---

## 📊 edgar_financial_parser.py - XBRL Parser

### What It Does
Fetches filings via EDGAR and parses XBRL statements (balance sheet, income statement, cash flow) into analysis-friendly JSON. Can also parse an existing JSON file without hitting the API.

### Usage

Fetch from EDGAR (10-K and 10-Q by default):
```bash
python edgar_financial_parser.py -t AAPL MSFT -f 10-K 10-Q --limit 4 --save
```

Date-filtered:
```bash
python edgar_financial_parser.py -t AAPL -f 10-K --start 2020-01-01 --end 2024-12-31 --limit 6 --save
```

Parse an existing JSON instead of calling the API:
```bash
python edgar_financial_parser.py --input-file SEC_financials/financials_2025-12-27.json --save
```

### Key Arguments
- `-t / --tickers`: Tickers or CIKs
- `-f / --forms`: Form types (default: 10-K 10-Q)
- `--start`, `--end`: Date filters (YYYY-MM-DD)
- `--limit`: Max filings per form (default: 4)
- `--save`: Write consolidated JSON to `SEC_financials/financials_YYYY-MM-DD.json`
- `--input-file`: Parse an existing JSON (skips SEC network calls; when set, tickers are optional)
- `--output-dir`: Custom output folder

### Output Shape (per ticker)
- Files are saved under `SEC_financials/<YYYY-MM-DD>/<TICKER>_financials.json` (date comes from `metadata.extracted_at` when present, otherwise today)
- Inside each file:
  - `metadata`: ticker, forms, start/end, limit, extracted_at
  - `filings`: list of filings with `form`, `filing_date`, `period_of_report`, `accession_number`, plus `balance_sheet`, `income_statement`, `cash_flow` (when XBRL available)

Tips:
- 10-K and 10-Q provide the richest XBRL data; some 8-Ks may lack statements.
- `--input-file` is useful to re-run transformations without refetching.
- When using `--input-file`, you can pass just the filename if it lives anywhere inside this repository; the parser will search the project folder for you.
- If you only want recent filings, set `--limit` to a small number (e.g., 3 or 4).

---

## 🎯 example_usage.py - Quick Start

### What It Does
A pre-configured script that downloads 10 years of data for major global stock indices. This is a ready-to-run example showing how to use `get_quotes()`.

### Usage
```bash
python example_usage.py
```

### What It Downloads
- `^GSPC` - S&P 500 (US stocks)
- `^STOXX` - STOXX Europe 600 (European stocks)
- `AAXJ` - Asia ex-Japan ETF (Asian stocks)
- `^N225` - Nikkei 225 (Japanese stocks)

### Output
- Creates `indices_10years.json` with 10 years of daily data
- Prints summary statistics for each index

### Customize It
Edit the file to use your own stocks:
```python
# Replace this line:
indices = ['^GSPC', '^STOXX', 'AAXJ', '^N225']

# With your stocks:
my_stocks = ['AAPL', 'MSFT', 'TSLA', 'NVDA']
data = get_quotes(my_stocks, start_date, end_date, return_format='dict')
```

---

## 📊 volatility_analysis.py - Volatility Analysis

### What It Does
Analyzes historical volatility of stocks from **multiple JSON and/or CSV files** and generates visual reports and JSON data files:
- Rolling volatility for 1-month, 3-month, 6-month, and 1-year periods
- Volatility quartiles (low, medium-low, medium-high, high zones)
- Color-coded charts showing volatility patterns over time
- Current volatility levels compared to historical ranges
- **JSON export** with full timeseries and statistics
- **Two calculation methods**: Log returns (default) or Basis points
- **Process multiple files at once** - combine data from different sources

### Calculation Methods

Choose between two return calculation methods:

#### Log Returns (default - recommended)
- Formula: `ln(P_t / P_t-1)`
- More mathematically sound for volatility
- Symmetric for gains and losses
- Time-additive (can sum across periods)
- **Use this for standard volatility analysis**

#### Basis Points (BPS)
- Formula: `(P_t - P_t-1) / P_t-1 × 10,000`
- Measures price changes in basis points (1 bp = 0.01%)
- More intuitive for some practitioners
- Useful when comparing to fixed income

### Supported File Formats

#### JSON Files
- Must contain `metadata.tickers` and `data` structure
- Can include multiple tickers in one file
- Use output from get_quotes.py or example_usage.py

#### CSV Files
- Must have columns: `Date`, `Close` (required)
- Optional columns: `Open`, `High`, `Low`, `Volume`
- One ticker per file
- Ticker name derived from filename (e.g., `AAPL.csv` → ticker is `AAPL`)
- Example CSV format:
  ```csv
  Date,Open,High,Low,Close,Volume
  2024-01-01,150.25,152.00,149.50,151.00,50000000
  2024-01-02,151.50,153.25,150.75,152.50,48000000
  ```

### Usage

#### 1. Analyze All Stocks in a JSON File (Default: Log Returns)
```bash
python volatility_analysis.py indices_10years.json
```
Analyzes all tickers using log returns and saves plots + JSON to `data/` folder.

#### 2. Analyze Multiple Files (JSON + CSV)
```bash
python volatility_analysis.py stocks.json AAPL.csv MSFT.csv TSLA.csv
```
Processes all files and combines tickers for analysis.

#### 3. Analyze Specific Stocks from Multiple Files
```bash
python volatility_analysis.py indices_10years.json tech_stocks.csv --tickers ^GSPC AAPL MSFT
```
Only analyzes the specified tickers found across all files.

#### 4. Use Basis Points Method
```bash
python volatility_analysis.py indices_10years.json --method bps
```
Calculates volatility using basis points instead of log returns.

#### 5. Custom Output Directory with Multiple Files
```bash
python volatility_analysis.py data/*.json data/*.csv --output-dir results
```
Processes all JSON and CSV files in the data folder.

#### 6. Combined Example
```bash
python volatility_analysis.py output.json AAPL.csv MSFT.csv TSLA.csv --tickers AAPL MSFT TSLA --output-dir my_analysis --method log
```

### Command-Line Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `files` | - | One or more JSON/CSV files (required) | `data.json stocks.csv` |
| `--tickers` | `-t` | Specific tickers to analyze | `--tickers AAPL MSFT` |
| `--output-dir` | `-o` | Directory for output plots and JSON | `--output-dir results` |
| `--method` | `-m` | Calculation method: log or bps | `--method log` |

### Understanding the Output

#### Console Report
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

#### Volatility Quartiles
- **Q1 (Low)**: Bottom 25% - Very calm market conditions
- **Q2 (Medium-Low)**: 25-50% - Below average volatility
- **Q3 (Medium-High)**: 50-75% - Above average volatility
- **Q4 (High)**: Top 25% - Elevated volatility, high risk

#### Chart Colors
- 🟢 **Green**: Q1 - Low volatility zone
- 🟡 **Yellow**: Q2 - Medium-low volatility
- 🟠 **Orange**: Q3 - Medium-high volatility
- 🔴 **Red**: Q4 - High volatility zone

#### Visual Charts
Each stock gets a 4-panel chart showing:
1. **1-Month Rolling Volatility** - Recent short-term volatility
2. **3-Month Rolling Volatility** - Medium-term trends
3. **6-Month Rolling Volatility** - Longer-term patterns
4. **1-Year Rolling Volatility** - Annual volatility cycles

Charts are saved as high-resolution PNG files (300 DPI) perfect for reports.

#### JSON Data Export
Each stock also gets a JSON file (e.g., `volatility_AAPL.json`) containing:
- **Calculation method used** (log or bps)
- **Current volatility** for all periods with quartile assignments
- **Statistical measures**: min, max, mean, std dev, percentiles
- **Complete timeseries data** with date, volatility, and quartile for each day

Example JSON structure:
```json
{
  "ticker": "AAPL",
  "method": "log",
  "calculation_date": "2025-12-26T10:30:00",
  "volatility_by_period": {
    "1M": {
      "current": 0.185,
      "current_quartile": "Q2 (Medium-Low)",
      "q1_25th_percentile": 0.152,
      "q2_50th_percentile": 0.198,
      "q3_75th_percentile": 0.254
    }
  },
  "timeseries": {
    "1M": [
      {"date": "2024-01-15", "volatility": 0.165, "quartile": "Q1 (Low)"},
      {"date": "2024-01-16", "volatility": 0.172, "quartile": "Q2 (Medium-Low)"}
    ]
  }
}
```

### Tips
- Requires at least 252 trading days (1 year) for meaningful 1-year volatility
- Shorter periods (1M, 3M) show data earlier in the time series
- Annualized volatility = standard deviation × √252

---

## 📁 Output Files

### Generated Files
- **output.json** / **indices_10years.json** - Stock price data from get_quotes.py
- **data/volatility_*.png** - Volatility charts from volatility_analysis.py
- **data/volatility_*.json** - Volatility data and statistics from volatility_analysis.py
- **company_tickers.json** - Reference file of company ticker symbols
- **S&P500Tickers.csv** - List of S&P 500 companies

---

## 🔄 Complete Workflow Example

Here's how to use all tools together:

### Step 1: Activate Environment
```bash
source .venv/bin/activate
```

### Step 2: Collect Data
```bash
# Option A: Use the example script
python example_usage.py

# Option B: Get your own stocks
python get_quotes.py --tickers AAPL MSFT TSLA NVDA GOOGL --start 2020-01-01 --end 2025-12-26 --output my_stocks.json
```

### Step 3: Analyze Volatility
```bash
# Single file analysis (using log returns - recommended)
python volatility_analysis.py my_stocks.json

# Multiple files (JSON + CSV)
python volatility_analysis.py my_stocks.json AAPL.csv MSFT.csv

# Or use basis points method
python volatility_analysis.py my_stocks.json --method bps

# Analyze specific tickers from multiple sources
python volatility_analysis.py indices.json tech_stocks.csv --tickers AAPL TSLA ^GSPC --output-dir tech_analysis --method log
```

### Step 4: Review Results
- Check console output for volatility reports
- View PNG charts in the `data/` folder (or your custom output directory)
- Open JSON files for detailed volatility timeseries and statistics

### Step 5: Deactivate
```bash
deactivate
```

---

## 🛠️ Troubleshooting

### Error: "No such file or directory: venv/bin/activate"
**Solution**: Your virtual environment is `.venv` (with a dot):
```bash
source .venv/bin/activate
```

### Error: "ModuleNotFoundError: No module named 'yfinance'"
**Solution**: Install required packages:
```bash
pip install yfinance pandas numpy matplotlib
```

### Error: "JSON file not found"
**Solution**: 
- Check the file path is correct
- Run `get_quotes.py` first to create the JSON file
- Use quotes if filename has spaces: `"my data.json"`

### Error: "No data for ticker"
**Solution**:
- Ticker not in JSON file - check `metadata.tickers` list
- Ticker spelling must match exactly (case-sensitive)
- For indices, use correct format: `^GSPC` not `GSPC`

### Warning: "Not enough data"
**Solution**: Volatility calculations need:
- 21 days for 1-month
- 63 days for 3-month
- 126 days for 6-month
- 252 days for 1-year

Fetch more historical data with an earlier start date.

### Python Command Not Found
**Solution**: Use `python3` instead:
```bash
python3 get_quotes.py
python3 volatility_analysis.py indices_10years.json
```

---

## 📚 Additional Resources

### Popular Stock Symbols
- **Tech**: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA
- **Finance**: JPM, BAC, GS, MS, V, MA
- **Energy**: XOM, CVX, COP, SLB
- **Healthcare**: JNJ, UNH, PFE, ABBV

### Index Symbols
- **US**: ^GSPC (S&P 500), ^DJI (Dow), ^IXIC (NASDAQ)
- **Global**: ^FTSE (UK), ^GDAXI (Germany), ^N225 (Japan)
- **Emerging**: EEM (Emerging Markets), EWZ (Brazil), FXI (China)

### Time Periods
- **Daily data**: `--interval 1d`
- **Monthly data**: `--interval 1mo`
- **Start dates**: Use YYYY-MM-DD format (e.g., `2020-01-01`)

---

## 📝 Notes

- All dates use YYYY-MM-DD format
- Ticker symbols are case-sensitive
- Index symbols often start with `^` (e.g., `^GSPC`)
- Data comes from Yahoo Finance via yfinance library
- Charts use annualized volatility (standard deviation × √252)
- Virtual environment keeps packages isolated from system Python

---

**Questions or issues?** Check the Troubleshooting section or review the individual script help:
```bash
python get_quotes.py --help
python volatility_analysis.py --help
python mahalanobis_regime.py --help
```

---

## 🎯 mahalanobis_regime.py - Multivariate Stress Detection

### What It Does
Identifies market stress periods vs normal times using Mahalanobis distance—a multivariate technique that accounts for correlations between multiple volatility series. Outputs both discrete stress regimes (Normal, Elevated, High, Extreme) and continuous stress scores.

### How It Works
1. **Loads** daily volatilities from one or more `vol_ratios.json` files
2. **Calculates** Mahalanobis distance using rolling covariance (252-day window)
3. **Assigns** discrete regimes via percentile buckets:
   - **Normal**: ≤50th percentile
   - **Elevated**: 50th–75th percentile
   - **High**: 75th–90th percentile
   - **Extreme**: >90th percentile
4. **Computes** continuous stress scores using chi-squared p-values (0=normal, 1=extreme stress)
5. **Exports** results to `Volatility_output/regimes/mahalanobis_regimes.json`

### Basic Usage

#### Default (Single File)
```bash
python mahalanobis_regime.py
```
Uses `Volatility_output/ratios/vol_ratios.json` and 1M volatilities.

#### Multiple Input Files
```bash
python mahalanobis_regime.py --input file1.json file2.json file3.json
```

#### Custom Options
```bash
python mahalanobis_regime.py --input Volatility_output/ratios/vol_ratios.json \
                              --metric 3M \
                              --window 252 \
                              --output-dir ./stress_regimes
```

### Parameters
- `--input, -i`: One or more vol_ratios.json files (space-separated)
- `--metric, -m`: Volatility metric to use (default: `1M`). Options: `1M`, `3M`, `6M`, `1Y`
- `--window, -w`: Rolling window size in trading days (default: `252`)
- `--output-dir, -o`: Output directory (default: `Volatility_output/regimes`)

### Example Workflows

**1. Analyze single asset regime:**
```bash
python mahalanobis_regime.py --input Volatility_output/ratios/vol_ratios.json --metric 1M
```

**2. Multi-file stress analysis (combining different vol sources):**
```bash
python mahalanobis_regime.py --input vol_ratios_stocks.json vol_ratios_bonds.json vol_ratios_commodities.json
```

**3. Use 3-month volatility with custom window:**
```bash
python mahalanobis_regime.py --metric 3M --window 63
```

### Quickstart (copy/paste)
- Default inputs and 1M metric: `python mahalanobis_regime.py`
- Combine multiple vol sources: `python mahalanobis_regime.py --input Volatility_output/ratios/vol_ratios.json other_vols.json`
- Custom metric/window/output dir: `python mahalanobis_regime.py --metric 3M --window 126 --output-dir Volatility_output/regimes_3M`

### Sample Output Location
- See the consolidated sample descriptions in [sample_output/README.md](sample_output/README.md)
- Default runtime output is written to [Volatility_output/regimes/mahalanobis_regimes.json](Volatility_output/regimes/mahalanobis_regimes.json)

### Output

**File**: `Volatility_output/regimes/mahalanobis_regimes.json`

**Structure**:
```json
{
  "calculation_date": "2025-12-27T14:32:10.123456",
  "regimes": {
    "2020-01-02": {
      "distance": 1.234,
      "percentile": 45.2,
      "regime": "Normal"
    },
    "2020-01-03": {
      "distance": 2.567,
      "percentile": 72.1,
      "regime": "Elevated"
    }
  },
  "continuous_stress": {
    "2020-01-02": 0.123,
    "2020-01-03": 0.456
  }
}
```

### Interpretation

- **Discrete Regimes**: Use for classification, backtesting, or rule-based trading signals
- **Continuous Stress Scores**: Use for model inputs, risk weighting, or sensitivity analysis
- **High Percentile Readings**: Indicate unusual multivariate combinations across assets (market dislocation)
- **Low Percentile Readings**: Indicate correlated movement consistent with historical norms
