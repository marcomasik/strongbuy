"""SQLite schema and connection helper for strong_buy_screener.

Two tables:
- scans: one row per scan run (category + timestamp).
- scan_results: one row per ticker checked during a scan, linked to
  scans.id. Every ticker checked is stored, not just the ones that
  currently pass the Strong Buy threshold, so rating history stays
  available even if STRONG_BUY_THRESHOLD changes later or a ticker
  crosses the line between scans.

RUN (creates/updates the schema, safe to run repeatedly):
    python db.py
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "screener.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            run_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL REFERENCES scans(id),
            ticker TEXT NOT NULL,
            company TEXT,
            recommendation_key TEXT,
            recommendation_mean REAL,
            num_analysts INTEGER,
            price REAL,
            target_mean_price REAL,
            upside_pct REAL
        );

        CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id
            ON scan_results(scan_id);
        CREATE INDEX IF NOT EXISTS idx_scan_results_ticker
            ON scan_results(ticker);
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
