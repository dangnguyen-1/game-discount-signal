"""
Q3: trading rule backtest with placebo tests.

Usage, from the repo root:
    python -m src.q3_trading_rule

Inputs:  data/processed/events.csv, data/processed/event_returns.csv, data/interim/returns.csv,
         data/manual/earnings_<publisher>.csv (main sample only)
Outputs: output/tables/q3_trades.csv, output/tables/q3_summary.csv, output/figures/q3_placebo.png,
         rows added to docs/trial_log.csv (D14)

Rule (D12): for each tentpole with early_cut_rt, short the stock against its local index from the close of
the discount day 0 to the close of the first trading day after the next scheduled earnings announcement
(announcements are after the close). Trade return = index return - stock return over the holding period,
minus COST_BPS on the stock leg at entry and at exit. Equal weight per trade. Borrow costs not modeled.

Placebos:
  random     (D12)  same publisher and holding length, entry on a random trading day at least
                    PLACEBO_MIN_GAP_DAYS calendar days from any real discount or earnings day 0 of that publisher.
  same_month (added after Q2, logged)  as above, but entry restricted to the same calendar month as the real entry.
  q2_month   (added after Q2, logged)  for every first discount (all groups), the market-model abnormal return over
                    days 0..+10 versus the same quantity on random same-month dates, using each event's alpha and beta.
"""

from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config


def load():
    ev = pd.read_csv(config.PROCESSED / "events.csv", parse_dates=["day0_discount", "day0_earnings"])
    rt = pd.read_csv(config.PROCESSED / "event_returns.csv")
    ev = ev.merge(rt[["steam_appid", "discount_alpha", "discount_beta", "CAR_D_0_10"]], on="steam_appid", how="left")
    ev = ev[~ev["holdout"].astype(bool)].copy()
    ev["early_cut_rt"] = ev["early_cut_rt"].astype(bool)
    ev["tentpole"] = ev["tentpole"].map({True: True, False: False, "True": True, "False": False})
    ev["tentpole_a"] = ev["tentpole_a"].map({True: True, False: False, "True": True, "False": False})
    ev["cut_vs_norm"] = ev["first_cut_depth"] - ev["norm_at_first_cut"]
    ret = pd.read_csv(config.INTERIM / "returns.csv", parse_dates=["date"])
    earn = pd.concat([pd.read_csv(p, parse_dates=["announcement_date"])
                      for p in sorted(config.MANUAL.glob("earnings_*.csv"))], ignore_index=True)
    if "event_type" in earn:
        earn = earn[earn["event_type"].fillna("scheduled") == "scheduled"]
    return ev, ret, earn


class Stock:
    """Cumulative log returns for fast holding-period returns."""

    def __init__(self, r):
        r = r.sort_values("date").reset_index(drop=True)
        self.dates = pd.DatetimeIndex(r["date"])
        self.ret = r["ret"].fillna(0).to_numpy()
        self.idx = r["index_ret"].fillna(0).to_numpy()
        self.cs = np.concatenate([[0], np.cumsum(np.log1p(self.ret))])
        self.ci = np.concatenate([[0], np.cumsum(np.log1p(self.idx))])

    def pos(self, d):
        i = self.dates.searchsorted(d)
        return i if i < len(self.dates) and self.dates[i] == d else None

    def hold(self, i_entry, i_exit):
        """Simple returns of stock and index from the close of i_entry to the close of i_exit."""
        rs = np.exp(self.cs[i_exit + 1] - self.cs[i_entry + 1]) - 1
        ri = np.exp(self.ci[i_exit + 1] - self.ci[i_entry + 1]) - 1
        return rs, ri


