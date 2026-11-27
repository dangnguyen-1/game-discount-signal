"""
Rerun the analysis from the collected data, in order.

Usage, from the repo root:
    python run_all.py

Assumes the data collection steps have been run (fetch_steam, fetch_itad, fetch_stocks, fetch_reviews), so
data/raw/ and data/interim/ exist locally, and the hand-built files in data/manual/ are in place.
The holdout (src.holdout) is deliberately not included: D13 allows it to be run once.
"""

import subprocess
import sys

STEPS = [
    "src.build_prices",
    "src.fetch_stocks",       # reads cached prices from data/raw/stocks/; downloads only if missing
    "src.build_events",
    "src.event_study --include-holdout",   # holdout already run once (docs/holdout_run.txt); keeps
                                          # event_returns.csv complete. Q1-Q3 still exclude holdout games.
    "src.q1_regression",
    "src.q2_discount_reaction",
    "src.q3_trading_rule",
]

for step in STEPS:
    print(f"\n=== {step} ===", flush=True)
    result = subprocess.run([sys.executable, "-m", *step.split()])
    if result.returncode != 0:
        sys.exit(f"{step} failed (exit code {result.returncode}); stopping.")
print("\nAll steps completed.")
