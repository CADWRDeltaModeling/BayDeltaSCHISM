"""Tests to make sure that Suisun Marsh Salinity Control Gates are operated properly"""

import pytest
import os
import xarray as xr
import datetime
from vtools import elapsed_datetime, datetime_elapsed, days
from schimpy.model_time import read_th
import pandas as pd
import numpy as np

bds_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../")
)
gate_dir = os.path.abspath(os.path.join(bds_dir, "data/time_history/"))


def read_smscg_dfs(file_dir, time_basis=None):
    boat = read_th(
        os.path.join(file_dir, "montezuma_boat_lock.th"), time_basis=time_basis
    )
    flash = read_th(os.path.join(file_dir, "montezuma_flash.th"), time_basis=time_basis)
    radial = read_th(
        os.path.join(file_dir, "montezuma_radial.th"), time_basis=time_basis
    )

    return boat, flash, radial


@pytest.fixture(scope="module")
def smscg_dfs(sim_dir, params):

    return read_smscg_dfs(sim_dir, time_basis=params.run_start)


@pytest.fixture(scope="module")
def elapse_smscg_dfs(smscg_dfs, params):
    start = params.run_start
    boat, flash, radial = [elapsed_datetime(x, reftime=start) for x in smscg_dfs]

    return align_dfs(boat, flash, radial)


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


def compare_matches(matches, matches_hist):
    """Compares two boolean series and returns a series that is True only where matches is True and matches_hist is False."""

    # Convert both to sets of pd.Timestamp for comparison
    sim_times = set(pd.to_datetime(matches.index[matches]))
    hist_times = set(pd.to_datetime(matches_hist.index[matches_hist]))

    # Only keep matches not in historical record
    unmatched_times = sim_times - hist_times

    # Create a boolean Series for the unmatched times
    matches = matches[matches.index.isin(unmatched_times)]

    return matches


@pytest.mark.prerun
def test_smscg_boatlock(sim_dir, params, elapse_smscg_dfs, historical_gates):
    """Checks that the boatlock is open whenever the radial gates are operated tidally (op_up=0)"""

    boat, flash, radial = elapse_smscg_dfs

    # Compare the 4th column (op_up) of `boat` with `radial`
    matches = (radial.iloc[:, 3] == 0) & (boat.iloc[:, 3] == 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    if historical_gates:
        print("Checking boatlock errors consistent with historical operations...")
        boat_hist, flash_hist, radial_hist = read_smscg_dfs(gate_dir)
        boat_hist, flash_hist, radial_hist = align_dfs(
            boat_hist, flash_hist, radial_hist
        )

        # Compare the 4th column (op_up) of `boat` with `radial`
        matches_hist = (radial_hist.iloc[:, 3] == 0) & (boat_hist.iloc[:, 3] == 0)

        matches = compare_matches(matches, matches_hist)
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
def test_smscg_flash(sim_dir, params, elapse_smscg_dfs, historical_gates):
    """Checks that the flashboards are closed when the radial gates are operated tidally (op_up=0)"""

    boat, flash, radial = elapse_smscg_dfs

    # Compare the 4th column (op_up) of `flash` with `radial`, ensuring that when radial gates are tidally operated, the flashboards are closed
    matches = (radial.iloc[:, 3] == 0) & (flash.iloc[:, 3] != 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    if historical_gates:
        print("Checking flash board errors consistent with historical operations...")
        boat_hist, flash_hist, radial_hist = read_smscg_dfs(gate_dir)
        boat_hist, flash_hist, radial_hist = align_dfs(
            boat_hist, flash_hist, radial_hist
        )

        # Compare the 4th column (op_up) of `flash` with `radial`, ensuring that when radial gates are tidally operated, the flashboards are closed
        matches_hist = (radial_hist.iloc[:, 3] == 0) & (flash_hist.iloc[:, 3] != 0)

        matches = compare_matches(matches, matches_hist)
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
def test_smscg_radial_tides(sim_dir, params, elapse_smscg_dfs, historical_gates):
    """Checks that the tidal radial operations make sense"""

    boat, flash, radial = elapse_smscg_dfs

    # Compare the 3rd and 4th columns (op_down and op_up) of radial, ensuring tidal operation
    matches = (radial.iloc[:, 3] == 0) & (radial.iloc[:, 2] == 0)
    matches_seconds = datetime_elapsed(matches, reftime=params.run_start)

    if historical_gates:
        print("Checking radial tide errors consistent with historical operations...")
        boat_hist, flash_hist, radial_hist = read_smscg_dfs(gate_dir)
        boat_hist, flash_hist, radial_hist = align_dfs(
            boat_hist, flash_hist, radial_hist
        )

        # Compare the 3rd and 4th columns (op_down and op_up) of radial, ensuring tidal operation
        matches_hist = (radial_hist.iloc[:, 3] == 0) & (radial_hist.iloc[:, 2] == 0)

        matches = compare_matches(matches, matches_hist)
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
def test_smscg_radial_open(sim_dir, params, elapse_smscg_dfs, historical_gates):
    """Checks that the radial operations make sense"""

    boat, flash, radial = elapse_smscg_dfs

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
