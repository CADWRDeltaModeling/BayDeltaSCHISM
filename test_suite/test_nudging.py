""" Tests to make sure the nudging files are as expected
"""


import pytest
import os
import xarray as xr
import datetime


@pytest.fixture(scope="module")
def nudge_nc_modules(sim_dir, params):
    """ Reads param.nml and lists tracers that use netCDF nudging"""
    nc_nudge_list = []
    nc_dict = {1: 'TEM',
               2: 'SAL',
               3: 'GEN', # TODO: check the tracer names from here down
               4: 'AGE',
               5: 'SED',
               6: 'ECO',
               7: 'ICM',
               8: 'COS',
               9: 'FIB',
               10: 'TIMOR-NOT-ACTIVE',
               11: 'FBM'}

    for i in range(1, 12):
        if params._namelist['OPT'][f'inu_tr({i})']['value'] == 2:
            nc_nudge_list.append(nc_dict[i])

    return nc_nudge_list


@pytest.mark.prerun
def test_nudging_cofile(sim_dir, params, nudge_nc_modules):
    """ Checks that the nudging suffixes for TEM and SAL are consistent - eliminates issues of indexing on nudging for SAL/TEM """

    for MOD in nudge_nc_modules:
        target_gr3 = os.readlink(os.path.join(sim_dir, f'{MOD}_nudge.gr3'))
        print(f'{MOD}_nudge.gr3: \t{target_gr3}')
        target_nc = os.readlink(os.path.join(sim_dir, f'{MOD}_nu.nc'))
        print(f'{MOD}_nu.nc: \t{target_nc}')

        gr_suffix = target_gr3.split("nudge")[1].split(".")[0]
        nc_suffix = target_nc.split("nu")[1].split(".")[0]

        assert gr_suffix == nc_suffix, f'target_gr3 {MOD} suffix: {gr_suffix} does not match target_nc {MOD} suffix: {nc_suffix}'
