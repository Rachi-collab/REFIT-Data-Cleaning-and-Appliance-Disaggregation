"""Washing-machine cycle detection."""
import numpy as np
import pandas as pd
from . import config as C


def detect_cycles(p, on_w=None, min_minutes=None, merge_gap_min=None):
    """p: regular 1-minute Series (NaN allowed).
    A cycle = run of minutes with power > on_w. Gaps shorter than merge_gap_min are merged (washers pause while soaking/draining).
    Runs shorter than min_minutes are discarded as spikes. Returns DataFrame start,end,duration_min,peak_w,energy_wh."""
    on_w = C.ON_W if on_w is None else on_w
    min_minutes = C.MIN_CYCLE_MIN if min_minutes is None else min_minutes
    merge_gap_min = C.MERGE_GAP_MIN if merge_gap_min is None else merge_gap_min
    v = p.to_numpy(dtype=float)
    on = np.nan_to_num(v, nan=0.0) > on_w
    if not on.any():
        return pd.DataFrame(columns=["start", "end", "duration_min", "peak_w", "energy_wh"])
    edges = np.diff(np.r_[0, on.astype(int), 0])
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0] - 1
    ms, me = [starts[0]], [ends[0]]
    for s, e in zip(starts[1:], ends[1:]):
        if s - me[-1] - 1 <= merge_gap_min:
            me[-1] = e
        else:
            ms.append(s); me.append(e)
    rows = []
    for s, e in zip(ms, me):
        dur = e - s + 1
        if dur >= min_minutes:
            seg = v[s:e + 1]
            rows.append(dict(start=p.index[s], end=p.index[e], duration_min=dur,
                             peak_w=float(np.nanmax(seg)), energy_wh=float(np.nansum(seg) / 60.0)))
    return pd.DataFrame(rows, columns=["start", "end", "duration_min", "peak_w", "energy_wh"])
