#!/usr/bin/env python3
"""
Volatility Analysis Tool
Calculates 1m/3m/6m/1y rolling volatility and plots quartile distributions

Usage:
    python volatility_analysis.py <file1> [file2 file3 ...] [--output-dir <dir>] [--tickers <ticker1> <ticker2> ...] [--method <log|bps>]
    
Examples:
    python volatility_analysis.py indices_10years.json
    python volatility_analysis.py data1.json data2.csv --output-dir results
    python volatility_analysis.py stocks.json AAPL.csv MSFT.csv --tickers AAPL MSFT
    python volatility_analysis.py indices_10years.json --method bps
"""

import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
import os
import argparse
import sys
import glob
from pathlib import Path

def find_files(file_patterns, search_root=None):
    """
    Find files by searching recursively in the project directory.
    
    Args:
        file_patterns: List of file paths, patterns, or filenames
        search_root: Root directory to search from (default: script directory)
        
    Returns:
        List of absolute paths to files found
    """
    if search_root is None:
        search_root = os.path.dirname(os.path.abspath(__file__))
    
    found_files = []
    
    for pattern in file_patterns:
        # If it's an absolute path or exists as-is, use it directly
        if os.path.isabs(pattern) or os.path.exists(pattern):
            # Handle glob patterns in existing paths
            matches = glob.glob(pattern)
            if matches:
                found_files.extend([os.path.abspath(f) for f in matches])
            elif os.path.exists(pattern):
                found_files.append(os.path.abspath(pattern))
            continue
        
        # Check if pattern has wildcards
        if '*' in pattern or '?' in pattern:
            # Search recursively for files matching pattern
            search_pattern = os.path.join(search_root, '**', pattern)
            matches = glob.glob(search_pattern, recursive=True)
            found_files.extend([os.path.abspath(f) for f in matches])
        else:
            # Search for exact filename recursively
            for root, dirs, files in os.walk(search_root):
                # Skip hidden directories and common exclusions
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'old_code']]
                
                if pattern in files:
                    found_files.append(os.path.abspath(os.path.join(root, pattern)))
    
    return found_files

def load_csv_file(csv_file):
    """
    Load data from a CSV file
    
    Args:
        csv_file: Path to CSV file with columns: Date, Open, High, Low, Close, Volume
                  OR FRED format: observation_date, <ticker_name>
        
    Returns:
        Tuple: (DataFrame with stock price data, is_fred_data boolean)
    """
    df = pd.read_csv(csv_file)
    is_fred_data = False
    
    # Handle FRED data format (observation_date + ticker column)
    if 'observation_date' in df.columns:
        df.rename(columns={'observation_date': 'Date'}, inplace=True)
        is_fred_data = True
        
        # Find the value column (usually the second column that's not Date)
        value_cols = [col for col in df.columns if col not in ['Date', 'observation_date']]
        if value_cols:
            # Use first non-date column as the Close price
            df.rename(columns={value_cols[0]: 'Close'}, inplace=True)
    
    # Check for required columns after potential renaming
    if 'Date' not in df.columns or 'Close' not in df.columns:
        raise ValueError(f"CSV file {csv_file} must contain 'Date' and 'Close' columns (or FRED format: observation_date + value column)")
    
    # Ensure 'Close' is numeric; drop rows with missing values
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    
    return df, is_fred_data

def load_data(json_file):
    """
    Load data from any JSON file
    
    Args:
        json_file: Path to JSON file containing stock data
        
    Returns:
        Dictionary with metadata and stock price data
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data

def load_file(file_path):
    """
    Load data from JSON or CSV file
    
    Args:
        file_path: Path to JSON or CSV file
        
    Returns:
        Dictionary with structure: {'ticker': ticker_name, 'data': DataFrame, 'is_fred': boolean}
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.json':
        # Load JSON file
        data = load_data(file_path)
        # Return in standard format
        return {'format': 'json', 'data': data, 'is_fred': False}
    
    elif file_ext == '.csv':
        # Load CSV file - derive ticker name from filename
        ticker = os.path.splitext(os.path.basename(file_path))[0]
        df, is_fred = load_csv_file(file_path)
        # Convert to standard format
        return {
            'format': 'csv',
            'ticker': ticker,
            'data': df,
            'is_fred': is_fred
        }
    
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Use .json or .csv files.")

