"""Section 1: inspect and clean RAW REFIT House 1, resample to 1 minute, plot before/after.
Outputs: results/section1_findings.json|md, data/processed/house1_1min.csv, figures/s1_*.png"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refit_nilm import config as C
from refit_nilm.io import find_house_file, load_raw_house
from refit_nilm.cleaning import inspect_raw, clean_raw_to_1min, power_cols


def main():
    C.RESULTS_DIR.mkdir(exist_ok=True); C.FIG_DIR.mkdir(exist_ok=True); C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = find_house_file(C.RAW_DIR if C.RAW_DIR.exists() else C.DATA_DIR, C.RAW_HOUSE, clean=False)
    if path is None:
        sys.exit(f"Raw House{C.RAW_HOUSE} csv not found under {C.DATA_DIR}. Run scripts/download_data.py first.")
    print("raw file:", path)
    raw = load_raw_house(path)
    findings = inspect_raw(raw)
    findings["file"] = path.name
    clean = clean_raw_to_1min(raw)
    pc = power_cols(raw)
    findings["cleaned_minutes"] = int(len(clean))
    findings["minutes_interpolated_(<=%d min gaps)" % C.MAX_FILL_MIN] = int(clean["was_filled"].sum())
    findings["minutes_flagged_long_gap_(not filled)"] = int(clean["long_gap"].sum())
    findings["pct_minutes_flagged_long_gap"] = round(100 * float(clean["long_gap"].mean()), 2)
    # list the long outages (>= 60 min) for DATA.md
    lg = clean["long_gap"].astype(int)
    edges = np.diff(np.r_[0, lg.to_numpy(), 0])
    s, e = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    outages = [(str(clean.index[a]), str(clean.index[b]), int(b - a + 1)) for a, b in zip(s, e) if b - a + 1 >= 60]
    outages.sort(key=lambda x: -x[2])
    findings["longest_outages_(start,end,minutes)"] = outages[:10]
    (C.RESULTS_DIR / "section1_findings.json").write_text(json.dumps(findings, indent=2, default=str))

    md = ["# Section 1 findings (auto-generated; copy into DATA.md)\n", "| Check | Result |", "|---|---|"]
    for k, v in findings.items():
        md.append(f"| {k} | {v} |")
    (C.RESULTS_DIR / "section1_findings.md").write_text("\n".join(md))
    clean.to_csv(C.PROCESSED_DIR / "house1_1min.csv")

    # ---- plots: aggregate + two appliance channels, before vs after, for one busy day ----
    apps = [c for c in pc if c != "Aggregate"]
    top2 = raw[apps].var().sort_values(ascending=False).index[:2].tolist()     # the two most active channels
    cols = ["Aggregate"] + top2
    day_counts = clean[~clean["long_gap"]].groupby(clean[~clean["long_gap"]].index.date).size()
    full_days = day_counts[day_counts >= 1400].index
    if len(full_days) == 0:
        full_days = day_counts.index
    act = clean.loc[[d in set(full_days) for d in clean.index.date]].groupby(lambda x: x.date())[top2[0]].std()
    day = act.idxmax()
    d0 = pd.Timestamp(day, tz="UTC"); d1 = d0 + pd.Timedelta(days=1)
    r = raw[(raw["ts"] >= d0) & (raw["ts"] < d1)].sort_values("ts")
    c = clean[(clean.index >= d0) & (clean.index < d1)]
    fig, ax = plt.subplots(3, 2, figsize=(14, 8), sharex=True)
    for i, col in enumerate(cols):
        ax[i, 0].plot(r["ts"], r[col], lw=0.5, color="tab:gray"); ax[i, 0].set_ylabel(f"{col} (W)")
        ax[i, 1].plot(c.index, c[col], lw=0.8, color="tab:blue")
    ax[0, 0].set_title(f"BEFORE: raw House {C.RAW_HOUSE}, {day} (~8 s samples, as recorded)")
    ax[0, 1].set_title("AFTER: cleaned, 1-minute mean")
    for a in ax[-1]:
        a.set_xlabel("time (UTC)")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s1_before_after_day.png", dpi=130); plt.close(fig)

    # whole-period view: where is data usable?
    daily = (~clean["long_gap"]).groupby(clean.index.date).mean()
    fig, ax = plt.subplots(2, 1, figsize=(14, 6), sharex=False)
    ax[0].plot(clean.index, clean["Aggregate"], lw=0.3); ax[0].set_ylabel("Aggregate (W), cleaned")
    ax[0].set_title("Whole period: cleaned aggregate (NaN gaps = flagged outages, not filled)")
    ax[1].bar(pd.to_datetime(list(daily.index)), daily.values, width=1.0); ax[1].set_ylabel("fraction of day usable")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s1_coverage_overview.png", dpi=130); plt.close(fig)
    print("\n".join(md[:40]))


if __name__ == "__main__":
    main()
