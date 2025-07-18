# -*- coding: utf-8 -*-
"""
Estimate Clifton Court Forebay Gate opening height.

This module provides functions to estimate the gate opening height for Clifton Court Forebay
based on SWP export, eligible intervals for opening, priority level, maximum gate height allowed,
OH4 stage level, and CVP pump rate for a given period.
"""
import datetime as dtm
import pandas as pd
from vtools.functions.unit_conversions import M2FT, FT2M
from dms_datastore.read_ts import read_ts
from dms_datastore.read_multi import read_ts_repo
from vtools.functions.filter import cosine_lanczos
from vtools.functions.merge import ts_merge
import schimpy.param as parms
import numpy as np
from vtools.functions import tidalhl
import os
import math
import matplotlib.pyplot as plt
import click

# %% Functions

ccf_A = 91868000  # area of ccf forbay above 0 navd 88 in ft^2
ccf_reference_level = 2.0  # navd 88 in ft


def tlmax(arr):
    """return HH(1) or LH (0)"""
    idx = np.argmax(arr)  # only the first occurence of the maxima is return
    # print(arr,idx)
    return idx


def tlmin(arr):
    """return LL(1) or HL(0)"""
    idx = np.argmin(arr)
    return idx


def get_tidal_hh_lh(sh):
    sth = sh.rolling(2).apply(tlmax, raw=True)
    sth.iloc[0] = (
        0 if sth.iloc[1, 0] > 0 else 1
    )  # fill in the first value based on next value
    return sth.iloc[:, 0].map({np.nan: "", 0: "LH", 1: "HH"}).astype(str)


def get_tidal_ll_hl(sl):
    stl = sl.rolling(2).apply(tlmin, raw=True)
    stl.iloc[0] = (
        0 if stl.iloc[1, 0] > 0 else 1
    )  # fill in the first value based on next value
    return stl.iloc[:, 0].map({np.nan: "", 0: "HL", 1: "LL"}).astype(str)


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


