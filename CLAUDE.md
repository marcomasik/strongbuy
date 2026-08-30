# strong_buy_screener

## Working mode (FastAPI/SQLite/frontend build-out)

While building out the backend (FastAPI), database (SQLite), and any
frontend on top of `strong_buy_screener.py`:

- Work in small, incremental steps — one step per turn, not a batch of
  steps done in one go. Each step should deliver something concrete and
  working, even if it's not visible/exciting (e.g. "the DB schema exists
  and the scan results are being written to it").
- Before starting a step, if anything about scope or approach is
  ambiguous, ask rather than assume.
- After finishing a step, stop and wait for confirmation/direction before
  moving to the next one — don't chain multiple steps together.
- Keep the core screener logic (scraping, rating checks, category
  functions in `strong_buy_screener.py`) loosely coupled from the
  DB/API/frontend layers. The Python screening logic is expected to keep
  evolving (new categories, new fields, etc.) — the DB schema and API
  contract should be stable enough to absorb that without breaking the
  frontend or requiring coordinated changes across all layers at once.

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
