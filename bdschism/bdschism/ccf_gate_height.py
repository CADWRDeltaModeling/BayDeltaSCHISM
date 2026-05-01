# -*- coding: utf-8 -*-
"""
Estimate Clifton Court Forebay Gate opening height.

This module provides functions to estimate the gate opening height for Clifton Court Forebay
based on SWP export, eligible intervals for opening, priority level, maximum gate height allowed,
OH4 stage level, and CVP pump rate for a given period.
"""

import pandas as pd
from vtools.functions.unit_conversions import M2FT, FT2M, CMS2CFS
from vtools import days, hours ,minutes, divide_interval
from dms_datastore.read_ts import read_ts
from dms_datastore.read_multi import read_ts_repo
from vtools.functions.filter import cosine_lanczos
from vtools.functions.coarsen import ts_coarsen

import schimpy.param as parms
from schimpy.th_io import read_th
import numpy as np
import numba
from vtools.functions import tidalhl
import os
import math
import matplotlib.pyplot as plt
import click
import glob


Q_NORM = 5000.0

OH4_SF_COEF = 1.057768
OH4_SJR_EXCESS_COEF = 0.237763
OH4_SJR_THRESHOLD = 2500.0

# Fixed intercept from the fit. This replaces per-window mean removal.
OH4_SUB_INTERCEPT = -3.716825

ccf_A = 91868000  # area of ccf forbay above 0 navd 88 in ft^2
ccf_reference_level = 2.0  # navd 88 in ft

# NOTE:
# SFFPX is shifted by ~8.5 hours here to align tidal phase for priority logic.
# The same shifted series is passed into OH4 prediction, where an additional
# ~150-minute lag is applied to the subtidal component. Total effective shift
# for OH4 subtidal is therefore ~11 hours.
sffpx_level_shift_h = minutes(30+8*60)


def flow_to_priority(
    flow, breaks=[-100, 2000, 4000.0, 9000.0, 99999.0], labels=[1, 2, 3, 4]
):
    """Convert export flows to priorities based on numerical brackets with breaks.
    Labels must be integers"""
    priority = pd.cut(
        flow, breaks, labels=labels  # These are the boundaries between priorities
    ).astype(int)
    priority.name = "priority"
    return priority


def flow_to_max_gate(
    flow, breaks=[-100, 400, 1200, 3000.0, 4000, 99999.0], labels=[3, 5, 8, 10, 16]
):
    """Convert export flows to max gate height on numerical brackets with breaks."""
    gmax = pd.cut(flow, breaks, labels=labels)
    gmax.name = "max_gate"
    return gmax


def create_priority_series(p1, p2, p3, p4, priority, stime, etime):
    """Choose priorities day-by-day based on the value of the priority argument"""
    pgate = pd.concat([p1, p2, p3, p4], axis=1)[stime:etime]
    pgate.columns = pgate.columns.map(int)  # has to be integer
    priority2 = priority.loc[pgate.index.date]
    pgate = pgate.ffill()
    pgate2 = pgate.stack()
    lookup = pd.MultiIndex.from_arrays([pgate.index, priority2.values])
    pgate2.name = "op"
    pgate3 = pgate2.reindex(lookup).dropna()
    pgate3a = pgate3.loc[pgate3 != pgate3.shift(1)]
    pgate4 = pgate3a.reset_index()
    pgate4 = pgate4.set_index("DATETIME").rename(columns={"level_1": "priority"})
    pgate4.index.names = ["Datetime"]
    # idx= pgate4.index.to_series().diff() > Timedelta('1 days 00:00:00')
    # pgate5 = pgate4.iloc[idx]

    return pgate4


