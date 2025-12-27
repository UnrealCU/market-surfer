#!/usr/bin/env python3
"""
Mahalanobis Distance Regime Finder
Identifies stress periods vs normal times using multivariate volatility distance.

Usage:
    python mahalanobis_regime.py [--input <vol_ratios.json>] [--output-dir <dir>]
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2


def load_vol_ratios(input_files):
    """
    Load volatility data from one or more JSON files and merge them.
    Handles both vol_ratios.json format and individual volatility_*.json files.
    
    Args:
        input_files: List of file paths or a single file path
    
    Returns:
        Merged dictionary of all vol_ratios
    """
    if isinstance(input_files, str):
        input_files = [input_files]
    
    merged = {}
    for file_path in input_files:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
            # Check if this is a volatility_*.json file (has 'ticker' at top level)
            if 'ticker' in data and 'timeseries' in data:
                # Single ticker file - wrap it
                ticker = data['ticker']
                merged[f"volatility_{ticker}"] = data
            else:
                # vol_ratios.json format - merge directly
                merged.update(data)
    
    return merged


def build_timeseries_df(vol_ratios, metrics=['1M', '1Y']):
    """
    Build a DataFrame with daily values for each symbol and metric combination.
    Also calculates short/long ratio (1M/1Y) for each symbol.
    Handles both vol_ratios.json format and volatility_*.json format.
    
    Args:
        vol_ratios: Dict from vol_ratios.json or merged volatility files
        metrics: List of metrics to use (e.g., ['1M', '1Y'])
    
    Returns:
        DataFrame with dates as index, symbol_metric combinations as columns
    """
    data = {}
    
    for symbol, info in vol_ratios.items():
        ticker = info.get('ticker', symbol)
        
        # Check if this has 'daily' (vol_ratios.json) or 'timeseries' (volatility_*.json)
        if 'daily' in info:
            # vol_ratios.json format
            daily = info.get('daily', [])
            for record in daily:
                date = record.get('date')
                
                if date:
                    if date not in data:
                        data[date] = {}
                    
                    # Add each metric as a separate column
                    values = {}
                    for metric in metrics:
                        value = record.get(metric)
                        if value is not None:
                            col_name = f"{ticker}_{metric}"
                            data[date][col_name] = value
                            values[metric] = value
                    
                    # Calculate ratio: 1M / 1Y (short/long)
                    if '1M' in values and '1Y' in values and values['1Y'] != 0:
                        ratio = values['1M'] / values['1Y']
                        data[date][f"{ticker}_ratio"] = ratio
        
        elif 'timeseries' in info:
            # volatility_*.json format
            timeseries = info.get('timeseries', {})
            
            # Build maps for each metric
            metric_maps = {}
            for metric in metrics:
                if metric in timeseries:
                    metric_maps[metric] = {
                        entry['date']: entry['volatility']
                        for entry in timeseries[metric]
                        if 'date' in entry and 'volatility' in entry
                    }
            
            # Get all dates
            all_dates = set()
            for metric_map in metric_maps.values():
                all_dates.update(metric_map.keys())
            
            # Populate data
            for date in all_dates:
                if date not in data:
                    data[date] = {}
                
                values = {}
                for metric in metrics:
                    if metric in metric_maps and date in metric_maps[metric]:
                        value = metric_maps[metric][date]
                        col_name = f"{ticker}_{metric}"
                        data[date][col_name] = value
                        values[metric] = value
                
                # Calculate ratio: 1M / 1Y (short/long)
                if '1M' in values and '1Y' in values and values['1Y'] != 0:
                    ratio = values['1M'] / values['1Y']
                    data[date][f"{ticker}_ratio"] = ratio
    
    df = pd.DataFrame.from_dict(data, orient='index')
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    
    return df


def calculate_mahalanobis_distance(df, window=252):
    """
    Calculate Mahalanobis distance for each date using rolling covariance.
    
    Args:
        df: DataFrame with symbols as columns, dates as index
        window: Rolling window size for covariance estimation
    
    Returns:
        Series with Mahalanobis distances indexed by date
    """
    distances = []
    dates = []
    
    for i in range(window, len(df)):
        # Get rolling window
        window_data = df.iloc[i-window:i]
        current_point = df.iloc[i].values
        
        # Skip if any NaN
        if window_data.isna().any().any() or np.any(np.isnan(current_point)):
            continue
        
        # Calculate mean and covariance
        mean = window_data.mean().values
        cov = window_data.cov().values
        
        # Skip if singular
        try:
            inv_cov = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            continue
        
        # Mahalanobis distance
        diff = current_point - mean
        dist = np.sqrt(diff @ inv_cov @ diff.T)
        
        distances.append(dist)
        dates.append(df.index[i])
    
    return pd.Series(distances, index=dates, name='Mahalanobis_Distance')


def assign_percentile_buckets(distances, buckets=None):
    """
    Assign discrete stress regimes based on percentile buckets.
    
    Args:
        distances: Series of Mahalanobis distances
        buckets: Dict of percentile thresholds, e.g. {50: 'Normal', 75: 'Elevated', 90: 'High', 100: 'Extreme'}
    
    Returns:
        DataFrame with distance, percentile, and regime assignment
    """
    if buckets is None:
        buckets = {50: 'Normal', 75: 'Elevated', 90: 'High', 100: 'Extreme'}
    
    result = pd.DataFrame({
        'date': distances.index,
        'distance': distances.values,
        'percentile': distances.rank(pct=True) * 100,
    })
    
    # Assign regime based on percentile
    def assign_regime(pct):
        for threshold in sorted(buckets.keys()):
            if pct <= threshold:
                return buckets[threshold]
        return buckets[max(buckets.keys())]
    
    result['regime'] = result['percentile'].apply(assign_regime)
    result = result.set_index('date')
    
    return result


def calculate_chi2_pvalue(distances, dof):
    """
    Calculate p-value under chi-squared distribution (continuous stress metric).
    Lower p-value = more unusual (higher stress).
    
    Args:
        distances: Series or array of Mahalanobis distances
        dof: Degrees of freedom (number of symbols)
    
    Returns:
        Series of p-values (stress: 1 - pvalue, so 0=normal, 1=extreme)
    """
    # Mahalanobis distance squared ~ chi2(dof)
    distances_sq = distances ** 2
    pvalues = 1 - chi2.cdf(distances_sq, dof)
    stress = 1 - pvalues  # Invert: stress = 1 - pvalue
    
    return pd.Series(stress, index=distances.index, name='Stress_Score')


def export_results(regime_df, stress_scores, output_dir, metadata):
    """
    Export regime and stress results to JSON and text files.
    
    Args:
        regime_df: DataFrame with distance, percentile, and regime
        stress_scores: Series with continuous stress scores
        output_dir: Base output directory
        metadata: Dict with conditions/parameters used
    """
    output_dir = Path(output_dir)
    data_dir = output_dir / 'data'
    text_dir = output_dir / 'text'
    
    data_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    # Combine results for JSON
    results = {
        'calculation_date': datetime.now().isoformat(),
        'conditions': metadata,
        'regimes': {},
        'continuous_stress': {}
    }
    
    for date in regime_df.index:
        date_str = date.strftime('%Y-%m-%d')
        results['regimes'][date_str] = {
            'distance': float(regime_df.loc[date, 'distance']),
            'percentile': float(regime_df.loc[date, 'percentile']),
            'regime': str(regime_df.loc[date, 'regime']),
        }
        
        if date in stress_scores.index:
            results['continuous_stress'][date_str] = float(stress_scores.loc[date])
    
    # Save JSON to data folder
    date_str = datetime.now().strftime('%Y%m%d')
    num_vars = metadata.get('num_variables', 0)
    json_file = data_dir / f'mahalanobis_regimes_{date_str}_{num_vars}vars.json'
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Saved JSON data to {json_file}")
    
    # Save text report to text folder
    text_file = text_dir / f'mahalanobis_report_{date_str}_{num_vars}vars.txt'
    with open(text_file, 'w') as f:
        # Write header with conditions
        f.write("="*80 + "\n")
        f.write("MAHALANOBIS DISTANCE REGIME ANALYSIS REPORT\n")
        f.write("="*80 + "\n\n")
        
        f.write("ANALYSIS CONDITIONS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Calculation Date:     {metadata.get('calculation_date', 'N/A')}\n")
        f.write(f"Input Files:          {', '.join(metadata.get('input_files', []))}\n")
        f.write(f"Metrics Used:         {', '.join(metadata.get('metrics', []))}\n")
        f.write(f"Number of Variables:  {metadata.get('num_variables', 0)}\n")
        f.write(f"Rolling Window:       {metadata.get('window', 0)} trading days\n")
        f.write(f"Date Range:           {metadata.get('date_start', 'N/A')} to {metadata.get('date_end', 'N/A')}\n")
        f.write(f"Total Observations:   {len(regime_df)}\n")
        f.write("\n" + "="*80 + "\n\n")
        
        # Summary statistics
        f.write("DISTANCE STATISTICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean:     {regime_df['distance'].mean():.6f}\n")
        f.write(f"Median:   {regime_df['distance'].median():.6f}\n")
        f.write(f"Std Dev:  {regime_df['distance'].std():.6f}\n")
        f.write(f"Min:      {regime_df['distance'].min():.6f}\n")
        f.write(f"Max:      {regime_df['distance'].max():.6f}\n\n")
        
        # Regime distribution
        f.write("REGIME DISTRIBUTION:\n")
        f.write("-" * 80 + "\n")
        regime_counts = regime_df['regime'].value_counts().sort_index()
        for regime, count in regime_counts.items():
            pct = 100 * count / len(regime_df)
            f.write(f"{regime:15s}: {count:5d} days ({pct:5.1f}%)\n")
        f.write("\n")
        
        # Stress score statistics
        f.write("CONTINUOUS STRESS STATISTICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean:     {stress_scores.mean():.6f}\n")
        f.write(f"Median:   {stress_scores.median():.6f}\n")
        f.write(f"Std Dev:  {stress_scores.std():.6f}\n")
        f.write(f"Max:      {stress_scores.max():.6f}\n\n")
        
        # Top 20 highest stress dates
        f.write("TOP 20 HIGHEST STRESS DATES:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Date':<12} {'Distance':>12} {'Percentile':>12} {'Regime':>15} {'Stress':>12}\n")
        f.write("-" * 80 + "\n")
        
        top_stress = regime_df.nlargest(20, 'distance')
        for date in top_stress.index:
            date_str = date.strftime('%Y-%m-%d')
            dist = regime_df.loc[date, 'distance']
            pct = regime_df.loc[date, 'percentile']
            reg = regime_df.loc[date, 'regime']
            stress = stress_scores.loc[date] if date in stress_scores.index else np.nan
            f.write(f"{date_str:<12} {dist:12.6f} {pct:12.2f} {reg:>15s} {stress:12.6f}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*80 + "\n")
    
    print(f"Saved text report to {text_file}")
    
    return json_file, text_file


def print_summary(regime_df, stress_scores):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("MAHALANOBIS DISTANCE REGIME SUMMARY")
    print("="*60)
    
    print(f"\nDistance Statistics:")
    print(f"  Mean: {regime_df['distance'].mean():.4f}")
    print(f"  Std:  {regime_df['distance'].std():.4f}")
    print(f"  Min:  {regime_df['distance'].min():.4f}")
    print(f"  Max:  {regime_df['distance'].max():.4f}")
    
    print(f"\nRegime Distribution:")
    regime_counts = regime_df['regime'].value_counts().sort_index()
    for regime, count in regime_counts.items():
        pct = 100 * count / len(regime_df)
        print(f"  {regime}: {count} days ({pct:.1f}%)")
    
    print(f"\nStress Score Statistics:")
    print(f"  Mean:   {stress_scores.mean():.4f}")
    print(f"  Median: {stress_scores.median():.4f}")
    print(f"  Max:    {stress_scores.max():.4f}")
    
    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Calculate Mahalanobis distance-based stress regimes')
    parser.add_argument('--input', '-i', nargs='+', default=['Volatility_output/ratios/vol_ratios.json'],
                        help='Input vol_ratios.json file(s) (space-separated for multiple files)')
    parser.add_argument('--output-dir', '-o', default='regime_output',
                        help='Output directory for regime data (default: regime_output)')
    parser.add_argument('--window', '-w', type=int, default=252,
                        help='Rolling window size for covariance (default: 252 trading days)')
    
    args = parser.parse_args()
    
    print(f"Loading vol_ratios from {len(args.input)} file(s)...")
    for f in args.input:
        print(f"  - {f}")
    vol_ratios = load_vol_ratios(args.input)
    
    print(f"Building timeseries DataFrame with 1M, 1Y, and ratio (1M/1Y) metrics...")
    df = build_timeseries_df(vol_ratios, metrics=['1M', '1Y'])
    
    print(f"Data shape: {df.shape}")
    print(f"Symbols: {', '.join(df.columns)}")
    print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")
    
    # Drop rows with NaN
    df_clean = df.dropna()
    print(f"After dropping NaN: {df_clean.shape[0]} rows")
    
    print(f"\nCalculating Mahalanobis distances (window={args.window})...")
    distances = calculate_mahalanobis_distance(df_clean, window=args.window)
    
    print(f"Assigning percentile-based regimes...")
    regime_df = assign_percentile_buckets(distances)
    
    print(f"Calculating continuous stress scores (chi-squared p-values)...")
    stress_scores = calculate_chi2_pvalue(distances, dof=len(df.columns))
    
    print_summary(regime_df, stress_scores)
    
    # Prepare metadata for export
    metadata = {
        'calculation_date': datetime.now().isoformat(),
        'input_files': args.input,
        'metrics': ['1M', '1Y', 'ratio (1M/1Y)'],
        'num_variables': len(df.columns),
        'window': args.window,
        'date_start': df.index[0].strftime('%Y-%m-%d'),
        'date_end': df.index[-1].strftime('%Y-%m-%d'),
    }
    
    print(f"\nExporting results...")
    export_results(regime_df, stress_scores, args.output_dir, metadata)


if __name__ == '__main__':
    main()
