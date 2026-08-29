"""
Strong Buy Stock Screener (free, no API key required)
========================================================

Scans a list of tickers (default: S&P 500) and flags the ones where
Wall Street analyst consensus is "Strong Buy", using Yahoo Finance
data via the free `yfinance` library.

SETUP (run once):
    pip install yfinance pandas requests lxml

RUN:
    python strong_buy_screener.py
    python strong_buy_screener.py --category semiconductor

    --category sets which ticker universe to scan:
        sp500          S&P 500 constituents (default)
        semiconductor  SOXX (iShares Semiconductor ETF) holdings
        nuclear        NLR (VanEck Uranium+Nuclear Energy ETF) holdings
        oil-gas        IXC (iShares Global Energy ETF) holdings
        clean-energy   ICLN (iShares Global Clean Energy ETF) holdings
        drone          DRNZ (REX Drone ETF) holdings

OUTPUT:
    Prints a table to the console and saves a timestamped CSV
    (e.g. strong_buy_stocks_sp500_19_08_2026_1.csv) in the same folder.
    Previous outputs are never overwritten; the trailing index
    restarts at 1 each new day.

NOTES:
- yfinance pulls from Yahoo Finance's public endpoints. It's free,
  but not official/supported by Yahoo, so it can occasionally break
  or rate-limit you. If that happens, wait a bit and rerun, or
  reduce MAX_TICKERS below.
- "Strong Buy" here is inferred from Yahoo's recommendationKey field
  (values: strong_buy, buy, hold, sell, strong_sell) plus the
  recommendationMean score (1.0 = Strong Buy, 5.0 = Strong Sell).
- This checks hundreds of tickers one by one, so it can take several
  minutes. A progress counter is printed so you can see it's working.
"""

import argparse
import glob
import os
import re
import time
from datetime import date

import pandas as pd
import requests
import yfinance as yf

# How many tickers to scan. Set to None to scan the full list.
MAX_TICKERS = None

# Consider a stock "Strong Buy" if Yahoo's average rating score is
# at or below this threshold (1.0 = unanimous Strong Buy, 5.0 = Strong Sell)
STRONG_BUY_THRESHOLD = 1.8


def get_sp500_tickers():
    """Pull the current S&P 500 ticker list from Wikipedia (free, no key)."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    # Wikipedia blocks the default Python user-agent with a 403, so fetch
    # the page ourselves with a browser-like header, then hand the HTML
    # text to pandas instead of letting pandas fetch the URL directly.
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
    return tickers


def get_semiconductor_tickers():
    """Pull current SOXX (iShares Semiconductor ETF) holdings from
    stockanalysis.com (free, no key)."""
    url = "https://stockanalysis.com/etf/soxx/holdings/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
    return tickers


# stockanalysis.com prefixes non-US holdings as "EXCHANGE: CODE". Map those
# prefixes to the suffix Yahoo Finance expects (e.g. "TSX: NXE" -> "NXE.TO").
EXCHANGE_SUFFIX = {
    "TSX": "TO",
    "TSXV": "V",
    "ASX": "AX",
    "LON": "L",
    "HKG": "HK",
    "KRX": "KS",
    "HEL": "HE",
    "EPA": "PA",
    "BIT": "MI",
    "SHA": "SS",
    "CPH": "CO",
    "BVMF": "SA",
    "ELI": "LS",
    "TYO": "T",
    "TLV": "TA",
    "NSE": "NS",
    "ETR": "DE",
    "BME": "MC",
    "CSE": "CN",
}


def normalize_ticker(raw_symbol):
    """Convert a stockanalysis.com holdings Symbol into a Yahoo-style
    ticker. Returns None if the exchange prefix isn't recognized."""
    raw_symbol = raw_symbol.strip()
    if ":" in raw_symbol:
        prefix, code = (part.strip() for part in raw_symbol.split(":", 1))
        suffix = EXCHANGE_SUFFIX.get(prefix)
        if not suffix:
            return None
        return f"{code}.{suffix}"
    return raw_symbol


def get_nuclear_tickers():
    """Pull current NLR (VanEck Uranium+Nuclear Energy ETF) holdings from
    stockanalysis.com (free, no key), translated to Yahoo-style tickers."""
    url = "https://stockanalysis.com/etf/nlr/holdings/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = [normalize_ticker(s) for s in df["Symbol"]]
    return [t for t in tickers if t]


