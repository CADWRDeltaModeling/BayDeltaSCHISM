"""Tests to make sure that the sources, sinks and mass sources time history files
tally in columns with source_sinks.in, are long enough in duration and are apparently in
the right (SI) units
"""

import pytest
import os
import pandas as pd
from schimpy.schism_source import read_sources
from vtools import elapsed_datetime, days


def read_th(sim_dir, params, fname):
    df = pd.read_csv(os.path.join(sim_dir, "vsource.th"), index_col=0, sep=r"\s+")


@pytest.fixture(scope="module")
def source_dfs(sim_dir, params):
    """Reads vsource, vsink and msource.th files and returns as list of DataFrames"""
    start = params.run_start
    vsource = pd.read_csv(os.path.join(sim_dir, "vsource.th"), index_col=0, sep=r"\s+")
    vsink = pd.read_csv(os.path.join(sim_dir, "vsink.th"), index_col=0, sep=r"\s+")
    msource = pd.read_csv(os.path.join(sim_dir, "msource.th"), index_col=0, sep=r"\s+")
    return [elapsed_datetime(x, reftime=start) for x in (vsource, vsink, msource)]


@pytest.mark.prerun
def test_source_sink_count(sim_dir, source_dfs):
    """Test that the number of columns in the vsource, vsink and msource time histories match the number
    of sources and sinks in source_sink.th

    """

    fname = os.path.join(sim_dir, "source_sink.in")
    src, sink = read_sources(fname)
    assert len(src) > 200
    assert len(sink) > 200

    vsource, vsink, msource = source_dfs
    assert len(vsource.columns) == len(src)
    assert len(vsink.columns) == len(sink)

    assert len(msource.columns) % len(src) == 0


@pytest.mark.prerun
def test_source_sink_duration(sim_dir, params, source_dfs):
    """Test if the source/sink files are long enough to cover the run
    #todo: can it be short by one day?
    """
    start = params.run_start
    rnday = params["rnday"]
    end = params.run_start + days(rnday)
    print(start == end)

    for name, df in zip(("vsource.th", "vsink.th", "msource.th"), source_dfs):
        dfend = df.last_valid_index() + days(1)
        assert (
            dfend >= end
        ), f"Source data th file {name} does not cover run period. File end is {dfend}, run goes to {end}"


@pytest.mark.prerun
def test_source_sink_units(sim_dir, params, source_dfs):
    """Test if the source/sink files units seem to be in the right range?"""
    q = source_dfs[0].quantile(0.7).iloc[0]
    assert q < 0.15

    q = source_dfs[1].quantile(0.15).iloc[0]
    assert q > -0.5
