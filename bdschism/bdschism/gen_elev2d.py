#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate elev2D.th for a Bay-Delta SCHSIM model using tides at
Point Reyes and Monterey.

2015-06-16: Customized
"""

import pandas as pd

from netCDF4 import Dataset
from vtools.functions.separate_species import separate_species
from schimpy.schism_mesh import read_mesh
from vtools import days, seconds
from vtools.data.gap import describe_null
from dms_datastore.read_ts import read_noaa, read_ts
from dms_datastore.read_multi import read_ts_repo
import numpy as np
from datetime import datetime
import struct, argparse
import click
import warnings
import glob
import os

class THWriter(object):
    def __init__(self, path, size, starttime):
        pass
        # self.myfilehnandle =

    def write_step(self, iter, time, vals):
        pass

    def write_all(self, times, vals):
        # if you get to this point
        pass

    def __del__(self):
        pass
        # tear down/close things


class BinaryTHWriter(THWriter):
    # super(THWriter, self).__init__(path)
    def __init__(self, fpath_out, nloc, starttime):
        self.outfile = open(fpath_out, "wb")
        # self.myfilehnandle =
        self.tformat = "f"
        self.valformat = "f" * nloc

    def write_step(self, iter, time, vals):
        print("Writing Output")
        buf = struct.pack(self.tformat, time)
        self.outfile.write(buf)
        buf = struct.pack(self.valformat, *vals)
        self.outfile.write(buf)

    def write_all(self, times, vals):
        # if you get to this point
        pass

    def __del__(self):
        self.outfile.close()
        # tear down/close things


class NetCDFTHWriter(THWriter):
    def __init__(self, fpath_out, nloc, starttime, dt, slr, hgrid_fpath):
        self.outfile = Dataset(fpath_out, "w", format="NETCDF4_CLASSIC")
        fout = self.outfile

        time = fout.createDimension("time", None)
        nOpenBndNodes = fout.createDimension("nOpenBndNodes", nloc)
        nLevels = fout.createDimension("nLevels", 1)
        nComponents = fout.createDimension("nComponents", 1)
        one = fout.createDimension("one", 1)

        # create netCDF dimension variables and
        self.times = fout.createVariable("time", "f8", ("time",))
        # todo: what is timestep all about? Did we invent this? Why variable rather than attribute?
        # todo: what is timestep all about? Did we invent this? Why variable rather than attribute?
        self.timestep = fout.createVariable("time_step", "f4", ("one",))
        self.timestep[0] = dt

        # create elevation time series data to be writen to netCDF file
        self.timeseries = fout.createVariable(
            "time_series", "f4", ("time", "nOpenBndNodes", "nLevels", "nComponents")
        )

        # variable attributes
        self.times.long_name = "simulation time in seconds"
        self.times.units = "seconds since " + str(starttime)
        self.timeseries.long_name = "water surface elevation at ocean boundary"
        self.timestep.long_name = "time step in seconds"
        self.timeseries.units = "meters NAVD88"

        # Global Attributes -- Metadata
        fout.description = (
            "Water Surface Elevation Boundary Conditions at Ocean Boundary "
        )
        fout.history = "Created " + str(datetime.now())
        fout.source = "gen_ elev2D.py"
        fout.slr = str(slr)
        fout.hgrid = os.path.abspath(hgrid_fpath)

    def write_step(self, iter, time, vals):
        self.timeseries[iter, :, 0, 0] = vals
        self.times[iter] = time

    def write_all(self, times, vals):
        # if you get to this point
        pass

    def __del__(self):
        self.outfile.close()


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--stime",
    default=None,
    required=False,
    help="Start time in ISO-like format 2009-03-12T00:00:00. Time part and 'T' are optional.",
)
@click.option("--etime", default=None, required=False, help="End time.")
@click.option(
    "--hgrid",
    default="hgrid.gr3",
    required=False,
    help="Name of hgrid file if not hgrid.gr3",
)
@click.option(
    "--outfile",
    default="elev2D.th.nc",
    help="Name of output file: either elev2D.th or elev2D.th.nc",
)
@click.option(
    "--slr",
    default=0.0,
    type=float,
    required=False,
    help="Scalar sea level rise increment",
)

@click.argument("files", nargs=-1, type=str, required=False)
def gen_elev2d_cli(stime, etime, hgrid, outfile, slr, files):
    """
    Script to create elev2D.th.nc boundary condition from Point Reyes and Monterey NOAA file

    ============== Example ==================
    > gen_elev2D.py --outfile elev2D.th.nc --stime=2009-03-12 --etime=2010-01-01 9415020_gageheight.csv 9413450_gageheight.csv
    
    > bds gen_elev2d --outfile elev2D.th.nc --hgrid=hgrid.gr3 --stime=2025-8-27 --etime=2026-01-04 --slr 0.0 "/path/to/noaa_pryc1_9415020_elev_*.csv" "path/to/noaa_mtyc1_9413450_elev_*.csv"
    """
    # Default values
    pt_reyes = "pryc1"
    monterey = "mtyc1"
    
    if files:
        if len(files) == 0:
            # Use defaults
            pass
        elif len(files) == 1:
            # Single file - assume it's pt_reyes
            pt_reyes = files[0]
        elif len(files) == 2:
            # Two files - traditional behavior
            pt_reyes = files[0]
            monterey = files[1]
        else:
            # Multiple files - separate by station name
            pt_reyes_files = []
            monterey_files = []
            
            for f in files:
                if 'pryc1' in f.lower() or '9415020' in f:
                    pt_reyes_files.append(f)
                elif 'mtyc1' in f.lower() or '9413450' in f:
                    monterey_files.append(f)
            
            pt_reyes = pt_reyes_files if pt_reyes_files else "pryc1"
            monterey = monterey_files if monterey_files else "mtyc1"
    
    return gen_elev2D(hgrid, outfile, pt_reyes, monterey, stime, etime, slr)


def _get_data(src, start,end=None):
    """Get data from file(s) or repository.
    
    Args:
        src: Either a single file path, list of file paths, or station code string
        start: Start time
        end: End time  
        tbuf: Time buffer
        bufend: Buffered end time
    """
    # Handle list of files
    if isinstance(src, list):
        if not src:
            raise ValueError("Empty file list provided")
        if len(src) == 1:
            src = src[0]
        else:
            # Read and concatenate multiple files
            dfs = []
            for fpath in sorted(src):  # Sort to ensure chronological order
                try:
                    df = read_noaa(fpath, start=start, end=end, force_regular=True)
                except Exception:
                    df = read_ts(fpath, start=start, end=end, force_regular=True)
                dfs.append(df)
            # Concatenate and remove duplicates
            out = pd.concat(dfs, axis=0)
            out = out[~out.index.duplicated(keep='first')]
            out = out.sort_index()
            return out
    
    # Handle single file or station code
    if isinstance(src, str) and src.endswith(".csv"):
        try:
            out = read_noaa(
                src, start=start, end=end, force_regular=True
            )
        except Exception as e:
            out = read_ts(
                src, start=start, end=end, force_regular=True
        )
    else:
        # assume it is from repo
        if src not in ("pryc1","pt_reyes","mtyc1","monterey"):
            raise ValueError(f"Station code {src} not known")
        if src in ("pryc1","pt_reyes"):
            src = "pryc1"
        elif src in ("mtyc1","monterey"):
            src = "mtyc1"
        out = read_ts_repo(src, "elev", start=start)
    return out

def gen_elev2D(hgrid_fpath, outfile, pt_reyes_fpath, monterey_fpath, start, end, slr):
    max_gap = 5
    stime = start
    etime = end
    fpath_out = outfile

    # todo: hardwire
    nnode = 83

    tbuf = days(16)
    # convert start time string input to datetime
    sdate = pd.Timestamp(stime)
    bufstart = sdate - tbuf

    if not etime is None:
        # convert start time string input to datetime
        edate = pd.Timestamp(etime)
        bufend = edate + tbuf
    else:
        edate = None
        bufend = None

    # UTM positions of Point Reyes, Monterey, SF
    pos_pr = np.array([502195.03, 4205445.47])
    pos_mt = np.array([599422.84, 4051630.37])
    pos_sf = np.array([547094.79, 4184499.42])

    var_subtidal = np.array([0.938, 0.905, 0.969])  # pr, mt, sf
    var_semi = np.array([0.554, 0.493, 0.580])

    # Assume 45 degree from north-west to south-east
    tangent = np.array([1, -1])
    tangent = tangent / np.linalg.norm(tangent)  # Normalize
    # Rotate 90 cw to get normal vec
    normal = np.array([tangent[1], -tangent[0]])
    print("tangent: {}".format(tangent))
    print("normal: {}".format(normal))

    mt_rel = pos_mt - pos_pr
    x_mt = np.dot(tangent, mt_rel)  # In pr-mt direction
    y_mt = np.dot(normal, mt_rel)  # Normal to x-direction to the

    # Grid
    # todo: what is the difference between this and m = read_grid()??
    mesh = read_mesh(hgrid_fpath)

    ocean_boundary = mesh.boundaries[0]  # First one is ocean

    # Data
    print("Reading Point Reyes...")
    pt_reyes = _get_data(pt_reyes_fpath, bufstart, bufend)


    # --- Add this check for coverage ---
    pt_start = pt_reyes.first_valid_index()
    pt_end = pt_reyes.last_valid_index()
    expected_start = bufstart
    expected_end = bufend
    if pt_start > expected_start or pt_end < expected_end:
        warnings.warn(
            f"Point Reyes data does not fully span required range: {expected_start} to {expected_end}. "
            f"Actual range: {pt_start} to {pt_end}"
        )
    # --- End check ---

    pt_reyes.interpolate(limit=max_gap, inplace=True)
    if pt_reyes.isna().any(axis=None):
        describe_null(pt_reyes, "Pt Reyes")
        raise ValueError("pt_reyes has gaps larger than fill limit")
    if pt_reyes.empty:
        raise ValueError(
            "No data loaded for Point Reyes. Check file path and date range."
        )

    ts_pr_subtidal, ts_pr_diurnal, ts_pr_semi, noise = separate_species(
        pt_reyes, noise_thresh_min=150
    )
    del noise

    print("Reading Monterey...")
    monterey = _get_data(monterey_fpath, bufstart, bufend)

    # --- Add this check for coverage ---
    mt_start = monterey.first_valid_index()
    mt_end = monterey.last_valid_index()
    if mt_start > expected_start or mt_end < expected_end:
        warnings.warn(
            f"Monterey data does not fully span required range: {expected_start} to {expected_end}. "
            f"Actual range: {mt_start} to {mt_end}"
        )
    # --- End check ---

    monterey.interpolate(limit=max_gap, inplace=True)
    if monterey.isna().any(axis=None):
        describe_null(monterey, "Monterey")
        raise ValueError("monterey has gaps larger than fill limit")
    if monterey.empty:
        raise ValueError("No data loaded for Monterey. Check file path and date range.")

    if pt_reyes.index.freq != monterey.index.freq:
        raise ValueError(
            "Point Reyes and Monterey time step must be the same in gen_elev2D.py"
        )

    ts_mt_subtidal, ts_mt_diurnal, ts_mt_semi, noise = separate_species(
        monterey, noise_thresh_min=150
    )
    del noise

    dt = monterey.index.freq / seconds(1)

    print("Done Reading")

    print("Interpolating and subsetting Point Reyes")
    # interpolate_ts(ts_pr_subtidal.window(sdate,edate),step)
    ts_pr_subtidal = ts_pr_subtidal.loc[sdate:edate]
    ts_pr_diurnal = ts_pr_diurnal.loc[sdate:edate]
    # interpolate_ts(ts_pr_semi.window(sdate,edate),step)
    ts_pr_semi = ts_pr_semi.loc[sdate:edate]

    print("Interpolating and subsetting Monterey")
    # interpolate_ts(ts_mt_subtidal.window(sdate,edate),step)
    ts_mt_subtidal = ts_mt_subtidal.loc[sdate:edate]
    # interpolate_ts(ts_mt_diurnal.window(sdate,edate),step)
    ts_mt_diurnal = ts_mt_diurnal.loc[sdate:edate]
    # interpolate_ts(ts_mt_semi.window(sdate,edate),step)
    ts_mt_semi = ts_mt_semi.loc[sdate:edate]

    print("Creating writer")  # requires dt be known for netcdf
    if fpath_out.endswith("th"):
        thwriter = BinaryTHWriter(fpath_out, nnode, None)
    elif fpath_out.endswith("nc"):
        thwriter = NetCDFTHWriter(fpath_out, nnode, sdate, dt, slr, hgrid_fpath)
    else:
        raise ValueError(
            "File extension for output not recognized in file: {}".format(fpath_out)
        )

    # Grid
    boundaries = mesh.nodes[ocean_boundary.nodes]
    pos_rel = boundaries[:, :2] - pos_pr

    # x, y in a new principal axes
    x = np.dot(pos_rel, tangent.reshape((2, -1)))
    y = np.dot(pos_rel, normal.reshape((2, -1)))
    theta_x = x / x_mt
    theta_x_comp = 1.0 - theta_x
    theta_y = y / y_mt
    theta_y_comp = 1.0 - theta_y

    var_y = theta_y_comp * var_semi[0] + theta_y * var_semi[1]

    # adj_subtidal_mt = 0.08  # Adjustment in Monterey subtidal signal
    # scaling_diurnal_mt = 0.95 # Scaling of Monterey diurnal signal (for K1/Q1)
    # Used this up to v75
    adj_subtidal_mt = 0.0  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 1.0  # Scaling of Monterey diurnal signal (for K1/Q1)
    # New trial for LSC2 with v75
    adj_subtidal_mt = -0.07  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.95  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.03

    adj_subtidal_mt = -0.14  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.90  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.07

    adj_subtidal_mt = 0.10  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.90  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.03

    adj_subtidal_mt = 0.10  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.97  # Scaling of Monterey diurnal signal (for K1/Q1)
    # Scaling of Point Reyes diurnal signal (for K1/Q1)
    scaling_diurnal_pr = 0.97
    scaling_semidiurnal_mt = 1.025  # Scaling at Monterey semi-diurnal signal

    adj_subtidal_mt = 0.09  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.94  # Scaling of Monterey diurnal signal (for K1/Q1)
    # Scaling of Point Reyes diurnal signal (for K1/Q1)
    scaling_diurnal_pr = 0.94
    scaling_semidiurnal_mt = 1.0  # Scaling at Monterey semi-diurnal signal

    if ts_pr_semi.isna().any(axis=None):
        print(ts_pr_semi[ts_pr_semi.isna()])
        raise ValueError("Above times are missing in Point Reyes data")

    for i in range(len(ts_pr_semi)):
        t = float(dt * i)
        # semi-diurnal
        # Scaling
        pr = ts_pr_semi.iloc[i, 0]
        mt = ts_mt_semi.iloc[i, 0] * scaling_semidiurnal_mt

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")

        eta_pr_side = var_y / var_semi[0] * pr
        eta_mt_side = var_y / var_semi[1] * mt
        eta = eta_pr_side * theta_x_comp + eta_mt_side * theta_x

        # diurnal
        # Interpolate in x-direction only to get a better phase
        pr = ts_pr_diurnal.iloc[i, 0] * scaling_diurnal_pr
        mt = ts_mt_diurnal.iloc[i, 0] * scaling_diurnal_mt
        # if i < 5:
        #    print("yu")
        #    print(pr)
        #    print(mt)

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")

        eta += pr * theta_x_comp + mt * theta_x

        # Subtidal
        # No phase change in x-direction. Simply interpolate in
        # y-direction.
        pr = ts_pr_subtidal.iloc[i, 0]
        mt = ts_mt_subtidal.iloc[i, 0] + adj_subtidal_mt

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")
        eta += pr * theta_y_comp + mt * theta_y + slr

        # write data to netCDF file
        thwriter.write_step(i, t, eta)

    # Delete class
    del thwriter


if __name__ == "__main__":
    gen_elev2d_cli()
