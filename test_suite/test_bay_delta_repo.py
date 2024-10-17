import os
import glob
import pytest

def test_raw_num_files(repo_raw):
    num_files = len(os.listdir(repo_raw))
    expected = 1950
    assert num_files > expected,f"Expected > {expected} total files in /raw repository, found {num_files}"
    
@pytest.mark.parametrize("source,expected", [("ncro", 410), ("noaa", 25),("des",384),("usgs",770)])
def test_raw_agency_num_files(repo_raw,source,expected):
    num_files = len(glob.glob(os.path.join(repo_raw,f"{source}_*")))
    assert num_files >= expected, f"Expected a minimum of {expected} files from source {source} in /raw repository, found {num_files}"
    
@pytest.mark.parametrize("source,expected", [("ncro",6800), ("noaa", 229),("des",2935),("usgs",5765)])
def test_formatted_agency_num_files(repo_formatted,source,expected):
    num_files = len(glob.glob(os.path.join(repo_formatted,f"{source}_*")))
    assert num_files >= expected, f"Expected a minimum of {expected} files from source {source} in /formatted repository, found {num_files}"
    
    
    