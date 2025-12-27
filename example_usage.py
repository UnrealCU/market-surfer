#!/usr/bin/env python3
"""Get 10 years of daily quotes for major indices"""

from get_quotes import get_quotes
from datetime import datetime, timedelta
import json

# Calculate dates for past 10 years
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')

print("Fetching 10 years of daily quotes for major indices...")
print(f"Date range: {start_date} to {end_date}")
print("=" * 60)

# List of indices
# ^GSPC = S&P 500, ^STOXX = STOXX Europe 600, AAXJ = Asia ex-Japan, ^N225 = Nikkei 225
indices = ['^GSPC', '^STOXX', 'AAXJ', '^N225']

# Fetch data
data = get_quotes(indices, start_date, end_date, return_format='dict')

# Print summary
print("\nSUMMARY:")
print("-" * 60)
for ticker in indices:
    if ticker in data['summary']:
        summary = data['summary'][ticker]
        print(f"\n{ticker}:")
        print(f"  Records: {summary['records']}")
        print(f"  Start Price: ${summary['start_price']:.2f}")
        print(f"  End Price: ${summary['end_price']:.2f}")
        print(f"  Min Price: ${summary['min_price']:.2f}")
        print(f"  Max Price: ${summary['max_price']:.2f}")
        print(f"  Avg Price: ${summary['avg_price']:.2f}")

# Save to JSON file
print("\n" + "=" * 60)
json_output = get_quotes(indices, start_date, end_date)
with open('indices_10years.json', 'w') as f:
    f.write(json_output)
print("✓ Full data saved to: indices_10years.json")
