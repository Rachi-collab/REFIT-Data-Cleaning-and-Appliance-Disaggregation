"""Section 2: washing-machine EDA on the OFFICIAL CLEANED data, several houses, 1-minute resolution.
Outputs: results/eda_*.csv|md and figures/s2_*.png"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refit_nilm import config as C
from refit_nilm.io import find_house_file, load_clean_house
from refit_nilm.cycles import detect_cycles

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def main():
    C.RESULTS_DIR.mkdir(exist_ok=True); C.FIG_DIR.mkdir(exist_ok=True)
    root = C.CLEAN_DIR if C.CLEAN_DIR.exists() else C.DATA_DIR
    frames, rows, cyc_all = {}, [], []
    for h in C.EDA_HOUSES:
        p = find_house_file(root, h, clean=True)
        if p is None:
            print(f"House {h}: file not found, skipping"); continue
        m = load_clean_house(p, h)
        frames[h] = m
        cyc = detect_cycles(m["WM"].where(m["usable"]))
        cyc["house"] = h
        cyc_all.append(cyc)
        u = m[m["usable"]]
        rows.append(dict(house=h, washer_channel=f"Appliance{C.WASHER_CHANNEL[h]}", start=m.index.min().date(), end=m.index.max().date(),
                         minutes=len(m), pct_missing=round(100 * m["missing"].mean(), 2), pct_flat_ffilled=round(100 * m["flat"].mean(), 2),
                         pct_issues=round(100 * m["issue"].mean(), 2), usable_days=round(len(u) / 1440, 1),
                         pct_washer_off_of_usable=round(100 * float((u["WM"] <= C.ON_W).mean()), 2), cycles=len(cyc),
                         cycles_per_usable_week=round(len(cyc) / max(len(u) / 10080, 1e-9), 2),
                         max_washer_W=round(float(u["WM"].max()), 0)))
        print(f"House {h}: {len(cyc)} cycles")
    if len(frames) < 4:
        print(f"WARNING: only {len(frames)} houses with data; the brief asks for at least 4.")
    summ = pd.DataFrame(rows)
    summ.to_csv(C.RESULTS_DIR / "eda_house_summary.csv", index=False)
    (C.RESULTS_DIR / "eda_house_summary.md").write_text(summ.to_markdown(index=False) if hasattr(summ, "to_markdown") and _has_tabulate() else summ.to_string(index=False))
    cycles = pd.concat(cyc_all, ignore_index=True)
    cycles.to_csv(C.RESULTS_DIR / "eda_cycles.csv", index=False)

    # ---- usage patterns by hour and weekday (counts normalised by usable observation time) ----
    cycles["hour"] = cycles["start"].dt.hour; cycles["dow"] = cycles["start"].dt.day_of_week
    fig, ax = plt.subplots(1, 2, figsize=(14, 4))
    hr = cycles.groupby(["house", "hour"]).size().unstack(0).reindex(range(24)).fillna(0)
    (hr / hr.sum()).plot(ax=ax[0], marker="o", ms=3); ax[0].set_title("Share of cycle starts by hour of day (per house)")
    ax[0].set_xlabel("hour (UTC; UK local = UTC or UTC+1)"); ax[0].set_ylabel("share of that house's cycles")
    dw = cycles.groupby(["house", "dow"]).size().unstack(0).reindex(range(7)).fillna(0)
    (dw / dw.sum()).plot(kind="bar", ax=ax[1]); ax[1].set_xticklabels(DOW, rotation=0); ax[1].set_title("Share of cycle starts by day of week")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s2_usage_by_hour_dow.png", dpi=130); plt.close(fig)
    cycles.groupby("hour").size().to_csv(C.RESULTS_DIR / "eda_cycles_by_hour.csv")
    cycles.groupby("dow").size().rename(index=dict(enumerate(DOW))).to_csv(C.RESULTS_DIR / "eda_cycles_by_dow.csv")

    # ---- (i) representative 24 h: aggregate + washer ----
    best = cycles.groupby("house").size().idxmax()
    m = frames[best]
    c = cycles[cycles["house"] == best].copy()
    c["day"] = c["start"].dt.date
    cand = c.groupby("day").size()
    ok_days = [d for d in cand.index if m[(m.index.date == d)]["usable"].mean() > 0.98]
    day = max(ok_days, key=lambda d: cand[d]) if ok_days else cand.idxmax()
    d0 = pd.Timestamp(day, tz="UTC"); d1 = d0 + pd.Timedelta(days=1)
    seg = m[(m.index >= d0) & (m.index < d1)]
    fig, ax = plt.subplots(2, 1, figsize=(13, 6), sharex=True)
    ax[0].plot(seg.index, seg["Aggregate"], lw=0.8); ax[0].set_ylabel("Aggregate (W)")
    ax[0].set_title(f"House {best}, {day}: whole-home aggregate")
    ax[1].plot(seg.index, seg["WM"], lw=0.8, color="tab:red"); ax[1].set_ylabel("Washing machine (W)")
    ax[1].set_title("Washing-machine channel (same day)"); ax[1].set_xlabel("time (UTC)")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s2_representative_24h.png", dpi=130); plt.close(fig)

    # ---- (ii) detected cycles ----
    ex = c.sort_values("start").iloc[:: max(1, len(c) // 6)].head(6)
    fig, axs = plt.subplots(2, 3, figsize=(14, 6)); axs = axs.ravel()
    for a, (_, r) in zip(axs, ex.iterrows()):
        pad = pd.Timedelta(minutes=20)
        s = m.loc[r["start"] - pad: r["end"] + pad, "WM"]
        a.plot(s.index, s.values, lw=1); a.axvspan(r["start"], r["end"], color="orange", alpha=0.25)
        a.set_title(f"{r['start']:%Y-%m-%d %H:%M}  {r['duration_min']:.0f} min, peak {r['peak_w']:.0f} W", fontsize=9)
        a.tick_params(axis="x", labelrotation=30, labelsize=7)
    fig.suptitle(f"House {best}: detected cycles (shaded = detected cycle: power > {C.ON_W:g} W, >= {C.MIN_CYCLE_MIN} min, pauses <= {C.MERGE_GAP_MIN} min merged)")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s2_detected_cycles.png", dpi=130); plt.close(fig)

    # ---- (iii) cross-house comparison ----
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
    for a, (col, lab) in zip(ax, [("duration_min", "Duration (min)"), ("peak_w", "Peak power (W)"), ("energy_wh", "Energy per cycle (Wh)")]):
        groups = [cycles.loc[cycles["house"] == h, col].values for h in sorted(cycles["house"].unique())]
        a.boxplot(groups, tick_labels=[str(h) for h in sorted(cycles["house"].unique())]) if _new_mpl() else a.boxplot(groups, labels=[str(h) for h in sorted(cycles["house"].unique())])
        a.set_xlabel("house"); a.set_ylabel(lab); a.set_title(lab + " by house")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s2_cross_house_comparison.png", dpi=130); plt.close(fig)
    cmp_ = cycles.groupby("house")[["duration_min", "peak_w", "energy_wh"]].agg(["count", "median", "mean"]).round(1)
    cmp_.to_csv(C.RESULTS_DIR / "eda_cycle_characteristics_by_house.csv")
    print(summ.to_string(index=False)); print(cmp_.to_string())


def _has_tabulate():
    try:
        import tabulate  # noqa
        return True
    except ImportError:
        return False


def _new_mpl():
    return tuple(int(x) for x in matplotlib.__version__.split(".")[:2]) >= (3, 9)


if __name__ == "__main__":
    main()