def make_priorities(input_tide, stime, etime, save_intermediate=False):
    """
    Function that makes the priorities schedule time series based on the predicted tide at San Francisco.

    Parameters
    ----------

    input_tide : :py:class:`Series <pandas:pandas.Series>`
        Time series of the Predicted tide at SF in LST
        The time series should be taken from the datastore (water level in m, NAVD88). Headers: datetime,predicted_m,elev_m.
    stime: :py:class:`pd.Timestamp`
        start time.
    etime: :py:class:`pd.Timestamp`
        end time.

    Output: 3 irregular time series that contain the schedule for the priority 1, 2 and 3.
    """

    print("Making priorities from tide")

    s = input_tide[stime:etime]
    if isinstance(s, pd.Series):
        sframe = s.to_frame()
    else:
        sframe = s
    
    # Find minimum and maximums
    # SFFPX is pre-filtered upstream; find_peaks on sequential 25h windows
    # is much faster than the default rolling method for long series.
    sh, sl = tidalhl.get_tidal_hl(sframe, method="find_peaks")  # Get Tidal highs and lows
    sh = pd.concat([sh, tidalhl.get_tidal_hh_lh(sh)], axis=1)
    sh.columns = ["max", "max_name"]
    sl = pd.concat([sl, tidalhl.get_tidal_ll_hl(sl)], axis=1)
    sl.columns = ["min", "min_name"]


    # --------  flag open and close portions - OG Priority 3
    # when it opens
    idx1 = sl[sl["min_name"] == "LL"].index + pd.Timedelta("1h")
    idx2 = sh[sh["max_name"] == "HH"].index - pd.Timedelta("1h")
    idx3 = sh[sh["max_name"] == "LH"].index - pd.Timedelta(
        "1h"
    )  # This is so it opens during the HL-LH-HL sequence
    ci = idx1.union(idx2).union(idx3)
    opens = pd.DataFrame(data=np.ones(len(ci)), index=ci)


    # when it closes
    idx1 = sl[sl["min_name"] == "HL"].index + pd.Timedelta("2h")
    idx2 = sl[sl["min_name"] == "LL"].index - pd.Timedelta("2h")
    closes = pd.DataFrame(data=np.zeros(len(sl)), index=idx1.union(idx2))

    prio3_ts = opens.squeeze().combine_first(closes.squeeze()).to_frame()
    prio3_ts.columns = [3]
    prio3_ts.index.name = "DATETIME"
    prio3_ts = prio3_ts[prio3_ts[3] != prio3_ts[3].shift()]
    prio3_ts.head()

    # ------- flag open and close portions - Priority 2

    # when it opens
    idx1 = sl[sl["min_name"] == "LL"].index + pd.Timedelta("1h")
    idx2 = sh[sh["max_name"] == "HH"].index - pd.Timedelta("1h")
    idx3 = sh[sh["max_name"] == "LH"].index - pd.Timedelta(
        "1h"
    )  # This is so it opens during the HL-LH-HL sequence
    ci = idx1.union(idx2).union(idx3)
    opens = pd.DataFrame(data=np.ones(len(ci)), index=ci)
    opens.head()

    # when it closes
    idx1 = sl[sl["min_name"] == "HL"].index - pd.Timedelta("1h")
    idx2 = sl[sl["min_name"] == "LL"].index - pd.Timedelta("2h")
    closes = pd.DataFrame(data=np.zeros(len(sl)), index=idx1.union(idx2))

    prio2_ts = opens.squeeze().combine_first(closes.squeeze()).to_frame()
    prio2_ts.columns = [2]
    prio2_ts.index.name = "DATETIME"
    prio2_ts = prio2_ts[prio2_ts[2] != prio2_ts[2].shift()]
    prio2_ts.head()

    # ------ flag open and close portions - Priority 1

    # when it opens
    idx1 = sh[sh["max_name"] == "LH"].index + pd.Timedelta("1h")
    idx2 = sh[sh["max_name"] == "HH"].index + pd.Timedelta("1h")
    ci = idx1.union(idx2)
    opens = pd.DataFrame(data=np.ones(len(ci)), index=ci)

    # when it closes
    idx1 = sl[sl["min_name"] == "HL"].index - pd.Timedelta("1h")
    idx2 = sl[sl["min_name"] == "LL"].index - pd.Timedelta("2h")
    closes = pd.DataFrame(data=np.zeros(len(sl)), index=idx1.union(idx2))

    prio1_ts = opens.squeeze().combine_first(closes.squeeze()).to_frame()
    prio1_ts.columns = [1]
    prio1_ts.index.name = "DATETIME"
    prio1_ts = prio1_ts[prio1_ts[1] != prio1_ts[1].shift()]
    prio1_ts.head()

    p4 = (
        prio1_ts.rename(columns={1: 4}).resample("1D").mean() * 0 + 1
    )  # Priority 4 is when exports are so large that gates are always open. 1 value per day.

    if save_intermediate:
        save_prio_ts("prio_ts", s, prio1_ts, prio2_ts, prio3_ts, p4)

    return s, prio1_ts, prio2_ts, prio3_ts, p4


def save_prio_ts(tsdir, tide_lagged, p1, p2, p3, p4):

    if not os.path.exists(tsdir):
        os.makedirs(tsdir)

    print("saving prio time series to", tsdir)
    p1.to_csv(os.path.join(tsdir, "p1.csv"))
    p2.to_csv(os.path.join(tsdir, "p2.csv"))
    p3.to_csv(os.path.join(tsdir, "p3.csv"))
    p4.to_csv(os.path.join(tsdir, "p4.csv"))
    tide_lagged.to_csv(os.path.join(tsdir, "tide_lagged.csv"))


def export_lookup(x):

    xp = [-100, 400, 1200, 2000, 3000, 4000, 9000, 99999]
    p = [1, 1, 1, 2, 2, 3, 4]
    max_g = [3, 5, 8, 8, 10, 16, 16]

    if (x >= xp[0]) & (x < xp[1]):
        prio = p[0]
        max_gate = max_g[0]
    if (x >= xp[1]) & (x < xp[2]):
        prio = p[1]
        max_gate = max_g[1]
    if (x >= xp[2]) & (x < xp[3]):
        prio = p[2]
        max_gate = max_g[2]
    if (x >= xp[3]) & (x < xp[4]):
        prio = p[3]
        max_gate = max_g[3]
    if (x >= xp[4]) & (x < xp[5]):
        prio = p[4]
        max_gate = max_g[4]
    if (x >= xp[5]) & (x < xp[6]):
        prio = p[5]
        max_gate = max_g[5]
    if (x >= xp[6]) & (x < xp[7]):
        prio = p[6]
        max_gate = max_g[6]

    print("Export is", x, "CFS--> Priority =", prio, " Max GH =", max_gate)


