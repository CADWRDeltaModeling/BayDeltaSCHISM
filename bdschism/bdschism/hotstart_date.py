#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Use example as command-line interface function:
# python hotstart_date.py --fn ./hotstart.nc --hotstart 2024-06-24 --runstart 2024-06-24

# or with bdschism in your environment::

# hot_date --fn ./hotstart.nc --hotstart 2024-06-24 --runstart 2024-06-24

import logging

import xarray as xr
import pandas as pd
import click
from pathlib import Path

logger = logging.getLogger(__name__)


def set_hotstart_date(fn, run_start, restart_time, outprefix, dt):
    """Change timestamp and date implied by hotstart."""
    run_start = pd.to_datetime(run_start)
    run_start_str = run_start.strftime("%Y-%m-%dT%H:%M")
    restart_time = pd.to_datetime(restart_time)

    restart_sec = (restart_time - run_start).total_seconds()
    restart_timestr = restart_time.strftime("%Y%m%d")
    nsteps = int(restart_sec / dt)
    outfile = f"{outprefix}.{restart_timestr}.{nsteps}.nc"

    logger.info(
        "Restarting on %s. nsteps (iterations) = %d, elapsed secs at restart = %g",
        restart_time, nsteps, restart_sec,
    )
    logger.info("Time origin of run is %s", run_start_str)
    logger.info("Output file is %s", outfile)

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
        "  hot_date --fn ./hotstart.nc --run_start 2024-06-24 --restart_time 2024-06-24"
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
    help="Run start date in format YEAR-MONTH-DAY, e.g., 2024-06-01.",
)
@click.option(
    "--restart_time",
    required=True,
    type=str,
    help="Hotstart restart date in format YEAR-MONTH-DAY, e.g., 2024-06-24.",
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
@click.option(
    "--logdir",
    default=None,
    type=click.Path(),
    help="Directory for log files.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.help_option("-h", "--help")
def set_hotstart_date_cli(fn, run_start, restart_time, outprefix, dt, logdir, debug):
    """CLI for setting hotstart date."""
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="hot_date",
    )
    set_hotstart_date(fn, run_start, restart_time, outprefix, dt)


if __name__ == "__main__":
    set_hotstart_date_cli()
