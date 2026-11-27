"""
Phase 3: daily price series and per-game discount measures.

Usage, from the repo root:
    python -m src.build_prices                  # every publisher with an itad_summary file
    python -m src.build_prices capcom ubisoft   # only these

Inputs:  data/interim/itad_summary_<publisher>.csv, data/raw/itad/<itad_id>.json,
         data/manual/price_overrides.csv
Outputs: data/processed/daily_prices.csv  (one row per game per day since launch)
         data/processed/game_prices.csv   (one row per game: P0, depths, first cut)

Rules (docs/preregistration.md D5, D15; docs/data_log.md cleaning rules):
  - Steam US store days are calendar days in US Pacific time.
  - Entries with a regular price of 0 or less are dropped before anything else.
  - Daily price = lowest price available at any point that day.
  - P0 = regular price in effect at the end of launch day, unless a confirmed override exists.
  - depth on day k = max(0, 1 - price_k / P0), measured on calendar day k after launch.
  - first_cut_day = first day after day 14 with depth >= 20%.
"""

import argparse
import json
from datetime import timedelta

import pandas as pd

import config

STORE_TZ = "America/Los_Angeles"


def load_log(itad_id):
    """Cleaned ITAD history log: local store date, price, regular. Raw file is not modified."""
    entries = json.loads((config.RAW_ITAD / f"{itad_id}.json").read_text())
    log = pd.DataFrame({
        "ts": [pd.Timestamp(e["timestamp"]).tz_convert("UTC") for e in entries],
        "price": [e["deal"]["price"]["amount"] for e in entries],
        "regular": [e["deal"]["regular"]["amount"] for e in entries],
    })
    log = log[log["regular"] > 0].sort_values("ts", kind="stable").reset_index(drop=True)
    log["date"] = log["ts"].dt.tz_convert(STORE_TZ).dt.date
    return log


def daily_lowest(log, start, end):
    """Lowest price available on each calendar day from start to end (inclusive)."""
    day_min = log.groupby("date")["price"].min()
    day_last = log.groupby("date")["price"].last()
    before = log[log["date"] < start]
    carry = before["price"].iloc[-1] if len(before) else None

    rows, d = [], start
    while d <= end:
        candidates = [p for p in (carry, day_min.get(d)) if p is not None]
        rows.append({"date": d, "price": min(candidates) if candidates else None})
        if d in day_last.index:
            carry = day_last[d]
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def load_overrides():
    path = config.MANUAL / "price_overrides.csv"
    if not path.exists():
        return {}
    o = pd.read_csv(path)
    o = o[(o["status"] == "confirmed") & (o["field"] == "p0")]
    return dict(zip(o["steam_appid"].astype(int), o["corrected_value"].astype(float)))


def build_game(g, publisher, overrides, last_day):
    log = load_log(g["itad_id"])
    launch = pd.Timestamp(g["pc_launch_date"]).date()
    flags = []

    at_launch = log[log["date"] <= launch]
    if len(at_launch):
        p0_itad = at_launch["regular"].iloc[-1]
    else:
        p0_itad = log["regular"].iloc[0]
        flags.append("no_entry_before_launch")

    appid = int(g["steam_appid"])
    p0, p0_source = (overrides[appid], "override") if appid in overrides else (p0_itad, "itad")

    end = min(launch + timedelta(days=config.DAILY_SERIES_DAYS), last_day)
    daily = daily_lowest(log, launch, end)
    daily["day"] = range(len(daily))
    daily["depth"] = (1 - daily["price"] / p0).clip(lower=0)

    if (daily["price"] > p0 + 0.01).any():
        flags.append(f"price_above_p0_{int((daily['price'] > p0 + 0.01).sum())}d")
    if (daily["price"] <= 0).any():
        flags.append("zero_price_day")

    def depth_on(k):
        row = daily[daily["day"] == k]
        return row["depth"].iloc[0] if len(row) else None
    
    def max_depth_to(k):
        window = daily[(daily["day"] > config.LAUNCH_DISCOUNT_DAYS) & (daily["day"] <= k)]
        return window["depth"].max() if len(daily) > k else None

    cuts = daily[(daily["day"] > config.LAUNCH_DISCOUNT_DAYS) & (daily["depth"] >= config.FIRST_CUT_THRESHOLD)]
    first_cut = cuts.iloc[0] if len(cuts) else None

    summary = {
        "publisher": publisher,
        "game_title": g["game_title"],
        "steam_appid": appid,
        "pc_launch_date": launch,
        "holdout": launch >= config.HOLDOUT_START,
        "p0": p0,
        "p0_source": p0_source,
        "p0_itad": p0_itad,
        **{f"depth_{k}": depth_on(k) for k in config.DEPTH_DAYS},
        **{f"max_depth_{k}": max_depth_to(k) for k in config.DEPTH_DAYS},
        "first_cut_day": int(first_cut["day"]) if first_cut is not None else None,
        "first_cut_depth": first_cut["depth"] if first_cut is not None else None,
        "days_observed": len(daily),
        "flags": "; ".join(flags),
    }
    daily.insert(0, "steam_appid", appid)
    daily.insert(0, "publisher", publisher)
    return daily[["publisher", "steam_appid", "day", "date", "price", "depth"]], summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("publishers", nargs="*")
    args = parser.parse_args()

    if config.DATA_COLLECTION_DATE is None:
        raise SystemExit("Set DATA_COLLECTION_DATE in config.py first.")
    # last full day of data: the day before collection
    last_day = config.DATA_COLLECTION_DATE - timedelta(days=1)

    publishers = args.publishers or sorted(
        p.stem.replace("itad_summary_", "") for p in config.INTERIM.glob("itad_summary_*.csv"))
    overrides = load_overrides()

    all_daily, all_summary = [], []
    for pub in publishers:
        games = pd.read_csv(config.INTERIM / f"itad_summary_{pub}.csv").dropna(subset=["itad_id"])
        for _, g in games.iterrows():
            daily, summary = build_game(g, pub, overrides, last_day)
            all_daily.append(daily)
            all_summary.append(summary)

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    pd.concat(all_daily).to_csv(config.PROCESSED / "daily_prices.csv", index=False)
    result = pd.DataFrame(all_summary)
    result.to_csv(config.PROCESSED / "game_prices.csv", index=False)

    show = result.copy()
    for c in ["depth_45", "depth_90", "depth_180", "first_cut_depth"]:
        show[c] = show[c].map(lambda x: f"{x:.0%}" if pd.notna(x) else "-")
    print(show[["game_title", "p0", "p0_source", "depth_45", "depth_90", "depth_180",
                "first_cut_day", "first_cut_depth", "holdout", "flags"]].to_string(index=False))
    print(f"\nSaved {config.PROCESSED / 'daily_prices.csv'} and {config.PROCESSED / 'game_prices.csv'}")


if __name__ == "__main__":
    main()
