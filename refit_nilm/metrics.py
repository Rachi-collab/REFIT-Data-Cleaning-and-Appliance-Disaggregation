"""Evaluation metrics, chosen because the washer is OFF ~98% of the time."""
import numpy as np
import pandas as pd
from . import config as C
from .cycles import detect_cycles


def regression_and_state(y, yhat, on_w=None):
    on_w = C.ON_W if on_w is None else on_w
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    mae = float(np.mean(np.abs(y - yhat)))
    rmse = float(np.sqrt(np.mean((y - yhat) ** 2)))
    sae = float(abs(yhat.sum() - y.sum()) / max(y.sum(), 1e-9))          # signal aggregate error: error in TOTAL energy
    yt, pt = y > on_w, yhat > on_w
    tp, fp, fn = int((yt & pt).sum()), int((~yt & pt).sum()), int((yt & ~pt).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    return dict(MAE_W=mae, RMSE_W=rmse, SAE=sae, precision=prec, recall=rec, F1_on=f1)


def cycle_level(true_p, pred_p):
    """Did we find the cycles? A true cycle is found if any predicted cycle overlaps it; a predicted cycle is false if it overlaps none."""
    tc, pc = detect_cycles(true_p), detect_cycles(pred_p)
    def overlaps(a, b):
        return not (a["end"] < b["start"] or b["end"] < a["start"])
    found = sum(any(overlaps(t, p) for _, p in pc.iterrows()) for _, t in tc.iterrows())
    false = sum(not any(overlaps(p, t) for _, t in tc.iterrows()) for _, p in pc.iterrows())
    e_true = float(tc["energy_wh"].sum()) if len(tc) else 0.0
    e_pred = float(pc["energy_wh"].sum()) if len(pc) else 0.0
    return dict(true_cycles=len(tc), pred_cycles=len(pc), cycles_found=int(found),
                cycle_recall=found / max(len(tc), 1), false_cycles=int(false),
                cycle_precision=(len(pc) - false) / max(len(pc), 1), energy_true_wh=e_true, energy_pred_wh=e_pred)