def make_3_prio(input_tide, stime, etime, save_intermediate=False):
    """
    Function that makes the priorities schedule time series based on the predicted tide at San Francisco.

    Parameters
    ----------

    input_tide : :py:class:`Series <pandas:pandas.Series>`
        Time series of the Predicted tide at SF in LST
        The time series should be taken from the datastore (water level in m, NAVD88). Headers: datetime,predicted_m,elev_m.
    stime: :py:class:`datetime.timedelta`
        start time.
    etime: :py:class:`datetime.timedelta`
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
    sh, sl = tidalhl.get_tidal_hl(sframe)  # Get Tidal highs and lows
    sh = pd.concat([sh, get_tidal_hh_lh(sh)], axis=1)
    sh.columns = ["max", "max_name"]
    sl = pd.concat([sl, get_tidal_ll_hl(sl)], axis=1)
    sl.columns = ["min", "min_name"]

    # --------  flagg open and close portions - OG Priority 3
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

    # combined the df
    open_close = pd.concat([opens, closes], axis=1)

    prio3_ts = open_close.iloc[:, 0].combine_first(open_close.iloc[:, 1]).to_frame()
    prio3_ts.columns = [3]
    prio3_ts.index.name = "DATETIME"
    prio3_ts = prio3_ts[prio3_ts[3] != prio3_ts[3].shift()]
    prio3_ts.head()

    # ------- flagg open and close portions - Priority 2

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

    # combined the df
    open_close = pd.concat([opens, closes], axis=1)
    prio2_ts = open_close.iloc[:, 0].combine_first(open_close.iloc[:, 1]).to_frame()
    prio2_ts.columns = [2]
    prio2_ts.index.name = "DATETIME"
    prio2_ts = prio2_ts[prio2_ts[2] != prio2_ts[2].shift()]
    prio2_ts.head()

    # ------ flagg open and close portions - Priority 1

    # when it opens
    idx1 = sh[sh["max_name"] == "LH"].index + pd.Timedelta("1h")
    idx2 = sh[sh["max_name"] == "HH"].index + pd.Timedelta("1h")
    ci = idx1.union(idx2)
    opens = pd.DataFrame(data=np.ones(len(ci)), index=ci)

    # when it closes
    idx1 = sl[sl["min_name"] == "HL"].index - pd.Timedelta("1h")
    idx2 = sl[sl["min_name"] == "LL"].index - pd.Timedelta("2h")
    closes = pd.DataFrame(data=np.zeros(len(sl)), index=idx1.union(idx2))

    # combined the df
    open_close = pd.concat([opens, closes], axis=1)
    prio1_ts = open_close.iloc[:, 0].combine_first(open_close.iloc[:, 1]).to_frame()
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

    tide_lag, p1, p2, p3, p4 = make_3_prio(input_tide, stime, etime)

    # export flows to priorities type
    priority = flow_to_priority(export_1day)
    # make the priority schedule irr ts
    priority_df = create_priority_series(p1, p2, p3, p4, priority, stime, etime)
    # assign max gate heights base on export level (sipping)
    max_gate_height = flow_to_max_gate(export_1day).astype("float64")

    return priority_df, max_gate_height


def get_export_ts(s1, s2, flux):
    """
      retrieve swp and cvp pumping rate from a SCHISM flux.th

    Parameters
    ----------
    s1 : :py:class:'datetime <datetime.datetime>'
        start time.
    s2 : :py:class:'datetime <datetime.datetime>'
        end time.
    flux : str
        path to the SCHISM flux th file.

    Returns
    -------
    swp_ts : :py:class:'DataFrame <pandas.DataFrame>'
        swp pump rate in cfs.
    cvp_ts  : :py:class:'DataFrame <pandas.DataFrame>'
        cvp pump rate in cfs.

    """
    # flux = "//cnrastore-bdo/SCHISM/studies/itp202411/th_files/repo/flux_20241213.th"
    flux_ts = pd.read_csv(flux, parse_dates=True, index_col=0, sep=r"\s+")
    swp_ts = flux_ts["swp"][s1:s2] * M2FT * M2FT * M2FT
    cvp_ts = flux_ts["cvp"][s1:s2] * M2FT * M2FT * M2FT
    return swp_ts, cvp_ts


def sffpx_level(sdate, edate, sf_data_repo, margin=dtm.timedelta(days=30)):

    s1 = dtm.datetime.strptime(sdate, "%Y-%m-%d")
    s2 = dtm.datetime.strptime(edate, "%Y-%m-%d")
    ts_df = read_ts_repo("sffpx", "elev", repo=sf_data_repo, src_priority="infer")
    ts_df_pred = read_ts_repo(
        "sffpx", "predictions", repo=sf_data_repo, src_priority="infer"
    )
    # Check if missing values and replace with predicted values
    if ts_df.isnull().any().any():
        print("Missing values detected in SFFPX data. Replacing with predicted values.")
        ts_df = ts_df.combine_first(ts_df_pred)

    # Shift for SCHISM time zone
    shift_h = dtm.timedelta(hours=8.5)
    position_shift = int(shift_h / ts_df.index.freq)
    ts_df = ts_df.shift(position_shift)
    ts_df = ts_df.loc[s1 - margin : s2 + margin]
    ts_df.columns = ["elev"]

    return ts_df


def predict_oh4_level(s1, s2, astro_tide_file, sffpx_elev):

    sffpx = sffpx_elev * M2FT
    sffpx_subtide = cosine_lanczos(sffpx_elev, cutoff_period="40h")
    sffpx_subtide = sffpx_subtide.resample("15min").ffill()

    oh4_astro = (
        pd.read_csv(
            astro_tide_file,
            parse_dates=True,
            index_col=0,
            dtype=float,
            date_format="%Y-%m-%d %H:%M",
            header=None,
            sep=",",
        )
        .squeeze()
        .asfreq("15min")
    )

    ## linear regression of sffpx sub tide to oh4 sub tide
    oh4_sub_predicted = sffpx_subtide * 0.9620 + 1.1513
    best_shift = -10
    oh4_sub_predicted = oh4_sub_predicted.shift(-best_shift).squeeze()
    oh4_predicted = oh4_sub_predicted + oh4_astro - oh4_sub_predicted.mean()
    return oh4_predicted[s1:s2]


def raidal_gate_flow_ts(zdown_ts, zup_ts, height_ts, s1, s2, dt):

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


def radial_gate_flow(zdown, zup, height, n=5, width=6.096 * M2FT, zsill=-4.044 * M2FT):
    """
    compuate ccf radial gate flow in cubic feet/s

    Args:
        n : number of gate opened
        width: width of the each gate
        zup: upstream water elevation
        zill: elevation of gate sill
        zdown: downstream water elev
        height: gate opening height
    Returns:
        gate flow in cfs
    """
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
    s1 : datetime.datetime
        Start time.
    s2 : datetime.datetime
        End time.
    dt : datetime.timedelta
        Output time step.

    Returns
    -------
    gate_height : pandas.DataFrame
        Radial gate height time series.
    zin : pandas.DataFrame
        Predicted forebay inside water level time series.
    """
    t = s1
    relax_period = dtm.timedelta(minutes=6)
    smooth_steps = int(relax_period / dt)
    height_ts = []
    tt = []
    height = 0.0
    v0 = (inside_level0 - ccf_reference_level) * ccf_A
    vt = v0
    accumulate_export = 0.0
    zin = inside_level0
    export_ts_freq = export_ts.index[1] - export_ts.index[0]
    export_ts_daily = (export_ts.resample("D").sum()) * export_ts_freq.total_seconds()
    prio = 0
    op = 0
    zin_lst = []
    ztime = []
    zin_lst2 = []
    ztime2 = []
    draw_down = 0.0

    while t < s2:
        zin2 = 2 + vt / ccf_A
        zin_lst2.append(zin2)
        ztime2.append(t)
        tday = dtm.datetime(*t.timetuple()[:3])
        tday1 = tday + dtm.timedelta(days=1)
        tleft = tday1 - t
        nleft = int(tleft / dt)

        if tday == t:
            accumulate_export = 0.0
        loc = export_ts.index.searchsorted(t) - 1
        export = export_ts.iloc[loc]
        export_daily = export_ts_daily[tday]
        loc = priority.index.searchsorted(t) - 1
        prio = priority.priority.iloc[loc]
        op = priority.op.iloc[loc]
        loc = oh4_level.index.searchsorted(t) - 1
        zup = oh4_level.iloc[loc] - draw_down
        loc = max_height.index.searchsorted(t) - 1
        max_h = max_height.iloc[loc]

        if (prio < 1) or (op == 0) or ((zup - zin) < 0.0):
            height_target = 0.0
            accumulate_time = []
            relax_height = []
            if height == height_target:
                height_ts.append(height)
                tt.append(t)
                accumulate_time.append(t)
                relax_height = [height]
                t = t + dt
            else:  # closing smoothly
                relax_n = smooth_steps
                relax_step = -1.0 / relax_n
                relax_height_t = np.arange(1.0, relax_step, relax_step) * height
                relax_height_t[-1] = height_target
                relax_n = len(relax_height_t) - 1
                relax_height = relax_height_t[1:]
                height_ts = height_ts + relax_height.tolist()
                tt = tt + [t + i * dt for i in range(relax_n)]
                accumulate_time += [t + i * dt for i in range(relax_n)]
                t = tt[-1] + dt

            for ttemp, htemp in zip(accumulate_time, relax_height):
                loc = export_ts.index.searchsorted(ttemp) - 1
                export = export_ts.iloc[loc]
                loc = oh4_level.index.searchsorted(ttemp) - 1
                zup = oh4_level.iloc[loc] - draw_down
                zin, vt, qint = simple_mass_balance(export, zup, zin, htemp, dt, vt)
                accumulate_export += export * dt.total_seconds()
                zin_lst.append(zin)
                ztime.append(ttemp)
                loc = cvp_ts.index.searchsorted(ttemp)
                if loc >= len(cvp_ts):
                    loc = len(cvp_ts) - 1  # Clamp to the last valid index
                cvp = cvp_ts.iloc[loc]
                draw_down = draw_down_regression(cvp, qint)
            # print(ttemp,vt,zin,export,qint)
            height = height_target

            continue

        export_remain = export_daily - accumulate_export

        if vt > export_remain:
            height_target = 0.0
            ## smoothing closing gate in relax period
            relax_n = smooth_steps
            relax_step = -1.0 / relax_n
            relax_height = np.arange(1.0, 0, relax_step) * height
            left_height = nleft * [height_target]
            relax_n = len(relax_height) - 1
            if nleft >= relax_n:
                left_height[0:relax_n] = relax_height[1:]

            height_ts = height_ts + left_height
            tt = tt + [t + i * dt for i in range(nleft)]
            vt = vt - export_remain
            accumulate_export = accumulate_export + export_remain
            zin = ccf_reference_level + vt / ccf_A

            t = tday1
            height = height_target
            zin_lst.append(zin)
            ztime.append(t)
            loc = cvp_ts.index.searchsorted(t)
            cvp = cvp_ts.iloc[loc]
            draw_down = draw_down_regression(cvp, 0)
            continue

        height_target = min(11 * math.pow(zup - zin, -0.3) - 0.5, max_h)

        if height == 0:
            ## open smoothly
            relax_n = smooth_steps
        else:
            relax_n = 1
        height_step = (height_target - height) / relax_n

        for i in range(relax_n):
            height_temp = height + height_step * (i + 1)
            loc = oh4_level.index.searchsorted(t) - 1
            zup = oh4_level.iloc[loc] - draw_down
            loc = export_ts.index.searchsorted(t) - 1
            export = export_ts.iloc[loc]
            zin, vt, qint = simple_mass_balance(export, zup, zin, height_temp, dt, vt)
            accumulate_export = accumulate_export + export * dt.total_seconds()
            height_ts.append(height_temp)
            tt.append(t)
            zin_lst.append(zin)
            ztime.append(t)
            loc = cvp_ts.index.searchsorted(t) - 1
            cvp = cvp_ts.iloc[loc]
            draw_down = draw_down_regression(cvp, qint)
            t += dt
        height = height_target

    # Create the DataFrame
    df = pd.DataFrame(height_ts, index=tt, columns=["ccfb_height"])
    zin_df2 = pd.DataFrame(zin_lst2, index=ztime2, columns=["ccfb_interior_surface"])
    return df, zin_df2


