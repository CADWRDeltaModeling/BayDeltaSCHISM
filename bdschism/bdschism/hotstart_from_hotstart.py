# -*- coding: utf-8 -*-
"""
Adapted from ZZheng - generate hotstart - transfer from one grid to another
"""

# Use example with bdschism in your environment::
# hot_from_hot ./hotstart_from_hotstart.yaml --f_in hotstart_it=480000.nc --src_dir ./source_dir/ --trg_dir ./target_dir/

# Standard Library Imports
import os
import string
import tempfile
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Third-Party Library Imports
import numpy as np
import pandas as pd
import xarray as xr
import click

# Project-Specific Imports
import schimpy.schism_hotstart as sh
import schimpy.param as parms
import bdschism.config as config
from schimpy.yaml_util import yaml_from_file


def _normalize_modules(modules):
    """Normalize CLI module inputs.

    Supports repeated flags (e.g. --modules SAL --modules TEM) and
    comma-separated input (e.g. --modules SAL,TEM).
    """
    if modules is None:
        return None

    normalized = []
    for item in modules:
        if item is None:
            continue
        for token in str(item).split(","):
            name = token.strip()
            if name:
                normalized.append(name.upper())

    return normalized or None


def hotstart_newgrid(
    yaml_template_fn: str,
    hotstart_in,
    hotstart_out,
    src_dir,
    trg_dir,
    modules=None,
    crs="EPSG:26910",
    visit=False,
    visit_outname="schout_hotstart.nc",
):
    """Transfer hotstart data from one grid to another."""

    # Check that all files are available
    param_nml_in = os.path.join(src_dir, "param.nml")
    param_nml_out = os.path.join(trg_dir, "param.nml")
    hgrid_in = os.path.join(src_dir, "hgrid.gr3")  # used to fill strings in temp_yaml
    hgrid_out = os.path.join(trg_dir, "hgrid.gr3")  # used to fill strings in temp_yaml
    vgrid_in = os.path.join(src_dir, "vgrid.in")  # used to fill strings in temp_yaml
    vgrid_out = os.path.join(trg_dir, "vgrid.in")  # used to fill strings in temp_yaml

    check_dirs = [src_dir, trg_dir]
    check_files = [
        hotstart_in,
        yaml_template_fn,
        param_nml_in,
        param_nml_out,
        hgrid_in,
        hgrid_out,
        vgrid_in,
        vgrid_out,
    ]
    # Ensure directories exist
    missing_directories = [
        directory for directory in check_dirs if not os.path.isdir(directory)
    ]
    missing_files = [file for file in check_files if not os.path.isfile(file)]

    if missing_directories or missing_files:
        if missing_directories:
            print("Missing directories:")
            for directory in missing_directories:
                print(f"  - {directory}")
        if missing_files:
            print("Missing files:")
            for file in missing_files:
                print(f"  - {file}")
        raise FileNotFoundError(
            "Some required directories or files are missing. See the output above for details."
        )

    # Get params
    params_in = parms.read_params(param_nml_in)
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

    envvar={
            "hotstart_in": str(hotstart_in),
            "hotstart_out": str(hotstart_out),
            "timestep": str(timestep),
            "run_start": str(run_start),
            "hot_date": str(hot_date),
            "hgrid_in": str(hgrid_in),
            "hgrid_out": str(hgrid_out),
            "vgrid_in": str(vgrid_in),
            "vgrid_out": str(vgrid_out),
            "src_dir": str(src_dir),
            "trg_dir": str(trg_dir),
        }

    modules = _normalize_modules(modules)

    # Create a hotstart file for SCHISM
    hot = sh.hotstart(yaml_template_fn, modules=modules, crs=crs, envvar=envvar)
    hnc = hot.create_hotstart(
        write_visit_nc=visit,
        visit_outname=visit_outname,
    )
    hnc = hot.nc_dataset

    # Write out the hotstart file to NetCDF
    encoding = None
    if "tracer_list" in hnc.coords:
        tracer_values = [str(x) for x in hnc["tracer_list"].values]
        hnc = hnc.drop_vars("tracer_list")
        hnc = hnc.assign_coords(
            tracer_list=("tracer_list", np.array(tracer_values, dtype=object))
        )
        encoding = {"tracer_list": {"dtype": "S10"}}

    hnc.to_netcdf(hotstart_out, encoding=encoding)


