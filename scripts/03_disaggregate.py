"""Section 3: estimate washing-machine power from the household aggregate (1-minute), validated on UNSEEN HOUSES.
Split design: train houses -> validation houses (choose hyper-parameters) -> test houses (final evaluation, run once).
Outputs: results/model_*.csv|md, results/failure_*.csv, figures/s3_*.png"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refit_nilm import config as C
from refit_nilm.io import find_house_file, load_clean_house
from refit_nilm.features import make_windows, subsample_for_training
from refit_nilm.metrics import regression_and_state, cycle_level
from refit_nilm.cycles import detect_cycles


def load_set(houses):
    root = C.CLEAN_DIR if C.CLEAN_DIR.exists() else C.DATA_DIR
    out = {}
    for h in houses:
        p = find_house_file(root, h, clean=True)
        if p is None:
            print(f"House {h}: file not found, skipping"); continue
        m = load_clean_house(p, h)
        X, y, t, ok = make_windows(m)
        out[h] = dict(m=m, X=X, y=y, t=t, ok=ok, agg=m["Aggregate"].to_numpy(dtype="float32")[C.WINDOW // 2: len(m) - C.WINDOW // 2])
        print(f"House {h}: {len(y):,} minutes, {ok.mean()*100:.1f}% usable windows, washer on {np.mean(y[ok] > C.ON_W)*100:.1f}%")
    return out


def post(pred, agg):
    """Physical post-processing: power cannot be negative or exceed the whole-home aggregate; tiny values -> 0."""
    p = np.clip(pred, 0, None)
    p = np.minimum(p, np.nan_to_num(agg, nan=0.0))
    p[p < 5.0] = 0.0
    return drop_short_runs(p, C.MIN_CYCLE_MIN)


def drop_short_runs(p, min_len):
    """A washing cycle lasts >= MIN_CYCLE_MIN minutes, so isolated short 'on' blips are treated as false alarms."""
    on = (p > C.ON_W).astype(np.int8)
    d = np.diff(np.concatenate([[0], on, [0]]))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    p = p.copy()
    for a, b in zip(starts, ends):
        if b - a < min_len:
            p[a:b] = 0.0
    return p


def hour_profile(train):
    """Baseline 2: mean washer power by (weekday, hour), learned on the training houses only."""
    frames = []
    for d in train.values():
        frames.append(pd.DataFrame({"y": d["y"][d["ok"]], "dow": d["t"][d["ok"]].day_of_week, "hour": d["t"][d["ok"]].hour}))
    f = pd.concat(frames)
    return f.groupby(["dow", "hour"])["y"].mean()


def predict_profile(prof, t):
    key = list(zip(t.day_of_week, t.hour))
    return prof.reindex(pd.MultiIndex.from_tuples(key, names=["dow", "hour"])).fillna(0).to_numpy()


def main():
    C.RESULTS_DIR.mkdir(exist_ok=True); C.FIG_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(C.SEED)
    train, val, test = load_set(C.TRAIN_HOUSES), load_set(C.VAL_HOUSES), load_set(C.TEST_HOUSES)
    if not train or not test:
        sys.exit("Need at least one train and one test house with data (edit refit_nilm/config.py).")
    if not val:
        print("WARNING: no validation houses found; using the default hyper-parameters.")

    Xtr = np.vstack([d["X"][d["ok"]] for d in train.values()]); ytr = np.concatenate([d["y"][d["ok"]] for d in train.values()])
    Xs, ys = subsample_for_training(Xtr, ytr, rng)
    print(f"training rows after off-subsampling: {len(ys):,} (on-fraction {np.mean(ys > C.ON_W)*100:.1f}%)")

    grid = [dict(learning_rate=0.1, max_leaf_nodes=31, max_iter=200), dict(learning_rate=0.05, max_leaf_nodes=63, max_iter=300),
            dict(learning_rate=0.1, max_leaf_nodes=15, max_iter=200, l2_regularization=1.0)]
    best, best_rmse, rows = None, np.inf, []
    for g in grid:
        mdl = HistGradientBoostingRegressor(random_state=C.SEED, **g).fit(Xs, ys)
        if val:
            r = []
            for d in val.values():
                pr = post(mdl.predict(d["X"][d["ok"]]), d["agg"][d["ok"]])
                r.append(regression_and_state(d["y"][d["ok"]], pr))
            mean = pd.DataFrame(r).mean().to_dict(); rows.append({**g, **mean})
            if mean["RMSE_W"] < best_rmse:
                best, best_rmse = (mdl, g), mean["RMSE_W"]
        else:
            best = (mdl, g); break
    pd.DataFrame(rows).to_csv(C.RESULTS_DIR / "model_validation_grid.csv", index=False)
    model, g = best
    print("selected hyper-parameters (lowest mean validation RMSE):", g)

    prof = hour_profile(train)
    res, cyc_rows, daily, fail_bins, miss_rows, preds = [], [], [], [], [], {}
    for h, d in test.items():
        ok, y, t, agg = d["ok"], d["y"], d["t"], d["agg"]
        pm = post(model.predict(d["X"]), agg)
        pp = post(predict_profile(prof, t), agg)
        p0 = np.zeros_like(y)
        preds[h] = dict(t=t, y=y, ok=ok, model=pm, profile=pp, agg=agg)
        for name, p in [("always_off", p0), ("hour_dow_profile", pp), ("gradient_boosting", pm)]:
            res.append(dict(house=h, predictor=name, **regression_and_state(y[ok], p[ok])))
            tp = pd.Series(y, index=t).where(ok); pr_ = pd.Series(p, index=t).where(ok)
            cyc_rows.append(dict(house=h, predictor=name, **cycle_level(tp, pr_)))
        # daily energy
        df = pd.DataFrame({"y": y, "pm": pm, "ok": ok}, index=t)
        for day, g_ in df[df["ok"]].groupby(df[df["ok"]].index.date):
            if len(g_) >= 1200:
                daily.append(dict(house=h, day=day, usable_min=len(g_), true_wh=g_["y"].sum() / 60, pred_wh=g_["pm"].sum() / 60))
        # failure analysis: error vs how much OTHER load is running while the washer is on
        on = ok & (y > C.ON_W)
        other = agg[on] - y[on]
        bins = pd.cut(other, [-np.inf, 300, 800, 2000, np.inf], labels=["<300 W", "300-800 W", "800-2000 W", ">2000 W"])
        e = pd.DataFrame({"bin": bins, "abs_err": np.abs(y[on] - pm[on]), "err": pm[on] - y[on]})
        fb = e.groupby("bin", observed=True).agg(minutes=("abs_err", "size"), MAE_W=("abs_err", "mean"), mean_error_W=("err", "mean")).reset_index()
        fb.insert(0, "house", h); fail_bins.append(fb)
        # missed cycles
        tc, pc_ = detect_cycles(pd.Series(y, index=t).where(ok)), detect_cycles(pd.Series(pm, index=t).where(ok))
        for _, c in tc.iterrows():
            hit = ((pc_["end"] >= c["start"]) & (pc_["start"] <= c["end"])).any() if len(pc_) else False
            if not hit:
                seg = (t >= c["start"]) & (t <= c["end"])
                miss_rows.append(dict(house=h, start=c["start"], duration_min=c["duration_min"], peak_w=c["peak_w"],
                                      mean_other_load_W=float(np.mean(agg[seg] - y[seg]))))

    R = pd.DataFrame(res)
    R.to_csv(C.RESULTS_DIR / "model_test_metrics.csv", index=False)
    pooled = R.groupby("predictor")[["MAE_W", "RMSE_W", "SAE", "precision", "recall", "F1_on"]].mean().round(3)
    pooled.to_csv(C.RESULTS_DIR / "model_test_metrics_mean_over_houses.csv")
    CY = pd.DataFrame(cyc_rows); CY.to_csv(C.RESULTS_DIR / "model_test_cycle_level.csv", index=False)
    D = pd.DataFrame(daily); D.to_csv(C.RESULTS_DIR / "model_test_daily_energy.csv", index=False)
    FB = pd.concat(fail_bins); FB.to_csv(C.RESULTS_DIR / "failure_error_by_other_load.csv", index=False)
    MS = pd.DataFrame(miss_rows, columns=["house", "start", "duration_min", "peak_w", "mean_other_load_W"]); MS.to_csv(C.RESULTS_DIR / "failure_missed_cycles.csv", index=False)

    # ---- plots ----
    h_best = max(preds, key=lambda h: preds[h]["y"][preds[h]["ok"]].sum())
    P = preds[h_best]
    s = pd.DataFrame({"agg": P["agg"], "actual": P["y"], "model": P["model"], "profile": P["profile"], "ok": P["ok"]}, index=P["t"])
    dayE = s[s["ok"]].groupby(s[s["ok"]].index.date)["actual"].sum()
    dayN = s[s["ok"]].groupby(s[s["ok"]].index.date).size()
    cand = dayE[dayN >= 1400]
    day = cand.idxmax() if len(cand) else dayE.idxmax()
    sd = s[s.index.date == day]
    fig, ax = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    ax[0].plot(sd.index, sd["agg"], lw=0.8, color="tab:gray"); ax[0].set_ylabel("Aggregate (W)"); ax[0].set_title(f"TEST house {h_best} (never seen in training), {day}")
    ax[1].plot(sd.index, sd["actual"], lw=1.2, label="actual washer", color="black")
    ax[1].plot(sd.index, sd["model"], lw=1.0, label="gradient boosting", color="tab:red")
    ax[1].plot(sd.index, sd["profile"], lw=0.8, label="hour/weekday profile baseline", color="tab:green", alpha=0.8)
    ax[1].set_ylabel("washing machine (W)"); ax[1].legend(); ax[1].set_xlabel("time (UTC)")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s3_actual_vs_predicted_day.png", dpi=130); plt.close(fig)

    tc = detect_cycles(pd.Series(P["y"], index=P["t"]).where(P["ok"]))
    if len(tc):
        c = tc.sort_values("energy_wh").iloc[len(tc) // 2]
        z = s.loc[c["start"] - pd.Timedelta(minutes=30): c["end"] + pd.Timedelta(minutes=30)]
        fig, ax = plt.subplots(figsize=(11, 4.5))
        ax.plot(z.index, z["actual"], color="black", label="actual"); ax.plot(z.index, z["model"], color="tab:red", label="model")
        ax.plot(z.index, z["agg"] / 4, color="tab:gray", lw=0.6, label="aggregate / 4 (for scale)")
        ax.set_title(f"Zoom on one cycle, test house {h_best}"); ax.set_ylabel("W"); ax.legend()
        fig.tight_layout(); fig.savefig(C.FIG_DIR / "s3_actual_vs_predicted_cycle_zoom.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    piv = FB.pivot(index="bin", columns="house", values="MAE_W"); piv.plot(kind="bar", ax=ax)
    ax.set_ylabel("MAE while washer is ON (W)"); ax.set_xlabel("other load running at the same time"); ax.set_title("Failure analysis: error vs overlapping load")
    fig.tight_layout(); fig.savefig(C.FIG_DIR / "s3_failure_error_vs_other_load.png", dpi=130); plt.close(fig)

    if len(D):
        fig, ax = plt.subplots(figsize=(5.5, 5.5))
        ax.scatter(D["true_wh"], D["pred_wh"], s=12); lim = max(D["true_wh"].max(), D["pred_wh"].max()) * 1.05
        ax.plot([0, lim], [0, lim], "k--", lw=0.8); ax.set_xlabel("actual washer energy per day (Wh)"); ax.set_ylabel("predicted (Wh)")
        ax.set_title("Daily energy, test houses")
        fig.tight_layout(); fig.savefig(C.FIG_DIR / "s3_daily_energy_scatter.png", dpi=130); plt.close(fig)

    print("\nTEST metrics per house:\n", R.round(3).to_string(index=False))
    print("\nMean over test houses:\n", pooled.to_string())
    print("\nCycle-level:\n", CY.round(3).to_string(index=False))
    print("\nFailure by overlapping load:\n", FB.round(1).to_string(index=False))
    print(f"\nMissed cycles: {len(MS)}")


if __name__ == "__main__":
    main()
