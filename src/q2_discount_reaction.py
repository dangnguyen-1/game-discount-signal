"""
Q2: does the stock react when a game is first discounted, and is the reaction at the discount or at earnings?

Usage, from the repo root:
    python -m src.q2_discount_reaction

Inputs:  data/processed/events.csv, data/processed/event_returns.csv,
         data/processed/abnormal_returns_daily.csv (main sample only)
Outputs: output/tables/q2_groups.csv, output/tables/q2_regression.csv,
         output/figures/q2_car_paths.png, rows added to docs/trial_log.csv (D14)

Groups (D15, D4):  A = early_cut_rt and tentpole   B = early_cut_rt, not tentpole   C = not early_cut_rt
Underreaction (H2): little reaction at the discount (CAR_D near 0) but a negative reaction at earnings (CAR_E < 0)
for group A. The alternative, that the market reacts at once, predicts CAR_D < 0 and CAR_E near 0.
Tests are cross-sectional t-tests across games; with 3 publishers they are descriptive.
"""

from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import config

CARS = ["CAR_D_0_2", "CAR_D_0_10", "CAR_E"]


def load():
    ev = pd.read_csv(config.PROCESSED / "events.csv")
    rt = pd.read_csv(config.PROCESSED / "event_returns.csv")
    d = ev.merge(rt[["steam_appid"] + CARS], on="steam_appid", how="inner")
    d = d[~d["holdout"].astype(bool)].copy()
    d["early_cut_rt"] = d["early_cut_rt"].astype(bool)
    d["tentpole"] = d["tentpole"].map({True: True, False: False, "True": True, "False": False})
    d["cut_vs_norm"] = d["first_cut_depth"] - d["norm_at_first_cut"]
    d["early_cut_strict"] = d["early_cut_rt"] & (d["cut_vs_norm"] >= 0.10)
    d["near_earnings"] = d["flags"].fillna("").str.contains("discount_within_10_tdays_of_earnings")
    return d


def assign_group(d, flag):
    g = np.where(~d[flag], "C: no early cut",
                 np.where(d["tentpole"] == True, "A: early-cut tentpole",
                          np.where(d["tentpole"] == False, "B: early cut, not tentpole", "unknown")))
    return pd.Series(g, index=d.index)


def t_stat(x):
    x = x.dropna()
    if len(x) < 2:
        return np.nan, np.nan
    se = x.std(ddof=1) / np.sqrt(len(x))
    t = x.mean() / se
    from math import erf, sqrt
    return t, 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))


def group_table(d, flag, label):
    d = d.assign(group=assign_group(d, flag))
    rows = []
    for grp, g in d.groupby("group"):
        if grp == "unknown":
            continue
        row = {"variant": label, "group": grp, "n": int(g["CAR_D_0_10"].notna().sum())}
        for c in CARS:
            t, p = t_stat(g[c])
            row.update({f"mean_{c}": g[c].mean(), f"t_{c}": t, f"p_{c}": p})
        row["share_CAR_D_0_10_negative"] = (g["CAR_D_0_10"] < 0).mean()
        rows.append(row)
    return rows


def cut_regression(d):
    e = d[d["early_cut_rt"]].dropna(subset=["CAR_D_0_10", "cut_vs_norm"])
    m = smf.ols("CAR_D_0_10 ~ cut_vs_norm + C(publisher)", e).fit(cov_type="HC1")
    return {"variant": "CAR_D_0_10 ~ cut_vs_norm (early cuts)", "coef": m.params["cut_vs_norm"],
            "se": m.bse["cut_vs_norm"], "p": m.pvalues["cut_vs_norm"], "n": int(m.nobs)}


def plot_paths(d):
    daily = pd.read_csv(config.PROCESSED / "abnormal_returns_daily.csv")
    daily = daily[daily["event"] == "discount"].merge(
        d[["steam_appid"]].assign(group=assign_group(d, "early_cut_rt")), on="steam_appid")
    daily = daily[daily["group"] != "unknown"].sort_values(["steam_appid", "rel_day"])
    daily["car"] = daily.groupby("steam_appid")["ar"].cumsum()
    base = daily[daily["rel_day"] == -1].set_index("steam_appid")["car"]
    daily["car"] = daily["car"] - daily["steam_appid"].map(base).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for grp, g in daily.groupby("group"):
        path = g.groupby("rel_day")["car"].mean()
        ax.plot(path.index, path.values * 100, label=f"{grp} (n={g['steam_appid'].nunique()})")
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("Trading days relative to first discount (day 0)")
    ax.set_ylabel("Mean cumulative abnormal return from day -1 (%)")
    ax.set_title("Stock reaction around a game's first discount of 20% or more")
    ax.legend(fontsize=8)
    fig.tight_layout()
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    path = config.FIGURES / "q2_car_paths.png"
    fig.savefig(path, dpi=150)
    return path


def log_trials(group_rows, reg):
    path = config.DOCS / "trial_log.csv"
    log = pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame(
        columns=["date", "phase", "variant", "description", "result"])
    new = [{"date": date.today().isoformat(), "phase": "Q2", "variant": f"{r['variant']} | {r['group']}",
            "description": "Mean CARs by group",
            "result": f"n={r['n']}; CAR_D_0_10={r['mean_CAR_D_0_10']:.4f} (p={r['p_CAR_D_0_10']:.3f}); "
                      f"CAR_E={r['mean_CAR_E']:.4f} (p={r['p_CAR_E']:.3f})"} for r in group_rows]
    new.append({"date": date.today().isoformat(), "phase": "Q2", "variant": reg["variant"],
                "description": "Early cuts, publisher FE, HC1",
                "result": f"coef={reg['coef']:.4f}; se={reg['se']:.4f}; p={reg['p']:.3f}; n={reg['n']}"})
    new = pd.DataFrame(new)
    log = log[~((log["phase"] == "Q2") & (log["variant"].isin(new["variant"])))]
    pd.concat([log, new], ignore_index=True).to_csv(path, index=False)


def main():
    d = load()
    rows = (group_table(d, "early_cut_rt", "primary")
            + group_table(d, "early_cut_strict", "strict_flag")
            + group_table(d[~d["near_earnings"]], "early_cut_rt", "excl_near_earnings"))
    groups = pd.DataFrame(rows)
    reg = cut_regression(d)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    groups.to_csv(config.TABLES / "q2_groups.csv", index=False)
    pd.DataFrame([reg]).to_csv(config.TABLES / "q2_regression.csv", index=False)
    fig = plot_paths(d)
    log_trials(rows, reg)

    show = groups[["variant", "group", "n", "mean_CAR_D_0_2", "mean_CAR_D_0_10", "p_CAR_D_0_10",
                   "mean_CAR_E", "p_CAR_E", "share_CAR_D_0_10_negative"]]
    print(f"Q2 sample: {len(d)} games\n")
    print("Mean abnormal returns at the first discount (CAR_D) and at earnings (CAR_E), by group:")
    print(show.round(4).to_string(index=False))
    print(f"\nRegression, early cuts only: CAR_D_0_10 on (first-cut depth - norm at that day): "
          f"coef {reg['coef']:.4f}, se {reg['se']:.4f}, p {reg['p']:.3f}, n {reg['n']}")
    print("Cross-sectional t-tests; with 3 publishers these are descriptive.")
    print(f"\nSaved tables to {config.TABLES}, figure to {fig}; {len(rows) + 1} rows written to docs/trial_log.csv")


if __name__ == "__main__":
    main()
