#!/usr/bin/env python3
"""
make_south_delta_barrier_status.py

Reads four barrier installation files (space-separated, #-commented) with at least:
  - datetime
  - install
And for Grant Line, an additional weir elevation column (accepts either 'elev_weir' or 'weir_elev').

Computes the per-barrier installation status at midnight (last known value strictly
BEFORE each midnight) and writes a single CSV with per-barrier status plus an ag_count
column.

Special rule for Grant Line:
  If the weir-elevation column exists and is < 0 at a timestamp, treat the instantaneous
  'install' value as 0.5 (partial). This is applied before computing the midnight state.
  (So daily 'grantline' may be 0, 0.5, or 1.0.)

ag_count:
  Sum of the three ag barriers (oldr_tracy, midr, grantline) using their numeric
  daily values (so totals like 2.5 are possible). oldr_head is excluded from ag_count.

Output:
  south_delta_barrier_install_and_count_daily.csv
  Columns: date, oldr_tracy, midr, grantline, oldr_head, ag_count
"""

from pathlib import Path
import pandas as pd

# Input file mapping (edit paths as needed)
PATHS = {
    "oldr_tracy": "oldr_tracy_barrier.th",
    "midr": "midr_weir.th",
    "grantline": "grantline_barrier.th",
    "oldr_head": "oldr_head_barrier.th",
}

def _grantline_adjust(df: pd.DataFrame) -> pd.DataFrame:
    """Grant Line rule:
       - install == 0 → stays 0
       - install == 1 & weir_elev < 0 → 0.5
       - install == 1 & weir_elev > 0 → 1
    """
    df["install"] = pd.to_numeric(df["install"])
    elev = pd.to_numeric(df["elev_weir"])


    df.loc[(df["install"] == 1) & (elev < 0.), "install"] = 0.5
    df.loc[(df["install"] == 1) & (elev > 0.), "install"] = 1.0
    return df

def read_install_series(path: str, name: str) -> pd.Series:
    """Read a barrier file with required headers 'datetime' and 'install'.
    For 'grantline', apply the weir-elevation adjustment (0.5 when elev < 0) if present.
    Returns a time-indexed Series of numeric install values.
    """
    df = pd.read_csv(
        path,
        sep=r"\s+",
        comment="#",
        engine="python"
    )
    if "datetime" not in df.columns or "install" not in df.columns:
        raise ValueError(f"{path} must contain 'datetime' and 'install' columns.")
    df["install"] = df["install"].astype(float)
    if name == "grantline":
        df = _grantline_adjust(df)
    s = pd.Series(df["install"].values, index=pd.to_datetime(df["datetime"], errors="coerce"))
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s

def status_at_midnight(s: pd.Series, days: pd.DatetimeIndex) -> pd.Series:
    """Status at 00:00 of each day = last known value strictly BEFORE that instant."""
    query_times = days - pd.Timedelta(nanoseconds=1)
    vals = s.asof(query_times)
    out = pd.Series(vals.values, index=days)
    return out.fillna(0.0)

def main():
    series_map = {name: read_install_series(path, name) for name, path in PATHS.items()}
    min_dt = min(s.index.min() for s in series_map.values())
    max_dt = max(s.index.max() for s in series_map.values())
    days = pd.date_range(min_dt.floor("D"), (max_dt + pd.Timedelta(days=1)).floor("D"), freq="D")
    daily = pd.DataFrame(index=days)
    for name, s in series_map.items():
        daily[name] = status_at_midnight(s, days)
    daily["ag_count"] = daily[["oldr_tracy", "midr", "grantline"]].sum(axis=1)
    daily.index = daily.index.strftime("%Y-%m-%d")
    daily.index.name = "date"
    out_path = Path("south_delta_barrier_install_and_count_daily.csv")
    daily.to_csv(out_path)
    print(f"Wrote {out_path.resolve()}")

if __name__ == "__main__":
    main()
