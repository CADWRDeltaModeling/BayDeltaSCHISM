# -*- coding: utf-8 -*-
"""
Adapted from ZZheng - generate hotstart - transfer from one grid to another
"""

# Use example with bdschism in your environment::
# bds hot_from_hot ./hotstart_from_hotstart.yaml --f_in ./baseline_sim_dir/hotstart_it=480000.nc --f_out ./franks_sim_dir/hotstart_480000_franks.nc --src_dir ./baseline_sim_dir/ --trg_dir ./franks_sim_dir/

# Standard Library Imports
import os
import string
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Third-Party Library Imports
import pandas as pd
import xarray as xr
import click
import yaml

# Project-Specific Imports
import schimpy.schism_hotstart as sh
from schimpy.util.yaml_load import yaml_from_file
import schimpy.param as parms
import bdschism.config as config


################# command line application #####################
def str_or_path(value):
    """Helper function to handle string or Path inputs."""
    return Path(value) if Path(value).exists() else value


def hotstart_newgrid(
    yaml_fn: str,
    hotstart_in,
    hotstart_out,
    src_dir,
    trg_dir,
    modules=None,
    crs="EPSG:26910",
    envvar=None,
):
    """Transfer hotstart data from one grid to another."""

    # Build standard hotstart transfer dictionary
    repl_dict = {
        "hotstart_in": str(hotstart_in),
        "param_nml_in": os.path.join(src_dir, "param.nml"),
        "param_nml_out": os.path.join(trg_dir, "param.nml"),
        "hgrid_in": os.path.join(src_dir, "hgrid.gr3"),
        "hgrid_out": os.path.join(trg_dir, "hgrid.gr3"),
        "vgrid_in": os.path.join(src_dir, "vgrid.in"),
        "vgrid_out": os.path.join(trg_dir, "vgrid.in"),
        "src_dir": str(src_dir),
        "trg_dir": str(trg_dir),
    }
    if envvar is not None:
        if not isinstance(envvar, dict):
            raise ValueError("envvar must be a dictionary if provided.")
        repl_dict.update(envvar)

    # Ensure files and directories exist
    missing_filesdirs = [f for f in repl_dict.values() if not os.path.exists(f)]

    if missing_filesdirs:
        print("Missing directories or files:")
        for filedir in missing_filesdirs:
            print(f"  - {filedir}")
        raise FileNotFoundError(
            "Some required directories or files are missing. See the output above for details."
        )
    repl_dict["hotstart_out"] = str(hotstart_out)

    # Get params
    params_in = parms.read_params(repl_dict["param_nml_in"])
    params_out = parms.read_params(repl_dict["param_nml_out"])

    # Get start date from hotstart file
    refds = xr.open_dataset(hotstart_in)
    run_start_in = params_in.run_start
    repl_dict["hot_date"] = (
        pd.Timedelta(seconds=refds["time"].values[0]) + run_start_in
    ).strftime(
        "%Y-%m-%d %H:%M"
    )  # used to fill strings in yaml
    repl_dict["timestep"] = str(
        int(params_out._namelist["CORE"]["dt"]["value"])
    )  # used to fill strings in yaml
    repl_dict["run_start"] = params_out.run_start.strftime(
        "%Y-%m-%d %H:%M"
    )  # use runstart to pass to yaml

    # Get modules used from hotstart infile
    if modules is None:
        ntracers, ntrs, irange_tr, modules = sh.describe_tracers(
            repl_dict["param_nml_out"]
        )  # pull module list from param_nml

    # Create a hotstart file for SCHISM
    h = sh.hotstart(yaml_fn, modules=modules, crs=crs, envvar=repl_dict)
    h.create_hotstart()
    hnc = h.nc_dataset
    # Add the YAML file content as an entry to the netCDF file
    yaml_content = yaml_from_file(yaml_fn, envvar=repl_dict)
    yaml_str = yaml.safe_dump(yaml_content, sort_keys=False)
    hnc.attrs["yaml_input"] = yaml_str

    # Write out the hotstart file to NetCDF
    print(f"Writing hotstart file to {hotstart_out}")
    hnc.to_netcdf(hotstart_out)


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
@click.help_option("-h", "--help")
@click.argument("extra", nargs=-1)
def hotstart_newgrid_cli(
    yaml: str,
    f_in,
    f_out,
    src_dir,
    trg_dir,
    modules=None,
    crs="EPSG:26910",
    extra=(),
):
    """
    Command-line interface for transferring hotstart data from one grid to another.
    Arguments
    ---------
        yaml      Path to the YAML file (e.g., hotstart_from_hotstart.yaml).
    Options
    -------
        f_in      Hotstart input file path (e.g., hotstart_it=480000.nc).
        f_out     Hotstart output file path (e.g., hotstart_480000_franks.nc).
        src_dir   Source directory containing hgrid.gr3, vgrid.in, and param.nml.
        trg_dir   Target directory where the hotstart will be re-written.
        modules   Modules to be transferred to/from hotstart files.
        crs       Coordinate system (default: EPSG:26910).
        extra     Additional key-value pairs for environment variables (e.g., --key value).
    Examples
    --------
        bds hot_from_hot ./hotstart_from_hotstart.yaml --f_in ./baseline_sim_dir/hotstart_it=480000.nc --f_out ./franks_sim_dir/hotstart_480000_franks.nc --src_dir ./baseline_sim_dir/ --trg_dir ./franks_sim_dir/
    """
    # Ensure input and output directories exist
    if not os.path.exists(src_dir):
        raise ValueError(f"Source directory {src_dir} does not exist.")
    if not os.path.exists(trg_dir):
        raise ValueError(f"Target directory {trg_dir} does not exist.")

    # Parse extra arguments into a dictionary (expects --key value pairs)
    envvar = {}
    key = None
    for item in extra:
        if item.startswith("--"):
            key = item.lstrip("-")
        elif key is not None:
            envvar[key] = item
            key = None
    if key is not None:
        raise ValueError(f"No value provided for extra argument: {key}")

    # Convert empty tuple to None for modules
    if modules == () or modules is None:
        modules = None
    else:
        modules = list(modules)

    # Call the hotstart transfer function
    hotstart_newgrid(
        yaml,
        f_in,
        f_out,
        src_dir,
        trg_dir,
        modules=modules,
        crs=crs,
        envvar=envvar if envvar else None,
    )


if __name__ == "__main__":
    """Main function to handle hotstart transfer."""
    hotstart_newgrid_cli()
    # os.chdir("D:/schism/hotstart_transfer_test")
    # yaml = "./hotstart_from_hotstart.yaml"
    # f_in = "./baseline_sim_dir/hotstart_it=480000.nc"
    # f_out = "./hotstart_480000_franks.nc"
    # src_dir = "./baseline_sim_dir/"
    # trg_dir = "./franks_sim_dir/"

    # hotstart_newgrid(
    #     yaml,
    #     f_in,
    #     f_out,
    #     src_dir,
    #     trg_dir,
    # )
