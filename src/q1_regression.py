"""
Q1: does abnormal discount depth by day 90 predict the stock reaction at the next earnings announcement?

Usage, from the repo root:
    python -m src.q1_regression

Inputs:  data/processed/events.csv, data/processed/event_returns.csv (main sample only)
Outputs: output/tables/q1_results.csv, rows added to docs/trial_log.csv (D14)

Primary specification (D7, D10, with logged deviations):
    CAR_E ~ abn_90 + reviews_pos + log_size (missing-indicator) + pre_return_60 + publisher fixed effects
Prediction: coefficient on abn_90 < 0.

Inference: HC1 robust SEs; SEs clustered by earnings announcement; the publisher-block bootstrap (D10)
computed exactly over all 27 resamples of 3 publishers; leave-one-publisher-out estimates.
With 3 publishers the pilot's inference is descriptive (deviation 2026-11-27).
"""

import itertools
from datetime import date

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

import config

CONTROLS = "reviews_pos + log_size_f + size_missing + pre_return_60"
CONTROL_LIST = ["reviews_pos", "log_size_f", "size_missing", "pre_return_60"]


def load():
    ev = pd.read_csv(config.PROCESSED / "events.csv")
    rt = pd.read_csv(config.PROCESSED / "event_returns.csv")
    keep = ["steam_appid", "CAR_E", "SCAR_E", "pre_return_60"]
    d = ev.merge(rt[keep], on="steam_appid", how="inner")
    d = d[~d["holdout"].astype(bool)].copy()
    d["size_missing"] = d["size_missing"].astype(bool).astype(int)
    d["log_size_f"] = d["log_size"].fillna(0.0)
    d["late_to_steam"] = d["late_to_steam"].astype(bool)
    d["event_id"] = d["publisher"] + "_" + d["earnings_date"].astype(str)
    return d


def fit(d, x="abn_90", controls=True, cluster=None):
    d = d.dropna(subset=["CAR_E", x, "reviews_pos", "pre_return_60"])
    terms = [x] + ([c for c in CONTROL_LIST if d[c].nunique() > 1] if controls else [])
    formula = "CAR_E ~ " + " + ".join(terms) + " + C(publisher)"
    if cluster:
        groups = pd.factorize(d[cluster])[0]
        m = smf.ols(formula, d).fit(cov_type="cluster", cov_kwds={"groups": groups})
    else:
        m = smf.ols(formula, d).fit(cov_type="HC1")
    return m, d


def coef_row(name, m, x, n_events=None):
    return {"variant": name, "coef": m.params[x], "se": m.bse[x], "t": m.tvalues[x],
            "p": m.pvalues[x], "n": int(m.nobs), "n_events": n_events}


def block_bootstrap(d, x="abn_90"):
    """Exact publisher-block bootstrap: every ordered draw of 3 publishers with replacement."""
    pubs = sorted(d["publisher"].unique())
    coefs = []
    for draw in itertools.product(pubs, repeat=len(pubs)):
        parts = [d[d["publisher"] == p].assign(publisher=f"{p}_{k}") for k, p in enumerate(draw)]
        b = pd.concat(parts)
        try:
            coefs.append(fit(b, x)[0].params[x])
        except Exception:
            continue
    coefs = np.array(coefs)
    return {"draws": len(coefs), "share_negative": (coefs < 0).mean(),
            "ci_low": np.percentile(coefs, 2.5), "ci_high": np.percentile(coefs, 97.5)}


def event_level(d, x="abn_90"):
    """One observation per earnings announcement: game-level variables averaged."""
    d = d.dropna(subset=["CAR_E", x, "reviews_pos", "pre_return_60"])
    cols = [x, "reviews_pos", "log_size_f", "size_missing", "pre_return_60", "CAR_E"]
    agg = d.groupby(["event_id", "publisher"], as_index=False)[cols].mean()
    return fit(agg, x)[0], len(agg)


def log_trials(rows):
    path = config.DOCS / "trial_log.csv"
    log = pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame(
        columns=["date", "phase", "variant", "description", "result"])
    new = pd.DataFrame([{"date": date.today().isoformat(), "phase": "Q1", "variant": r["variant"],
                         "description": r.get("description", ""),
                         "result": f"coef={r['coef']:.4f}; se={r['se']:.4f}; p={r['p']:.3f}; n={r['n']}"}
                        for r in rows])
    log = log[~((log["phase"] == "Q1") & (log["variant"].isin(new["variant"])))]
    pd.concat([log, new], ignore_index=True).to_csv(path, index=False)


def main():
    d = load()
    rows = []

    m, used = fit(d)
    rows.append({**coef_row("primary_HC1", m, "abn_90", used["event_id"].nunique()),
                 "description": "Primary: abn_90 + controls + publisher FE, HC1 SEs"})
    mc, _ = fit(d, cluster="event_id")
    rows.append({**coef_row("primary_cluster_event", mc, "abn_90", used["event_id"].nunique()),
                 "description": "Primary, SEs clustered by earnings announcement"})

    specs = [
        ("no_controls", "abn_90 + publisher FE only", lambda: fit(d, controls=False)[0], "abn_90"),
        ("single_day_depth", "abn_single_90 (original D5) instead of abn_90",
         lambda: fit(d, x="abn_single_90")[0], "abn_single_90"),
        ("norm_depth_filter", "Drop games with n_norm_90 < 5", lambda: fit(d[d["n_norm_90"] >= 5])[0], "abn_90"),
        ("drop_late_to_steam", "Drop games not on Steam at launch",
         lambda: fit(d[~d["late_to_steam"]])[0], "abn_90"),
    ]
    for name, desc, f, x in specs:
        mm = f()
        rows.append({**coef_row(name, mm, x), "description": desc})

    me, n_ev = event_level(d)
    rows.append({**coef_row("event_level", me, "abn_90", n_ev),
                 "description": "One observation per earnings announcement (averaged)"})

    for p in sorted(d["publisher"].unique()):
        sub = d[d["publisher"] != p]
        mm = fit(sub)[0]
        rows.append({**coef_row(f"leave_out_{p}", mm, "abn_90"), "description": f"Drop {p}"})

    boot = block_bootstrap(d)
    results = pd.DataFrame(rows)
    config.TABLES.mkdir(parents=True, exist_ok=True)
    results.to_csv(config.TABLES / "q1_results.csv", index=False)
    log_trials(rows + [{"variant": "publisher_block_bootstrap", "coef": np.nan, "se": np.nan, "p": np.nan,
                        "n": len(used), "description": f"Exact, {boot['draws']} draws"}])

    print(f"Q1 sample: {len(used)} games, {used['event_id'].nunique()} earnings announcements, "
          f"{used['publisher'].nunique()} publishers\n")
    print("Primary model (HC1 standard errors):")
    print(m.summary().tables[1])
    print("\nabn_90 coefficient across specifications (prediction: negative):")
    print(results[["variant", "coef", "se", "p", "n", "n_events"]].round(4).to_string(index=False))
    print(f"\nPublisher-block bootstrap (exact, {boot['draws']} draws): "
          f"95% interval [{boot['ci_low']:.4f}, {boot['ci_high']:.4f}], "
          f"share of draws with a negative coefficient {boot['share_negative']:.0%}")
    print("With 3 publishers this interval is descriptive, not a reliable test.")
    print(f"\nSaved {config.TABLES / 'q1_results.csv'}; {len(rows) + 1} rows written to docs/trial_log.csv")


if __name__ == "__main__":
    main()
