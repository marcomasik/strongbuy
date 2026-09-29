#!/bin/bash
#
# Run a screener scan and append its output to a per-day log file
# (data/logs/scan_<YYYY-MM-DD>.log).
#
# launchd runs this on weeknights at 23:00 — see
# com.strong-buy-screener.daily.plist in this directory. It's also fine to
# run by hand, optionally for a single category:
#
#     ./scripts/daily_scan.sh           # every category (default)
#     ./scripts/daily_scan.sh nuclear   # just one
#
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data/logs

exec ./.venv/bin/python strong_buy_screener.py --category "${1:-all}" \
  >>"data/logs/scan_$(date +%Y-%m-%d).log" 2>&1
