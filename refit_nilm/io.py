"""Finding and loading REFIT files."""
import re
from pathlib import Path
import numpy as np
import pandas as pd
from . import config as C


def find_house_file(root, house, clean):
    """Locate House<N> csv under root (robust to folder layout / _Part1/_Part2 naming; prefers Part2 = NaN not zero)."""
    pat = re.compile(rf"^{'clean_' if clean else '(raw_)?'}house_?{house}(_part\d)?\.csv$", re.I)
    hits = [p for p in Path(root).rglob("*.csv") if pat.match(p.name)]
    if not hits:
        return None
    hits.sort(key=lambda p: ("part2" not in p.name.lower(), len(str(p))))
    return hits[0]


def _col(df_cols, name):
    for c in df_cols:
        if c.strip().lower() == name.lower():
            return c
    for c in df_cols:
        if name.lower() in c.strip().lower():
            return c
    raise KeyError(f"column like '{name}' not found in {list(df_cols)}")


def load_raw_house(path):
    """Raw file -> DataFrame with a UTC 'ts' column, Aggregate, Appliance1..9 (NaNs kept as NaN)."""
    df = pd.read_csv(path)
    unix = _col(df.columns, "unix")
    out = pd.DataFrame({"ts": pd.to_datetime(df[unix], unit="s", utc=True)})   # Unix is UTC: avoids DST ambiguity of the text time
    for c in df.columns:
        if re.match(r"(aggregate|appliance\d)", c.strip(), re.I):
            out[c.strip().capitalize()] = pd.to_numeric(df[c], errors="coerce")
    return out


def load_clean_house(path, house, channel=None):
    """CLEAN file -> 1-minute frame: Aggregate, WM (washer), Issues, flat (forward-filled suspect), missing, usable."""
    from .cleaning import flag_flatlines
    ch = channel or C.WASHER_CHANNEL[house]
    head = pd.read_csv(path, nrows=0).columns
    unix, agg, wm = _col(head, "unix"), _col(head, "aggregate"), _col(head, f"appliance{ch}")
    cols = [unix, agg, wm] + ([c for c in head if c.strip().lower() == "issues"])
    df = pd.read_csv(path, usecols=cols)
    ts = pd.to_datetime(df[unix], unit="s", utc=True)
    out = pd.DataFrame({"Aggregate": df[agg].values, "WM": df[wm].values,
                        "Issues": df["Issues"].values if "Issues" in df.columns else 0}, index=ts)
    out = out[~out.index.duplicated(keep="first")].sort_index()
    m = out.resample(C.RESAMPLE).agg({"Aggregate": "mean", "WM": "mean", "Issues": "max"})
    m["missing"] = m["Aggregate"].isna() | m["WM"].isna()
    m["flat"] = flag_flatlines(m["Aggregate"], C.FLAT_MIN)
    m["issue"] = m["Issues"].fillna(0) > 0
    m["usable"] = ~(m["missing"] | m["flat"] | m["issue"])
    return m
