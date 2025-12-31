#!/usr/bin/env python3
"""Fetch quotes for S&P 500 tickers missing from spy_3y.json.

The script loads S&P 500 tickers, compares them to the tickers already present
in clean_data/spy_3y.json, fetches the missing ones, and saves incremental
progress to clean_data/spy_3y_3.json so work is not lost mid-run.
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import pandas as pd

from get_quotes import get_quotes


def load_sp500_tickers(path: str) -> set:
    df = pd.read_csv(path)
    return set(df["Symbol"].str.upper())


def load_spy_tickers(path: Path) -> set:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
        return set(data.get("data", {}).keys())
    except Exception as exc:  # tolerate malformed/mid-write file
        print(f"Warning: could not read {path}: {exc}")
        return set()


def fetch_ticker(ticker: str, start_date: str, end_date: str) -> dict:
    return get_quotes(ticker, start_date, end_date, return_format="dict")


def persist(path: Path, payload: dict) -> None:
    try:
        path.write_text(json.dumps(payload, indent=2, default=str))
    except Exception as exc:
        print(f"Warning: failed to write {path}: {exc}")


def main() -> None:
    # 3-year window
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    sp500_path = "clean_data/S&P500Tickers.csv"
    spy_path = Path("clean_data/spy_3y.json")
    out_path = Path("clean_data/spy_3y_3.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sp500_tickers = load_sp500_tickers(sp500_path)
    spy_3y_tickers = load_spy_tickers(spy_path)
    tickers_to_fetch = sorted(sp500_tickers - spy_3y_tickers)

    print(f"Fetching {len(tickers_to_fetch)} tickers missing from spy_3y.json")
    print(f"Date range: {start_date} to {end_date}")
    print("=" * 60)

    results = {
        "metadata": {
            "start_date": start_date,
            "end_date": end_date,
            "interval": "1d",
            "generated_at": datetime.now().isoformat(),
        },
        "data": {},
        "summary": {},
    }

    min_interval = 0.5  # seconds between calls
    failed: list[str] = []

    if not tickers_to_fetch:
        print("Nothing to fetch: all S&P 500 tickers already present.")
        persist(out_path, results)
        return

    for idx, ticker in enumerate(tickers_to_fetch, 1):
        t0 = time.perf_counter()
        try:
            payload = fetch_ticker(ticker, start_date, end_date)
            for key, val in payload.get("data", {}).items():
                results["data"][key] = val
            results["summary"].update(payload.get("summary", {}))
            print(
                f"[{idx}/{len(tickers_to_fetch)}] Fetched {ticker}: "
                f"records={len(payload.get('data', {}).get(ticker, []))}"
            )
        except Exception as exc:
            print(f"Failed to fetch {ticker}: {exc}")
            failed.append(ticker)
        finally:
            elapsed = time.perf_counter() - t0
            remaining = min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

        persist(out_path, results)  # write progress each loop

    persist(out_path, results)
    print(f"\nDone. Saved incremental results to: {out_path}")
    if failed:
        print(f"Failed tickers: {failed}")


if __name__ == "__main__":
    main()