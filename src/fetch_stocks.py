"""
Phase 4: daily stock and benchmark index prices.

Usage, from the repo root:
    python -m src.fetch_stocks

Reads tickers and benchmark indices from data/manual/publishers.csv, downloads daily
adjusted closes from Yahoo Finance (cached in data/raw/stocks/), and writes
data/interim/returns.csv: one row per stock per trading day, with the stock's simple
return and its benchmark's return on the same day (D8: local currency, local index).

Then prints data-quality checks and each stock's largest daily moves, which should be
matched against known news before the returns are used.
"""

from datetime import date

import pandas as pd
import yfinance as yf

import config

RAW_STOCKS = config.RAW / "stocks"
STOCK_START = date(2015, 1, 1)     # leaves room for the [-250, -30] estimation window before 2016 events
EXTREME_MOVE = 0.15                # daily moves this large get listed for a manual check


def download(symbol):
    """Adjusted daily closes for one symbol, cached after the first download."""
    cache = RAW_STOCKS / f"{symbol.replace('^', 'IDX_')}.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"])

    hist = yf.Ticker(symbol).history(start=STOCK_START.isoformat(),
                                     end=config.DATA_COLLECTION_DATE.isoformat(),
                                     auto_adjust=True)
    if hist.empty:
        raise SystemExit(f"No data returned for {symbol}")

    df = pd.DataFrame({
        "date": hist.index.tz_localize(None).normalize(),
        "close": hist["Close"].values,
        "volume": hist["Volume"].values,
    })
    RAW_STOCKS.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    return df


def build_returns(stock, index, ticker, index_symbol):
    """Stock and index returns over the same intervals: the stock's actual trading days.

    Zero-volume rows are dropped first: Yahoo pads exchange holidays and trading
    suspensions with a repeated price at zero volume, which would show as fake 0% returns.
    A return across a closure or suspension is recorded on the day trading resumes.
    """
    s = stock[stock["volume"] > 0].sort_values("date").copy()
    s = s.merge(index[["date", "close"]].rename(columns={"close": "index_close"}), on="date", how="left")
    s["ret"] = s["close"].pct_change(fill_method=None)
    s["index_ret"] = s["index_close"].pct_change(fill_method=None)
    s.insert(1, "ticker", ticker)
    s.insert(2, "index", index_symbol)
    return s[["date", "ticker", "index", "close", "volume", "ret", "index_close", "index_ret"]]


def quality(r):
    """One row of data-quality checks for one stock."""
    gaps = r["date"].diff().dt.days
    return {
        "ticker": r["ticker"].iloc[0],
        "index": r["index"].iloc[0],
        "first_day": r["date"].min().date(),
        "last_day": r["date"].max().date(),
        "trading_days": len(r),
        "missing_index_days": int(r["index_ret"].isna().sum() - 1),
        "zero_volume_days": int((r["volume"] == 0).sum()),
        "longest_gap_days": int(gaps.max()),
        "moves_over_15pct": int((r["ret"].abs() > EXTREME_MOVE).sum()),
    }


def main():
    if config.DATA_COLLECTION_DATE is None:
        raise SystemExit("Set DATA_COLLECTION_DATE in config.py first.")

    pubs = pd.read_csv(config.MANUAL / "publishers.csv")
    pairs = pubs[["ticker", "benchmark_index"]].drop_duplicates()

    frames = []
    for _, p in pairs.iterrows():
        print(f"Downloading {p['ticker']} and {p['benchmark_index']}")
        frames.append(build_returns(download(p["ticker"]), download(p["benchmark_index"]),
                                    p["ticker"], p["benchmark_index"]))

    returns = pd.concat(frames, ignore_index=True)
    out = config.INTERIM / "returns.csv"
    returns.to_csv(out, index=False)
    print(f"\nSaved {out}\n")

    print(pd.DataFrame([quality(r) for _, r in returns.groupby("ticker")]).to_string(index=False))

    print("\nLargest daily moves (check each against news before using the returns):")
    for ticker, r in returns.groupby("ticker"):
        top = r.loc[r["ret"].abs().sort_values(ascending=False).index[:5], ["date", "ret", "index_ret"]]
        top["date"] = top["date"].dt.date
        print(f"\n{ticker}\n" + top.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