@click.command(
    help=(
        "Transfer hotstart data from one grid to another'\n\n"
        "Arguments:\n"
        "  YAML  Path to the YAML file."
        "For instance hotstart_from_hotstart.yaml_template_fn (found in examples/hotstart/examples)"
    )
)
@click.argument("yaml_template_fn")
@click.option(
    "--f_in",
    required=True,
    type=click.Path(exists=True),
    help="Hotstart input file path - uses hgrid.gr3 and vgrid.in from src_dir.",
)
@click.option(
    "--f_out",
    required=True,
    type=click.Path(),
    help="Hotstart output file path - will be translated to hgrid.gr3 and vgrid.in from trg_dir.",
)
@click.option(
    "--src_dir",
    required=True,
    type=click.Path(exists=True),
    help="Source directory: has hgrid.gr3, vgrid.in, and param.nml (links are ok).",
)
@click.option(
    "--trg_dir",
    required=True,
    type=click.Path(exists=True),
    help="Target directory: has hgrid.gr3, vgrid.in, and param.nml that the hotstart will be re-written to (links are ok).",
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
@click.option(
    "--visit",
    is_flag=True,
    default=False,
    help="Also write VisIt-friendly output netCDF (schout-like) using create_hotstart(write_visit_nc=True).",
)
@click.option(
    "--visit-outname",
    default="schout_hotstart.nc",
    type=click.Path(),
    help="Output filename for VisIt-friendly netCDF when --visit is enabled.",
)
@click.help_option("-h", "--help")
def hotstart_newgrid_cli(
    yaml_template_fn: str,
    f_in,
    f_out,
    src_dir,
    trg_dir,
    modules=None,
    crs="EPSG:26910",
    visit=False,
    visit_outname="schout_hotstart.nc",
):
    """
    Command-line interface for transferring hotstart data from one grid to another.
    """
    # Ensure input and output directories exist
    if not os.path.exists(src_dir):
        raise ValueError(f"Source directory {src_dir} does not exist.")
    if not os.path.exists(trg_dir):
        raise ValueError(f"Target directory {trg_dir} does not exist.")

    # Call the hotstart transfer function
    hotstart_newgrid(
        yaml_template_fn,
        f_in,
        f_out,
        src_dir,
        trg_dir,
        modules=modules,
        crs=crs,
        visit=visit,
        visit_outname=visit_outname,
    )


if __name__ == "__main__":
    """Main function to handle hotstart transfer."""
    hotstart_newgrid_cli()
    
    # os.chdir(
    #     "//cnrastore-bdo/SCHISM/studies/hindcast_2026/hotstart_nudging/20180315_2019grid/"
    # )
    # # Call the hotstart transfer function
    # hotstart_newgrid(
    #     "hotstart_from_hotstart.yaml",
    #     "hotstart.20190901.513600.nc",
    #     "hotstart_2019grid.20190901.513600.nc",
    #     "./2018_source",
    #     "./2019_target",
    #     modules=None,
    #     crs="EPSG:26910",
    # )
    
#     import schimpy.schism_hotstart as sh
#     envvar={
#             "hotstart_in": "hotstart_from_hotstart.yaml",
#             "hotstart_out": str(hotstart_out),
#             "timestep": str(timestep),
#             "run_start": str(run_start),
#             "hot_date": str(hot_date),
#             "hgrid_in": str(hgrid_in),
#             "hgrid_out": str(hgrid_out),
#             "vgrid_in": str(vgrid_in),
#             "vgrid_out": str(vgrid_out),
#             "src_dir": str(src_dir),
#             "trg_dir": str(trg_dir),
#         }
#     # Create a hotstart file for SCHISM
#     hot = sh.hotstart(yaml_template_fn, modules=modules, crs=crs, envvar=envvar)
#     sh.hotstart_to_outputnc(
#     "hotstart_2019grid.20190901.513600.nc",
#     str(h.date),
#     hgrid_fn="../../data_in/hgrid.gr3",
#     vgrid_fn="../../data_in/vgrid.in.3d",
#     vgrid_version=h.vgrid_version,
#     outname="schout_hotstart.nc",
# # )