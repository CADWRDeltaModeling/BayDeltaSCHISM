# import os
# import xarray as xr
import numpy as np
import datetime
import schimpy.param as parms
from test_elev2d import test_elev2d_time
import test_nudging
import test_open_boundary
import test_smscg
import test_source_sink
import test_vgrid
import conftest

if __name__ == "__main__":
    # code here
    sim_dir = "./example_sim_dir"
    fname = os.path.join(sim_dir, "param.nml.clinic")
    params = parms.read_params(fname)

    test_elev2d_time(sim_dir, params, elev2dfn="example.elev2D.th.nc")
