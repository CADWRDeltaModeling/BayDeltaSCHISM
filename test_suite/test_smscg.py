"""Tests to make sure that Suisun Marsh Salinity Control Gates are operated properly"""

import pytest
import os
import xarray as xr
import datetime
from vtools import elapsed_datetime, datetime_elapsed, days
import pandas as pd
import numpy as np


@pytest.fixture(scope="module")
def smscg_dfs(sim_dir, params):
    """Reads the three montezuma .th files"""
    start = params.run_start
    boat = pd.read_csv(
        os.path.join(sim_dir, "montezuma_boat_lock.th"),
        index_col=0,
        sep=r"\s+",
        header=None,
        comment="#",
    )
    flash = pd.read_csv(
        os.path.join(sim_dir, "montezuma_flash.th"),
        index_col=0,
        sep=r"\s+",
        header=None,
        comment="#",
    )
    radial = pd.read_csv(
        os.path.join(sim_dir, "montezuma_radial.th"),
        index_col=0,
        sep=r"\s+",
        header=None,
        comment="#",
    )
    return [elapsed_datetime(x, reftime=start) for x in (boat, flash, radial)]


def align_dfs(boat, flash, radial):
    """Ensures alignment of the three dataframes and fills to radial index"""
    org_indices = sorted(set(pd.concat([boat, flash, radial]).index))
    boat = extend_idx(boat, org_indices[0], org_indices[-1])
    flash = extend_idx(flash, org_indices[0], org_indices[-1])
    radial = extend_idx(radial, org_indices[0], org_indices[-1])

    boat = boat.resample("1min").asfreq().ffill()
    flash = boat.resample("1min").asfreq().ffill()
    radial = boat.resample("1min").asfreq().ffill()

    # Get rid of unecessary (unchanged) timestamps
    boat = boat.loc[org_indices]
    flash = flash.loc[org_indices]
    radial = radial.loc[org_indices]
    return [boat, flash, radial]


def extend_idx(df, start, end):
    start_row = df.iloc[0].to_frame().T
    if start_row.index[0] > start:
        start_row.index = [start]
        df = pd.concat([start_row, df])
    end_row = df.iloc[-1].to_frame().T
    if end_row.index[0] < end:
        end_row.index = [end]
        df = pd.concat([df, end_row])

    return df


@pytest.mark.prerun
def test_smscg_boatlock(sim_dir, params, smscg_dfs):
    """Checks that the boatlock is open whenever the radial gates are operated tidally (op_up=0)"""

    boat, flash, radial = smscg_dfs
    boat, flash, radial = align_dfs(boat, flash, radial)

    # Compare the 4th column (op_up) of `boat` with `radial`
    matches = (radial.iloc[:, 3] == 0) & (boat.iloc[:, 3] == 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    print("Boatlock Error Times ----------------")
    for match, sec in zip(
        matches.index[matches].values, matches_seconds.index[matches].values
    ):
        print(
            f"Seconds: {sec}, Datetime: {match}, Radial op_down: {radial.loc[match].iloc[2]}, Radial op_up: {radial.loc[match].iloc[3]}, Boatlock op_up: {boat.loc[match].iloc[3]}"
        )
    assert (
        ~matches
    ).all(), f"montezuma_boat_lock should not be closed when montezuma_radial is in tidal operation."


@pytest.mark.prerun
def test_smscg_flash(sim_dir, params, smscg_dfs):
    """Checks that the flashboards are closed when the radial gates are operated tidally (op_up=0)"""

    boat, flash, radial = smscg_dfs
    boat, flash, radial = align_dfs(boat, flash, radial)

    # Compare the 4th column (op_up) of `flash` with `radial`, ensuring that when radial gates are tidally operated, the flashboards are closed
    matches = (radial.iloc[:, 3] == 0) & (flash.iloc[:, 3] != 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    print("Flash Error Times ----------------")
    for match, sec in zip(
        matches.index[matches].values, matches_seconds.index[matches].values
    ):
        print(
            f"Seconds: {sec}, Datetime: {match}, Radial op_down: {radial.loc[match].iloc[2]}, Radial op_up: {radial.loc[match].iloc[3]}, Flash op_up: {flash.loc[match].iloc[3]}"
        )
    assert (
        ~matches
    ).all(), f"montezuma_flash should not be open when montezuma_radial is in tidal operation."


@pytest.mark.prerun
def test_smscg_radial_tides(sim_dir, params, smscg_dfs):
    """Checks that the tidal radial operations make sense"""

    boat, flash, radial = smscg_dfs

    # Compare the 3rd and 4th columns (op_down and op_up) of radial, ensuring tidal operation
    matches = (radial.iloc[:, 3] == 0) & (radial.iloc[:, 2] == 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    print("Tidal Radial Error Times ----------------")
    for match, sec in zip(
        matches.index[matches].values, matches_seconds.index[matches].values
    ):
        print(
            f"Seconds: {sec}, Datetime: {match}, Radial op_down: {radial.loc[match].iloc[2]}, Radial op_up: {radial.loc[match].iloc[3]}"
        )

    assert (
        ~matches
    ).all(), f"montezuma_radial tidal operation not correct. op_down should be 1.0 when op_up is 0.0."


@pytest.mark.prerun
def test_smscg_radial_open(sim_dir, params, smscg_dfs):
    """Checks that the radial operations make sense"""

    boat, flash, radial = smscg_dfs

    # Compare the 3rd and 4th columns (op_down and op_up) of radial, ensuring tidal operation
    matches = (radial.iloc[:, 3] == 1) & (radial.iloc[:, 2] != 1)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    print("Radial Error Times ----------------")
    for match, sec in zip(
        matches.index[matches].values, matches_seconds.index[matches].values
    ):
        print(
            f"Seconds: {sec}, Datetime: {match}, Radial op_down: {radial.loc[match].iloc[2]}, Radial op_up: {radial.loc[match].iloc[3]}"
        )

    assert (
        ~matches
    ).all(), f"montezuma_radial open condition not correct. op_down should be 1.0 when op_up is 1.0."
