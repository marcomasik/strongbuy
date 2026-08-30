"""One-off backfill: load existing data/<category>/*.csv history into SQLite.

Each CSV produced by strong_buy_screener.py is the Strong Buy result set
for one scan run. This script turns each CSV into one `scans` row plus its
`scan_results` rows, so past scans aren't lost when the DB becomes the
source of truth.

Notes / limitations:
- CSVs only contain Strong Buy qualifiers (that's all the screener saved),
  so backfilled scans have fewer rows than a live scan going forward, which
  stores every ticker checked.
- Category is taken from the parent folder name (data/<category>/), which
  also covers older sp500 files whose names lack the category token.
- Scan date comes from the DD_MM_YYYY in the filename; if absent
  (e.g. the original data/sp500/strong_buy_stocks.csv), the file's
  modification date is used. Time is set to 00:00:00.
- Idempotent: a CSV whose (category, run_at) already exists in `scans` is
  skipped, so re-running this script won't duplicate rows.

RUN:
    python backfill_csvs.py
"""

import csv
import glob
import os
import re
from datetime import datetime

import db

DATA_DIR = os.path.dirname(db.DB_PATH)

# Maps CSV header -> the dict key db.record_scan expects (screener's names).
CSV_TO_ROW_KEY = {
    "Ticker": "Ticker",
    "Company": "Company",
    "RecommendationKey": "RecommendationKey",
    "RecommendationMean": "RecommendationMean",
    "NumAnalysts": "NumAnalysts",
    "Price": "Price",
    "TargetMeanPrice": "TargetMeanPrice",
    "UpsidePct": "UpsidePct",
}
FLOAT_KEYS = {"RecommendationMean", "Price", "TargetMeanPrice", "UpsidePct"}
INT_KEYS = {"NumAnalysts"}

DATE_RE = re.compile(r"(\d{2})_(\d{2})_(\d{4})")


def _to_float(value):
    value = (value or "").strip()
    return float(value) if value else None


def scan_datetime_for(path):
    """ISO 'YYYY-MM-DDT00:00:00' for a CSV: from the DD_MM_YYYY in the
    filename, else from the file's modification date."""
    match = DATE_RE.search(os.path.basename(path))
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}T00:00:00"
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return mtime.strftime("%Y-%m-%dT00:00:00")


def rows_from_csv(path):
    rows = []
    with open(path, newline="") as f:
        for raw in csv.DictReader(f):
            row = {}
            for csv_key, row_key in CSV_TO_ROW_KEY.items():
                value = raw.get(csv_key)
                if row_key in FLOAT_KEYS:
                    row[row_key] = _to_float(value)
                elif row_key in INT_KEYS:
                    num = _to_float(value)
                    row[row_key] = int(num) if num is not None else None
                else:
                    value = (value or "").strip()
                    row[row_key] = value or None
            rows.append(row)
    return rows


def existing_scan_keys(conn):
    return {tuple(r) for r in conn.execute("SELECT category, run_at FROM scans")}


def main():
    db.init_db()
    conn = db.get_connection()
    already = existing_scan_keys(conn)
    conn.close()

    paths = sorted(glob.glob(os.path.join(DATA_DIR, "*", "*.csv")))
    imported = skipped = total_rows = 0

    for path in paths:
        category = os.path.basename(os.path.dirname(path))
        run_at = scan_datetime_for(path)
        rel = os.path.relpath(path, DATA_DIR)

        if (category, run_at) in already:
            print(f"skip   {rel}  (already imported: {category} @ {run_at})")
            skipped += 1
            continue

        rows = rows_from_csv(path)
        scan_id = db.record_scan(category, rows, run_at=run_at)
        already.add((category, run_at))
        imported += 1
        total_rows += len(rows)
        print(f"import {rel}  -> scan #{scan_id}  ({len(rows)} rows, {category} @ {run_at})")

    print(
        f"\nDone. {imported} file(s) imported ({total_rows} rows), "
        f"{skipped} skipped, {len(paths)} seen."
    )


if __name__ == "__main__":
    main()