def build_trades(ev, stocks, earn, selector, cost_bps):
    rows = []
    for _, g in ev[selector(ev)].iterrows():
        s = stocks[g["ticker"]]
        if pd.isna(g["day0_discount"]):
            continue
        i0 = s.pos(g["day0_discount"])
        nxt = earn[(earn["publisher"] == g["publisher"]) &
                   (earn["announcement_date"] >= g["day0_discount"])].sort_values("announcement_date")
        if i0 is None or nxt.empty:
            continue
        i1 = s.dates.searchsorted(nxt.iloc[0]["announcement_date"], side="right")
        if i1 >= len(s.dates):
            continue
        rs, ri = s.hold(i0, i1)
        gross = ri - rs
        rows.append({"publisher": g["publisher"], "game_title": g["game_title"], "ticker": g["ticker"],
                     "entry": s.dates[i0].date(), "exit": s.dates[i1].date(), "holding_days": i1 - i0,
                     "stock_return": rs, "index_return": ri, "gross": gross,
                     "net": gross - 2 * cost_bps / 1e4})
    return pd.DataFrame(rows)


def summarize(t, label):
    n = len(t)
    if n == 0:
        return {"variant": label, "trades": 0}
    se = t["net"].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return {"variant": label, "trades": n, "mean_net": t["net"].mean(), "median_net": t["net"].median(),
            "t_stat": t["net"].mean() / se if se else np.nan, "hit_rate": (t["net"] > 0).mean(),
            "mean_holding_days": t["holding_days"].mean()}


def event_days(ev, stocks):
    """All real discount and earnings day-0 dates, per ticker."""
    out = {}
    for tk, g in ev.groupby("ticker"):
        out[tk] = pd.DatetimeIndex(pd.concat([g["day0_discount"], g["day0_earnings"]]).dropna().unique())
    return out


def candidate_positions(s, real_days, holding, month=None, start="2016-01-01"):
    gap = pd.Timedelta(days=config.PLACEBO_MIN_GAP_DAYS)
    ok = s.dates >= pd.Timestamp(start)
    if len(real_days):
        dist = np.min(np.abs(s.dates.values[:, None] - real_days.values[None, :]), axis=1)
        ok &= dist >= gap.to_timedelta64()
    if month is not None:
        ok &= s.dates.month == month
    pos = np.where(ok)[0]
    return pos[pos + holding < len(s.dates)]


def placebo(trades, stocks, real, rng, same_month):
    """Mean net return across the trade set, recomputed on random entry dates, PLACEBO_RUNS times."""
    pools = []
    for _, t in trades.iterrows():
        s = stocks[t["ticker"]]
        month = pd.Timestamp(t["entry"]).month if same_month else None
        pools.append((s, candidate_positions(s, real[t["ticker"]], t["holding_days"], month), t["holding_days"]))
    means = np.empty(config.PLACEBO_RUNS)
    cost = 2 * config.COST_BPS / 1e4
    for k in range(config.PLACEBO_RUNS):
        vals = []
        for s, pos, h in pools:
            if len(pos) == 0:
                continue
            i0 = rng.choice(pos)
            rs, ri = s.hold(i0, i0 + h)
            vals.append(ri - rs - cost)
        means[k] = np.mean(vals)
    return means


def q2_month_placebo(ev, stocks, real, rng):
    """Mean abnormal return over days 0..+10 after first discounts vs random same-month dates."""
    e = ev.dropna(subset=["day0_discount", "discount_alpha", "discount_beta", "CAR_D_0_10"])
    pools = []
    for _, g in e.iterrows():
        s = stocks[g["ticker"]]
        pos = candidate_positions(s, real[g["ticker"]], 10, g["day0_discount"].month)
        pools.append((s, pos, g["discount_alpha"], g["discount_beta"]))
    means = np.empty(config.PLACEBO_RUNS)
    for k in range(config.PLACEBO_RUNS):
        vals = []
        for s, pos, a, b in pools:
            if len(pos) == 0:
                continue
            i0 = rng.choice(pos)
            w = slice(i0, i0 + 11)
            vals.append(np.sum(s.ret[w] - (a + b * s.idx[w])))
        means[k] = np.mean(vals)
    return e["CAR_D_0_10"].mean(), means, len(e)


def log_trials(rows):
    path = config.DOCS / "trial_log.csv"
    log = pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame(
        columns=["date", "phase", "variant", "description", "result"])
    new = pd.DataFrame([{"date": date.today().isoformat(), "phase": "Q3", "variant": r["variant"],
                         "description": r["description"], "result": r["result"]} for r in rows])
    log = log[~((log["phase"] == "Q3") & (log["variant"].isin(new["variant"])))]
    pd.concat([log, new], ignore_index=True).to_csv(path, index=False)