def gen_prio_for_varying_exports(input_tide, export_df):

    dt = export_df.index.inferred_freq
    export_df.where(export_df.values > 0, 0, inplace=True)
    if dt == "D":
        export_1day = export_df.squeeze()  # the original data is daily
        export_15min = export_df.resample("15min").ffill()
        print("The input export dt is Daily")
    elif dt == "15min":
        export_1day = (
            export_df.resample("D").mean().squeeze()
        )  # the original data is 15 minutes
        export_15min = export_df.squeeze()
        print("The input export ts dt is 15 Min")
    else:
        print("Cannot infer dt for the Export time series")

    stimee = export_df.index[0]
    etimee = export_df.index[-1]

    wl_df = input_tide
    stime = max(wl_df.index[0], stimee)
    etime = min(wl_df.index[-1], etimee)

    tide_lag, p1, p2, p3, p4 = make_priorities(input_tide, stime, etime)

    # export flows to priorities type
    priority = flow_to_priority(export_1day)
    # make the priority schedule irr ts
    priority_df = create_priority_series(p1, p2, p3, p4, priority, stime, etime)
    # assign max gate heights base on export level (sipping)
    max_gate_height = flow_to_max_gate(export_1day).astype("float64")

    return priority_df, max_gate_height


def get_flux_ts_cfs(s1, s2, flux):
    """
    Retrieve SWP, CVP, and SJR flows from a SCHISM flux.th file in cfs.

    SJR is sign-adjusted so positive values represent San Joaquin River inflow.
    """
    flux_ts = read_th(flux).loc[s1:s2]

    required = ["swp", "cvp", "sjr"]
    missing = [c for c in required if c not in flux_ts.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {flux!r}: {missing}. "
            f"Found: {flux_ts.columns.tolist()}"
        )

    out = flux_ts[required].copy() * CMS2CFS
    out["sjr"] = -out["sjr"]
    return out



def sffpx_level(sdate, edate, sffpx_datasrc):
    margin = days(5)
    s = pd.to_datetime(sdate) - margin
    e = pd.to_datetime(edate) + margin

    matches = (
        glob.glob(sffpx_datasrc) if any(ch in sffpx_datasrc for ch in "*?[]") else []
    )
    is_file_like = os.path.exists(sffpx_datasrc) or len(matches) > 0

    if is_file_like:
        print("Reading sffpx data from file(s):", sffpx_datasrc)
        sf = read_ts(sffpx_datasrc, start=s, end=e, force_regular=True)
    else:
        try:
            print("Reading sffpx data from repository:", sffpx_datasrc)
            sf = read_ts_repo(
                "sffpx",
                "elev",
                repo=sffpx_datasrc,
                start=s,
                end=e,
                force_regular=True,
            )
        except Exception as exc:
            print(exc)
            raise ValueError(
                f"Could not interpret --sffpx-datasrc={sffpx_datasrc!r} "
                "as an existing file/pattern or as a repo name for "
                "read_ts_repo('sffpx', 'elev', repo=...)."
            ) from exc

    sf.columns = ["elev"]
    if sf.isnull().any(axis=None):
        raise ValueError("Error: sffpx data contains NaN values. This may be an attempt to read straight from a repo or web site."
            "Please  learn how to acquire a properly vetted and filled series. "
            "Make sure you understand the severe caveats on SF tidal data particularly in 2024. Vetted and filled series are available"
        )
    return sf


def predict_oh4_level(s1, s2, oh4_astro_ts, sffpx_elev_ts, sjr_ts):
    """Predict total OH4 stage using harmonic tide, SFFPX subtidal, and SJR flow."""
    sffpx = sffpx_elev_ts

    # SFFPX input is meters in the processed repo; the OH4 fit is in feet.
    sffpx_subtide = cosine_lanczos(sffpx * M2FT, cutoff_period="40h")
    sffpx_subtide = sffpx_subtide.resample("15min").ffill()

    # Existing workflow applies the additional 150-min subtidal lag here.
    lag = divide_interval(minutes(150), sffpx_subtide.index.freq)
    sffpx_subtide = sffpx_subtide.shift(lag).squeeze()

    sjr = sjr_ts.resample("15min").ffill()
    sjr_excess_norm = np.maximum(sjr - OH4_SJR_THRESHOLD, 0.0) / Q_NORM

    parts = pd.concat(
        [
            oh4_astro_ts.rename("oh4_astro"),
            sffpx_subtide.rename("sffpx_subtide"),
            sjr_excess_norm.rename("sjr_excess_norm"),
        ],
        axis=1,
    ).dropna()

    oh4_sub_predicted = (
        OH4_SUB_INTERCEPT
        + OH4_SF_COEF * parts["sffpx_subtide"]
        + OH4_SJR_EXCESS_COEF * parts["sjr_excess_norm"]
    )

    oh4_predicted = parts["oh4_astro"] + oh4_sub_predicted
    return oh4_predicted[s1:s2]