def calculate_volatility(df, windows={'1M': 21, '3M': 63, '6M': 126, '1Y': 252}, method='log', is_fred_data=False):
    """
    Calculate rolling realized volatility for different time periods.

    Args:
        df: DataFrame with 'Close' prices and 'Date' index
        windows: Dictionary of period names and trading days (N)
        method: 'log' for log returns, 'bps' for basis points differences
        is_fred_data: True if data is from FRED (yields in percent units)

    Returns:
        DataFrame with volatility columns for each period, including rolling means.
    """
    # Calculate returns based on method and data type
    if method == 'log':
        # Log returns: ln(P_t / P_{t-1})
        df['Returns'] = np.log(df['Close'] / df['Close'].shift(1))
    else:  # bps
        if is_fred_data:
            # FRED yields (percent units): Δy_t(bp) = 100 * (y_t - y_{t-1})
            df['Returns'] = 100 * (df['Close'] - df['Close'].shift(1))
        else:
            # Prices: basis points from percent change: 10,000 * ΔP/P
            df['Returns'] = 10000 * df['Close'].pct_change()

    # Calculate realized volatility for each window
    for period_name, N in windows.items():
        # Rolling mean μ_t over N days
        df[f'RollMean_{period_name}'] = df['Returns'].rolling(window=N).mean()
        # Rolling variance with ddof=1 (unbiased sample variance)
        roll_var = df['Returns'].rolling(window=N).var(ddof=1)
        # Rolling std (realized vol)
        roll_std = np.sqrt(roll_var)
        # Annualize (optional per design): multiply by √252
        df[f'Vol_{period_name}'] = roll_std * np.sqrt(252)

    return df

def calculate_quartiles(series):
    """Calculate quartile breakpoints"""
    q1 = series.quantile(0.25)
    q2 = series.quantile(0.50)
    q3 = series.quantile(0.75)
    return q1, q2, q3

def assign_quartile(value, q1, q2, q3):
    """Assign a value to a quartile"""
    if pd.isna(value):
        return None
    elif value <= q1:
        return 'Q1 (Low)'
    elif value <= q2:
        return 'Q2 (Medium-Low)'
    elif value <= q3:
        return 'Q3 (Medium-High)'
    else:
        return 'Q4 (High)'

