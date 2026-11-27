"""
Steam review counts in fixed windows after launch (D4 size, D10 reviews_pos).

Usage, from the repo root:
    python -m src.fetch_reviews

For each game in data/processed/game_prices.csv:
  launch_30   reviews dated within 30 days of PC launch          -> size (D4)
  launch_90   reviews dated within 90 days of PC launch          -> reviews_pos (D10)
  lifetime    all reviews, no date filter                        -> check that the date filter worked
For games that came to Steam more than 7 days after their PC launch (Epic / Ubisoft Store launches),
the same 30- and 90-day windows are also counted from the Steam release date (steam_30, steam_90).

Counts come from the query summary of Steam's IUserReviewsService/GetAppReviews (date_range_start/end),
so each window is one request. Counts reflect reviews as they exist today (deleted reviews and accounts are gone).
Raw responses are cached in data/raw/steam_reviews/.
"""

import json
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

import config

URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
HEADERS = {"User-Agent": "game-discount-signal (personal research project)"}
DELAY_SECONDS = 1.6          # Steam store endpoints allow about 200 requests per 5 minutes
LATE_STEAM_DAYS = 7


def window_bounds(start_date, days):
    """Unix timestamps from 00:00 US Pacific (08:00 UTC) on start_date to the same time `days` later."""
    start = datetime(start_date.year, start_date.month, start_date.day, 8, tzinfo=timezone.utc)
    return int(start.timestamp()), int((start + timedelta(days=days)).timestamp())


def review_summary(appid, start=None, end=None):
    """Review totals for one app from IUserReviewsService/GetAppReviews, optionally within a date window.

    Steam retired store.steampowered.com/appreviews on 2026-10-22; this is its documented replacement.
    Filters are enums: filter 1 = Recent, review_type 0 = All, purchase_type 1 = All purchases.
    Off-topic ("review bomb") reviews stay excluded, Steam's default.
    """
    tag = f"{start}_{end}" if start else "lifetime"
    cache = config.RAW_STEAM_REVIEWS / f"{appid}_{tag}_v2.json"
    if cache.exists():
        data = json.loads(cache.read_text())
    else:
        query = {"appid": int(appid), "filter": 1, "languages": ["all"], "review_type": 0,
                 "purchase_type": 1, "num_per_page": 1, "cursor": "*"}
        if start:
            query.update({"date_range_start": int(start), "date_range_end": int(end)})
        for _ in range(3):
            resp = requests.get(URL, params={"input_json": json.dumps(query)}, headers=HEADERS,
                                timeout=30, allow_redirects=False)
            if resp.status_code == 429:
                print("  rate limited, waiting 60 seconds")
                time.sleep(60)
                continue
            if resp.status_code != 200 or "json" not in resp.headers.get("content-type", ""):
                raise RuntimeError(f"Unexpected response for {appid}: HTTP {resp.status_code}, "
                                   f"{resp.headers.get('content-type')}")
            data = resp.json()
            break
        else:
            raise RuntimeError(f"Request kept failing for {appid}")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data))
        time.sleep(DELAY_SECONDS)

    body = (data or {}).get("response", {})
    s = body.get("query_summary", {})
    if "total_reviews" not in s:
        return None
    return {"total": s.get("total_reviews"), "positive": s.get("total_positive")}


def steam_release_dates():
    rows = []
    for path in config.INTERIM.glob("steam_details_*.csv"):
        d = pd.read_csv(path)
        rows.append(pd.DataFrame({"steam_appid": d["steam_appid"],
                                  "steam_release_date": pd.to_datetime(d["release_date"], format="mixed")}))
    return pd.concat(rows).drop_duplicates("steam_appid")


def main():
    games = pd.read_csv(config.PROCESSED / "game_prices.csv", parse_dates=["pc_launch_date"])
    games = games.merge(steam_release_dates(), on="steam_appid", how="left")

    rows = []
    for _, g in games.iterrows():
        appid = int(g["steam_appid"])
        print(f"{g['game_title']} ({appid})")
        windows = {"launch_30": (g["pc_launch_date"], 30), "launch_90": (g["pc_launch_date"], 90)}
        late = pd.notna(g["steam_release_date"]) and \
            (g["steam_release_date"] - g["pc_launch_date"]).days > LATE_STEAM_DAYS
        if late:
            windows.update({"steam_30": (g["steam_release_date"], 30), "steam_90": (g["steam_release_date"], 90)})

        row = {"publisher": g["publisher"], "game_title": g["game_title"], "steam_appid": appid,
               "pc_launch_date": g["pc_launch_date"].date(), "steam_release_date": g["steam_release_date"].date()
               if pd.notna(g["steam_release_date"]) else None, "late_to_steam": late}
        life = review_summary(appid)
        row["lifetime_total"] = life["total"] if life else None
        for name, (start_date, days) in windows.items():
            s = review_summary(appid, *window_bounds(start_date, days))
            row[f"{name}_total"] = s["total"] if s else None
            row[f"{name}_positive"] = s["positive"] if s else None

        flags = []
        lt, t30, t90 = row["lifetime_total"], row.get("launch_30_total"), row.get("launch_90_total")
        if lt is None or t30 is None:
            flags.append("request_failed")
        elif t30 == lt and lt > 0 and not late:
            flags.append("date_filter_ignored?")
        elif t90 is not None and t90 < t30:
            flags.append("90d_below_30d")
        row["flags"] = "; ".join(flags)
        rows.append(row)

    out = pd.DataFrame(rows)
    out["size"] = out["launch_30_total"]
    out["reviews_pos"] = out["launch_90_positive"] / out["launch_90_total"]
    if "steam_30_total" in out:
        out["size_steam"] = out["steam_30_total"]
        out["reviews_pos_steam"] = out["steam_90_positive"] / out["steam_90_total"]

    path = config.PROCESSED / "reviews.csv"
    out.to_csv(path, index=False)
    print(f"\nSaved {path}")
    cols = ["publisher", "game_title", "lifetime_total", "size", "reviews_pos", "late_to_steam",
            "size_steam", "reviews_pos_steam", "flags"]
    print(out[[c for c in cols if c in out]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()