def radial_gate_flow_ts(zdown_ts, zup_ts, height_ts, s1, s2, dt):

    t = s1

    tt = []
    flows = []

    while t <= s2:
        tt.append(t)
        loc = zdown_ts.index.searchsorted(t) - 1
        zdown = zdown_ts.iloc[loc, 0]
        loc = zup_ts.index.searchsorted(t) - 1
        zup = zup_ts.iloc[loc]
        loc = height_ts.index.searchsorted(t) - 1
        h = height_ts.iloc[loc]
        flow = radial_gate_flow(zdown, zup, h)
        flows.append(flow)
        t += dt
        # print(t,flow)
    df = pd.DataFrame(flows, index=tt, columns=["ccfb_flow"])

    return df


def remove_continuous_duplicates(df, column_name):
    """
    Removes consecutive duplicate values in a specified column of a Pandas DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to check for duplicates.

    Returns:
        pd.DataFrame: A new DataFrame with consecutive duplicates removed.
    """
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in DataFrame.")

    mask = df[column_name].diff().ne(0)
    return df[mask]


def radial_gate_flow(zdown, zup, height, n=5, width=None, zsill=None):
    """
    compuate ccf radial gate flow in cubic feet/s

    Args:
        n : number of gate opened
        width: width of the each gate (default: 6.096 * M2FT)
        zup: upstream water elevation
        zsill: elevation of gate sill (default: -4.044 * M2FT)
        zdown: downstream water elev
        height: gate opening height
    Returns:
        gate flow in cfs
    """
    # Set default values here to avoid issues with mocked imports during doc build
    if width is None:
        width = 6.096 * M2FT
    if zsill is None:
        zsill = -4.044 * M2FT

    if zup < zdown:
        return 0
    d = 0.67  # constant 1
    s = 0.67  # constant 2
    g = 32.2  # gravity
    d = 0.75
    s = 0.8

    r = min(1.0, height / (zup - zsill))
    c = d + s * r
    A = min(height, zup - zsill) * width
    q = n * c * A * np.sqrt(2 * g * (zup - zdown))
    return q


def draw_down_regression(cvp, qin):
    qnormal = 5000.0
    draw_down = -0.0547 + cvp * 0.1815 / qnormal + qin * 0.1413 / qnormal
    return draw_down


def simple_mass_balance(export, zup, zin0, height, dt, vt):
    qin0 = radial_gate_flow(zin0, zup, height, 5)
    zin_predict = zin0 - (export - qin0) * dt.total_seconds() / ccf_A
    qin1 = radial_gate_flow(zin_predict, zup, height, 5)
    qint = 0.5 * (qin0 + qin1)
    zin = zin0 - (export - qint) * dt.total_seconds() / ccf_A
    vt = vt - (export - qint) * dt.total_seconds()
    return zin, vt, qint


@numba.jit(nopython=True)
def _radial_gate_flow_scalar(zdown, zup, height, n, width, zsill):
    """Pure-scalar gate flow for numba nopython JIT inside the tight loop."""
    if zup < zdown:
        return 0.0
    d = 0.75
    s = 0.8
    g = 32.2
    r = min(1.0, height / (zup - zsill))
    c = d + s * r
    A = min(height, zup - zsill) * width
    q = n * c * A * math.sqrt(2.0 * g * (zup - zdown))
    return q


@numba.jit(nopython=True)
def _simple_mass_balance_scalar(export, zup, zin0, height, dt_sec, vt, ccf_A_val, width, zsill):
    """Scalar mass balance with pre-computed dt_sec and constants for numba."""
    qin0 = _radial_gate_flow_scalar(zin0, zup, height, 5, width, zsill)
    zin_predict = zin0 - (export - qin0) * dt_sec / ccf_A_val
    qin1 = _radial_gate_flow_scalar(zin_predict, zup, height, 5, width, zsill)
    qint = 0.5 * (qin0 + qin1)
    zin = zin0 - (export - qint) * dt_sec / ccf_A_val
    vt = vt - (export - qint) * dt_sec
    return zin, vt, qint


