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
import threading
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from db import DB_PATH, init_db
from strong_buy_screener import CATEGORIES, run_scan

app = FastAPI(title="strong_buy_screener API")

init_db()  # ensure data/screener.db and its schema exist on a fresh checkout

# In-memory state for the one scan that's allowed to run at a time. Lost on
# server restart, which is fine: it only tracks the current run, not history
# (history lives in the DB via db.record_scan).
_scan_lock = threading.Lock()
_scan_state = {"running": False, "category": None, "started_at": None, "error": None}


def _run_scan_in_background(category):
    try:
        run_scan(category)
    except Exception as e:
        _scan_state["error"] = str(e)
    finally:
        _scan_state["running"] = False


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


@app.get("/scans")
def scans(category: str = Query(..., description="Category name, e.g. 'nuclear'")):
    """Every recorded scan date for `category`, newest first."""
    rows = query(
        "SELECT id, run_at FROM scans WHERE category = ? "
        "ORDER BY run_at DESC, id DESC",
        (category,),
    )
    return {"category": category, "scans": rows}


@app.get("/stocks")
def stocks(
    category: str = Query(..., description="Category name, e.g. 'nuclear'"),
    scan_id: Optional[int] = Query(
        None, description="Specific scan id (see /scans). Defaults to the latest scan."
    ),
):
    """Every ticker checked in a scan for `category`.

    Returns all rows recorded for that scan, not just Strong Buy
    qualifiers. Defaults to the most recent scan; pass `scan_id` (from
    /scans) to fetch an older one. If the category has no recorded
    scans, returns an empty list with run_at = null (HTTP 200, not 404).
    """
    if scan_id is not None:
        latest = query(
            "SELECT id, run_at FROM scans WHERE id = ? AND category = ?",
            (scan_id, category),
        )
    else:
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


@app.get("/scans/status")
def scan_status():
    """Current state of the (at most one) in-progress scan."""
    return dict(_scan_state)


@app.post("/scans/run")
def scan_run(category: str = Query(..., description="Category name, e.g. 'nuclear'")):
    """Kick off a scan for `category` in a background thread.

    Only one scan may run at a time (across all categories) since the
    screener scrapes Yahoo Finance live and shouldn't be hammered with
    overlapping requests. Returns 409 if a scan is already running, 404
    if `category` isn't a known category.
    """
    if category not in CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    with _scan_lock:
        if _scan_state["running"]:
            raise HTTPException(
                status_code=409,
                detail=f"A scan for '{_scan_state['category']}' is already running",
            )
        _scan_state["running"] = True
        _scan_state["category"] = category
        _scan_state["started_at"] = datetime.now().isoformat(timespec="seconds")
        _scan_state["error"] = None
        threading.Thread(
            target=_run_scan_in_background, args=(category,), daemon=True
        ).start()

    return dict(_scan_state)
