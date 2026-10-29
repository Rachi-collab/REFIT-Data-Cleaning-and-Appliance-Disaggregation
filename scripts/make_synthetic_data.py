"""Generate SYNTHETIC data in the REFIT file format, ONLY to smoke-test the pipeline when the real data is not available.
Nothing produced from this data is a result. Usage: python scripts/make_synthetic_data.py [out_dir]"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refit_nilm import config as C

DAYS = 35


def washer_profile(rng):
    heat = rng.integers(10, 18); wash = rng.integers(25, 45); spin = rng.integers(8, 15)
    return np.r_[np.full(heat, 2050.0), 150 + 60 * rng.random(wash), 400 + 80 * rng.random(spin)] * (0.9 + 0.2 * rng.random())


def make_house(seed, washer_ch, start="2014-03-01"):
    rng = np.random.default_rng(seed)
    n = DAYS * 86400 // 8
    unix = int(pd.Timestamp(start, tz="UTC").timestamp()) + np.arange(n) * 8
    t = pd.to_datetime(unix, unit="s", utc=True)
    app = np.zeros((n, 9))
    fridge = (np.sin(np.arange(n) / 40.0) > 0.3) * 90.0
    app[:, 0] = fridge
    wm = np.zeros(n)
    per_min = 7.5
    for d in range(DAYS):
        for _ in range(rng.choice([0, 1, 1, 2], p=[.25, .35, .25, .15])):
            s = int((d * 1440 + rng.integers(7 * 60, 21 * 60)) * per_min)
            p = np.repeat(washer_profile(rng), 7)
            wm[s:s + len(p)] = p[: max(0, min(len(p), n - s))]
    kettle = np.zeros(n)
    for _ in range(DAYS * 5):
        s = int(rng.integers(0, n - 40)); kettle[s:s + rng.integers(8, 30)] = 2800
    other_big = np.zeros(n)
    for _ in range(DAYS):
        s = int(rng.integers(0, n - 2000)); other_big[s:s + rng.integers(100, 600)] = rng.choice([800, 2200])
    chans = [i for i in range(9) if i != washer_ch - 1 and i != 0]
    app[:, chans[0]] = kettle
    app[:, washer_ch - 1] = wm
    base = 250 + 80 * np.sin(np.arange(n) / 9000.0) + rng.normal(0, 25, n)
    agg = base + app.sum(axis=1) + other_big
    return unix, t, agg, app


def write_clean(house, out_dir):
    ch = C.WASHER_CHANNEL[house]
    unix, t, agg, app = make_house(house, ch)
    n = len(unix)
    agg = agg.copy()
    o = n // 3; agg[o:o + 6000] = agg[o - 1]                      # forward-filled outage (flat line), as in REFIT CLEAN
    df = pd.DataFrame({"Time": t.tz_localize(None).strftime("%Y-%m-%d %H:%M:%S"), "Unix": unix, "Aggregate": agg.round(0)})
    for i in range(9):
        df[f"Appliance{i+1}"] = app[:, i].round(0)
    df["Issues"] = (app.sum(axis=1) > agg).astype(int)
    path = Path(out_dir) / "clean" / f"CLEAN_House{house}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_raw_house1(out_dir):
    rng = np.random.default_rng(7)
    unix, t, agg, app = make_house(1, C.WASHER_CHANNEL[1])
    df = pd.DataFrame({"Time": t.tz_localize(None).strftime("%Y-%m-%d %H:%M:%S"), "Unix": unix, "Aggregate": agg.round(0)})
    for i in range(9):
        df[f"Appliance{i+1}"] = app[:, i].round(0)
    n = len(df)
    keep = rng.random(n) > 0.04                                   # irregular sampling
    df = df[keep].reset_index(drop=True)
    cols = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
    df.loc[1000:1900, cols] = np.nan                              # short outage
    a = len(df) // 2
    df.loc[a:a + 20000, cols] = np.nan                            # long outage
    df.loc[500:520, "Aggregate"] = -50                            # impossible negative
    df.loc[3000:3003, "Appliance3"] = 90000                       # impossible spike
    dup = df.iloc[4000:4100].copy()
    df = pd.concat([df, dup]).reset_index(drop=True)              # duplicate timestamps, appended out of order
    path = Path(out_dir) / "raw" / "House1.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else C.ROOT / "data" / "synthetic"
    write_raw_house1(out)
    for h in sorted(set(C.EDA_HOUSES + C.TRAIN_HOUSES + C.VAL_HOUSES + C.TEST_HOUSES)):
        write_clean(h, out)
    print("synthetic data written to", out)
