"""
Phase 3: IsThereAnyDeal (ITAD) price histories.

Usage, from the repo root:
    python -m src.fetch_itad capcom

For every eligible candidate (has a steam_appid and is not in exclusions.csv):
  1. look up its ITAD game ID from the Steam app ID
  2. download its full US price history from its reference store (D3)
  3. summarize coverage, so gaps show up before any measures are built

Optional columns in data/manual/candidates_<publisher>.csv:
  reference_shop            steam (default), epic, or ubisoft_store
  pc_launch_date_override   real PC launch date (YYYY-MM-DD) when it differs from Steam's date

Raw responses are cached in data/raw/itad/ and never downloaded twice.
ITAD terms: do not alter or redistribute the raw data; publish derived measures only.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

import config

BASE_URL = "https://api.isthereanydeal.com"
SHOP_IDS = {"steam": 61, "epic": 16, "ubisoft_store": 62}   # from /service/shops/v1, 2026-11-27
HISTORY_SINCE = "2010-01-01T00:00:00Z"
LATE_START_DAYS = 7

load_dotenv(config.ROOT / ".env")
API_KEY = os.getenv("ITAD_API_KEY")


def history_path(itad_id, shop="steam"):
    """Cache path for one game's history at one store (Steam keeps the original file name)."""
    name = f"{itad_id}.json" if shop == "steam" else f"{itad_id}_{shop}.json"
    return config.RAW_ITAD / name


def get_json(path, params, cache_path):
    """Return the cached response if present; otherwise request, cache, and wait."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    if not API_KEY:
        raise SystemExit("ITAD_API_KEY not found in .env")

    headers = {"ITAD-API-Key": API_KEY}
    for _ in range(3):
        resp = requests.get(BASE_URL + path, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 60))
            print(f"  rate limited, waiting {wait} seconds")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
        time.sleep(config.REQUEST_DELAY_SECONDS)
        return data

    raise RuntimeError(f"Request kept failing: {path} {params}")


def eligible_games(publisher):
    cands = pd.read_csv(config.MANUAL / f"candidates_{publisher}.csv")
    details = pd.read_csv(config.INTERIM / f"steam_details_{publisher}.csv")
    excl_path = config.MANUAL / "exclusions.csv"
    excluded = set(pd.read_csv(excl_path)["steam_appid"].dropna().astype(int)) if excl_path.exists() else set()

    for col in ["reference_shop", "pc_launch_date_override"]:
        if col not in cands.columns:
            cands[col] = None

    cands = cands.dropna(subset=["steam_appid"])
    cands["steam_appid"] = cands["steam_appid"].astype(int)
    cands = cands[~cands["steam_appid"].isin(excluded)]

    merged = cands.merge(details[["steam_appid", "release_date"]], on="steam_appid", how="left")
    steam_date = pd.to_datetime(merged["release_date"], format="mixed")
    override = pd.to_datetime(merged["pc_launch_date_override"], errors="coerce")
    merged["pc_launch_date"] = override.fillna(steam_date).dt.date
    merged["steam_release_date"] = steam_date.dt.date
    merged["reference_shop"] = merged["reference_shop"].fillna("steam")

    unknown = set(merged["reference_shop"]) - set(SHOP_IDS)
    if unknown:
        raise SystemExit(f"Unknown reference_shop value(s): {unknown}. Use one of {list(SHOP_IDS)}.")
    return merged[["game_title", "steam_appid", "pc_launch_date", "steam_release_date", "reference_shop"]]


def lookup(appid):
    data = get_json("/games/lookup/v1", {"appid": appid},
                    config.RAW_ITAD / f"lookup_{appid}.json")
    if data and data.get("found"):
        return data["game"]["id"], data["game"].get("title")
    return None, None


def history(itad_id, shop):
    return get_json("/games/history/v2",
                    {"id": itad_id, "country": config.REFERENCE_REGION,
                     "shops": SHOP_IDS[shop], "since": HISTORY_SINCE},
                    history_path(itad_id, shop)) or []


def summarize(entries, launch_date):
    """Coverage summary for one game's history log."""
    if not entries:
        return {"n_changes": 0, "flag": "no_history"}

    log = pd.DataFrame({
        "ts": [pd.Timestamp(e["timestamp"]).tz_convert("UTC") for e in entries],
        "price": [e["deal"]["price"]["amount"] for e in entries],
        "regular": [e["deal"]["regular"]["amount"] for e in entries],
        "currency": [e["deal"]["price"]["currency"] for e in entries],
    }).sort_values("ts")

    first_day = log["ts"].iloc[0].date()
    launch_cutoff = pd.Timestamp(launch_date, tz="UTC") + pd.Timedelta(days=1)
    at_launch = log[(log["ts"] < launch_cutoff) & (log["regular"] > 0)]
    regular_at_launch = at_launch.iloc[-1]["regular"] if len(at_launch) else log.iloc[0]["regular"]
    days_late = (first_day - launch_date).days

    flags = []
    if days_late > LATE_START_DAYS:
        flags.append(f"starts_{days_late}d_after_launch")
    if regular_at_launch < config.MIN_LAUNCH_PRICE_USD:
        flags.append("below_min_launch_price")
    if set(log["currency"]) != {"USD"}:
        flags.append("non_usd")

    return {
        "n_changes": len(log),
        "first_change": first_day,
        "last_change": log["ts"].iloc[-1].date(),
        "days_first_change_after_launch": days_late,
        "regular_at_launch_usd": regular_at_launch,
        "lowest_price_usd": log["price"].min(),
        "flag": "; ".join(flags),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("publisher")
    publisher = parser.parse_args().publisher.lower()

    rows = []
    for _, g in eligible_games(publisher).iterrows():
        print(f"{g['game_title']} ({g['steam_appid']}, {g['reference_shop']})")
        itad_id, itad_title = lookup(g["steam_appid"])
        if not itad_id:
            rows.append({**g, "itad_id": None, "flag": "lookup_failed"})
            continue
        rows.append({**g, "itad_id": itad_id, "itad_title": itad_title,
                     **summarize(history(itad_id, g["reference_shop"]), g["pc_launch_date"])})

    result = pd.DataFrame(rows)
    out = config.INTERIM / f"itad_summary_{publisher}.csv"
    result.to_csv(out, index=False)

    print(f"\nSaved {out}")
    cols = ["game_title", "reference_shop", "pc_launch_date", "first_change", "n_changes",
            "regular_at_launch_usd", "flag"]
    print(result[[c for c in cols if c in result.columns]].to_string(index=False))
    print(f"\nDownloaded {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
          "Log the download date in docs/data_log.md.")


if __name__ == "__main__":
    main()
