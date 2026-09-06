"""Minimal FastAPI layer over the screener's SQLite database.

This is the frontend-facing layer. It only reads from data/screener.db
(written by strong_buy_screener.py / backfill_csvs.py) and never triggers
scans itself.

RUN (from the project root):
    ./.venv/bin/uvicorn api:app --reload

Then:
    http://127.0.0.1:8000/health
    http://127.0.0.1:8000/categories
    http://127.0.0.1:8000/docs   (interactive API docs)
"""

import sqlite3

from fastapi import FastAPI

from db import DB_PATH, init_db

app = FastAPI(title="strong_buy_screener API")

init_db()  # ensure data/screener.db and its schema exist on a fresh checkout


def query(sql, params=()):
    """Run a read-only query and return rows as a list of dicts."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@app.get("/health")
def health():
    """Liveness check plus a couple of DB counters."""
    scans = query("SELECT COUNT(*) AS n FROM scans")[0]["n"]
    results = query("SELECT COUNT(*) AS n FROM scan_results")[0]["n"]
    return {"status": "ok", "scans": scans, "scan_results": results}


@app.get("/categories")
def categories():
    """Distinct categories that have at least one recorded scan."""
    rows = query("SELECT DISTINCT category FROM scans ORDER BY category")
    return {"categories": [r["category"] for r in rows]}
