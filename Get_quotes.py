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
        # Extra datasets
        self.options: dict = {}
        self.earnings: dict = {}
        self.balance_sheet: dict = {}
        self.financials: dict = {}
        
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

    # ---------- Fundamentals and Derivatives ----------
    def fetch_option_chains(self, expirations: Optional[List[str]] = None) -> dict:
        """
        Fetch option chains for tickers.

        Args:
            expirations: List of expiration dates (YYYY-MM-DD). If None, uses all available expirations.

        Returns:
            Dictionary keyed by ticker → expiration → {calls: [...], puts: [...]} (records format)
        """
        results: dict = {}
        for ticker in self.tickers:
            try:
                t = yf.Ticker(ticker)
                exps = expirations or list(getattr(t, 'options', []) or [])
                if not exps:
                    continue
                results[ticker] = {}
                for exp in exps:
                    try:
                        chain = t.option_chain(exp)
                        calls = chain.calls.reset_index(drop=True).to_dict(orient='records') if hasattr(chain, 'calls') else []
                        puts = chain.puts.reset_index(drop=True).to_dict(orient='records') if hasattr(chain, 'puts') else []
                        results[ticker][exp] = {"calls": calls, "puts": puts}
                    except Exception as e:
                        # Skip problematic expiration
                        continue
            except Exception:
                continue
        self.options = results
        return results

    def fetch_earnings(self) -> dict:
        """Fetch earnings history and upcoming dates for each ticker."""
        results: dict = {}
        for ticker in self.tickers:
            try:
                t = yf.Ticker(ticker)
                earnings = {}
                # Historical yearly/quarterly earnings
                df_year = getattr(t, 'earnings', pd.DataFrame())
                df_q = getattr(t, 'quarterly_earnings', pd.DataFrame())
                earnings['yearly'] = df_year.reset_index().to_dict(orient='records') if not df_year.empty else []
                earnings['quarterly'] = df_q.reset_index().to_dict(orient='records') if not df_q.empty else []
                # Earnings dates (past/upcoming)
                try:
                    edates = t.get_earnings_dates(limit=40)
                    earnings['earnings_dates'] = edates.reset_index().to_dict(orient='records') if isinstance(edates, pd.DataFrame) else []
                except Exception:
                    earnings['earnings_dates'] = []
                results[ticker] = earnings
            except Exception:
                results[ticker] = {}
        self.earnings = results
        return results

    def fetch_balance_sheet_and_financials(self) -> dict:
        """Fetch balance sheet and key financial statements (annual and quarterly)."""
        results: dict = {}
        for ticker in self.tickers:
            try:
                t = yf.Ticker(ticker)
                bs = getattr(t, 'balance_sheet', pd.DataFrame())
                bs_q = getattr(t, 'quarterly_balance_sheet', pd.DataFrame())
                fin = {}
                income = getattr(t, 'financials', pd.DataFrame())
                income_q = getattr(t, 'quarterly_financials', pd.DataFrame())
                cash = getattr(t, 'cashflow', pd.DataFrame())
                cash_q = getattr(t, 'quarterly_cashflow', pd.DataFrame())

                def _to_records(df: pd.DataFrame) -> list:
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        df2 = df.copy()
                        try:
                            df2.columns = df2.columns.map(str)
                        except Exception:
                            df2.columns = [str(c) for c in df2.columns]
                        return df2.reset_index().to_dict(orient='records')
                    return []

                results[ticker] = {
                    'balance_sheet': _to_records(bs),
                    'quarterly_balance_sheet': _to_records(bs_q),
                    'income_statement': _to_records(income),
                    'quarterly_income_statement': _to_records(income_q),
                    'cashflow': _to_records(cash),
                    'quarterly_cashflow': _to_records(cash_q),
                }
            except Exception:
                results[ticker] = {}
        self.balance_sheet = {k: {"balance_sheet": v.get("balance_sheet"), "quarterly_balance_sheet": v.get("quarterly_balance_sheet")}
                              for k, v in results.items()}
        self.financials = {k: {
            'income_statement': v.get('income_statement'),
            'quarterly_income_statement': v.get('quarterly_income_statement'),
            'cashflow': v.get('cashflow'),
            'quarterly_cashflow': v.get('quarterly_cashflow'),
        } for k, v in results.items()}
        return results
    
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
        Creates two subfolders:
          - price_data: CSVs per ticker
          - financial_data: JSON bundle of options/earnings/financials (if available)
        Format: Yahoo_extracted/YYYY-MM-DD/{price_data|financial_data}/...
        """
        import os
        from datetime import date
        
        # Create date folder
        today = date.today().strftime("%Y-%m-%d")
        base_dir = f"Yahoo_extracted/{today}"
        price_dir = os.path.join(base_dir, "price_data")
        fin_dir = os.path.join(base_dir, "financial_data")
        os.makedirs(price_dir, exist_ok=True)
        os.makedirs(fin_dir, exist_ok=True)
        
        # Save each ticker to its own file
        for ticker, df in self.data.items():
            filename = os.path.join(price_dir, f"{ticker}.csv")
            df.to_csv(filename)
            print(f"Saved: {filename}")

        # If we have any fundamentals/options content, save a single JSON bundle
        has_fin_content = any([
            bool(self.options), bool(self.earnings), bool(self.balance_sheet), bool(self.financials)
        ])
        if has_fin_content:
            fin_payload = {
                'metadata': {
                    'tickers': self.tickers,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'interval': self.interval,
                    'generated_at': datetime.now().isoformat(),
                },
                'options': self.options,
                'earnings': self.earnings,
                'balance_sheet': self.balance_sheet,
                'financials': self.financials,
            }
            fin_path = os.path.join(fin_dir, "financial_info.json")
            with open(fin_path, 'w') as f:
                json.dump(fin_payload, f, indent=2)
            print(f"Saved fundamentals/options JSON: {fin_path}")

    def save_extracted_json_separated(self, options_type: str = "both", max_expirations: Optional[int] = None,
                                      financial_granularity: str = "both",
                                      include_earnings: bool = True,
                                      include_balance_sheet: bool = True,
                                      include_financials: bool = True) -> None:
        """
        Save extracted datasets in JSON under type-first folders and then date.

        Structure:
            Yahoo_extracted/
              price/YYYY-MM-DD/{TICKER}.json
              options/YYYY-MM-DD/{TICKER}.json
              financial/YYYY-MM-DD/{TICKER}.json

        Args:
            options_type: 'calls', 'puts', or 'both' when saving option chains
            max_expirations: If provided, limit to the first N upcoming expirations per ticker
        """
        import os
        from datetime import date

        today = date.today().strftime("%Y-%m-%d")
        base_dir = "Yahoo_extracted"
        price_dir = os.path.join(base_dir, "price", today)
        options_dir = os.path.join(base_dir, "options", today)
        financial_dir = os.path.join(base_dir, "financial", today)

        os.makedirs(price_dir, exist_ok=True)
        os.makedirs(options_dir, exist_ok=True)
        os.makedirs(financial_dir, exist_ok=True)

        # Save price as JSON per ticker
        for ticker, df in self.data.items():
            path = os.path.join(price_dir, f"{ticker}.json")
            payload = {
                'ticker': ticker,
                'interval': self.interval,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'data': df.reset_index().to_dict(orient='records')
            }
            with open(path, 'w') as f:
                json.dump(payload, f, indent=2, default=str)
            print(f"Saved price JSON: {path}")

        # Save options chains per ticker
        if self.options:
            for ticker, exps_map in self.options.items():
                # Order expirations ascending and apply limit if given
                exps_sorted = sorted(exps_map.keys())
                if max_expirations is not None:
                    exps_sorted = exps_sorted[:max_expirations]
                filtered = {}
                for exp in exps_sorted:
                    entry = exps_map.get(exp, {})
                    if options_type == 'calls':
                        filtered[exp] = { 'calls': entry.get('calls', []) }
                    elif options_type == 'puts':
                        filtered[exp] = { 'puts': entry.get('puts', []) }
                    else:
                        filtered[exp] = {
                            'calls': entry.get('calls', []),
                            'puts': entry.get('puts', [])
                        }
                path = os.path.join(options_dir, f"{ticker}.json")
                payload = {
                    'ticker': ticker,
                    'options_type': options_type,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'expirations': filtered
                }
                with open(path, 'w') as f:
                    json.dump(payload, f, indent=2, default=str)
                print(f"Saved options JSON: {path}")

        # Save financials per ticker
        if self.earnings or self.balance_sheet or self.financials:
            tickers = set(self.tickers)
            for ticker in tickers:
                path = os.path.join(financial_dir, f"{ticker}.json")
                # Filter payload by requested granularity and inclusion flags
                gran = (financial_granularity or 'both').lower()
                if gran not in ('annual', 'quarterly', 'both'):
                    gran = 'both'

                e_src = self.earnings.get(ticker) if self.earnings else {}
                bs_src = self.balance_sheet.get(ticker) if self.balance_sheet else {}
                fin_src = self.financials.get(ticker) if self.financials else {}

                earnings_payload = {}
                if include_earnings and isinstance(e_src, dict):
                    if gran in ('annual', 'both') and 'yearly' in e_src:
                        earnings_payload['yearly'] = e_src.get('yearly')
                    if gran in ('quarterly', 'both') and 'quarterly' in e_src:
                        earnings_payload['quarterly'] = e_src.get('quarterly')
                    # Always include earnings dates if available
                    if 'earnings_dates' in e_src:
                        earnings_payload['earnings_dates'] = e_src.get('earnings_dates')

                balance_sheet_payload = {}
                if include_balance_sheet and isinstance(bs_src, dict):
                    if gran in ('annual', 'both') and 'balance_sheet' in bs_src:
                        balance_sheet_payload['balance_sheet'] = bs_src.get('balance_sheet')
                    if gran in ('quarterly', 'both') and 'quarterly_balance_sheet' in bs_src:
                        balance_sheet_payload['quarterly_balance_sheet'] = bs_src.get('quarterly_balance_sheet')

                financials_payload = {}
                if include_financials and isinstance(fin_src, dict):
                    if gran in ('annual', 'both'):
                        if 'income_statement' in fin_src:
                            financials_payload['income_statement'] = fin_src.get('income_statement')
                        if 'cashflow' in fin_src:
                            financials_payload['cashflow'] = fin_src.get('cashflow')
                    if gran in ('quarterly', 'both'):
                        if 'quarterly_income_statement' in fin_src:
                            financials_payload['quarterly_income_statement'] = fin_src.get('quarterly_income_statement')
                        if 'quarterly_cashflow' in fin_src:
                            financials_payload['quarterly_cashflow'] = fin_src.get('quarterly_cashflow')

                payload = {
                    'ticker': ticker,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'earnings': earnings_payload,
                    'balance_sheet': balance_sheet_payload,
                    'financials': financials_payload,
                }
                with open(path, 'w') as f:
                    json.dump(payload, f, indent=2, default=str)
                print(f"Saved financial JSON: {path}")
    
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
            'summary': self.summary_stats(),
            'options': self.options,
            'earnings': self.earnings,
            'balance_sheet': self.balance_sheet,
            'financials': self.financials,
        }
        
        # Convert each ticker's DataFrame to records format
        for ticker, df in self.data.items():
            result['data'][ticker] = df.reset_index().to_dict(orient='records')
        
        return json.dumps(result, indent=2, default=str)

    def save_info_json(self, output_dir: str = "Fundamentals_output") -> str:
        """Save options/earnings/financials data to a single JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"info_{self.start_date}_to_{self.end_date}.json")
        payload = {
            'metadata': {
                'tickers': self.tickers,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'interval': self.interval,
            },
            'options': self.options,
            'earnings': self.earnings,
            'balance_sheet': self.balance_sheet,
            'financials': self.financials,
        }
        with open(out_path, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"Saved fundamentals/options JSON to: {out_path}")
        return out_path


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
    # Data-type selections
    want_price: bool = False
    want_options: bool = False
    want_financial: bool = False
    # Options specifics
    opt_type: str = 'both'  # 'calls' | 'puts' | 'both'
    opt_exp_count: Optional[int] = None
    # Financial specifics
    want_earnings: bool = False
    want_balance_sheet: bool = False
    want_financials: bool = False
    financial_granularity: str = 'both'  # 'annual' | 'quarterly' | 'both'

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
            ans = input("Which data to fetch? (price options financial) [default: price]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 0
                continue
            if not ans:
                want_price, want_options, want_financial = True, False, False
            else:
                tokens = set([t.strip() for t in ans.split()])
                want_price = 'price' in tokens or ('options' not in tokens and 'financial' not in tokens)
                want_options = 'options' in tokens
                want_financial = 'financial' in tokens
            # If options selected, branch to options type; else if financial selected, branch to financial subtypes; else go to dates
            step = 2 if want_options else (3 if want_financial else 4)
            continue

        if step == 2:
            # Options specifics: type
            ans = input("Options type (calls/puts/both) [default: both]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 1
                continue
            opt_type = ans if ans in ("calls", "puts", "both") else "both"
            step = 2.5
            continue

        if step == 2.5:
            # Options specifics: upcoming expirations count
            ans = input("Number of upcoming expirations to include (integer) [default: all]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 2
                continue
            if ans == "" or ans == "all":
                opt_exp_count = None
            else:
                try:
                    opt_exp_count = max(1, int(ans))
                except ValueError:
                    opt_exp_count = None
            # After options branch, if financial also selected, go to financial specifics; else go to dates
            step = 3 if want_financial else 4
            continue

        if step == 3:
            # Financial specifics: choose subtypes
            ans = input("Select financial datasets (earnings balance-sheet financials) [default: all]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                # If options selected, go back to options expirations; else back to data-type
                step = 2.5 if want_options else 1
                continue
            if not ans or ans == 'all':
                want_earnings = True
                want_balance_sheet = True
                want_financials = True
            else:
                tokens = set([t.strip() for t in ans.split()])
                want_earnings = 'earnings' in tokens
                want_balance_sheet = 'balance-sheet' in tokens
                want_financials = 'financials' in tokens
                if not (want_earnings or want_balance_sheet or want_financials):
                    # default to all if none parsed
                    want_earnings = True
                    want_balance_sheet = True
                    want_financials = True
            step = 3.5
            continue

        if step == 3.5:
            # Financial granularity
            ans = input("Financial granularity (annual/quarterly/both) [default: both]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 3
                continue
            financial_granularity = ans if ans in ("annual", "quarterly", "both") else "both"
            step = 4
            continue

        if step == 4:
            ans = input("Enter start date (YYYY-MM-DD, e.g., 2024-01-01): ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                # If financial selected, go back to its specifics; else if options selected, go back to options; else back to data-type
                step = 3 if want_financial else (2.5 if want_options else 1)
                continue
            try:
                datetime.strptime(ans, '%Y-%m-%d')
                start_date = ans
                step = 5
            except ValueError:
                print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
            continue

        if step == 5:
            from datetime import date as _date
            ans = input("Enter end date (YYYY-MM-DD) [default: today]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 4
                continue
            if ans == "":
                end_date = _date.today().strftime('%Y-%m-%d')
                step = 6
            else:
                try:
                    datetime.strptime(ans, '%Y-%m-%d')
                    end_date = ans
                    step = 6
                except ValueError:
                    print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
            continue

        if step == 6:
            # Skip interval if not fetching price data
            if not want_price:
                step = 8
                continue
            ans = input("Enter interval (1d for daily, 1mo for monthly) [default: 1d]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 5
                continue
            if ans in ['1d', '1mo']:
                interval = ans
            else:
                interval = '1d'
                if not ans:
                    print("Using daily (1d)")
            step = 7
            continue

        if step == 7:
            # Skip columns if not fetching price data
            if not want_price:
                columns = None
                step = 8
                continue
            ans = input("Enter specific columns to retrieve (Open, High, Low, Close, Volume, Adj Close) [leave blank for all]: ").strip()
            if ans in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if ans in ("back", "b"):
                step = 6
                continue
            columns = ans.split() if ans else None
            step = 8
            continue

        if step == 8:
            print("\nReview your selections:")
            print(f"  Tickers : {' '.join(tickers or [])}")
            print(f"  Data    : {'price ' if want_price else ''}{'options ' if want_options else ''}{'financial' if want_financial else ''}".strip())
            if want_options:
                print(f"  OptType : {opt_type}")
                print(f"  Expirations: {'all' if opt_exp_count is None else opt_exp_count}")
            if want_financial:
                fin_parts = []
                if want_earnings: fin_parts.append('earnings')
                if want_balance_sheet: fin_parts.append('balance-sheet')
                if want_financials: fin_parts.append('financials')
                print(f"  Financial: {' '.join(fin_parts) if fin_parts else 'all'}")
            print(f"  Start   : {start_date}")
            print(f"  End     : {end_date}")
            if want_price:
                print(f"  Interval: {interval}")
                print(f"  Columns : {'ALL (OHLCV)' if not columns else ' '.join(columns)}")
            ans = input("Proceed to download? (yes/back/quit) [default: yes]: ").strip().lower()
            if ans in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if ans in ("back", "b"):
                # Go back to columns
                step = 7
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
    
    # Fetch only requested datasets
    if want_price:
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
        # Fetch extras based on interactive selections
        if want_options:
            collector.fetch_option_chains(expirations=None)
        if want_financial:
            if want_earnings:
                collector.fetch_earnings()
            if want_balance_sheet or want_financials:
                collector.fetch_balance_sheet_and_financials()

        # Save JSON in type-first structure
        collector.save_extracted_json_separated(
            options_type=opt_type,
            max_expirations=opt_exp_count,
            financial_granularity=financial_granularity,
            include_earnings=want_earnings,
            include_balance_sheet=want_balance_sheet,
            include_financials=want_financials
        )
        print("✓ Data saved to Yahoo_extracted/{price|options|financial}/YYYY-MM-DD")


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
    # New functionality flags
    parser.add_argument('--options', action='store_true',
                        help='Fetch option chains for the specified tickers')
    parser.add_argument('--options-expirations', nargs='*',
                        help='Specific option expiration dates (YYYY-MM-DD). If omitted, fetches all available.')
    parser.add_argument('--earnings', action='store_true',
                        help='Fetch earnings history and earnings dates')
    parser.add_argument('--balance-sheet', action='store_true',
                        help='Fetch balance sheet (annual and quarterly) and key financial statements')
    parser.add_argument('--financials', action='store_true',
                        help='Fetch income statement and cashflow (annual and quarterly)')
    parser.add_argument('--save-info', action='store_true',
                        help='Save fetched options/earnings/financials into a JSON file')
    parser.add_argument('--info-output-dir', default='Fundamentals_output',
                        help='Directory to save fundamentals/options JSON (default: Fundamentals_output)')
    
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
        # Fetch extras if requested
        if args.options:
            collector.fetch_option_chains(expirations=args.options_expirations)
        if args.earnings:
            collector.fetch_earnings()
        if args.balance_sheet or args.financials:
            collector.fetch_balance_sheet_and_financials()
        # Save extras JSON if requested
        if args.save_info:
            collector.save_info_json(args.info_output_dir)




if __name__ == "__main__":
    main()
