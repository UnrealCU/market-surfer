#!/usr/bin/env python3
"""
EDGAR Financial Parser
Fetch filings via edgar (edgartools) and export XBRL financial statements to JSON
structured for analysis.
"""

import argparse
import glob
import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from edgar import set_identity, Company

# Identify to EDGAR
set_identity("Lukas Dabrowski ld3179@columbia.edu")


def resolve_input_file(path: str) -> str:
    """Locate an input file by searching within the project root if needed."""
    if not path:
        return ""

    # Absolute or directly existing path
    if os.path.isabs(path) and os.path.exists(path):
        return os.path.abspath(path)

    if os.path.exists(path):
        return os.path.abspath(path)

    search_root = os.path.dirname(os.path.abspath(__file__))

    # Check relative to project root first
    candidate = os.path.join(search_root, path)
    if os.path.exists(candidate):
        return os.path.abspath(candidate)

    # Recursive glob search for the filename anywhere in the project
    matches = glob.glob(os.path.join(search_root, "**", path), recursive=True)
    if matches:
        return os.path.abspath(matches[0])

    return ""


def _stmt_to_records(stmt: Any) -> List[Dict[str, Any]]:
    """Convert a statement object to list-of-dicts if possible, handling callables and DataFrames."""
    if stmt is None:
        return []
    try:
        # If it's a callable (common for edgartools financials), invoke it
        if callable(stmt):
            stmt = stmt()

        if stmt is None:
            return []

        # Pandas DataFrame-like objects
        if hasattr(stmt, "to_dict") and not isinstance(stmt, (dict, list)):
            try:
                return stmt.to_dict("records")  # type: ignore[arg-type]
            except TypeError:
                pass

        if hasattr(stmt, "to_dataframe"):
            df = stmt.to_dataframe()
            return df.to_dict(orient="records")

        if hasattr(stmt, "to_frame"):
            df = stmt.to_frame()
            return df.to_dict(orient="records")

        # Already list or dict
        if isinstance(stmt, list):
            return stmt
        if isinstance(stmt, dict):
            return [stmt]
    except Exception:
        return []
    # Fallback: string form
    try:
        return [{"raw": str(stmt)}]
    except Exception:
        return []


def _first_available(fin: Any, names: List[str]) -> Any:
    for name in names:
        if hasattr(fin, name):
            return getattr(fin, name)
    return None


def extract_financials_from_filing(filing: Any) -> Dict[str, Any]:
    """Extract core statements and metadata from a single filing."""
    data: Dict[str, Any] = {
        "form": getattr(filing, "form", None),
        "filing_date": str(getattr(filing, "filing_date", "")),
        "period_of_report": str(getattr(filing, "period_of_report", "")),
        "accession_number": getattr(filing, "accession_no", None),
    }

    fin = None
    # Try richer object first
    try:
        if hasattr(filing, "obj"):
            obj = filing.obj()
            if obj and hasattr(obj, "financials"):
                fin = obj.financials
    except Exception:
        fin = None

    # Fallback
    if fin is None and hasattr(filing, "financials"):
        fin = getattr(filing, "financials")

    if fin:
        bs = _first_available(fin, [
            "balance_sheet",
            "balance_sheets",
            "statement_of_financial_position",
        ])
        is_ = _first_available(fin, [
            "income_statement",
            "income_statements",
            "statement_of_operations",
            "statement_of_income",
        ])
        cf = _first_available(fin, [
            "cash_flow_statement",
            "cash_flow",
            "cashflow_statement",
            "cashflow",
            "statement_of_cash_flows",
            "statement_of_cashflows",
        ])

        data["balance_sheet"] = _stmt_to_records(bs)
        data["income_statement"] = _stmt_to_records(is_)
        data["cash_flow"] = _stmt_to_records(cf)
    else:
        data["xbrl_available"] = False
    return data


def collect_financials(
    tickers: List[str],
    forms: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    limit: int = 4,
) -> Dict[str, Any]:
    """Collect filings and parse financials for multiple tickers."""
    results: Dict[str, Any] = {}
    for ticker in tickers:
        try:
            company = Company(ticker)
        except Exception as exc:
            results[ticker] = {"error": f"Could not load company: {exc}"}
            continue

        filings_out: List[Dict[str, Any]] = []
        for form in forms:
            try:
                filings = company.get_filings(form=form).latest(limit)
            except Exception as exc:
                results[ticker] = {"error": f"Could not fetch filings: {exc}"}
                continue

            for filing in filings:
                f_date = str(getattr(filing, "filing_date", ""))
                if start_date and f_date and f_date < start_date:
                    continue
                if end_date and f_date and f_date > end_date:
                    continue
                parsed = extract_financials_from_filing(filing)
                filings_out.append(parsed)

        results[ticker] = {
            "metadata": {
                "ticker": ticker,
                "forms": forms,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "extracted_at": datetime.now().isoformat(),
            },
            "filings": filings_out,
        }
    return results


