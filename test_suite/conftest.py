# content of conftest.py
import pytest
import schimpy.param as parms
import os


def pytest_addoption(parser):
    parser.addoption(
        "--sim_dir", action="store", default=".", help="Home directory of run (where param.nml sits)"
    )


@pytest.fixture(scope="module")
def sim_dir(request):
    loc = request.config.getoption("--sim_dir")
    return os.path.abspath(loc)

@pytest.fixture(scope="module")
def params(sim_dir):
    fname = os.path.join(sim_dir,"param.nml")
    return parms.read_params(fname)
    
    