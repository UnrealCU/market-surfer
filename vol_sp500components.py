#!/usr/bin/env python3
"""
S&P 500 Components Volatility Analysis
Analyzes 1m/3m rolling annualized volatility for S&P 500 stocks from last 3 years of price data.
Outputs results organized by GICS sector.

Usage:
    python vol_sp500components.py [--output-dir <dir>] [--lookback-years 3]

Examples:
    python vol_sp500components.py
    python vol_sp500components.py --output-dir volatility_output --lookback-years 3
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import argparse
import sys
from pathlib import Path
from collections import defaultdict

def load_spy3y(filepath):
    """
    Load spy_3y.json containing price data for S&P 500 stocks
    
    Args:
        filepath: Path to spy_3y.json
        
    Returns:
        Tuple: (data dict, metadata dict)
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

def load_gics_mapping(filepath):
    """
    Load S&P500Tickers.csv and extract GICS sector mapping
    
    Args:
        filepath: Path to S&P500Tickers.csv
        
    Returns:
        Dict mapping ticker -> GICS Sector
    """
    df = pd.read_csv(filepath)
    gics_map = {}
    
    for _, row in df.iterrows():
        ticker = row['Symbol']
        sector = row['GICS Sector']
        gics_map[ticker] = sector
    
    return gics_map

def parse_date(date_str):
    """
    Parse date string, handling both YYYY-MM-DD and YYYY-MM-DD HH:MM:SS formats
    """
    if isinstance(date_str, str):
        if ' ' in date_str:
            date_str = date_str.split()[0]
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    return None

def calculate_volatility(prices, method='log'):
    """
    Calculate annualized volatility from price series
    
    Args:
        prices: List or Series of closing prices, sorted by date
        method: 'log' for log returns (default)
        
    Returns:
        Annualized volatility (as decimal, e.g., 0.25 = 25%)
    """
    if len(prices) < 2:
        return np.nan
    
    prices_array = np.array(prices, dtype=float)
    
    if method == 'log':
        returns = np.diff(np.log(prices_array))
    else:
        returns = np.diff(prices_array) / prices_array[:-1]
    
    if len(returns) == 0:
        return np.nan
    
    # Calculate standard deviation and annualize by sqrt(252)
    daily_vol = np.std(returns, ddof=1)
    annualized_vol = daily_vol * np.sqrt(252)
    
    return annualized_vol

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

def calculate_rolling_volatility(df, windows={'1M': 21, '3M': 63}):
    """
    Calculate rolling realized volatility for different time periods
    
    Args:
        df: DataFrame with 'Close' prices indexed by Date
        windows: Dictionary of period names and trading days
        
    Returns:
        DataFrame with volatility columns for each period
    """
    df['Returns'] = np.log(df['Close'] / df['Close'].shift(1))
    
    for period_name, N in windows.items():
        roll_std = df['Returns'].rolling(window=N).std()
        df[f'Vol_{period_name}'] = roll_std * np.sqrt(252)
    
    return df