def plot_volatility_quartiles(ticker_data, ticker_name, method='log', save_path=None):
    """
    Plot volatility time series with quartile bands
    
    Args:
        ticker_data: DataFrame with volatility columns
        ticker_name: Name of the ticker for plot title
        save_path: Optional path to save the plot
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'{ticker_name} - Volatility Analysis by Period', fontsize=16, fontweight='bold')
    
    periods = ['1M', '3M', '6M', '1Y']
    colors = {'Q1 (Low)': 'green', 'Q2 (Medium-Low)': 'yellow', 
              'Q3 (Medium-High)': 'orange', 'Q4 (High)': 'red'}
    
    for idx, period in enumerate(periods):
        ax = axes[idx // 2, idx % 2]
        col_name = f'Vol_{period}'
        
        if col_name not in ticker_data.columns:
            continue
        
        # Get volatility data
        vol_data = ticker_data[col_name].dropna()
        
        if len(vol_data) == 0:
            continue
        
        # Calculate quartiles
        q1, q2, q3 = calculate_quartiles(vol_data)
        
        # Plot volatility line
        ax.plot(vol_data.index, vol_data.values, linewidth=1, color='blue', alpha=0.6)
        
        # Add quartile horizontal lines (format based on method)
        if method == 'bps':
            ax.axhline(y=q1, color='green', linestyle='--', linewidth=1, label=f'Q1: {q1:.1f} bp')
            ax.axhline(y=q2, color='yellow', linestyle='--', linewidth=1, label=f'Q2: {q2:.1f} bp')
            ax.axhline(y=q3, color='orange', linestyle='--', linewidth=1, label=f'Q3: {q3:.1f} bp')
        else:
            ax.axhline(y=q1, color='green', linestyle='--', linewidth=1, label=f'Q1: {q1:.2%}')
            ax.axhline(y=q2, color='yellow', linestyle='--', linewidth=1, label=f'Q2: {q2:.2%}')
            ax.axhline(y=q3, color='orange', linestyle='--', linewidth=1, label=f'Q3: {q3:.2%}')
        
        # Fill between quartiles
        ax.fill_between(vol_data.index, 0, q1, alpha=0.1, color='green')
        ax.fill_between(vol_data.index, q1, q2, alpha=0.1, color='yellow')
        ax.fill_between(vol_data.index, q2, q3, alpha=0.1, color='orange')
        ax.fill_between(vol_data.index, q3, vol_data.max(), alpha=0.1, color='red')
        
        ax.set_title(f'{period} Rolling Volatility (Annualized)', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Volatility (bp)' if method == 'bps' else 'Volatility (%)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        # Format y-axis values based on method
        if method == 'bps':
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}'))
        else:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved plot to: {save_path}")
    
    plt.close()

def export_volatility_json(ticker_data, ticker_name, output_dir, method):
    """
    Export volatility data to JSON file
    
    Args:
        ticker_data: DataFrame with volatility columns
        ticker_name: Name of the ticker
        output_dir: Directory to save JSON file
        method: 'log' or 'bps' - the calculation method used
    """
    periods = ['1M', '3M', '6M', '1Y']
    
    volatility_data = {
        'ticker': ticker_name,
        'method': method,
        'units': 'bp' if method == 'bps' else 'percent',
        'calculation_date': datetime.now().isoformat(),
        'volatility_by_period': {},
        'timeseries': {}
    }
    
    for period in periods:
        col_name = f'Vol_{period}'
        
        if col_name not in ticker_data.columns:
            continue
        
        vol_data = ticker_data[col_name].dropna()
        
        if len(vol_data) == 0:
            continue
        
        # Calculate statistics
        q1, q2, q3 = calculate_quartiles(vol_data)
        current_vol = vol_data.iloc[-1]
        current_quartile = assign_quartile(current_vol, q1, q2, q3)
        
        # Store period statistics
        volatility_data['volatility_by_period'][period] = {
            'current': float(current_vol),
            'current_quartile': current_quartile,
            'q1_25th_percentile': float(q1),
            'q2_50th_percentile': float(q2),
            'q3_75th_percentile': float(q3),
            'min': float(vol_data.min()),
            'max': float(vol_data.max()),
            'mean': float(vol_data.mean()),
            'std_dev': float(vol_data.std())
        }
        
        # Store timeseries data
        volatility_data['timeseries'][period] = [
            {
                'date': idx.strftime('%Y-%m-%d'),
                'volatility': float(val),
                'quartile': assign_quartile(val, q1, q2, q3)
            }
            for idx, val in vol_data.items()
        ]
    
    # Save to JSON
    filename = f'volatility_{ticker_name.replace("^", "").replace(":", "")}.json'
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(volatility_data, f, indent=2)
    
    print(f"Saved volatility data to: {filepath}")

def generate_volatility_report(ticker_data, ticker_name, method='log'):
    """Generate text report of current volatility quartiles with unit-aware formatting"""
    print(f"\n{'='*60}")
    print(f"VOLATILITY REPORT: {ticker_name}")
    print(f"{'='*60}")
    
    periods = ['1M', '3M', '6M', '1Y']
    
    for period in periods:
        col_name = f'Vol_{period}'
        
        if col_name not in ticker_data.columns:
            continue
        
        vol_data = ticker_data[col_name].dropna()
        
        if len(vol_data) == 0:
            continue
        
        # Get current (latest) volatility
        current_vol = vol_data.iloc[-1]
        
        # Calculate quartiles
        q1, q2, q3 = calculate_quartiles(vol_data)
        
        # Assign current quartile
        current_quartile = assign_quartile(current_vol, q1, q2, q3)
        
        print(f"\n{period} Rolling Volatility:")
        if method == 'bps':
            print(f"  Current: {current_vol:.1f} bp [{current_quartile}]")
            print(f"  Q1 (25th percentile): {q1:.1f} bp")
            print(f"  Q2 (50th percentile): {q2:.1f} bp")
            print(f"  Q3 (75th percentile): {q3:.1f} bp")
            print(f"  Min: {vol_data.min():.1f} bp")
            print(f"  Max: {vol_data.max():.1f} bp")
        else:
            print(f"  Current: {current_vol:.2%} [{current_quartile}]")
            print(f"  Q1 (25th percentile): {q1:.2%}")
            print(f"  Q2 (50th percentile): {q2:.2%}")
            print(f"  Q3 (75th percentile): {q3:.2%}")
            print(f"  Min: {vol_data.min():.2%}")
            print(f"  Max: {vol_data.max():.2%}")

def main():
    """Main function to run volatility analysis"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Analyze volatility of stock data from JSON/CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python volatility_analysis.py indices_10years.json
  python volatility_analysis.py data1.json data2.csv --output-dir results
  python volatility_analysis.py stocks.json AAPL.csv MSFT.csv --tickers AAPL MSFT
  python volatility_analysis.py indices_10years.json --method bps
        ''')
    
    parser.add_argument('files', nargs='+', help='Path(s) to JSON or CSV files containing stock data')
    parser.add_argument('--output-dir', '-o', default='Volatility_output', 
                        help='Directory to save output plots and JSON (default: Volatility_output)')
    parser.add_argument('--tickers', '-t', nargs='+', 
                        help='Specific tickers to analyze (default: all tickers in files)')
    parser.add_argument('--method', '-m', choices=['log', 'bps'], default='log',
                        help='Return calculation method: log for log returns (default), bps for basis points')
    
    args = parser.parse_args()
    
    # Discover files using search
    print("Searching for files...")
    found_files = find_files(args.files)
    
    if not found_files:
        print(f"Error: No files found matching: {', '.join(args.files)}")
        print(f"Searched in: {os.path.dirname(os.path.abspath(__file__))}")
        sys.exit(1)
    
    # Show what was found
    print(f"Found {len(found_files)} file(s):")
    for f in found_files:
        rel_path = os.path.relpath(f, os.path.dirname(os.path.abspath(__file__)))
        print(f"  {rel_path}")
    print()
    
    # Use found files for processing
    args.files = found_files
    
    # Create output folder and subdirectories if they don't exist
    os.makedirs(args.output_dir, exist_ok=True)
    graphs_dir = os.path.join(args.output_dir, 'graphs')
    data_dir = os.path.join(args.output_dir, 'data')
    os.makedirs(graphs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    # Print method info
    print(f"Using return calculation method: {args.method.upper()}")
    if args.method == 'log':
        print("  (Log returns: ln(P_t / P_t-1))")
    else:
        print("  (Basis points: (P_t - P_t-1) / P_t-1 * 10000)")
    print()
    
    # Collect all ticker data from all files
    all_ticker_data = {}
    ticker_metadata = {}  # Track whether each ticker is FRED data
    
    for file_path in args.files:
        print(f"Loading data from {file_path}...")
        
        try:
            file_data = load_file(file_path)
            
            if file_data['format'] == 'json':
                # JSON file may contain multiple tickers
                json_data = file_data['data']
                if 'metadata' in json_data and 'tickers' in json_data['metadata']:
                    file_tickers = json_data['metadata']['tickers']
                    print(f"  Found {len(file_tickers)} tickers: {', '.join(file_tickers)}")
                    
                    for ticker in file_tickers:
                        if ticker in json_data['data']:
                            df = pd.DataFrame(json_data['data'][ticker])
                            # Ensure Close numeric and drop missing
                            df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                            df = df.dropna(subset=['Close'])
                            df['Date'] = pd.to_datetime(df['Date'])
                            df.set_index('Date', inplace=True)
                            df.sort_index(inplace=True)
                            all_ticker_data[ticker] = df
                            ticker_metadata[ticker] = False  # JSON data assumed to be stock prices
                else:
                    print(f"  Warning: JSON file missing metadata.tickers structure")
            
            elif file_data['format'] == 'csv':
                # CSV file contains single ticker
                ticker = file_data['ticker']
                is_fred = file_data['is_fred']
                print(f"  Loaded ticker: {ticker}" + (" (FRED yield data)" if is_fred else ""))
                df = file_data['data']
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df.sort_index(inplace=True)
                all_ticker_data[ticker] = df
                ticker_metadata[ticker] = is_fred
                
        except Exception as e:
            print(f"  Error loading {file_path}: {str(e)}")
            continue
    
    if not all_ticker_data:
        print("\nError: No valid data loaded from any file!")
        sys.exit(1)
    
    # Determine which tickers to analyze
    if args.tickers:
        tickers = args.tickers
        print(f"\nAnalyzing specified tickers: {', '.join(tickers)}")
        # Validate specified tickers exist
        missing = [t for t in tickers if t not in all_ticker_data]
        if missing:
            print(f"Warning: Tickers not found in loaded data: {', '.join(missing)}")
            tickers = [t for t in tickers if t in all_ticker_data]
    else:
        tickers = list(all_ticker_data.keys())
        print(f"\nAnalyzing all loaded tickers ({len(tickers)}): {', '.join(tickers)}")
    
    if not tickers:
        print("\nError: No tickers to analyze!")
        sys.exit(1)
    
    # Process each ticker
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        
        df = all_ticker_data[ticker]
        is_fred = ticker_metadata.get(ticker, False)
        
        # Calculate volatility using specified method
        df = calculate_volatility(df, method=args.method, is_fred_data=is_fred)
        
        # Generate report
        generate_volatility_report(df, ticker, method=args.method)
        
        # Plot and save to graphs folder
        plot_path = os.path.join(graphs_dir, f'volatility_{ticker.replace("^", "").replace(":", "")}.png')
        plot_volatility_quartiles(df, ticker, method=args.method, save_path=plot_path)
        
        # Export volatility data to JSON in data folder
        export_volatility_json(df, ticker, data_dir, args.method)
    
    print(f"\n{'='*60}")
    print(f"Analysis complete! Processed {len(tickers)} ticker(s) from {len(args.files)} file(s).")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
