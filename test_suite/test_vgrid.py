""" Tests to make sure there are no zero layered cells
"""


import pytest
import os
import xarray as xr
import datetime
from schimpy.schism_vertical_mesh import SchismLocalVerticalMeshReader as svg
import numpy as np


@pytest.fixture(scope="module")
def vgrid3d(sim_dir, params):
    """ Reads vgrid.3d.in. Assumes vgrid_version='5.10' """

    svg_ob = svg()
    vgrid = svg_ob.read(
        fpath=os.path.join(sim_dir, "vgrid.in.3d"), vgrid_version="5.10"
    )

    return vgrid


@pytest.mark.prerun
def test_zero_layer(sim_dir, params, vgrid3d):
    """ Checks for any 0-layer cells in the vgrid """

    # vgrid3d.sigma is the vgrid array
    all_nan_layers = np.all(np.isnan(vgrid3d.sigma), axis=1)

    # Find the indices of rows where all values are NaN
    indices_with_all_nan = np.where(all_nan_layers)[0]

    assert len(indices_with_all_nan)==0, f"Vgrid.in has zero-length vgrids. Re-build vgrid.in.3d and check minmax shapefile. Indices of layers with all NaNs: {indices_with_all_nan}"