def process_height(s1, s2, export, oh4_astro, sffpx_elev):
    """
    Create a ccfb radial gate height time series file

    Parameters
    ----------
    s1 : :py:class:`datetime.datetime`
        start time.
    s2 : :py:class:`datetime.datetime`
        end time.
    export : str
        path to SCHISM export th file.
    oh4_astro : str
        path to OH4 astronomic tide file .

    Returns
    -------
    sim_gate_height : :py:class:`pandas.DataFrame`
        predicted raidal gate height
    zin_df : :py:class:`pandas.DataFrame`
        predicted ccfb interior surface stage.
    """

    margin = dtm.timedelta(days=3)
    export_ts, cvp_ts = get_export_ts(s1 - margin, s2 + margin, export)
    export_ts_daily_average = export_ts.resample("D").mean()
    inside_level0 = 2.12  # in feet
    dt = dtm.timedelta(minutes=2)

    priority, max_height = gen_prio_for_varying_exports(
        sffpx_elev, export_ts_daily_average
    )

    oh4_predict = predict_oh4_level(s1 - margin, s2 + margin, oh4_astro, sffpx_elev)

    sim_gate_height, zin_df = gen_gate_height(
        export_ts, priority, max_height, oh4_predict, cvp_ts, inside_level0, s1, s2, dt
    )

    return sim_gate_height, zin_df


