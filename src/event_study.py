"""
Phase 7: market-model event study.

Usage, from the repo root:
    python -m src.event_study                    # main sample only
    python -m src.event_study --include-holdout  # final, one-time holdout run (D13)

Inputs:  data/processed/events.csv, data/interim/returns.csv
Outputs: data/processed/event_returns.csv          one row per game: CARs, market model, controls
         data/processed/abnormal_returns_daily.csv one row per game, event and day in PLOT_WINDOW

Rules (docs/preregistration.md):
  D8   market model R_stock = a + b * R_index, estimated by OLS over trading days [-250, -30]
       before each event, local currency, local index. At least MIN_EST_DAYS valid days required.
  D7   CAR_E: sum of abnormal returns over [-1, +1] around the earnings day 0.
  Q2   CAR_D: sums over [0, +2] and [0, +10] around the first-cut day 0.
  D10  pre_return_60: compounded raw stock return over trading days [-61, -2] before the earnings
       day 0 (ends before the CAR_E window starts).
Holdout games are skipped unless --include-holdout is given.
"""

import argparse

import numpy as np
import pandas as pd

import config

MIN_EST_DAYS = 150
EVENTS = {"earnings": "day0_earnings", "discount": "day0_discount"}


def market_model(est):
    """OLS of stock return on index return. Returns alpha, beta, residual sd, n."""
    est = est.dropna(subset=["ret", "index_ret"])
    n = len(est)
    if n < MIN_EST_DAYS:
        return np.nan, np.nan, np.nan, n
    x, y = est["index_ret"].to_numpy(), est["ret"].to_numpy()
    beta, alpha = np.polyfit(x, y, 1)
    resid = y - (alpha + beta * x)
    return alpha, beta, resid.std(ddof=2), n


def event_window(r, day0):
    """Abnormal returns around one event, or None if day 0 is not in the data."""
    dates = r["date"].to_numpy()
    hits = np.where(dates == np.datetime64(day0))[0]
    if len(hits) == 0:
        return None
    i = hits[0]
    lo, hi = config.EST_WINDOW
    est = r.iloc[max(i + lo, 0): max(i + hi + 1, 0)]
    alpha, beta, sigma, n_est = market_model(est)

    p_lo, p_hi = config.PLOT_WINDOW
    win = r.iloc[max(i + p_lo, 0): i + p_hi + 1].copy()
    win["rel_day"] = np.arange(len(win)) - (i - max(i + p_lo, 0))
    win["ar"] = win["ret"] - (alpha + beta * win["index_ret"])
    return {"alpha": alpha, "beta": beta, "sigma": sigma, "n_est": n_est, "i": i, "window": win}


def car(win, lo, hi):
    """Sum of abnormal returns over [lo, hi]; NaN if any day is missing."""
    w = win[(win["rel_day"] >= lo) & (win["rel_day"] <= hi)]
    if len(w) < hi - lo + 1 or w["ar"].isna().any():
        return np.nan
    return w["ar"].sum()


def pre_return(r, i, lo=-61, hi=-2):
    w = r.iloc[max(i + lo, 0): i + hi + 1]["ret"].dropna()
    return np.prod(1 + w) - 1 if len(w) >= (hi - lo + 1) * 0.9 else np.nan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-holdout", action="store_true")
    args = parser.parse_args()

    events = pd.read_csv(config.PROCESSED / "events.csv")
    returns = pd.read_csv(config.INTERIM / "returns.csv", parse_dates=["date"])
    if not args.include_holdout:
        events = events[~events["holdout"].astype(bool)]
    by_ticker = {t: r.sort_values("date").reset_index(drop=True) for t, r in returns.groupby("ticker")}

    rows, daily = [], []
    for _, g in events.iterrows():
        r = by_ticker[g["ticker"]]
        row = {"publisher": g["publisher"], "game_title": g["game_title"], "steam_appid": g["steam_appid"],
               "holdout": g["holdout"]}
        flags = []
        for name, col in EVENTS.items():
            if pd.isna(g[col]):
                flags.append(f"no_{name}_event")
                continue
            ev = event_window(r, pd.Timestamp(g[col]))
            if ev is None:
                flags.append(f"{name}_day0_not_in_returns")
                continue
            if np.isnan(ev["beta"]):
                flags.append(f"{name}_estimation_window_short_{ev['n_est']}d")
            row.update({f"{name}_alpha": ev["alpha"], f"{name}_beta": ev["beta"],
                        f"{name}_sigma": ev["sigma"], f"{name}_n_est": ev["n_est"]})
            win = ev["window"]
            if name == "earnings":
                lo, hi = config.CAR_E_WINDOW
                row["CAR_E"] = car(win, lo, hi)
                row["SCAR_E"] = row["CAR_E"] / (ev["sigma"] * np.sqrt(hi - lo + 1))
                row["pre_return_60"] = pre_return(r, ev["i"])
            else:
                for lo, hi in config.CAR_D_WINDOWS:
                    row[f"CAR_D_{lo}_{hi}"] = car(win, lo, hi)
            daily.append(win.assign(event=name, steam_appid=g["steam_appid"], publisher=g["publisher"])
                         [["publisher", "steam_appid", "event", "rel_day", "date", "ret", "index_ret", "ar"]])
        row["flags"] = "; ".join(flags)
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(config.PROCESSED / "event_returns.csv", index=False)
    pd.concat(daily).to_csv(config.PROCESSED / "abnormal_returns_daily.csv", index=False)

    print(f"Saved event_returns.csv ({len(out)} games"
          f"{', holdout included' if args.include_holdout else ', holdout skipped'})\n")
    print("Market model check (estimation windows):")
    print(out.groupby("publisher").agg(
        games=("game_title", "size"),
        earnings_beta=("earnings_beta", "median"), discount_beta=("discount_beta", "median"),
        est_days_min=("earnings_n_est", "min"),
        CAR_E_available=("CAR_E", lambda s: s.notna().sum()),
        CAR_D_available=("CAR_D_0_2", lambda s: s.notna().sum())).round(2).to_string())
    flagged = out[out["flags"] != ""]
    if len(flagged):
        print("\nFlags:\n" + flagged[["game_title", "flags"]].to_string(index=False))


if __name__ == "__main__":
    main()
