# -*- coding: utf-8 -*-
"""
Adapted from ZZheng - generate hotstart - transfer from one grid to another
"""

# Use example as command-line interface function:
# python hotstart_from_hotstart.py --test_dir ./ --in_dir ./in_dir --out_dir ./out_dir --yaml_fn ./hotstart_from_hotstart.yaml --hotstart_in ./in_dir/hotstart_it=480000.nc --hotstart_out out_hotstart_it=480000.nc
# or with bdschism in your environment::
# hot_from_hot --test_dir ./ --in_dir ./in_dir --out_dir ./out_dir --yaml_fn ./hotstart_from_hotstart.yaml --hotstart_in ./in_dir/hotstart_it=480000.nc --hotstart_out out_hotstart_it=480000.nc

# Standard Library Imports
import os
import string
import tempfile
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Third-Party Library Imports
import pandas as pd
import xarray as xr
import click

# Project-Specific Imports
import schimpy.schism_hotstart as sh
import schimpy.param as parms
import bdschism.config as config


################# command line application #####################
def str_or_path(value):
    """Helper function to handle string or Path inputs."""
    return Path(value) if Path(value).exists() else value


class SafeDict(dict):
    """Safe dictionary for string formatting."""

    def __missing__(self, key):
        return "{" + key + "}"


def fmt_string_file(fn_in, fn_out, str_dict, method="format_map"):
    """Format a file using a dictionary of strings."""
    with open(fn_in, "r") as f:
        fdata = f.read()

    if method == "format_map":
        fdata = string.Formatter().vformat(fdata, (), SafeDict((str_dict)))
    elif method == "replace":
        for key in str_dict.keys():
            fdata = fdata.replace(key, str_dict[key])

    with open(fn_out, "w") as fout:
        fout.write(fdata)


@click.command(
    help=(
        "Transfer hotstart data from one grid to another'\n\n"
        "Arguments:\n"
        "  YAML  Path to the YAML file."
        "For instance hotstart_from_hotstart.yaml (found in examples/hotstart/examples)"
    )
)
@click.argument("yaml")
@click.option(
    "--f_in",
    required=True,
    type=click.Path(exists=True),
    help="Hotstart input file path - uses hgrid.gr3 and vgrid.in from in_dir.",
)
@click.option(
    "--f_out",
    required=True,
    type=click.Path(),
    help="Hotstart output file path - will be translated to hgrid.gr3 and vgrid.in from out_dir.",
)
@click.option(
    "--in_dir",
    required=True,
    type=click.Path(exists=True),
    help="Input directory: has hgrid.gr3, vgrid.in, and param.nml (links are ok).",
)
@click.option(
    "--out_dir",
    required=True,
    type=click.Path(exists=True),
    help="Output directory: has hgrid.gr3, vgrid.in, and param.nml (links are ok).",
)
@click.option(
    "--modules",
    default=None,
    type=str,
    multiple=True,
    help="Modules to be transferred to/from hotstart files.",
)
@click.option(
    "--crs",
    default="EPSG:26910",
    type=str,
    help="Coordinate system (e.g., EPSG:26910).",
)
@click.help_option("-h", "--help")  # Add this line to enable both -h and --help
def hotstart_newgrid(
    yaml: str,
    hotstart_in,
    hotstart_out,
    in_dir,
    out_dir,
    modules=None,
    crs="EPSG:26910",
):
    """Transfer hotstart data from one grid to another."""
    # Get params
    param_nml_in = os.path.join(in_dir, "param.nml")
    params_in = parms.read_params(param_nml_in)
    param_nml_out = os.path.join(out_dir, "param.nml")
    params_out = parms.read_params(param_nml_out)

    # Get start date from hotstart file
    refds = xr.open_dataset(hotstart_in)
    run_start_in = params_in.run_start
    hot_date = (
        pd.Timedelta(seconds=refds["time"].values[0]) + run_start_in
    )  # used to fill strings in temp_yaml
    timestep = params_out._namelist["CORE"]["dt"][
        "value"
    ]  # used to fill strings in temp_yaml
    run_start = params_out.run_start  # use runstart to pass to yaml

    # set hgrid/vgrid in/outs
    hgrid_in = os.path.join(in_dir, "hgrid.gr3")  # used to fill strings in temp_yaml
    hgrid_out = os.path.join(out_dir, "hgrid.gr3")  # used to fill strings in temp_yaml
    vgrid_in = os.path.join(in_dir, "vgrid.in")  # used to fill strings in temp_yaml
    vgrid_out = os.path.join(out_dir, "vgrid.in")  # used to fill strings in temp_yaml

    # Create a temporary yaml filename
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_file:
        temp_yaml = temp_file.name
        # uses **locals(): timestep, run_start, hot_date, hgrid_in, hgrid_out, vgrid_in, vgrid_out to populate yaml_fn into temp_yaml
        fmt_string_file(yaml, temp_yaml, SafeDict(**locals()), method="format_map")
        print(f"\t Temporary yaml filename: {temp_yaml}")

    # Get modules used from hotstart infile
    if modules is None:
        ntracers, ntrs, irange_tr, modules = sh.describe_tracers(
            param_nml_out
        )  # pull module list from param_nml

    # Create a hotstart file for SCHISM
    h = sh.hotstart(temp_yaml, modules=modules, crs=crs)
    h.create_hotstart()
    hnc = h.nc_dataset
    hnc.to_netcdf(hotstart_out)
    os.remove(temp_yaml)


def main():
    """Main function to handle hotstart transfer."""
    hotstart_newgrid()


if __name__ == "__main__":
    main()
