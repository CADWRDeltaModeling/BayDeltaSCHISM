# content of conftest.py
import pytest
import schimpy.param as parms
import os


def pytest_addoption(parser):
    parser.addoption(
        "--sim_dir",
        action="store",
        default=".",
        help="Home directory of run (where param.nml sits)",
    ),
    parser.addoption(
        "--sea_level",
        action="store",
        default=0.97,
        help="Expected sea level (0.97 m is default)",
    )


@pytest.fixture(scope="module")
def sim_dir(request):
    loc = request.config.getoption("--sim_dir")
    # loc = "<local_path>"
    print(f"Simulation directory: {loc}")
    if not os.path.exists(loc):
        raise FileNotFoundError(f"Simulation directory does not exist: {loc}")
    return os.path.abspath(loc)


@pytest.fixture(scope="module")
def params(sim_dir):
    fname = os.path.join(sim_dir, "param.nml")
    return parms.read_params(fname)


@pytest.fixture(scope="module")
def sea_level(request):
    return request.config.getoption("--sea_level")
