"""Seq2Point-style windows: aggregate context in, appliance power at the window centre out."""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from . import config as C


def make_windows(m, window=None):
    """m: 1-minute frame from io.load_clean_house. Returns X, y, index, ok (rows whose whole window and target are usable)."""
    w = window or C.WINDOW
    half = w // 2
    agg = m["Aggregate"].to_numpy(dtype="float32")
    usable = m["usable"].to_numpy()
    agg0 = np.nan_to_num(agg, nan=0.0)
    n = len(agg)
    idx = np.arange(half, n - half)
    win = sliding_window_view(agg0, w)                       # (n-w+1, w): row i is centred at i+half
    ok = sliding_window_view(usable.astype(np.int8), w).min(axis=1).astype(bool)
    t = m.index[idx]
    feats = np.c_[win, win.mean(1), win.std(1), win.max(1), win.min(1),
                  np.abs(np.diff(win, axis=1)).max(1),        # largest minute-to-minute jump (edges of appliance switching)
                  t.hour, t.dayofweek].astype("float32")
    y = m["WM"].to_numpy(dtype="float32")[idx]
    return feats, y, t, ok


def subsample_for_training(X, y, rng):
    """Training only: keep every row where the washer is on (or near on) and a fraction of 'off' rows; cap total size."""
    on = y > C.ON_W
    keep = on | (rng.random(len(y)) < C.OFF_KEEP_FRAC)
    X, y = X[keep], y[keep]
    if len(y) > C.MAX_TRAIN_ROWS:
        sel = rng.choice(len(y), C.MAX_TRAIN_ROWS, replace=False)
        X, y = X[sel], y[sel]
    return X, y
