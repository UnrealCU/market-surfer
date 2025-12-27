# Financial Enlightenment - Stock Analysis Toolkit

A comprehensive Python toolkit for collecting and analyzing stock market data. This toolkit enables you to fetch historical stock prices, analyze volatility patterns, and generate visual reports.

---

## 📋 Table of Contents
- [Setup](#setup)
- [Get_quotes.py - Data Collection](#get_quotespy---data-collection)
- [example_usage.py - Quick Start](#example_usagepy---quick-start)
- [volatility_analysis.py - Volatility Analysis](#volatility_analysispy---volatility-analysis)
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
pip install yfinance pandas numpy matplotlib
```

### 3. Deactivate When Done
```bash
deactivate
```

---

## 📥 Get_quotes.py - Data Collection

### What It Does
Downloads historical stock price data from Yahoo Finance and saves it as JSON. This is your data collection tool that fetches OHLCV (Open, High, Low, Close, Volume) data for any stock or index.

### Basic Usage

#### Method 1: Command Line (Interactive)
```bash
python Get_quotes.py
```
Follow the prompts to enter:
- Tickers (e.g., `AAPL MSFT TSLA`)
- Start date (e.g., `2024-01-01`)
- End date (e.g., `2025-12-26`)
- Interval (`1d` for daily, `1mo` for monthly)
- Columns (press Enter for all, or specify like `Close Volume`)

#### Method 2: Command Line (Direct)
```bash
# Single stock
python Get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26

# Multiple stocks
python Get_quotes.py --tickers AAPL MSFT TSLA --start 2024-01-01 --end 2025-12-26

# Specific columns only
python Get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26 --columns Close Volume

# Monthly data instead of daily
python Get_quotes.py --tickers AAPL --start 2024-01-01 --end 2025-12-26 --interval 1mo

# Custom output file
python Get_quotes.py --tickers AAPL MSFT --start 2024-01-01 --end 2025-12-26 --output my_stocks.json
```

#### Method 3: Import in Python Code
```python
from Get_quotes import get_quotes

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
- Use output from Get_quotes.py or example_usage.py

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
- **output.json** / **indices_10years.json** - Stock price data from Get_quotes.py
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
python Get_quotes.py --tickers AAPL MSFT TSLA NVDA GOOGL --start 2020-01-01 --end 2025-12-26 --output my_stocks.json
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
- Run `Get_quotes.py` first to create the JSON file
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
python3 Get_quotes.py
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
python Get_quotes.py --help
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
