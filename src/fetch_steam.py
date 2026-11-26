"""
Phase 2: Steam store data for the game list.

Usage, from the repo root:
    python -m src.fetch_steam search capcom    # suggest app IDs for each candidate title
    python -m src.fetch_steam details capcom   # pull app details for the app IDs you verified

Every raw response is cached in data/raw/ and never downloaded twice.
"""

import argparse
import json
import re
import time

import pandas as pd
import requests

import config

SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
DETAILS_URL = "https://store.steampowered.com/api/appdetails"
RAW_STEAM_SEARCH = config.RAW / "steam_search"
HEADERS = {"User-Agent": "game-discount-signal (personal research project)"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def normalize(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def get_json(url, params, cache_path):
    """Return the cached response if it exists; otherwise request it, cache it, and wait."""
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    for _ in range(3):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 429:
            print("  rate limited, waiting 60 seconds")
            time.sleep(60)
            continue
        resp.raise_for_status()
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
        time.sleep(config.REQUEST_DELAY_SECONDS)
        return data

    raise RuntimeError(f"Request kept failing: {url} {params}")


def load_candidates(publisher):
    path = config.MANUAL / f"candidates_{publisher}.csv"
    if not path.exists():
        raise SystemExit(f"Not found: {path}")
    return path, pd.read_csv(path)


def search(publisher):
    """Write the top 5 Steam search results for every candidate title."""
    _, cands = load_candidates(publisher)
    rows = []

    for title in cands["game_title"]:
        print(f"Searching: {title}")
        data = get_json(SEARCH_URL, {"term": title, "l": "english", "cc": "US"},
                        RAW_STEAM_SEARCH / f"{slug(title)}.json")
        items = (data or {}).get("items", [])[:5]

        if not items:
            rows.append({"game_title": title, "rank": None, "steam_appid": None,
                         "steam_name": "NO RESULTS", "current_price_usd": None})
        for rank, item in enumerate(items, start=1):
            price = item.get("price") or {}
            initial = price.get("initial")
            rows.append({"game_title": title, "rank": rank,
                         "steam_appid": item.get("id"), "steam_name": item.get("name"),
                         "current_price_usd": initial / 100 if initial is not None else None})

    out = config.MANUAL / f"appid_suggestions_{publisher}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSaved {out}")
    print("Next: add a steam_appid column to the candidates file and fill in the verified base-game ID for each title.")


def expected_publisher_names(publisher):
    pubs = pd.read_csv(config.MANUAL / "publishers.csv")
    match = pubs[pubs["parent_company"].str.lower().str.replace(" ", "") == publisher.replace("_", "")]
    names = ";".join(match["steam_publisher_names"].dropna()).split(";")
    return [normalize(n) for n in names if n.strip()]


def details(publisher):
    """Pull Steam app details for every candidate with a verified steam_appid."""
    path, cands = load_candidates(publisher)
    if "steam_appid" not in cands.columns:
        raise SystemExit(f"Add a steam_appid column to {path} first.")

    cands["steam_appid"] = pd.to_numeric(cands["steam_appid"], errors="coerce").astype("Int64")
    expected = expected_publisher_names(publisher)
    rows = []

    for _, row in cands.dropna(subset=["steam_appid"]).iterrows():
        appid = int(row["steam_appid"])
        print(f"Fetching details: {row['game_title']} ({appid})")
        data = get_json(DETAILS_URL, {"appids": appid, "cc": "us", "l": "english"},
                        config.RAW_STEAM_APPDETAILS / f"{appid}.json")
        entry = (data or {}).get(str(appid), {})

        if not entry.get("success"):
            rows.append({"game_title": row["game_title"], "steam_appid": appid, "fetch_ok": False})
            continue

        d = entry["data"]
        publishers = d.get("publishers", [])
        rows.append({
            "game_title": row["game_title"],
            "steam_appid": appid,
            "steam_name": d.get("name"),
            "type": d.get("type"),
            "publishers": "; ".join(publishers),
            "developers": "; ".join(d.get("developers", [])),
            "release_date": d.get("release_date", {}).get("date"),
            "coming_soon": d.get("release_date", {}).get("coming_soon"),
            "is_free": d.get("is_free"),
            "publisher_matches": any(e in normalize(p) for p in publishers for e in expected),
            "fetch_ok": True,
        })

    result = pd.DataFrame(rows)
    out = config.INTERIM / f"steam_details_{publisher}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)

    print(f"\nSaved {out}")
    ok = result[result["fetch_ok"]] if "fetch_ok" in result else result
    flags = ok[(ok["type"] != "game") | (~ok["publisher_matches"].astype(bool)) | (ok["is_free"] == True)]
    failed = result[~result["fetch_ok"]]
    print(f"{len(ok)} fetched, {len(failed)} failed, {len(flags)} to check (not type 'game', free, or publisher mismatch)")
    if len(flags):
        print(flags[["game_title", "steam_appid", "type", "publishers", "is_free"]].to_string(index=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["search", "details"])
    parser.add_argument("publisher", help="e.g. capcom, ubisoft, square_enix")
    args = parser.parse_args()
    {"search": search, "details": details}[args.command](args.publisher.lower())


if __name__ == "__main__":
    main()