def gen_gate_height(
    export_ts, priority, max_height, oh4_level, cvp_ts, inside_level0, s1, s2, dt
):
    """
    Estimate Clifton Court Forebay Gate opening height.

    This function estimates the opening height of the Clifton Court Forebay (CCFB) radial gates
    based on SWP export, eligible intervals for opening and priority level, maximum gate height allowed,
    OH4 stage level, CVP pump rate, and other operational rules for a given period.

    Gate Opening Conditions
    -----------------------
    - **Priority Eligibility**: The gate opens only if priority eligibility criteria are met.
    - **Water Level Difference**: The gate opens if the water level outside the forebay is higher than the water level inside.

    Early Gate Closure
    ------------------

    The gate will close early if the volume of water above the 2 ft contour is sufficient to cover
    the remaining water allocation for the day. This simulates field operations where operators aim to
    maintain water elevation as close to 2 ft as possible.

    Gate Remains Open
    -----------------

    The gate will remain open if the volume of water above the 2 ft contour is insufficient to cover
    the daily allocation, preventing the water level inside the forebay from dropping too low.

    Gate Height Calculation
    -----------------------
    - The default gate height is 16 ft, but a maximum height based on export level is applied.
    - The height is adjusted to prevent flow from exceeding 12,000 cfs, reflecting operational constraints.
    - The gate height is calculated using a simplified version of the flow rating equation:

        Gate Height = 11 × (Head)^-0.3 - 0.5

      where Head = Water level upstream - Water level in the reservoir.

    Parameters
    ----------
    export_ts : pandas.Series
        Series of SWP pumping rate.
    priority : pandas.DataFrame
        CCFB gate operation priority series, must have 'priority' and 'op' columns.
    max_height : pandas.DataFrame
        CCFB gate maximum allowed open height.
    oh4_level : pandas.DataFrame
        OH4 surface stage, predicted or historical.
    cvp_ts : pandas.DataFrame
        CVP pumping rate.
    inside_level0 : float
        Initial CCFB surface stage.
    s1 : pd.Timestamp
        Start time.
    s2 : pd.Timestamp
        End time.
    dt : pd.Timedelta
        Output time step.

    Returns
    -------
    gate_height : pandas.DataFrame
        Radial gate height time series.
    zin : pandas.DataFrame
        Predicted forebay inside water level time series.
    """
    t = s1
    relax_period = minutes(6)
    smooth_steps = int(relax_period / dt)
    height = 0.0
    v0 = (inside_level0 - ccf_reference_level) * ccf_A
    vt = v0
    accumulate_export = 0.0
    zin = inside_level0
    export_ts_freq = export_ts.index[1] - export_ts.index[0]
    export_ts_daily = (export_ts.resample("D").sum()) * export_ts_freq.total_seconds()
    prio = 0
    op = 0
    draw_down = 0.0

    # Pre-extract numpy arrays for fast lookup inside the tight loop.
    # pandas .iloc inside a 2-min loop over 16+ years is ~100x slower than
    # direct numpy array indexing with np.searchsorted on int64 timestamps.
    #
    # IMPORTANT: pandas 2.x uses datetime64[us] by default, so .asi8 returns
    # microseconds.  pd.Timestamp.value always returns nanoseconds.  We
    # normalize all .asi8 arrays to nanoseconds here to match t_ns.
    _asi8_to_ns = pd.Timestamp(export_ts.index[0]).value // export_ts.index.asi8[0]
    export_idx = export_ts.index.asi8 * _asi8_to_ns
    export_val = export_ts.to_numpy(dtype=float)
    oh4_idx = oh4_level.index.asi8 * _asi8_to_ns
    oh4_val = oh4_level.to_numpy(dtype=float)
    priority_idx = priority.index.asi8 * _asi8_to_ns
    priority_val = priority["priority"].to_numpy(dtype=float)
    op_val = priority["op"].to_numpy(dtype=float)
    maxh_idx = max_height.index.asi8 * _asi8_to_ns
    maxh_val = max_height.to_numpy(dtype=float)
    cvp_idx = cvp_ts.index.asi8 * _asi8_to_ns
    cvp_val = cvp_ts.to_numpy(dtype=float)
    daily_idx = export_ts_daily.index.asi8 * _asi8_to_ns
    daily_val = export_ts_daily.to_numpy(dtype=float)
    dt_sec = dt.total_seconds()
    _width = 6.096 * M2FT
    _zsill = -4.044 * M2FT

    # Integer-nanosecond time loop: eliminates pd.Timestamp(t).value and
    # datetime arithmetic from the hot path (~4M iterations for 16 years).
    dt_ns = int(dt_sec * 1_000_000_000)
    day_ns = 86400 * 1_000_000_000
    t_ns = np.int64(pd.Timestamp(s1).value)
    s2_ns = np.int64(pd.Timestamp(s2).value)

    # Pre-allocate output arrays.  Upper bound: one row per dt step plus
    # some headroom for relax ramps.
    _max_steps = int((s2 - s1) / dt) + 2 * smooth_steps + 1
    height_arr = np.empty(_max_steps, dtype=float)
    tt_arr = np.empty(_max_steps, dtype='int64')
    zin2_arr = np.empty(_max_steps, dtype=float)
    zt2_arr = np.empty(_max_steps, dtype='int64')
    zin_arr = np.empty(_max_steps, dtype=float)
    zt_arr = np.empty(_max_steps, dtype='int64')
    n_out = 0       # index into height_arr / tt_arr
    n_zin2 = 0      # index into zin2_arr / zt2_arr
    n_zin = 0       # index into zin_arr / zt_arr

    while t_ns < s2_ns:
        zin2 = 2.0 + vt / ccf_A
        zin2_arr[n_zin2] = zin2
        zt2_arr[n_zin2] = t_ns
        n_zin2 += 1

        tday_ns = t_ns - (t_ns % day_ns)
        tday1_ns = tday_ns + day_ns
        tleft_ns = tday1_ns - t_ns
        nleft = int(tleft_ns // dt_ns)

        if t_ns == tday_ns:
            accumulate_export = 0.0

        loc = np.searchsorted(export_idx, t_ns) - 1
        export = export_val[loc]
        loc_day = np.searchsorted(daily_idx, tday_ns)
        if loc_day >= len(daily_val):
            loc_day = len(daily_val) - 1
        export_daily = daily_val[loc_day]
        loc = np.searchsorted(priority_idx, t_ns) - 1
        prio = priority_val[loc]
        op = op_val[loc]
        loc = np.searchsorted(oh4_idx, t_ns) - 1
        zup = oh4_val[loc] - draw_down
        loc = np.searchsorted(maxh_idx, t_ns) - 1
        max_h = maxh_val[loc]

        # if (prio < 1) or (op == 0) or ((zup - zin) < 0.0):
        if (prio < 1) or (op == 0):
            height_target = 0.0
            if height == height_target:
                # Single closed step
                height_arr[n_out] = height
                tt_arr[n_out] = t_ns
                n_out += 1
                # mass balance for this single step
                loc = np.searchsorted(oh4_idx, t_ns) - 1
                zup = oh4_val[loc] - draw_down
                zin, vt, qint = _simple_mass_balance_scalar(
                    export, zup, zin, height, dt_sec, vt, ccf_A, _width, _zsill)
                accumulate_export += export * dt_sec
                zin_arr[n_zin] = zin
                zt_arr[n_zin] = t_ns
                n_zin += 1
                loc = np.searchsorted(cvp_idx, t_ns)
                if loc >= len(cvp_val):
                    loc = len(cvp_val) - 1
                cvp = cvp_val[loc]
                draw_down = draw_down_regression(cvp, qint)
                t_ns += dt_ns
            else:  # closing smoothly
                relax_n = smooth_steps
                relax_step = -1.0 / relax_n
                relax_height_t = np.arange(1.0, relax_step, relax_step) * height
                relax_height_t[-1] = height_target
                relax_n = len(relax_height_t) - 1
                relax_height = relax_height_t[1:]
                # Write height ramp
                for ri in range(relax_n):
                    tt_arr[n_out] = t_ns + ri * dt_ns
                    height_arr[n_out] = relax_height[ri]
                    n_out += 1
                # Mass balance over the ramp
                ramp_t_ns = t_ns
                for ri in range(relax_n):
                    if ramp_t_ns == tday1_ns:
                        accumulate_export = 0.0
                    loc = np.searchsorted(export_idx, ramp_t_ns) - 1
                    export = export_val[loc]
                    loc = np.searchsorted(oh4_idx, ramp_t_ns) - 1
                    zup = oh4_val[loc] - draw_down
                    zin, vt, qint = _simple_mass_balance_scalar(
                        export, zup, zin, relax_height[ri], dt_sec, vt, ccf_A, _width, _zsill)
                    accumulate_export += export * dt_sec
                    zin_arr[n_zin] = zin
                    zt_arr[n_zin] = ramp_t_ns
                    n_zin += 1
                    loc = np.searchsorted(cvp_idx, ramp_t_ns)
                    if loc >= len(cvp_val):
                        loc = len(cvp_val) - 1
                    cvp = cvp_val[loc]
                    draw_down = draw_down_regression(cvp, qint)
                    ramp_t_ns += dt_ns
                t_ns = ramp_t_ns

            height = height_target
            continue

        export_remain = export_daily - accumulate_export

        if vt > export_remain:
            height_target = 0.0
            ## smoothing closing gate in relax period
            relax_n = smooth_steps
            relax_step = -1.0 / relax_n
            relax_height = np.arange(1.0, 0, relax_step) * height
            left_height_arr = np.zeros(nleft)
            relax_n = len(relax_height) - 1
            if nleft >= relax_n:
                left_height_arr[:relax_n] = relax_height[1:]

            for li in range(nleft):
                height_arr[n_out] = left_height_arr[li]
                tt_arr[n_out] = t_ns + li * dt_ns
                n_out += 1

            vt = vt - export_remain
            accumulate_export = accumulate_export + export_remain
            zin = ccf_reference_level + vt / ccf_A

            t_ns = tday1_ns
            height = height_target
            zin_arr[n_zin] = zin
            zt_arr[n_zin] = t_ns
            n_zin += 1
            loc = np.searchsorted(cvp_idx, t_ns)
            if loc >= len(cvp_val):
                loc = len(cvp_val) - 1
            cvp = cvp_val[loc]
            draw_down = draw_down_regression(cvp, 0)
            continue

        if zup - zin <= 0.0:
            height_target = max_h
        else:
            height_target = min(11.0 * math.pow(zup - zin, -0.3) - 0.5, max_h)

        if height == 0:
            relax_n = smooth_steps
        else:
            relax_n = 1

        height_step = (height_target - height) / relax_n

        for i in range(relax_n):
            height_temp = height + height_step * (i + 1)
            loc = np.searchsorted(oh4_idx, t_ns) - 1
            zup = oh4_val[loc] - draw_down
            loc = np.searchsorted(export_idx, t_ns) - 1
            export = export_val[loc]
            zin, vt, qint = _simple_mass_balance_scalar(export, zup, zin, height_temp, dt_sec, vt, ccf_A, _width, _zsill)
            accumulate_export = accumulate_export + export * dt_sec
            height_arr[n_out] = height_temp
            tt_arr[n_out] = t_ns
            n_out += 1
            zin_arr[n_zin] = zin
            zt_arr[n_zin] = t_ns
            n_zin += 1
            loc = np.searchsorted(cvp_idx, t_ns) - 1
            cvp = cvp_val[loc]
            draw_down = draw_down_regression(cvp, qint)
            t_ns += dt_ns
            ## if time passes the next day, reset the accumulate export
            if t_ns == tday1_ns:
                accumulate_export = 0.0
        height = height_target

    # Build DataFrames from pre-allocated arrays
    tt_index = pd.DatetimeIndex(tt_arr[:n_out], dtype='datetime64[ns]')
    df = pd.DataFrame(height_arr[:n_out], index=tt_index, columns=["ccfb_height"])
    zt2_index = pd.DatetimeIndex(zt2_arr[:n_zin2], dtype='datetime64[ns]')
    zin_df2 = pd.DataFrame(zin2_arr[:n_zin2], index=zt2_index, columns=["ccfb_interior_surface"])
    return df, zin_df2


def process_height(s1, s2, swp_ts,cvp_ts, sjr_ts, oh4_astro_ts, sffpx_elev_ts, save_intermediate=False):
    """
    Create a ccfb radial gate height time series file

    Parameters
    ----------
    s1 : :py:class:`datetime.datetime`
        start time.
    s2 : :py:class:`datetime.datetime`
        end time.
    swp_ts : :py:class:`pandas.dataframe`
        swp export time series.
    cvp_ts : :py:class:`pandas.dataframe`
        cvp export time series.
    oh4_astro_ts : :py:class:`pandas.dataframe`
        OH4 astronomic tide time series.
    sffpx_elev_ts : :py:class:`pandas.dataframe`
        sffpx elevation time series.
   

    Returns
    -------
    sim_gate_height : :py:class:`pandas.DataFrame`
        predicted radial gate height
    zin_df : :py:class:`pandas.DataFrame`
        predicted ccfb interior surface stage.
    """

    margin = days(3)
    #export_ts, cvp_ts = get_export_ts_cfs(s1 - margin, s2 + margin, export)
    export_ts_daily_average = swp_ts.resample("D").mean()
    inside_level0 = 2.12  # in feet
    ## vtools time delta deosn't have total_seconds, so we use pandas timedelta here
    dt = pd.Timedelta(minutes=2)

    priority, max_height = gen_prio_for_varying_exports(
        sffpx_elev_ts, export_ts_daily_average
    )
    print("Priority generation complete")

    if save_intermediate:
        full_path = os.path.abspath(os.path.join("./prio_ts", "priority.csv"))
        priority.to_csv(
            full_path,
            sep=" ",
            header=True,
            float_format="%.3f",
            date_format="%Y-%m-%dT%H:%M",
        )
    oh4_predict = predict_oh4_level(
        s1 - margin,
        s2 + margin,
        oh4_astro_ts,
        sffpx_elev_ts,
        sjr_ts,
    )
    print("OH4 prediction complete")

    print(f"Starting water balance loop: {s1} to {s2}")
    sim_gate_height, zin_df = gen_gate_height(
        swp_ts, priority, max_height, oh4_predict, cvp_ts, inside_level0, s1, s2, dt
    )
    print("Water balance loop complete")

    return sim_gate_height, zin_df


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Generate Clifton Court Forebay gate height from predicted tide and export flows.",
)
@click.option("--sdate", default=None, help="Start date, e.g. 2024-04-16.")
@click.option("--edate", default=None, help="End date, e.g. 2025-01-01.")
@click.option(
    "--output",
    type=click.Path(),
    default="./ccfb_gate_syn.th",
    show_default=True,
    help="Output path for predicted gate height.",
)
@click.option(
    "--oh4-astro-datasrc",
    type=str,
    required=True,
    help="OH4 astronomical source: file or pattern.",
)
@click.option(
    "--export-datasrc",
    type=str,
    required=True,
    help="Export source, typically flux.th.",
)
@click.option(
    "--sffpx-datasrc",
    type=str,
    required=True,
    help="SFFPX elevation source: file/pattern or repo name such as screened.",
)
@click.option(
    "--length-unit",
    type=click.Choice(["ft", "m"], case_sensitive=False),
    default="ft",
    show_default=True,
    help="Output gate-height length unit.",
)
@click.option("--plot", is_flag=True, default=False, help="Plot predicted gate height.")
@click.option(
    "--save-intermediate",
    "-si",
    is_flag=True,
    default=False,
    help="Save intermediate products such as priority time series.",
)
def ccf_gate_cli(
    sdate,
    edate,
    output,
    oh4_astro_datasrc,
    export_datasrc,
    sffpx_datasrc,
    length_unit,
    plot,
    save_intermediate,
):
    if sdate is None or edate is None:
        raise ValueError("Start date and end date must be provided.")

    sffpx_elev_ts = sffpx_level(sdate, edate, sffpx_datasrc)
    
    s1 = pd.Timestamp(sdate)
    s2 = pd.Timestamp(edate)
    out =get_flux_ts_cfs(s1, s2, export_datasrc)
    swp_ts = out['swp']
    cvp_ts = out['cvp']
    sjr_ts = out['sjr']
    oh4_astro_ts  = read_ts(oh4_astro_datasrc, force_regular=True).squeeze()


    ccf_gate(
        s1,
        s2,
        output,
        oh4_astro_ts,
        swp_ts,
        cvp_ts,
        sjr_ts,        
        sffpx_elev_ts,
        plot,
        save_intermediate,
    )


