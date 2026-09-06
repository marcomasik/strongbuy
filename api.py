"""Minimal FastAPI layer over the screener's SQLite database.

This is the frontend-facing layer. It only reads from data/screener.db
(written by strong_buy_screener.py / backfill_csvs.py) and never triggers
scans itself.

RUN (from the project root):
    ./.venv/bin/uvicorn api:app --reload

Then:
    http://127.0.0.1:8000/health
    http://127.0.0.1:8000/categories
    http://127.0.0.1:8000/stocks?category=nuclear
    http://127.0.0.1:8000/docs   (interactive API docs)
"""

import sqlite3

from fastapi import FastAPI, Query

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


@app.get("/stocks")
def stocks(category: str = Query(..., description="Category name, e.g. 'nuclear'")):
    """Every ticker checked in the most recent scan for `category`.

    Returns all rows recorded for that scan, not just Strong Buy
    qualifiers. If the category has no recorded scans, returns an empty
    list with run_at = null (HTTP 200, not 404).
    """
    latest = query(
        "SELECT id, run_at FROM scans WHERE category = ? "
        "ORDER BY run_at DESC, id DESC LIMIT 1",
        (category,),
    )
    if not latest:
        return {"category": category, "run_at": None, "count": 0, "stocks": []}

    scan = latest[0]
    rows = query(
        """
        SELECT ticker, company, recommendation_key, recommendation_mean,
               num_analysts, price, target_mean_price, upside_pct
        FROM scan_results
        WHERE scan_id = ?
        ORDER BY upside_pct DESC
        """,
        (scan["id"],),
    )
    return {
        "category": category,
        "run_at": scan["run_at"],
        "count": len(rows),
        "stocks": rows,
    }
