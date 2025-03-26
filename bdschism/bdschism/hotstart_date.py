#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Use example as command-line interface function:
# python hotstart_date.py --fn ./hotstart.nc --hotstart 2024-6-24 --runstart 2024-6-24

# or with bdschism in your environment::

# hot_date --fn ./hotstart.nc --hotstart 2024-6-24 --runstart 2024-6-24

import xarray as xr
import pandas as pd
import click
from pathlib import Path


def set_hotstart_date(fn, run_start, restart_time, outprefix, dt):
    """Change timestamp and date implied by hotstart."""
    run_start = pd.to_datetime(run_start)
    run_start_str = run_start.strftime("%Y-%m-%dT%H:%M")
    restart_time = pd.to_datetime(restart_time)

    restart_sec = (restart_time - run_start).total_seconds()
    restart_timestr = restart_time.strftime("%Y%m%d")
    nsteps = int(restart_sec / dt)
    outfile = f"{outprefix}.{restart_timestr}.{nsteps}.nc"

    click.echo(
        f"Restarting on {restart_time}. nsteps (iterations) = {nsteps}, elapsed secs at restart = {restart_sec}"
    )
    click.echo(f"Time origin of run is {run_start_str}")
    click.echo(f"Output file is {outfile}")

    with xr.open_dataset(fn) as ds:
        ds.variables["time"][:] = restart_sec
        ds.variables["nsteps_from_cold"][:] = nsteps
        ds.variables["iths"][:] = nsteps
        ds.variables["ifile"][:] = 1
        ds.attrs["time_origin_of_simulation"] = run_start_str
        ds.to_netcdf(outfile)


@click.command(
    help=(
        "The script will change the necessary date attributes in a hotstart file.\n\n"
        "Example:\n"
        "  hot_date --fn ./hotstart.nc --run_start 2024-6-24 --restart_time 2024-6-24"
    )
)
@click.option(
    "--fn",
    default="./hotstart.nc",
    type=click.Path(exists=True, path_type=Path),
    help="Hotstart *.nc filename. [default: ./hotstart.nc]",
)
@click.option(
    "--run_start",
    required=True,
    type=str,
    help="Run start date in format YEAR-MONTH-DAY, e.g., 2024-6-1.",
)
@click.option(
    "--restart_time",
    required=True,
    type=str,
    help="Hotstart restart date in format YEAR-MONTH-DAY, e.g., 2024-6-24.",
)
@click.option(
    "--outprefix",
    default="hotstart",
    type=str,
    help=(
        "Output prefix for the output .nc file. If outprefix is just 'hot', "
        "you would get hot.20240624.109440. [default: hotstart]"
    ),
)
@click.option(
    "--dt",
    default=90,
    type=int,
    help="Timestep in seconds. [default: 90]",
)
def set_hotstart_date_cli(fn, run_start, restart_time, outprefix, dt):
    """CLI for setting hotstart date."""
    set_hotstart_date(fn, run_start, restart_time, outprefix, dt)


if __name__ == "__main__":
    set_hotstart_date_cli()
