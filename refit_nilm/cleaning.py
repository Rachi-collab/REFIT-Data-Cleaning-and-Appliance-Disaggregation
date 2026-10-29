"""Section 1: inspect and clean RAW data (documented rules)."""
import numpy as np
import pandas as pd
from . import config as C


def power_cols(df):
    return [c for c in df.columns if c != "ts"]


def inspect_raw(df):
    """Findings for DATA.md. Returns an ordered dict of simple facts."""
    ts = df["ts"]
    d = ts.diff().dt.total_seconds().dropna()
    pc = power_cols(df)
    apps = [c for c in pc if c != "Aggregate"]
    f = {
        "rows": len(df), "start": str(ts.min()), "end": str(ts.max()),
        "span_days": round((ts.max() - ts.min()).total_seconds() / 86400, 1),
        "rows_out_of_time_order": int((ts.diff().dt.total_seconds() < 0).sum()),
        "duplicate_timestamps": int(ts.duplicated().sum()),
        "median_interval_s": float(d[d > 0].median()),
        "intervals_gt_30s": int((d > 30).sum()),
        "intervals_gt_5min": int((d > 300).sum()),
        "longest_gap_hours": round(float(d.max()) / 3600, 2),
        "missing_pct_by_col": {c: round(float(100 * df[c].isna().mean()), 2) for c in pc},
        "negative_values_by_col": {c: int((df[c] < 0).sum()) for c in pc},
        f"values_gt_{C.MAX_PLAUSIBLE_W}W_by_col": {c: int((df[c] > C.MAX_PLAUSIBLE_W).sum()) for c in pc},
        "max_W_by_col": {c: float(df[c].max()) for c in pc},
        "pct_rows_appliance_sum_gt_aggregate_x1.05": round(100 * float((df[apps].sum(axis=1) > 1.05 * df["Aggregate"]).mean()), 2),
    }
    return f


def clean_raw_to_1min(df):
    """Rules (all documented in DATA.md):
    1. sort by time;  2. drop duplicate timestamps, keep the FIRST reading;
    3. impossible values (negative, or > MAX_PLAUSIBLE_W) -> NaN;
    4. resample to 1-minute MEAN;  5. linearly interpolate gaps <= MAX_FILL_MIN minutes;
    6. longer gaps stay NaN and are flagged in 'long_gap' (never filled)."""
    pc = power_cols(df)
    d = df.sort_values("ts").drop_duplicates("ts", keep="first").set_index("ts")[pc]
    d = d.mask((d < 0) | (d > C.MAX_PLAUSIBLE_W))
    r = d.resample(C.RESAMPLE).mean()
    filled = r.interpolate(limit=C.MAX_FILL_MIN, limit_area="inside")
    out = filled.copy()
    out["was_filled"] = r[pc].isna().any(axis=1) & filled[pc].notna().all(axis=1)
    out["long_gap"] = filled[pc].isna().any(axis=1)
    return out


def flag_flatlines(s, min_minutes):
    """CLEAN data forward-fills NaN, so an outage looks like an exactly constant aggregate. Flag constant runs >= min_minutes."""
    same = s.diff().abs().lt(1e-6)
    run_id = (~same).cumsum()
    run_len = same.groupby(run_id).transform("sum") + 1
    return ((run_len >= min_minutes) & s.notna())