def get_oil_gas_tickers():
    """Pull current IXC (iShares Global Energy ETF) holdings from
    stockanalysis.com (free, no key), translated to Yahoo-style tickers."""
    url = "https://stockanalysis.com/etf/ixc/holdings/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = [normalize_ticker(s) for s in df["Symbol"]]
    return [t for t in tickers if t]


def get_clean_energy_tickers():
    """Pull current ICLN (iShares Global Clean Energy ETF) holdings from
    stockanalysis.com (free, no key), translated to Yahoo-style tickers."""
    url = "https://stockanalysis.com/etf/icln/holdings/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = [normalize_ticker(s) for s in df["Symbol"]]
    return [t for t in tickers if t]


def get_drone_tickers():
    """Pull current DRNZ (REX Drone ETF) holdings from stockanalysis.com
    (free, no key), translated to Yahoo-style tickers."""
    url = "https://stockanalysis.com/etf/drnz/holdings/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    tables = pd.read_html(resp.text)
    df = tables[0]
    tickers = [normalize_ticker(s) for s in df["Symbol"].dropna()]
    return [t for t in tickers if t]


CATEGORIES = {
    "sp500": get_sp500_tickers,
    "semiconductor": get_semiconductor_tickers,
    "nuclear": get_nuclear_tickers,
    "oil-gas": get_oil_gas_tickers,
    "clean-energy": get_clean_energy_tickers,
    "drone": get_drone_tickers,
}


def next_output_filename(category):
    """Build a strong_buy_stocks_<category>_<day>_<month>_<year>_<index>.csv
    filename that doesn't collide with an existing file, so past outputs are
    kept. The index restarts at 1 each new day per category."""
    today = date.today()
    date_part = f"{today.day:02d}_{today.month:02d}_{today.year}"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prefix = f"strong_buy_stocks_{category}_{date_part}"
    pattern = os.path.join(script_dir, f"{prefix}_*.csv")

    max_index = 0
    for path in glob.glob(pattern):
        match = re.search(rf"{prefix}_(\d+)\.csv$", os.path.basename(path))
        if match:
            max_index = max(max_index, int(match.group(1)))

    return os.path.join(script_dir, f"{prefix}_{max_index + 1}.csv")


def check_ticker(ticker):
    """Return a dict of rating info for one ticker, or None if unavailable."""
    try:
        info = yf.Ticker(ticker).info
        mean = info.get("recommendationMean")
        key = info.get("recommendationKey")
        target = info.get("targetMeanPrice")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        num_analysts = info.get("numberOfAnalystOpinions")

        if mean is None:
            return None

        upside = None
        if target and price:
            upside = round((target - price) / price * 100, 1)

        return {
            "Ticker": ticker,
            "Company": info.get("shortName"),
            "RecommendationKey": key,
            "RecommendationMean": mean,
            "NumAnalysts": num_analysts,
            "Price": price,
            "TargetMeanPrice": target,
            "UpsidePct": upside,
        }
    except Exception:
        return None


def parse_args():
    parser = argparse.ArgumentParser(description="Strong Buy stock screener")
    parser.add_argument(
        "--category",
        choices=sorted(CATEGORIES),
        default="sp500",
        help="Ticker universe to scan (default: sp500)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    category = args.category

    print(f"Fetching {category} ticker list...")
    tickers = CATEGORIES[category]()
    if MAX_TICKERS:
        tickers = tickers[:MAX_TICKERS]

    print(f"Scanning {len(tickers)} tickers for analyst ratings...\n")

    results = []
    for i, ticker in enumerate(tickers, 1):
        row = check_ticker(ticker)
        if row:
            results.append(row)
        if i % 25 == 0 or i == len(tickers):
            print(f"  ...checked {i}/{len(tickers)}")
        time.sleep(0.3)  # be polite, avoid rate limits

    df = pd.DataFrame(results)
    if df.empty:
        print("No data retrieved. Yahoo may be rate-limiting; try again shortly.")
        return

    strong_buys = df[
        (df["RecommendationMean"] <= STRONG_BUY_THRESHOLD)
        & (df["NumAnalysts"].fillna(0) >= 5)
    ].sort_values("RecommendationMean")

    print(f"\nFound {len(strong_buys)} Strong Buy stocks (mean rating <= {STRONG_BUY_THRESHOLD}, 5+ analysts):\n")
    if not strong_buys.empty:
        print(strong_buys.to_string(index=False))

    output_path = next_output_filename(category)
    strong_buys.to_csv(output_path, index=False)
    print(f"\nSaved full results to {os.path.basename(output_path)}")


if __name__ == "__main__":
    main()
