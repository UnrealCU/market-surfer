#!/usr/bin/env python3
"""Test script for get_quotes function"""

from Get_quotes import get_quotes
import json

# Test 1: Single ticker, JSON string
print("Test 1: Single ticker (JSON string)")
print("="*60)
data_json = get_quotes('AAPL', '2025-01-01', '2025-01-10')
data = json.loads(data_json)
print(f"Ticker: {data['metadata']['tickers']}")
print(f"Records: {data['summary']['AAPL']['records']}")
print(f"Average Price: ${data['summary']['AAPL']['avg_price']:.2f}")
print()

# Test 2: Multiple tickers, dictionary format
print("Test 2: Multiple tickers (dictionary)")
print("="*60)
data = get_quotes(['AAPL', 'MSFT', 'TSLA'], '2025-01-01', '2025-01-10', return_format='dict')
for ticker in data['metadata']['tickers']:
    print(f"{ticker}:")
    print(f"  Records: {data['summary'][ticker]['records']}")
    print(f"  Start: ${data['summary'][ticker]['start_price']:.2f}")
    print(f"  End: ${data['summary'][ticker]['end_price']:.2f}")
print()

# Test 3: Specific data points
print("Test 3: Specific columns only")
print("="*60)
data = get_quotes('AAPL', '2025-01-01', '2025-01-10', 
                  data_points=['Close', 'Volume'], 
                  return_format='dict')
print(f"Data points requested: {data['metadata']['data_points']}")
print(f"First record: {data['data']['AAPL'][0]}")
print()

# Test 4: Show JSON structure
print("Test 4: Full JSON output (first 500 chars)")
print("="*60)
json_output = get_quotes('MSFT', '2025-01-01', '2025-01-05')
print(json_output[:500] + "...")