def process_ticker(ticker, price_data, gics_map, lookback_days=750):
    """
    Process a single ticker and calculate volatility metrics
    
    Args:
        ticker: Ticker symbol
        price_data: List of price dicts with 'Date' and 'Close'
        gics_map: Dict mapping ticker to GICS sector
        lookback_days: Number of days to look back from most recent
        
    Returns:
        Dict with volatility metrics or None if insufficient data
    """
    if not price_data or len(price_data) < 63:  # Need at least 3 months of data
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(price_data)
    
    # Parse dates and ensure numeric Close
    df['Date'] = df['Date'].apply(parse_date)
    df = df[df['Date'].notna()]  # Remove rows with invalid dates
    
    if len(df) < 63:
        return None
    
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df[df['Close'].notna()]
    
    if len(df) < 63:
        return None
    
    df = df.sort_values('Date').reset_index(drop=True)
    df.set_index('Date', inplace=True)
    
    # Calculate rolling volatility
    df = calculate_rolling_volatility(df, windows={'1M': 21, '3M': 63})
    
    # Get current (latest) volatility values
    vol_1m = df['Vol_1M'].iloc[-1]
    vol_3m = df['Vol_3M'].iloc[-1]
    
    # Calculate historical stats
    vol_1m_series = df['Vol_1M'].dropna()
    vol_3m_series = df['Vol_3M'].dropna()
    
    # Calculate quartiles for each period
    q1_1m, q2_1m, q3_1m = calculate_quartiles(vol_1m_series) if len(vol_1m_series) > 0 else (None, None, None)
    q1_3m, q2_3m, q3_3m = calculate_quartiles(vol_3m_series) if len(vol_3m_series) > 0 else (None, None, None)
    
    gics_sector = gics_map.get(ticker, 'Unclassified_Tickers')
    
    result = {
        'ticker': ticker,
        'gics_sector': gics_sector,
        'method': 'log',
        'units': 'percent',
        'calculation_date': datetime.now().isoformat(),
        'num_data_points': len(df),
        'date_range_start': df.index[0].strftime('%Y-%m-%d'),
        'date_range_end': df.index[-1].strftime('%Y-%m-%d'),
        'volatility_by_period': {},
        'timeseries': {}
    }
    
    # Add 1M volatility data
    if not pd.isna(vol_1m) and q1_1m is not None:
        result['volatility_by_period']['1M'] = {
            'current': float(vol_1m),
            'current_quartile': assign_quartile(vol_1m, q1_1m, q2_1m, q3_1m),
            'q1_25th_percentile': float(q1_1m),
            'q2_50th_percentile': float(q2_1m),
            'q3_75th_percentile': float(q3_1m),
            'min': float(vol_1m_series.min()),
            'max': float(vol_1m_series.max()),
            'mean': float(vol_1m_series.mean()),
            'std_dev': float(vol_1m_series.std())
        }
        # Add timeseries for 1M
        result['timeseries']['1M'] = [
            {
                'date': idx.strftime('%Y-%m-%d'),
                'volatility': float(val),
                'quartile': assign_quartile(val, q1_1m, q2_1m, q3_1m)
            }
            for idx, val in vol_1m_series.items()
        ]
    
    # Add 3M volatility data
    if not pd.isna(vol_3m) and q1_3m is not None:
        result['volatility_by_period']['3M'] = {
            'current': float(vol_3m),
            'current_quartile': assign_quartile(vol_3m, q1_3m, q2_3m, q3_3m),
            'q1_25th_percentile': float(q1_3m),
            'q2_50th_percentile': float(q2_3m),
            'q3_75th_percentile': float(q3_3m),
            'min': float(vol_3m_series.min()),
            'max': float(vol_3m_series.max()),
            'mean': float(vol_3m_series.mean()),
            'std_dev': float(vol_3m_series.std())
        }
        # Add timeseries for 3M
        result['timeseries']['3M'] = [
            {
                'date': idx.strftime('%Y-%m-%d'),
                'volatility': float(val),
                'quartile': assign_quartile(val, q1_3m, q2_3m, q3_3m)
            }
            for idx, val in vol_3m_series.items()
        ]
    
    return result

def generate_volatility_report(ticker_data):
    """Generate text report of volatility metrics"""
    report = f"\n{'='*80}\n"
    report += f"TICKER: {ticker_data['ticker']}\n"
    report += f"SECTOR: {ticker_data['gics_sector']}\n"
    report += f"{'='*80}\n\n"
    
    report += "1-MONTH ROLLING VOLATILITY (Annualized):\n"
    if ticker_data['current_vol_1m']:
        report += f"  Current:  {ticker_data['current_vol_1m']:.2%}\n"
        report += f"  Mean:     {ticker_data['vol_1m_mean']:.2%}\n"
        report += f"  Min:      {ticker_data['vol_1m_min']:.2%}\n"
        report += f"  Max:      {ticker_data['vol_1m_max']:.2%}\n"
    else:
        report += "  [Insufficient data]\n"
    
    report += "\n3-MONTH ROLLING VOLATILITY (Annualized):\n"
    if ticker_data['current_vol_3m']:
        report += f"  Current:  {ticker_data['current_vol_3m']:.2%}\n"
        report += f"  Mean:     {ticker_data['vol_3m_mean']:.2%}\n"
        report += f"  Min:      {ticker_data['vol_3m_min']:.2%}\n"
        report += f"  Max:      {ticker_data['vol_3m_max']:.2%}\n"
    else:
        report += "  [Insufficient data]\n"
    
    report += f"\nData Points: {ticker_data['num_data_points']}\n"
    report += f"Period: {ticker_data['date_range_start']} to {ticker_data['date_range_end']}\n"
    
    return report

