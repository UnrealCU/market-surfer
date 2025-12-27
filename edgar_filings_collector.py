#!/usr/bin/env python3
"""
SEC EDGAR Filings Collector
Uses edgartools to extract financial data from SEC filings.
"""

import json
import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import argparse
from edgar import set_identity, Company, Filing


# Set identity for SEC EDGAR access
set_identity("Lukas Dabrowski ld3179@columbia.edu")


class EdgarFilingsCollector:
    """
    Collect and extract financial data from SEC EDGAR filings.
    
    Supports:
    - Company filings (10-K, 10-Q, 8-K, etc.)
    - Financial statements extraction
    - Multiple companies
    - Date range filtering
    
    Note: edgartools accepts both stock tickers (e.g., 'AAPL') and CIK numbers (e.g., '0000320193').
    """
    
    def __init__(self, tickers: List[str]):
        """
        Initialize the EDGAR Filings Collector.
        
        Args:
            tickers: List of stock tickers or CIK numbers (e.g., ['AAPL', 'MSFT'] or ['0000320193', '0000789019'])
                    edgartools automatically handles both formats.
        """
        self.tickers = tickers if isinstance(tickers, list) else [tickers]
        self.companies: Dict[str, Company] = {}
        self.filings: Dict[str, List[Filing]] = {}
        self.financials: Dict[str, Dict] = {}
        
    def load_companies(self) -> Dict[str, Company]:
        """
        Load company objects for all tickers.
        
        Returns:
            Dictionary with tickers as keys and Company objects as values
        """
        print(f"Loading {len(self.tickers)} company/companies from EDGAR...")
        
        for ticker in self.tickers:
            try:
                print(f"  Loading {ticker}...", end=" ")
                company = Company(ticker)
                self.companies[ticker] = company
                print(f"✓ {company.name}")
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                
        return self.companies
    
    def fetch_filings(self, 
                     form_types: Optional[List[str]] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: int = 10) -> Dict[str, List[Filing]]:
        """
        Fetch filings for loaded companies.
        
        Args:
            form_types: List of form types (e.g., ['10-K', '10-Q', '8-K'])
                       If None, fetches all recent filings
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            limit: Maximum number of filings per company per form type
            
        Returns:
            Dictionary with tickers as keys and lists of Filing objects
        """
        if not self.companies:
            self.load_companies()
            
        form_types = form_types or ['10-K', '10-Q', '8-K']
        print(f"\nFetching filings for form types: {', '.join(form_types)}")
        
        for ticker, company in self.companies.items():
            print(f"\n{ticker} ({company.name}):")
            self.filings[ticker] = []
            
            for form_type in form_types:
                try:
                    print(f"  Fetching {form_type}...", end=" ")
                    
                    # Get filings for this form type
                    filings_list = company.get_filings(form=form_type).latest(limit)
                    
                    # Apply date filters if specified
                    filtered = []
                    for filing in filings_list:
                        filing_date = str(filing.filing_date)
                        
                        if start_date and filing_date < start_date:
                            continue
                        if end_date and filing_date > end_date:
                            continue
                            
                        filtered.append(filing)
                    
                    self.filings[ticker].extend(filtered)
                    print(f"✓ ({len(filtered)} filings)")
                    
                except Exception as e:
                    print(f"✗ Error: {str(e)}")
                    
        return self.filings
    
    def extract_financials(self, download_full_filing: bool = True, extract_xbrl: bool = True) -> Dict[str, Dict]:
        """
        Extract financial data from fetched filings.
        
        Args:
            download_full_filing: If True, download complete filing HTML/text
            extract_xbrl: If True, attempt to extract XBRL financial statements
            
        Returns:
            Dictionary with financial data organized by ticker
        """
        if not self.filings:
            print("No filings loaded. Run fetch_filings() first.")
            return {}
            
        print("\nExtracting financial data...")
        if download_full_filing:
            print("(Downloading full filings - this may take a moment...)")
        
        for ticker, filings_list in self.filings.items():
            print(f"\n{ticker}:")
            self.financials[ticker] = {
                'company_info': {},
                'filings': []
            }
            
            # Get company info
            if ticker in self.companies:
                company = self.companies[ticker]
                self.financials[ticker]['company_info'] = {
                    'name': company.name,
                    'cik': company.cik,
                    'ticker': ticker,
                    'sic_code': getattr(company, 'sic_code', None),
                    'industry': getattr(company, 'category', None),
                }
            
            # Extract from each filing
            for filing in filings_list:
                try:
                    filing_data = {
                        'form': filing.form,
                        'filing_date': str(filing.filing_date),
                        'accession_number': filing.accession_no,
                        'period_of_report': str(getattr(filing, 'period_of_report', '')),
                        'filing_url': f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={filing.cik}&accession_number={filing.accession_no.replace('-', '')}&xbrl_type=v"
                    }
                    
                    # Download full filing content
                    if download_full_filing:
                        try:
                            # Get the filing HTML/text
                            filing_html = filing.html()
                            if filing_html:
                                filing_data['full_filing_html'] = str(filing_html)
                                filing_data['full_filing_length'] = len(str(filing_html))
                            
                            # Try to get the primary document text
                            try:
                                filing_text = filing.text()
                                if filing_text:
                                    filing_data['filing_text'] = str(filing_text)
                            except Exception:
                                pass
                                
                        except Exception as e:
                            filing_data['download_error'] = f"Could not download full filing: {str(e)}"
                    
                    # Extract XBRL financials if available
                    if extract_xbrl:
                        try:
                            # Try to access financials object
                            if hasattr(filing, 'obj'):
                                financials_obj = filing.obj()
                                if financials_obj and hasattr(financials_obj, 'financials'):
                                    fin = financials_obj.financials
                                    
                                    # Balance Sheet
                                    if hasattr(fin, 'balance_sheet') and fin.balance_sheet is not None:
                                        try:
                                            filing_data['balance_sheet'] = fin.balance_sheet.to_dict('records')
                                        except Exception:
                                            filing_data['balance_sheet'] = str(fin.balance_sheet)
                                    
                                    # Income Statement
                                    if hasattr(fin, 'income_statement') and fin.income_statement is not None:
                                        try:
                                            filing_data['income_statement'] = fin.income_statement.to_dict('records')
                                        except Exception:
                                            filing_data['income_statement'] = str(fin.income_statement)
                                    
                                    # Cash Flow Statement
                                    if hasattr(fin, 'cash_flow_statement') and fin.cash_flow_statement is not None:
                                        try:
                                            filing_data['cash_flow'] = fin.cash_flow_statement.to_dict('records')
                                        except Exception:
                                            filing_data['cash_flow'] = str(fin.cash_flow_statement)
                            
                            # Alternative: try direct financials attribute
                            elif hasattr(filing, 'financials') and filing.financials is not None:
                                fin = filing.financials
                                
                                if hasattr(fin, 'balance_sheet') and fin.balance_sheet is not None:
                                    try:
                                        filing_data['balance_sheet'] = fin.balance_sheet.to_dict('records')
                                    except Exception:
                                        filing_data['balance_sheet'] = str(fin.balance_sheet)
                                
                                if hasattr(fin, 'income_statement') and fin.income_statement is not None:
                                    try:
                                        filing_data['income_statement'] = fin.income_statement.to_dict('records')
                                    except Exception:
                                        filing_data['income_statement'] = str(fin.income_statement)
                                
                                if hasattr(fin, 'cash_flow_statement') and fin.cash_flow_statement is not None:
                                    try:
                                        filing_data['cash_flow'] = fin.cash_flow_statement.to_dict('records')
                                    except Exception:
                                        filing_data['cash_flow'] = str(fin.cash_flow_statement)
                                        
                        except Exception as e:
                            filing_data['xbrl_extraction_note'] = f"XBRL not available or error: {str(e)}"
                    
                    self.financials[ticker]['filings'].append(filing_data)
                    
                    # Show what was extracted
                    extracted = []
                    if 'full_filing_html' in filing_data:
                        extracted.append(f"HTML ({filing_data['full_filing_length']} chars)")
                    if 'balance_sheet' in filing_data:
                        extracted.append("BS")
                    if 'income_statement' in filing_data:
                        extracted.append("IS")
                    if 'cash_flow' in filing_data:
                        extracted.append("CF")
                    
                    status = " [" + ", ".join(extracted) + "]" if extracted else ""
                    print(f"  ✓ {filing.form} - {filing.filing_date}{status}")
                    
                except Exception as e:
                    print(f"  ✗ Error extracting {filing.form}: {str(e)}")
                    
        return self.financials
    
    def save_to_json(self, output_dir: str = "SEC_filings") -> None:
        """
        Save extracted filings data to JSON files.
        
        Args:
            output_dir: Directory to save JSON files (default: SEC_filings)
        """
        if not self.financials:
            print("No financial data to save. Run extract_financials() first.")
            return
            
        # Create date folder
        today = date.today().strftime("%Y-%m-%d")
        output_path = os.path.join(output_dir, today)
        os.makedirs(output_path, exist_ok=True)
        
        print(f"\nSaving filings to {output_path}...")
        
        for ticker, data in self.financials.items():
            filename = os.path.join(output_path, f"{ticker}_filings.json")
            
            # Add metadata
            output_data = {
                'metadata': {
                    'ticker': ticker,
                    'extraction_date': datetime.now().isoformat(),
                    'total_filings': len(data.get('filings', [])),
                },
                'company_info': data.get('company_info', {}),
                'filings': data.get('filings', [])
            }
            
            with open(filename, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            print(f"  Saved: {filename}")
    
    def print_summary(self) -> None:
        """Print summary of collected filings."""
        print("\n" + "="*60)
        print("SEC FILINGS SUMMARY")
        print("="*60)
        
        for ticker in self.tickers:
            company = self.companies.get(ticker)
            filings = self.filings.get(ticker, [])
            
            if company:
                print(f"\n{ticker} - {company.name}")
                print(f"  CIK: {company.cik}")
            else:
                print(f"\n{ticker}")
                
            if filings:
                print(f"  Total Filings: {len(filings)}")
                
                # Count by form type
                form_counts = {}
                for filing in filings:
                    form = filing.form
                    form_counts[form] = form_counts.get(form, 0) + 1
                
                print("  Filings by type:")
                for form, count in sorted(form_counts.items()):
                    print(f"    {form}: {count}")
            else:
                print("  No filings found")


def interactive_mode():
    """Interactive mode for the SEC Filings Collector."""
    print("\n" + "="*60)
    print("SEC EDGAR FILINGS COLLECTOR - Interactive Mode")
    print("="*60 + "\n")
    print("Tip: type 'back' to go to previous question, or 'quit' to abort.\n")
    
    step = 0
    tickers: list[str] | None = None
    form_types: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 10
    download_full: bool = True
    
    while True:
        if step == 0:
            ans = input("Enter ticker(s) (space-separated, e.g., AAPL MSFT TSLA): ").strip()
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
            ans = input("Form types (10-K 10-Q 8-K) [default: all three]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 0
                continue
            if not ans:
                form_types = ['10-K', '10-Q', '8-K']
            else:
                form_types = [t.upper() for t in ans.split()]
            step = 2
            continue
            
        if step == 2:
            ans = input("Start date (YYYY-MM-DD) [leave blank for all]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 1
                continue
            if ans:
                try:
                    datetime.strptime(ans, '%Y-%m-%d')
                    start_date = ans
                except ValueError:
                    print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
                    continue
            step = 3
            continue
            
        if step == 3:
            ans = input("End date (YYYY-MM-DD) [default: today]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 2
                continue
            if ans == "":
                end_date = date.today().strftime('%Y-%m-%d')
            else:
                try:
                    datetime.strptime(ans, '%Y-%m-%d')
                    end_date = ans
                except ValueError:
                    print("❌ Invalid date format. Please use YYYY-MM-DD.\n")
                    continue
            step = 4
            continue
            
        if step == 4:
            ans = input("Max filings per form type [default: 10]: ").strip()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 3
                continue
            if ans:
                try:
                    limit = max(1, int(ans))
                except ValueError:
                    limit = 10
            step = 5
            continue
            
        if step == 5:
            ans = input("Download complete filing content? (yes/no) [default: yes]: ").strip().lower()
            low = ans.lower()
            if low in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if low in ("back", "b"):
                step = 4
                continue
            download_full = ans not in ('no', 'n')
            step = 6
            continue
            
        if step == 6:
            print("\nReview your selections:")
            print(f"  Tickers    : {' '.join(tickers or [])}")
            print(f"  Form Types : {' '.join(form_types or [])}")
            print(f"  Start Date : {start_date or 'None'}")
            print(f"  End Date   : {end_date}")
            print(f"  Limit      : {limit} per form type")
            print(f"  Full Filing: {'Yes' if download_full else 'No (metadata only)'}")
            ans = input("Proceed to download? (yes/back/quit) [default: yes]: ").strip().lower()
            if ans in ("quit", "exit", "abort", "q"):
                print("Aborted by user.")
                return
            if ans in ("back", "b"):
                step = 5
                continue
            break
    
    # Create collector and fetch data
    collector = EdgarFilingsCollector(tickers=tickers)
    collector.load_companies()
    collector.fetch_filings(
        form_types=form_types,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    collector.extract_financials(download_full_filing=download_full, extract_xbrl=True)
    collector.print_summary()
    
    # Ask about saving
    while True:
        save_input = input("\nWould you like to save the data? (yes/no) [default: yes]: ").strip().lower()
        if save_input in ("quit", "exit", "abort", "q"):
            print("Aborted by user.")
            return
        if save_input in ['yes', 'y', 'no', 'n', '']:
            break
        print("❌ Please enter 'yes' or 'no'.\n")
    
    if save_input in ['yes', 'y', '']:
        collector.save_to_json()
        print("\n✓ Data saved to SEC_filings/YYYY-MM-DD/ folder")


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Collect SEC EDGAR filings data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python edgar_filings_collector.py
  
  # Command-line: Get latest 10-K for Apple
  python edgar_filings_collector.py -t AAPL -f 10-K --limit 5 --save
  
  # Multiple companies and form types
  python edgar_filings_collector.py -t AAPL MSFT GOOGL -f 10-K 10-Q --limit 3 --save
  
  # With date range
  python edgar_filings_collector.py -t TSLA -f 10-K -s 2020-01-01 -e 2024-12-31 --save
        """
    )
    
    parser.add_argument('-t', '--tickers', nargs='+',
                        help='Stock ticker(s) to fetch (space-separated)')
    parser.add_argument('-f', '--forms', nargs='+',
                        default=['10-K', '10-Q', '8-K'],
                        help='Form types to fetch (default: 10-K 10-Q 8-K)')
    parser.add_argument('-s', '--start-date',
                        help='Start date filter (YYYY-MM-DD)')
    parser.add_argument('-e', '--end-date',
                        help='End date filter (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Max filings per form type (default: 10)')
    parser.add_argument('--save', action='store_true',
                        help='Save data to SEC_filings folder')
    parser.add_argument('--output-dir', default='SEC_filings',
                        help='Output directory (default: SEC_filings)')
    parser.add_argument('--download-full', action='store_true', default=True,
                        help='Download complete filing HTML/text (default: True)')
    parser.add_argument('--metadata-only', action='store_true',
                        help='Only save filing metadata, skip downloading full content')
    parser.add_argument('--extract-xbrl', action='store_true', default=True,
                        help='Extract XBRL financial statements (default: True)')
    
    args = parser.parse_args()
    
    # If no tickers provided, use interactive mode
    if not args.tickers:
        interactive_mode()
    else:
        # Command-line mode
        collector = EdgarFilingsCollector(tickers=args.tickers)
        collector.load_companies()
        collector.fetch_filings(
            form_types=args.forms,
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit
        )
        
        # Determine if we download full content
        download_full = not args.metadata_only
        
        collector.extract_financials(
            download_full_filing=download_full,
            extract_xbrl=args.extract_xbrl
        )
        collector.print_summary()
        
        if args.save:
            collector.save_to_json(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
