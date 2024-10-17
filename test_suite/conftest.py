# content of conftest.py
import pytest
import os

def pytest_addoption(parser):
    parser.addoption(
        "--repo", action="store", default="repo_dir", help="Repository name"
    )


@pytest.fixture
def repo_home(request):
    return request.config.getoption("--repo")
    
@pytest.fixture    
def repo_raw(request):
    return os.path.join(request.config.getoption("--repo"),"raw")        

@pytest.fixture    
def repo_formatted(request):
    return os.path.join(request.config.getoption("--repo"),"formatted")        

@pytest.fixture    
def repo_screened(request):
    return os.path.join(request.config.getoption("--repo"),"screened")

    