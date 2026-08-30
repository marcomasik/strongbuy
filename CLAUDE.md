# strong_buy_screener

## Adding a new ETF category

Categories are added one at a time (see git history: semiconductor, nuclear,
oil-gas, clean-energy, drone). To add a new one, follow the existing pattern
exactly:

1. Write `get_<category>_tickers()` in `strong_buy_screener.py` that scrapes
   `https://stockanalysis.com/etf/<ETF_TICKER>/holdings/` with a browser-like
   `User-Agent` header (stockanalysis.com and Wikipedia block the default
   Python/requests user agent with a 403).
2. Run each symbol through `normalize_ticker()` to translate non-US
   "EXCHANGE: CODE" holdings (e.g. `TSX: NXE`) into Yahoo-style tickers
   (e.g. `NXE.TO`) via the `EXCHANGE_SUFFIX` map — add a new exchange prefix
   to that map if one isn't covered yet.
3. Register the function in the `CATEGORIES` dict.
4. Add the category to the module docstring's `--category` list at the top
   of the file so `--help` and the docs stay in sync.
