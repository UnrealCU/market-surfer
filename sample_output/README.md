# Sample Outputs (placeholder guide)

This folder keeps small example outputs for each script (left empty by default to keep the repo lean). Drop trimmed samples here locally if you want quick references without committing large files.

## Get_quotes.py
- Interactive layout: price/YYYY-MM-DD/TICKER.json, options/YYYY-MM-DD/TICKER.json, financial/YYYY-MM-DD/TICKER.json
- CLI --save layout: YYYY-MM-DD/price_data/TICKER.csv and YYYY-MM-DD/financial_data/financial_info.json

## edgar_filings_collector.py
- SEC_filings/YYYY-MM-DD/TICKER_filings.json (metadata, company_info, filings with BS/IS/CF when present)

## edgar_financial_parser.py
- SEC_financials/YYYY-MM-DD/TICKER_financials.json (metadata plus filings with BS/IS/CF records)

## example_usage.py
- indices_10years.json (10-year daily data for the pre-set indices)

## volatility_analysis.py
- data/volatility_TICKER.json and data/volatility_TICKER.png (rolling vol stats and charts)

## mahalanobis_regime.py
- Volatility_output/regimes/mahalanobis_regimes.json (regimes map with distances/percentiles and continuous_stress)
