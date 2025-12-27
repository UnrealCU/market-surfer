import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Union
import argparse
import os
import json


class FinancialDataCollector:
    """
    A flexible tool for collecting financial data using yfinance.
    
    Supports:
    - Multiple tickers
    - Custom date ranges
    - Daily or monthly data
    - Specific data points (OHLCV, etc.)
    """
    
    def __init__(self, tickers: List[str], start_date: str, end_date: str, 
                 interval: str = "1d", data_points: Optional[List[str]] = None):
        """
        Initialize the Financial Data Collector.
        
        Args:
            tickers: List of stock tickers (e.g., ['AAPL', 'GOOGL', 'MSFT'])
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'
            interval: '1d' for daily, '1mo' for monthly (default: '1d')
            data_points: List of columns to retrieve. If None, returns OHLCV.
                        Options: 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close'
        """
        self.tickers = tickers if isinstance(tickers, list) else [tickers]
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval
        self.data_points = data_points
        self.data = {}
        
    def fetch_data(self) -> dict:
        """
        Fetch financial data for specified tickers and date range.
        
        Returns:
            Dictionary with tickers as keys and DataFrames as values
        """
        print(f"Fetching {self.interval} data for {len(self.tickers)} ticker(s)...")
        print(f"Date range: {self.start_date} to {self.end_date}")
        
        for ticker in self.tickers:
            try:
                print(f"  Downloading {ticker}...", end=" ")
                ticker_data = yf.download(
                    ticker,
                    start=self.start_date,
                    end=self.end_date,
                    interval=self.interval,
                    progress=False
                )
                
                # Flatten multi-level columns if present (yfinance returns MultiIndex columns)
                if isinstance(ticker_data.columns, pd.MultiIndex):
                    # Get just the first level (Price, Open, High, etc.)
                    ticker_data.columns = ticker_data.columns.get_level_values(0)
                
                # Select specific columns if specified
                if self.data_points:
                    available_cols = [col for col in self.data_points if col in ticker_data.columns]
                    ticker_data = ticker_data[available_cols]
                
                self.data[ticker] = ticker_data
                print(f"✓ ({len(ticker_data)} records)")
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
        
        return self.data
    
    def get_single_ticker(self, ticker: str) -> pd.DataFrame:
        """Get data for a specific ticker."""
        return self.data.get(ticker, pd.DataFrame())
    
    def get_all_data(self) -> pd.DataFrame:
        """
        Combine all ticker data into a single DataFrame with multi-level columns.
        
        Returns:
            DataFrame with columns indexed by (Ticker, Data Point)
        """
        if not self.data:
            return pd.DataFrame()
        
        combined = pd.concat(self.data, axis=1)
        return combined
    
    def save_to_csv(self, output_dir: str = "data") -> None:
        """
        Save data to CSV files.
        
        Args:
            output_dir: Directory to save CSV files (default: data folder)
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        for ticker, df in self.data.items():
            filename = f"{output_dir}/{ticker}_{self.start_date}_to_{self.end_date}.csv"
            df.to_csv(filename)
            print(f"Saved: {filename}")
    
    def save_to_yahoo_extracted(self) -> None:
        """
        Save data to Yahoo_extracted folder organized by date.
        Each ticker gets its own file within a date-stamped folder.
        Format: Yahoo_extracted/YYYY-MM-DD/TICKER.csv
        """
        import os
        from datetime import date
        
        # Create date folder
        today = date.today().strftime("%Y-%m-%d")
        base_dir = f"Yahoo_extracted/{today}"
        os.makedirs(base_dir, exist_ok=True)
        
        # Save each ticker to its own file
        for ticker, df in self.data.items():
            filename = f"{base_dir}/{ticker}.csv"
            df.to_csv(filename)
            print(f"Saved: {filename}")
    
    def save_combined_csv(self, filename: str = "data/combined_data.csv") -> None:
        """
        Save combined data to a single CSV file.
        
        Args:
            filename: Output filename (default: data/combined_data.csv)
        """
        import os
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        combined = self.get_all_data()
        combined.to_csv(filename)
        print(f"Saved combined data to: {filename}")
    
    def summary_stats(self) -> dict:
        """
        Get summary statistics for all tickers.
        
        Returns:
            Dictionary with summary statistics for each ticker
        """
        stats = {}
        for ticker, df in self.data.items():
            if df.empty:
                stats[ticker] = {'error': 'No data available'}
            elif 'Close' in df.columns:
                close_prices = df['Close']
                
                # Helper function to convert to native Python type
                def to_python(val):
                    if hasattr(val, 'item'):
                        return val.item()
                    return float(val)
                
                stats[ticker] = {
                    'records': len(df),
                    'start_price': to_python(close_prices.iloc[0]) if len(df) > 0 else None,
                    'end_price': to_python(close_prices.iloc[-1]) if len(df) > 0 else None,
                    'min_price': to_python(close_prices.min()),
                    'max_price': to_python(close_prices.max()),
                    'avg_price': to_python(close_prices.mean()),
                }
            else:
                stats[ticker] = {'error': 'Close column not found'}
        
        return stats
    
    def print_summary(self) -> None:
        """Print summary statistics for all tickers."""
        stats = self.summary_stats()
        print("\n" + "="*60)
        print("FINANCIAL DATA SUMMARY")
        print("="*60)
        
        for ticker, ticker_stats in stats.items():
            print(f"\n{ticker}:")
            if 'error' in ticker_stats:
                print(f"  {ticker_stats['error']}")
            else:
                print(f"  Records: {ticker_stats['records']}")
                print(f"  Start Price: ${ticker_stats['start_price']:.2f}")
                print(f"  End Price: ${ticker_stats['end_price']:.2f}")
                print(f"  Min Price: ${ticker_stats['min_price']:.2f}")
                print(f"  Max Price: ${ticker_stats['max_price']:.2f}")
                print(f"  Avg Price: ${ticker_stats['avg_price']:.2f}")
    
    def to_json(self) -> str:
        """
        Convert collected data to JSON format.
        
        Returns:
            JSON string with all ticker data and metadata
        """
        result = {
            'metadata': {
                'tickers': self.tickers,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'interval': self.interval,
                'data_points': self.data_points
            },
            'data': {},
            'summary': self.summary_stats()
        }
        
        # Convert each ticker's DataFrame to records format
        for ticker, df in self.data.items():
            result['data'][ticker] = df.reset_index().to_dict(orient='records')
        
        return json.dumps(result, indent=2, default=str)


def get_quotes(tickers: Union[str, List[str]], 
               start_date: str, 
               end_date: str, 
               interval: str = "1d",
               data_points: Optional[List[str]] = None,
               return_format: str = "json") -> Union[str, dict]:
    """
    Fetch financial quotes data and return as JSON.
    
    This function can be imported and called from other Python files.
    
    Args:
        tickers: Single ticker string or list of tickers (e.g., 'AAPL' or ['AAPL', 'MSFT'])
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        interval: '1d' for daily, '1mo' for monthly (default: '1d')
        data_points: List of columns to retrieve. If None, returns all OHLCV data.
                    Options: ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        return_format: 'json' returns JSON string, 'dict' returns Python dictionary
    
    Returns:
        JSON string or dictionary containing:
        - metadata: Request parameters
        - data: Price data for each ticker
        - summary: Summary statistics
    
    Example:
        >>> from Get_quotes import get_quotes
        >>> data = get_quotes('AAPL', '2025-01-01', '2025-01-10')
        >>> print(data)
        
        >>> # Multiple tickers
        >>> data = get_quotes(['AAPL', 'MSFT'], '2025-01-01', '2025-01-10', return_format='dict')
        >>> print(data['summary']['AAPL'])
    """
    # Convert single ticker to list
    if isinstance(tickers, str):
        tickers = [tickers]
    
    # Create collector and fetch data
    collector = FinancialDataCollector(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        data_points=data_points
    )
    
    # Fetch data (silently for library usage)
    import sys
    from io import StringIO
    
    # Suppress print statements during fetch
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    try:
        collector.fetch_data()
    finally:
        sys.stdout = old_stdout
    
    # Return in requested format
    if return_format == "dict":
        return json.loads(collector.to_json())
    else:
        return collector.to_json()


def interactive_mode():
    """Interactive mode for the Financial Data Collector."""
    print("\n" + "="*60)
    print("FINANCIAL DATA COLLECTOR - Interactive Mode")
    print("="*60 + "\n")
    print("Tip: type 'back' to go to the previous question, or 'quit' to abort.\n")

    # Interactive wizard with back/quit support
    step = 0
    tickers: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    interval: str | None = None
    columns: list[str] | None = None

    while True:
        if step == 0:
            ans = input("Enter ticker(s) (space-separated, e.g., AAPL GOOGL MSFT): ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                print("Already at the first question.\n")
                continue
            if not ans:
                print("❌ Please enter at least one ticker.\n")
                continue
            tickers = [t.upper() for t in ans.split()]
            step = 1
            continue

        if step == 1:
            ans = input("Enter start date (YYYY-MM-DD, e.g., 2024-01-01): ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 0
                continue
            try:
                datetime.strptime(ans, '%Y-%m-%d')
                start_date = ans
                step = 2
            except ValueError:
                print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
            continue

        if step == 2:
            ans = input("Enter end date (YYYY-MM-DD, e.g., 2024-12-25): ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 1
                continue
            try:
                datetime.strptime(ans, '%Y-%m-%d')
                end_date = ans
                step = 3
            except ValueError:
                print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
            continue

        if step == 3:
            ans = input("Enter interval (1d for daily, 1mo for monthly) [default: 1d]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 2
                continue
            if ans in ['1d', '1mo']:
                interval = ans
            else:
                interval = '1d'
                if not ans:
                    print("Using daily (1d)")
            step = 4
            continue

        if step == 4:
            ans = input("Enter specific columns to retrieve (Open, High, Low, Close, Volume, Adj Close) [leave blank for all]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 3
                continue
            columns = ans.split() if ans else None
            step = 5
            continue

        if step == 5:
            print("\nReview your selections:")
            print(f"  Tickers : {' '.join(tickers or [])}")
            print(f"  Start   : {start_date}")
            print(f"  End     : {end_date}")
            print(f"  Interval: {interval}")
            print(f"  Columns : {'ALL (OHLCV)' if not columns else ' '.join(columns)}")
            ans = input("Proceed to download? (yes/back/quit) [default: yes]: ").strip().lower()
            if ans in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if ans in ("back", "b"):
                step = 4
                continue
            # default yes
            break

    # Create collector and fetch data
    collector = FinancialDataCollector(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        data_points=columns
    )
    
    collector.fetch_data()
    collector.print_summary()
    
    # Ask about saving
    while True:
        save_input = input("\nWould you like to save the data? (yes/no/back/quit) [default: no]: ").strip().lower()
        if save_input in ("quit", "exit", "abort", "q"):
            print("Aborted by user.")
            return
        if save_input in ("back", "b"):
            # Go back to confirmation step
            step = 5
            continue
        if save_input in ['yes', 'y', 'no', 'n', '']:
            break
        print("❌ Please enter 'yes', 'no', 'back', or 'quit'.\n")
    
    if save_input in ['yes', 'y']:
        collector.save_to_yahoo_extracted()
        print("✓ Data saved to Yahoo_extracted folder")


def main():
    """Main function with argument parsing for command-line or interactive mode."""
    parser = argparse.ArgumentParser(
        description='Collect financial data using yfinance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (Command-line mode):
  python Get_quotes.py -t AAPL GOOGL MSFT -s 2023-01-01 -e 2023-12-31
  python Get_quotes.py -t AAPL -s 2022-01-01 -e 2024-12-31 -i 1mo -c Close Volume
  python Get_quotes.py -t BTC-USD -s 2024-01-01 -e 2024-12-31 --save

Or just run: python Get_quotes.py (for interactive mode)
        """
    )
    
    parser.add_argument('-t', '--tickers', nargs='+',
                        help='Stock ticker(s) to download (space-separated)')
    parser.add_argument('-s', '--start',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('-e', '--end',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('-i', '--interval', default='1d',
                        choices=['1d', '1mo'],
                        help='Data interval: 1d for daily, 1mo for monthly (default: 1d)')
    parser.add_argument('-c', '--columns', nargs='+',
                        help='Specific columns to retrieve (Open, High, Low, Close, Volume, Adj Close)')
    parser.add_argument('--save', action='store_true',
                        help='Save data to Yahoo_extracted folder')
    parser.add_argument('--combined', action='store_true',
                        help='Save all tickers to a single CSV file')
    parser.add_argument('--output-dir', default='.',
                        help='Directory to save CSV files (default: current directory)')
    
    args = parser.parse_args()
    
    # If no arguments provided, use interactive mode
    if not args.tickers:
        interactive_mode()
    else:
        # Command-line mode
        # Normalize tickers to uppercase
        cli_tickers = [t.upper() for t in (args.tickers or [])]
        
        collector = FinancialDataCollector(
            tickers=cli_tickers,
            start_date=args.start,
            end_date=args.end,
            interval=args.interval,
            data_points=args.columns
        )
        
        collector.fetch_data()
        collector.print_summary()
        
        # Save if requested
        if args.save:
            collector.save_to_yahoo_extracted()




if __name__ == "__main__":
    main()