@click.command(
    help="Command Line function for generating Clifton Court Forebay gate height from predicted tide and export flows."
)
@click.option(
    "--sdate",
    default=None,
    help="Starting date of prediction, must be format like 2018-02-19. If not provided, find from param.nml",
)
@click.option(
    "--edate",
    default=None,
    help="End date of prediction, format same as sdate. If not provided, find from param.nml",
)
@click.option(
    "--dest",
    type=click.Path(),
    default="./ccfb_gate_syn.th",
    help="Path to store predicted gate height. Ex: './ccfb_gate_syn.th'",
)
@click.option(
    "--astro_file",
    type=click.Path(exists=True),
    required=True,
    help="Path of the predicted OH4 astronomic tide in vtide format. Ex: './astro/oh4_15min_predicted_10y_14_25.out'",
)
@click.option(
    "--export_file",
    type=click.Path(exists=True),
    required=True,
    help="Path of SCHISM export th file (flux.th with headers and dates)",
)
@click.option(
    "--sf_data_repo",
    type=click.Path(exists=True),
    help="Path of the SF data. Ex: '//cnrastore-bdo/Modeling_Data/repo/continuous/screened/'",
)
@click.option("--plot", default=False, help="Switch to plot the predicted gate height.")
@click.help_option("--help", "-h")
def ccf_gate_cli(sdate, edate, dest, astro_file, export_file, sf_data_repo, plot=False):

    if sdate is None or edate is None:
        # Get params from param.nml
        params = parms.read_params("param.nml")
        sdate = params.run_start
        edate = sdate + dtm.timedelta(days=params["rndays"])

    sffpx_elev = sffpx_level(sdate, edate, sf_data_repo)

    ccf_gate(sdate, edate, dest, astro_file, export_file, sffpx_elev, plot)


