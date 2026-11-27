"""
D13: one-time holdout analysis (games launched from 2025-01-01).

Usage, from the repo root, after `python -m src.event_study --include-holdout`:
    python -m src.holdout            # runs once; writes docs/holdout_run.txt
    python -m src.holdout --force    # rerun, recorded in docs/deviations.md

Uses the main-sample rules unchanged. With few games the results are descriptive:
per-game values, the sign of the simple CAR_E-abn_90 relation, group means, and the Q3 trades.
Outputs: output/tables/holdout_games.csv, output/tables/holdout_trades.csv
"""

import argparse
from datetime import datetime

import numpy as np
import pandas as pd

import config
from src.q3_trading_rule import Stock, build_trades

MARKER = config.DOCS / "holdout_run.txt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if MARKER.exists() and not args.force:
        raise SystemExit(f"The holdout was already run ({MARKER.read_text().strip()}). "
                         "D13 allows one run; use --force only with a reason, and it will be logged.")

    ev = pd.read_csv(config.PROCESSED / "events.csv", parse_dates=["day0_discount", "day0_earnings"])
    rt = pd.read_csv(config.PROCESSED / "event_returns.csv")
    ev = ev[ev["holdout"].astype(bool)].copy()
    missing = set(ev["steam_appid"]) - set(rt["steam_appid"])
    if missing:
        raise SystemExit("Holdout returns missing: run `python -m src.event_study --include-holdout` first.")

    d = ev.merge(rt[["steam_appid", "CAR_E", "CAR_D_0_2", "CAR_D_0_10"]], on="steam_appid", how="left")
    d["early_cut_rt"] = d["early_cut_rt"].astype(bool)
    d["tentpole"] = d["tentpole"].map({True: True, False: False, "True": True, "False": False})
    d["group"] = np.where(~d["early_cut_rt"], "C: no early cut",
                          np.where(d["tentpole"] == True, "A: early-cut tentpole", "B: early cut, not tentpole"))

    ret = pd.read_csv(config.INTERIM / "returns.csv", parse_dates=["date"])
    stocks = {tk: Stock(r) for tk, r in ret.groupby("ticker")}
    earn = pd.concat([pd.read_csv(p, parse_dates=["announcement_date"])
                      for p in sorted(config.MANUAL.glob("earnings_*.csv"))], ignore_index=True)
    if "event_type" in earn:
        earn = earn[earn["event_type"].fillna("scheduled") == "scheduled"]
    trades = build_trades(d, stocks, earn, lambda e: e["early_cut_rt"] & (e["tentpole"] == True), config.COST_BPS)

    cols = ["publisher", "game_title", "pc_launch_date", "max_depth_90", "norm_90", "abn_90", "first_cut_day",
            "early_cut_rt", "tentpole", "group", "earnings_date", "CAR_E", "CAR_D_0_10"]
    config.TABLES.mkdir(parents=True, exist_ok=True)
    d[cols].to_csv(config.TABLES / "holdout_games.csv", index=False)
    trades.to_csv(config.TABLES / "holdout_trades.csv", index=False)

    ok = d.dropna(subset=["abn_90", "CAR_E"])
    slope = np.polyfit(ok["abn_90"], ok["CAR_E"], 1)[0] if ok["abn_90"].nunique() > 1 else np.nan

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.force and MARKER.exists():
        with open(config.DOCS / "deviations.md", "a") as f:
            f.write(f"\n## {stamp[:10]}: holdout rerun with --force (previous run: {MARKER.read_text().strip()})\n"
                    "- Reason: [fill in]\n")
    MARKER.write_text(f"Holdout run {stamp}; {len(d)} games; {len(trades)} Q3 trades\n")

    print(f"HOLDOUT (D13), run {stamp}: {len(d)} games launched from {config.HOLDOUT_START}\n")
    print(d[cols].round(3).to_string(index=False))
    print(f"\nSimple slope of CAR_E on abn_90 (no controls, {len(ok)} games): {slope:+.4f} "
          f"(main sample, with controls: +0.082)")
    print("\nGroup means:")
    print(d.groupby("group")[["CAR_D_0_10", "CAR_E"]].agg(["count", "mean"]).round(4).to_string())
    print(f"\nQ3 trades in the holdout: {len(trades)}")
    if len(trades):
        print(trades[["game_title", "entry", "exit", "holding_days", "net"]].round(4).to_string(index=False))
        print(f"Mean net per trade: {trades['net'].mean():+.2%} (main sample: -5.5%)")
    print(f"\nSaved {config.TABLES}/holdout_games.csv and holdout_trades.csv; marker written to {MARKER}")


if __name__ == "__main__":
    main()