def save_results(payload: Dict[str, Any], output_dir: str = "SEC_financials") -> List[str]:
    """Save each ticker's data into date-partitioned subfolders with ticker-named files."""

    saved_paths: List[str] = []

    for ticker, info in payload.items():
        if not isinstance(info, dict) or "error" in info:
            continue

        meta = info.get("metadata", {}) if isinstance(info, dict) else {}
        ticker_name = meta.get("ticker") or str(ticker)

        # Derive date folder from extracted_at when available; fallback to today
        extracted_at = meta.get("extracted_at") or meta.get("extraction_date")
        if extracted_at:
            extracted_str = str(extracted_at)
            date_part = extracted_str.split("T")[0].split(" ")[0]
        else:
            date_part = date.today().strftime("%Y-%m-%d")

        target_dir = os.path.join(output_dir, date_part)
        os.makedirs(target_dir, exist_ok=True)

        filename = f"{ticker_name}_financials.json"
        path = os.path.join(target_dir, filename)

        with open(path, "w") as f:
            json.dump(info, f, indent=2, default=str)

        saved_paths.append(path)

    return saved_paths


def normalize_payload(payload: Any) -> Dict[str, Any]:
    """Normalize input payload so downstream loops can safely iterate tickers.

    Accepts either:
    - Dict keyed by ticker (preferred)
    - Dict with keys like filings/metadata/company_info (single ticker file)
    - List of filings (wraps into a single entry)
    """

    # If already in expected dict-of-dicts form, keep it
    if isinstance(payload, dict):
        # Heuristic: single-ticker file with top-level filings/metadata
        if any(k in payload for k in ["filings", "metadata", "company_info"]):
            return {"input_file": payload}
        return payload

    # Handle list of filings
    if isinstance(payload, list):
        return {"input_file": {"filings": payload}}

    # Fallback: wrap unknown structure
    return {"input_file": {"raw": payload}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract financial statements from SEC filings using edgar (edgartools)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive-like quick run
  python edgar_financial_parser.py -t AAPL MSFT -f 10-K 10-Q --limit 4 --save

  # Date-filtered
  python edgar_financial_parser.py -t AAPL -f 10-K --start 2020-01-01 --end 2024-12-31 --limit 6 --save
        """,
    )
    parser.add_argument("-t", "--tickers", nargs="+", required=False, help="Tickers or CIKs (required unless using --input-file)")
    parser.add_argument("-f", "--forms", nargs="+", default=["10-K", "10-Q"], help="Form types")
    parser.add_argument("-s", "--start", help="Start date YYYY-MM-DD")
    parser.add_argument("-e", "--end", help="End date YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=4, help="Max filings per form")
    parser.add_argument("--save", action="store_true", help="Save output JSON to SEC_financials")
    parser.add_argument("--output-dir", default="SEC_financials", help="Output directory")
    parser.add_argument("--input-file", help="Parse existing JSON instead of calling the SEC API")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.input_file:
        resolved_input = resolve_input_file(args.input_file)
        if not resolved_input:
            search_root = os.path.dirname(os.path.abspath(__file__))
            raise SystemExit(
                f"Input file not found: {args.input_file}. Searched under {search_root}"
            )

        print(f"Using input file: {resolved_input}")
        with open(resolved_input, "r") as f:
            payload = json.load(f)
        payload = normalize_payload(payload)
    else:
        if not args.tickers:
            raise SystemExit("Tickers are required unless --input-file is provided.")
        payload = collect_financials(
            tickers=args.tickers,
            forms=args.forms,
            start_date=args.start,
            end_date=args.end,
            limit=args.limit,
        )

    # Print summary to console
    for ticker, info in payload.items():
        print(f"\n=== {ticker} ===")
        if not isinstance(info, dict):
            print(f"Unsupported payload structure for {ticker} (expected dict, got {type(info).__name__}).")
            continue
        if "error" in info:
            print(f"Error: {info['error']}")
            continue
        filings = info.get("filings", [])
        print(f"Filings parsed: {len(filings)}")
        counts: Dict[str, int] = {}
        for f in filings:
            form = f.get("form")
            if form:
                counts[form] = counts.get(form, 0) + 1
        if counts:
            print("By form:")
            for form, count in sorted(counts.items()):
                print(f"  {form}: {count}")

    if args.save:
        saved = save_results(payload, args.output_dir)
        if saved:
            print("\nSaved files:")
            for p in saved:
                print(f"  {p}")
        else:
            print("\nNo files were saved (no successful ticker entries).")

    # If not saving, print compact JSON preview
    if not args.save:
        print("\nJSON Preview (truncated):")
        preview = json.dumps(payload, indent=2)[:2000]
        print(preview)


if __name__ == "__main__":
    main()