def main():
    ev, ret, earn = load()
    stocks = {tk: Stock(r) for tk, r in ret.groupby("ticker")}
    rng = np.random.default_rng(config.RANDOM_SEED)
    primary = lambda e: e["early_cut_rt"] & (e["tentpole"] == True)

    trades = build_trades(ev, stocks, earn, primary, config.COST_BPS)
    summary = [summarize(trades, f"primary_cost_{config.COST_BPS}bps")]
    for c in config.COST_BPS_ROBUSTNESS:
        summary.append(summarize(build_trades(ev, stocks, earn, primary, c), f"primary_cost_{c}bps"))
    summary.append(summarize(build_trades(
        ev, stocks, earn, lambda e: e["early_cut_rt"] & (e["cut_vs_norm"] >= 0.10) & (e["tentpole"] == True),
        config.COST_BPS), "strict_flag"))
    summary.append(summarize(build_trades(
        ev, stocks, earn, lambda e: e["early_cut_rt"] & (e["tentpole_a"] == True), config.COST_BPS),
        "tentpole_a_only"))

    real = event_days(ev, stocks)
    p_random = placebo(trades, stocks, real, rng, same_month=False)
    p_month = placebo(trades, stocks, real, rng, same_month=True)
    real_mean = trades["net"].mean()
    q2_real, q2_plac, q2_n = q2_month_placebo(ev, stocks, real, rng)

    tests = [("placebo_random", p_random, real_mean, "Share of placebo runs with mean net >= real (one-sided)"),
             ("placebo_same_month", p_month, real_mean, "Same, entries restricted to the real entry's month")]
    for name, dist, obs, desc in tests:
        summary.append({"variant": name, "trades": len(trades), "mean_net": obs,
                        "placebo_mean": dist.mean(), "placebo_p": (dist >= obs).mean()})

    config.TABLES.mkdir(parents=True, exist_ok=True)
    trades.to_csv(config.TABLES / "q3_trades.csv", index=False)
    summ = pd.DataFrame(summary)
    summ.to_csv(config.TABLES / "q3_summary.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (title, dist, obs) in zip(axes, [("Trade rule vs random dates", p_random, real_mean),
                                             ("Trade rule vs same-month dates", p_month, real_mean),
                                             ("Q2: 10-day AR after first discounts\nvs same-month dates",
                                              q2_plac, q2_real)]):
        ax.hist(dist * 100, bins=40, color="#9bb7d4")
        ax.axvline(obs * 100, color="#c0392b", lw=2, label="actual")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Mean return (%)")
        ax.legend(fontsize=8)
    fig.tight_layout()
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(config.FIGURES / "q3_placebo.png", dpi=150)

    q2_p_low = (q2_plac <= q2_real).mean()
    log_trials([{"variant": r["variant"], "description": "Q3 summary row",
                 "result": "; ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                                     for k, v in r.items() if k != "variant")} for r in summary]
               + [{"variant": "q2_month_placebo", "description": "Q2 10-day AR vs same-month random dates",
                   "result": f"actual={q2_real:.4f}; placebo_mean={q2_plac.mean():.4f}; p_low={q2_p_low:.3f}; n={q2_n}"}])

    print(f"Q3 primary rule: {len(trades)} trades, short early-cut tentpoles from discount to the day after earnings\n")
    cols = ["variant", "trades", "mean_net", "median_net", "t_stat", "hit_rate", "mean_holding_days",
            "placebo_mean", "placebo_p"]
    print(summ[[c for c in cols if c in summ]].round(4).to_string(index=False))
    print(f"\nPlacebo p = share of {config.PLACEBO_RUNS} random runs whose mean net return is at least the actual one.")
    print(f"\nQ2 seasonal check: mean 10-day abnormal return after first discounts = {q2_real:.2%} (n={q2_n}); "
          f"same-month random dates average {q2_plac.mean():.2%}; "
          f"share of placebo runs at or below the actual = {q2_p_low:.0%}")
    print(f"\nSaved {config.TABLES}/q3_trades.csv, q3_summary.csv and {config.FIGURES}/q3_placebo.png")


if __name__ == "__main__":
    main()