def ccf_gate(
    sdate,
    edate,
    dest,
    astro_file,
    export_file,
    sffpx_elev,
    plot=False,
    save_intermediate=False,
):
    """
    Generate the predicted gate height for the Clifton Court Forebay.

    Parameters
    ----------
    sdate : str
        Start date in the format "YYYY-MM-DD".
    edate : str
        End date in the format "YYYY-MM-DD".
    dest : str
        Destination file where the output file will be saved. ex: "ccfb_gate_syn.th"
    astro_file : str
        Path to the astronomical data file required for processing.
    export_file : str
        Path to the export file used in height processing.
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
    s1 = dtm.datetime.strptime(sdate, "%Y-%m-%d")
    s2 = dtm.datetime.strptime(edate, "%Y-%m-%d")
    oneday = dtm.timedelta(days=1)
    height, zin = process_height(s1, s2, export_file, astro_file, sffpx_elev)
    height_t = remove_continuous_duplicates(height, height.columns.tolist()[0])
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
    height_t[s1 : s2 + oneday].to_csv(
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
        ax1.set_ylabel("Height (ft)")
        plt.show()


if __name__ == "__main__":
    ccf_gate_cli()
    # os.chdir(r"/scratch/projects/summer_x2_2025/th_files/project/scripts")
    # sdate = "2024-04-16"
    # edate = "2025-01-01"
    # dest = "../ccfb_gate_syn.2024_noaciton.th"
    # astro_file = "../../oh4/oh4_15min_predicted_10y_14_25.out"
    # export_file = "../flux.2024_noaction.th"
    # sf_data_repo = "../../noaa_sf/"

    # sffpx_elev = sffpx_level(sdate, edate, sf_data_repo)

    # ccf_gate(
    #     sdate,
    #     edate,
    #     dest,
    #     astro_file,
    #     export_file,
    #     sffpx_elev,
    #     False,
    # )
