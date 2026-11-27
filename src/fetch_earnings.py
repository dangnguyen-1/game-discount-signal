"""
Phase 5: earnings announcement dates.

Usage, from the repo root:
    python -m src.fetch_earnings capcom

Capcom keeps one IR calendar page per fiscal year (calendar16.html = FY2016, which runs
April 2016 to March 2017 and also lists the FY2015 full-year results announced in May 2016).
This reads those pages, keeps every "Announcement ... Financial Results" entry, and writes
data/manual/earnings_capcom.csv for checking by hand.

The output goes in data/manual/ because it is a hand-verified file: once checked, fill in
guidance_change (D11) from each press release, and correct anything the scraper got wrong.
Running the script again will not overwrite a file that already exists.
"""

import argparse
import re
import time
from datetime import datetime

import pandas as pd
import requests

import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
SAVED_PAGES = config.RAW / "earnings"   # pages saved from a browser, used when a site blocks scripts
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
ENTRY = re.compile(rf"((?:{MONTHS}) \d{{1,2}}, \d{{4}})\s*-?\s*([^\n]*?(?i:announcement)[^\n]*?)(?=\s*(?:{MONTHS}) \d{{1,2}}, \d{{4}}|\n|$)")
PERIOD = [(r"1st Quarter|1Q|Q1", "Q1"), (r"2nd Quarter|2Q|Q2", "Q2"), (r"3rd Quarter|3Q|Q3", "Q3")]


def page_text(url, saved_path=None):
    """Page text from a saved copy if one exists, otherwise downloaded."""
    if saved_path is not None and saved_path.exists():
        html = saved_path.read_text(errors="ignore")
    else:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        html = resp.text
    text = re.sub(r"<[^>]+>", "\n", html)
    return re.sub(r"[ \t\xa0]+", " ", text)


def parse_entries(text):
    """(date, description) for every results announcement on one calendar page."""
    rows = []
    for date_str, desc in ENTRY.findall(text):
        desc = desc.strip(" -")
        if "results" not in desc.lower():
            continue
        period = next((p for pat, p in PERIOD if re.search(pat, desc)), "FY")
        fy = re.search(r"FY\s?(\d{4})", desc)
        rows.append({
            "announcement_date": datetime.strptime(date_str, "%B %d, %Y").date(),
            "period": period,
            "fiscal_year": int(fy.group(1)) if fy else None,
            "description": desc,
        })
    return rows


def capcom():
    """Capcom IR calendar archive. The site serves scripts an empty page, so save each page
    from a browser as data/raw/earnings/capcom/calendar16.html ... calendar26.html.

    Timing: releases came after the Tokyo close (15:00) through Oct 2024. The close moved to
    15:30 on 2024-11-05, so check the release time of every announcement from then on.
    """
    base = "https://www.capcom.co.jp/ir/english/calendar/"
    folder = SAVED_PAGES / "capcom"
    rows = []
    for yy in range(16, 27):
        url = f"{base}calendar{yy}.html"
        saved = folder / f"calendar{yy}.html"
        print(f"Reading {saved if saved.exists() else url}")
        text = page_text(url, saved)
        if not text or not text.strip():
            print("  empty or not found, skipped")
            continue
        for r in parse_entries(text):
            rows.append({**r, "source_url": url})
        time.sleep(config.REQUEST_DELAY_SECONDS)
    return rows, "9697.T", "after_close"


SCRAPERS = {"capcom": capcom}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("publisher", choices=list(SCRAPERS))
    publisher = parser.parse_args().publisher

    out = config.MANUAL / f"earnings_{publisher}.csv"
    if out.exists():
        raise SystemExit(f"{out} already exists; it may contain hand edits. Delete it first to re-scrape.")

    rows, ticker, timing = SCRAPERS[publisher]()
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No announcements found; the page layout may have changed.")

    df = (df[(df["announcement_date"] >= pd.Timestamp("2016-01-01").date()) &
             (df["announcement_date"] < config.DATA_COLLECTION_DATE)]
          .sort_values("announcement_date")
          .drop_duplicates(subset="announcement_date", keep="first"))
    df.insert(0, "publisher", publisher)
    df.insert(1, "ticker", ticker)
    df["timing"] = timing
    df["guidance_change"] = ""
    df["notes"] = ""
    df = df[["publisher", "ticker", "fiscal_year", "period", "announcement_date", "timing",
             "guidance_change", "description", "source_url", "notes"]]
    df.to_csv(out, index=False)

    print(f"\nSaved {out}: {len(df)} announcements")
    print(df[["fiscal_year", "period", "announcement_date", "description"]].to_string(index=False))
    gaps = pd.to_datetime(df["announcement_date"]).diff().dt.days
    if (gaps > 120).any():
        print("\nGaps over 120 days between announcements (a quarter may be missing):")
        print(df.loc[gaps > 120, ["announcement_date"]].to_string())


if __name__ == "__main__":
    main()