def ccf_gate(
    sdate,
    edate,
    dest,
    astro_ts,
    swp_ts,
    cvp_ts,
    sjr_ts,
    sffpx_elev_ts,
    plot=False,
    save_intermediate=False,
):
    """
    Generate the predicted gate height for the Clifton Court Forebay.

    Parameters
    ----------
    sdate : datetime.datetime
        Start date .
    edate : datetime.datetime
        End date .
    dest : str
        Destination file where the output file will be saved. ex: "ccfb_gate_syn.th"
    astro_ts : pd.DataFrame
        Astronomical oh4 tide time series required for processing.
    swp_ts : pd.DataFrame
        SWP time series required for height processing.
    cvp_ts : pd.DataFrame
        CVP time series required for height processing.
    sffpx_elev_ts : pd.DataFrame
        SFFPX elevation time series required for height processing.
    plot : bool, optional
        If True, a plot of the predicted gate height will be displayed (default is False).
    save_intermediate : bool, optional
        If True, intermediate results will be saved to files (default is False).

    Returns
    -------
    None
        The function saves the predicted gate height data to a file and optionally displays a plot.

    Notes
    -----
    The output file is saved to the destination file.
    The function processes the height data, removes continuous duplicates, and adds additional
    columns for installation, operation, elevation, and width parameters.
    """

    ## shift sffpx to match tidal phase at ccfb gate
    shift_h = sffpx_level_shift_h
    position_shift = int(shift_h / sffpx_elev_ts.index.freq)
    sffpx_elev_ts = sffpx_elev_ts.shift(position_shift)
    oneday = days(1)
    height, zin = process_height(sdate, edate, swp_ts,cvp_ts, sjr_ts, astro_ts, sffpx_elev_ts)
    #height_t = remove_continuous_duplicates(height, height.columns.tolist()[0])
    print(f"Coarsening {len(height)} rows of 2-min gate height output")
    height_t = ts_coarsen(height, grid="2min",preserve_vals=[0.0],qwidth=0.01,hyst=0.5,heartbeat_freq="60min")
    print(f"Coarsening complete: {len(height_t)} rows retained")
    height_t = height_t * FT2M
    height_t.index.name = "datetime"
    height_t.columns = ["height"]
    dlen = len(height_t)
    height_t.insert(0, "install", dlen * [1])
    height_t.insert(1, "ndup", dlen * [5])
    height_t.insert(2, "op_down", dlen * [1.0])
    height_t.insert(3, "op_up", dlen * [0.0])
    height_t.insert(4, "elev", dlen * [-4.0244])
    height_t.insert(5, "width", dlen * [6.096])

    print(f"Saving predicted gate height file to {dest}")
    height_t[sdate : edate + oneday].to_csv(
        dest,
        sep=" ",
        header=True,
        float_format="%.3f",
        date_format="%Y-%m-%dT%H:%M",
    )

    if plot:
        fig, (ax1) = plt.subplots(1, 1)
        lsyn = ax1.step(
            height_t.index,
            height_t["height"],
            where="post",
            label="ccfb gate height predicted",
        )
        ax1.set_ylabel("Height (m)")
        plt.show()


if __name__ == "__main__":
    ccf_gate_cli()
