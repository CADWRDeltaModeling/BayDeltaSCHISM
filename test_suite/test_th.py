"""Tests to validate that time history (.th) files have regular time intervals.

This module checks that flux.th, SAL_*.th, TEM_*.th, vsource.th, vsink.th,
and msource.th files have regular time steps as required by SCHISM.
"""

import pytest
import os
import pandas as pd
import glob
import numpy as np

# Try to import vtools and check version
vtools_available = False
vtools_version_ok = False
vtools_error_msg = None

try:
    from vtools.data.timeseries import is_regular
    import vtools
    from packaging import version

    vtools_available = True
    vtools_version = vtools.__version__
    required_version = "3.9.14"
    if version.parse(vtools_version) < version.parse(required_version):
        vtools_error_msg = f"vtools needs to be version 3.9.14 or later"
    else:
        vtools_version_ok = True
except ImportError:
    vtools_error_msg = "vtools needs to be version 3.9.14 or later"


def read_th_file(file_path):
    """Read a .th file and return as a pandas DataFrame with time index.

    Parameters
    ----------
    file_path : str
        Path to the .th file

    Returns
    -------
    pd.DataFrame
        DataFrame with time index (first column treated as elapsed time)
    """
    df = pd.read_csv(
        file_path, 
        index_col=0, 
        sep=r"\s+", 
        header=None, 
        dtype=float,
        parse_dates=[0]
    )
    return df


@pytest.mark.parametrize(
    "th_file_name",
    ["flux.th", "vsource.th", "vsink.th", "msource.th", "SAL_*.th", "TEM_*.th"],
    ids=lambda x: x,
)
@pytest.mark.prerun
def test_th_regular_index(sim_dir, th_file_name):
    """Test that the time index of .th files is regular.

    This parameterized test checks that time history files (flux.th, SAL_*.th,
    TEM_*.th, vsource.th, vsink.th, msource.th) have regular time intervals.

    Parameters
    ----------
    sim_dir : str
        Simulation directory from pytest fixture
    th_file_name : str
        Name of the .th file to test
    """
    # Check if vtools is available and has correct version
    if not vtools_version_ok:
        pytest.skip(vtools_error_msg)

    file_paths = glob.glob(os.path.join(sim_dir, th_file_name))

    for file_path in file_paths:
        # Skip test if file doesn't exist
        if not os.path.exists(file_path):
            pytest.skip(f"{th_file_name} not found in simulation directory")

        # Read the .th file
        df = read_th_file(file_path)

        # Check if the time index is regular
        assert is_regular(df), (
            f"{th_file_name} does not have a regular time index. "
            f"Time intervals: min={np.diff(df.index).min():.6f}, "
            f"max={np.diff(df.index).max():.6f}, "
            f"mean={np.diff(df.index).mean():.6f}"
        )