def export_volatility_json(ticker_data, output_dir):
    """
    Export volatility data to JSON file in sector directory
    
    Args:
        ticker_data: Dict with volatility metrics
        output_dir: Output directory path
    """
    sector = ticker_data['gics_sector'].replace(' ', '_')
    sector_dir = os.path.join(output_dir, sector)
    os.makedirs(sector_dir, exist_ok=True)
    
    filename = f"volatility_{ticker_data['ticker']}.json"
    filepath = os.path.join(sector_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(ticker_data, f, indent=2)
    
    return filepath, sector

def main():
    """Main function to run S&P 500 component volatility analysis"""
    
    parser = argparse.ArgumentParser(
        description='Analyze volatility of S&P 500 components from 3-year price data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python vol_sp500components.py
  python vol_sp500components.py --output-dir volatility_output
  python vol_sp500components.py --output-dir custom_output --lookback-years 3
        ''')
    
    parser.add_argument('--output-dir', '-o', default='volatility_output/sp500_vol',
                        help='Directory to save output (default: volatility_output/sp500_vol)')
    parser.add_argument('--lookback-years', '-y', type=float, default=3,
                        help='Years of data to look back (default: 3)')
    
    args = parser.parse_args()
    
    # Determine file paths - search from script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    spy3y_path = os.path.join(script_dir, 'clean_data', 'spy_3y.json')
    gics_path = os.path.join(script_dir, 'clean_data', 'S&P500Tickers.csv')
    
    # Verify files exist
    if not os.path.exists(spy3y_path):
        print(f"Error: spy_3y.json not found at {spy3y_path}")
        sys.exit(1)
    
    if not os.path.exists(gics_path):
        print(f"Error: S&P500Tickers.csv not found at {gics_path}")
        sys.exit(1)
    
    print(f"Loading data from:")
    print(f"  Price data: {spy3y_path}")
    print(f"  GICS mapping: {gics_path}")
    print()
    
    # Load data
    spy3y_data = load_spy3y(spy3y_path)
    gics_map = load_gics_mapping(gics_path)
    
    print(f"Loaded {len(gics_map)} tickers with GICS sector information")
    
    # Extract tickers from spy_3y.json
    if 'metadata' in spy3y_data and 'tickers' in spy3y_data['metadata']:
        tickers = spy3y_data['metadata']['tickers']
    else:
        tickers = [t for t in spy3y_data.get('data', {}).keys() if t != 'metadata']
    
    print(f"Found {len(tickers)} tickers in spy_3y.json")
    print()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Process each ticker
    results = []
    sector_stats = defaultdict(lambda: {'count': 0, 'mean_vol_1m': [], 'mean_vol_3m': []})
    
    print("=" * 80)
    print("PROCESSING TICKERS")
    print("=" * 80)
    print()
    
    for i, ticker in enumerate(sorted(tickers), 1):
        if ticker not in spy3y_data.get('data', {}):
            continue
        
        # Show which ticker is being processed
        print(f"[{i}/{len(tickers)}] Processing {ticker:6}...", end=" ", flush=True)
        
        price_data = spy3y_data['data'][ticker]
        ticker_result = process_ticker(ticker, price_data, gics_map)
        
        if ticker_result:
            results.append(ticker_result)
            
            # Collect sector statistics
            sector = ticker_result['gics_sector']
            sector_stats[sector]['count'] += 1
            
            vol_1m_data = ticker_result.get('volatility_by_period', {}).get('1M', {})
            vol_3m_data = ticker_result.get('volatility_by_period', {}).get('3M', {})
            
            if vol_1m_data and 'mean' in vol_1m_data:
                sector_stats[sector]['mean_vol_1m'].append(vol_1m_data['mean'])
            if vol_3m_data and 'mean' in vol_3m_data:
                sector_stats[sector]['mean_vol_3m'].append(vol_3m_data['mean'])
            
            # Print current volatility summary
            vol_1m_data = ticker_result.get('volatility_by_period', {}).get('1M', {})
            vol_3m_data = ticker_result.get('volatility_by_period', {}).get('3M', {})
            
            if vol_1m_data and vol_3m_data:
                vol_1m = vol_1m_data.get('current')
                vol_3m = vol_3m_data.get('current')
                print(f"1M: {vol_1m:6.2%}  3M: {vol_3m:6.2%}  [{sector}]")
            else:
                print(f"Insufficient data")
        else:
            print("Skipped (insufficient data)")
    
    # Export results to JSON files organized by sector
    print()
    print("=" * 80)
    print("SAVING RESULTS BY SECTOR")
    print("=" * 80)
    print()
    
    sector_files = defaultdict(list)
    for ticker_data in results:
        filepath, sector = export_volatility_json(ticker_data, args.output_dir)
        sector_files[sector].append(filepath)
        print(f"Saved {ticker_data['ticker']:10} -> {sector}")
    
    # Generate sector summary report
    print()
    print("=" * 80)
    print("SECTOR SUMMARY")
    print("=" * 80)
    print()
    
    summary_report = f"\n{'='*80}\n"
    summary_report += "S&P 500 COMPONENTS - VOLATILITY SUMMARY BY GICS SECTOR\n"
    summary_report += f"Calculation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    summary_report += f"{'='*80}\n\n"
    
    for sector in sorted(sector_stats.keys()):
        stats = sector_stats[sector]
        count = stats['count']
        mean_1m = np.mean(stats['mean_vol_1m']) if stats['mean_vol_1m'] else None
        mean_3m = np.mean(stats['mean_vol_3m']) if stats['mean_vol_3m'] else None
        
        summary_report += f"{sector}\n"
        summary_report += f"  Tickers: {count}\n"
        if mean_1m:
            summary_report += f"  Avg 1M Vol: {mean_1m:.2%}\n"
        if mean_3m:
            summary_report += f"  Avg 3M Vol: {mean_3m:.2%}\n"
        summary_report += "\n"
        
        print(f"{sector:30} {count:4} tickers", end="")
        if mean_1m:
            print(f"  Avg 1M: {mean_1m:.2%}", end="")
        if mean_3m:
            print(f"  Avg 3M: {mean_3m:.2%}")
        else:
            print()
    
    # Save summary report
    summary_path = os.path.join(args.output_dir, 'SECTOR_SUMMARY.txt')
    with open(summary_path, 'w') as f:
        f.write(summary_report)
    print(f"\nSector summary saved to: {summary_path}")
    
    # Save overall results to JSON
    overall_results = {
        'calculation_date': datetime.now().isoformat(),
        'method': 'log',
        'units': 'percent',
        'windows': {'1M': 21, '3M': 63},
        'total_tickers_processed': len(results),
        'by_sector': {}
    }
    
    for sector in sorted(sector_stats.keys()):
        stats = sector_stats[sector]
        overall_results['by_sector'][sector] = {
            'ticker_count': stats['count'],
            'avg_vol_1m': float(np.mean(stats['mean_vol_1m'])) if stats['mean_vol_1m'] else None,
            'avg_vol_3m': float(np.mean(stats['mean_vol_3m'])) if stats['mean_vol_3m'] else None
        }
    
    results_path = os.path.join(args.output_dir, 'volatility_summary.json')
    with open(results_path, 'w') as f:
        json.dump(overall_results, f, indent=2)
    print(f"Overall results saved to: {results_path}")
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Total tickers processed: {len(results)}")
    print(f"Output directory: {args.output_dir}")
    print()

if __name__ == "__main__":
    main()
