from vtools.functions.interpolate import rhistinterp
from vtools.data.vtime import days, minutes
from pyhecdss import get_ts, DSSFile
from pathlib import Path
import pandas as pd
import os


dss_e2_freq = {"1HOUR": "H", "1DAY": "D", "1MON": "M"}


def read_dss(
    filename,
    pathname,
    dt=minutes(15),
    p=2.0,
    start_date=None,
    end_date=None,
):
    """
    Reads in a DSM2 dss file and interpolates
    Outputs an interpolated DataFrame of that variable

    Parameters
    ----------
    filename: str|Path
        Path to the DSS file to read
    pathname: str
        Pathname within the DSS file to read.
        Needs to be in the format '/A_PART/B_PART/C_PART/D_PART/E_PART/F_PART/'
        (e.g. '//RSAN112/FLOW////')
    """
    ts_out_list = []
    col_names = []
    print(f"\t{pathname}")
    if len(pathname.split("/")[1:-1]) != 6:
        raise ValueError(f"Invalid DSS pathname: {pathname}, needs 6 parts (A-F)")
    ts = get_ts(filename, pathname)
    for i, tsi in enumerate(ts):
        ts_path = tsi[0].columns.values[0]
        path_lst = (ts_path).split("/")
        path_e = path_lst[5]
        # Set default start_date and end_date to cover the full period of record if not specified
        tt_full = tsi[0]
        if start_date is None:
            start_date = tt_full.index[0]
        if end_date is None:
            end_date = tt_full.index[-1]
        tt = tt_full[start_date:end_date]
        pidx = pd.period_range(start_date, tt.index[-1], freq=dss_e2_freq[path_e])
        ptt = pd.DataFrame(tt.values[:, 0], pidx)

        # Interpolate with rhistinterp
        if p != 0:
            col_data = rhistinterp(ptt, dt, p=p)
        elif p == 0:
            col_data = rhistinterp(ptt, dt)
        else:
            col_data = tsi[0]
        ts_out_list.append(col_data)
        col_names.append(ts_path)

    if ts_out_list:
        ts_out = pd.concat(ts_out_list, axis=1)
        ts_out.columns = col_names
        ts_out = ts_out.copy()  # Defragment the DataFrame
    else:
        with DSSFile(filename) as dssh:
            dfcat = dssh.read_catalog()
        raise ValueError(
            f"Warning: DSS data not found for {pathname}. Preview of available paths in {filename} are: {dfcat}"
        )

    return ts_out
