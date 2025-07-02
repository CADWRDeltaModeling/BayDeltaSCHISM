"""Tests to make sure that the elev2d.th.nc file is referencing the correct start date"""

import pytest
import os
import xarray as xr
import numpy as np
import datetime


@pytest.mark.prerun
def test_elev2d_time(sim_dir, params, elev2dfn="elev2D.th.nc"):
    """Reads elev2d.th.nc file and return start date, check against param.nml"""
    elev_df = xr.open_dataset(os.path.join(sim_dir, elev2dfn))
    elev_start = elev_df.time.values[0].astype("M8[ms]").astype(datetime.datetime)
    param_start = params.run_start.to_pydatetime()

    print(f"elev_start: {elev_start}")
    print(f"param_start: {param_start}")

    assert (
        elev_start == param_start
    ), f"elev2D.th.nc file start time {elev_start.strftime('%Y-%m-%d %H:%M')} does not match the param.nml start time {param_start.strftime('%Y-%m-%d %H:%M')}"


@pytest.mark.prerun
def test_sea_level(sim_dir, sea_level, elev2dfn="elev2D.th.nc"):
    elev_df = xr.open_dataset(
        os.path.join(sim_dir, elev2dfn)
    )  # shape is elev_df.time_series[timesteps, openboundarynodes, nlevels]

    mean_sea_level = elev_df.time_series[:, :, :].mean().item()

    nmon = int(
        ((elev_df.time.values[-1] - elev_df.time.values[0]) / np.timedelta64(1, "D"))
        / 30.44
    )

    sigma = min(0.4, 0.1 + 0.25 / nmon)

    assert (
        abs(sea_level - mean_sea_level) < sigma
    ), f"Mean sea level {mean_sea_level:.2f} is not within {sigma:.2f} of expected sea level {sea_level:.2f}"


@pytest.mark.prerun
def test_sea_level_units(sim_dir, elev2dfn="elev2D.th.nc"):
    elev_df = xr.open_dataset(
        os.path.join(sim_dir, elev2dfn)
    )  # shape is elev_df.time_series[timesteps, openboundarynodes, nlevels]

    std_dev = elev_df.time_series.std(dim=("nOpenBndNodes", "nLevels"))

    assert (
        std_dev.max().item() < 1.0
    ), f"Standard deviation of sea level is too high for units of meters, check download data for possible use of feet. Max standard deviation: {std_dev:.2f}"
