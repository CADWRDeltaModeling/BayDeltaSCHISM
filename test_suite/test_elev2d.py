""" Tests to make sure that the elev2d.th.nc file is referencing the correct start date
"""


import pytest
import os
import xarray as xr
import datetime


@pytest.mark.prerun
def test_elev2d_time(sim_dir, params):
    """ Reads elev2d.th.nc file and return start date, check against param.nml"""
    elev_df = xr.open_dataset(os.path.join(sim_dir, 'elev2D.th.nc'))
    elev_start = elev_df.time.values[0].astype(
        'M8[ms]').astype(datetime.datetime)
    param_start = params.run_start

    print(f'elev_start: {elev_start}')
    print(f'param_start: {param_start}')

    assert elev_start == param_start, f"elev2D.th.nc file start time {elev_start.strftime('%Y-%m-%d %H:%M')} does not match the param.nml start time {param_start.strftime('%Y-%m-%d %H:%M')}"
