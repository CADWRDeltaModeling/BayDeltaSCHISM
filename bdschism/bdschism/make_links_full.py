#!/usr/bin/env python
import os
import datetime
import click
from pathlib import Path
import pandas as pd




@click.command(
    help=(
        "The tool create symblic links to existing hrrr/narr/other sources containing air \
         pressure, solar radiation and precipitation data. Before year 2020, narr radiation \
         and precipitation and baydelta schism air pressure are linked. After 2020, hrrr \
         data are linked \n\n"
        "Example:\n"
        "  make_links_full --source ../data/atoms --dest ./sflux --start 2020-1-1 --end 2022-2-2 "
    )
)

@click.option(
    "--source",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="folder containing original air netcdf data files.",
)

@click.option(
    "--dest",
    required=True,
    default="./sflux",
    type=click.Path(exists=True, path_type=Path),
    help="folder where symbolic links will be put. [default: ./sflux]",
)


@click.option(
    "--start_date",
    required=True,
    type=str,
    help="data file start date in format YEAR-MONTH-DAY, e.g., 2020-1-1.",
)

@click.option(
    "--end_date",
    required=True,
    type=str,
    help="data file end date in format YEAR-MONTH-DAY, e.g., 2022-2-2.",
)

def make_links(start_date,end_date,source,dest):

    start = pd.to_datetime(start_date)
    dt = pd.Timedelta(days=1)
    end = pd.to_datetime(end_date)
    current = start
    if (current >= end):
        print(f'ERROR: Start date {start.strftime("%b %d, %Y")} is after end date {end.strftime("%b %d, %Y")}')
    nfile = 0

    hrrr_transition = pd.to_datetime("2020-1-1")

    src_dir = source.joinpath("baydelta_sflux_v20220916") 
    src_dir_narr = source.joinpath("NARR") 
    src_dir_hrrr = source.joinpath("hrrr")
    link_dir = dest

    while (current <= end):
        # Air data
        # Ours
        if current<hrrr_transition:
            src_str_air = os.path.join(src_dir,"baydelta_schism_air_%s%02d%02d.nc" % (current.year, current.month, current.day))
            # NARR
            # src_str_air = os.path.join(src_dir_narr, "%4d_%02d/narr_air.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))
            src_str_rad = os.path.join(src_dir_narr, "%4d_%02d/narr_rad.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))
            src_str_prc = os.path.join(src_dir_narr, "%4d_%02d/narr_prc.%4d_%02d_%02d.nc" % (current.year, current.month, current.year, current.month, current.day))

        ### HRRR
        else:
            src_str_atm = os.path.join(src_dir_hrrr,"%4d/hrrr_%4d%02d%02d00.nc" % (current.year, current.year, current.month, current.day))
            src_str_air = src_str_atm
            src_str_rad = src_str_atm
            src_str_prc = src_str_atm

        nfile += 1
        link_str_air = os.path.join(link_dir, "sflux_air_1.%04d.nc" % (nfile))
        link_str_rad = os.path.join(link_dir, "sflux_rad_1.%04d.nc" % (nfile))
        link_str_prc = os.path.join(link_dir, "sflux_prc_1.%04d.nc" % (nfile))
        if not os.path.exists(link_str_air):
            os.symlink(src_str_air, link_str_air)
        if not os.path.exists(link_str_rad):
            os.symlink(src_str_rad, link_str_rad)
        if not os.path.exists(link_str_prc):
            os.symlink(src_str_prc, link_str_prc)
        current += dt


if __name__ == "__main__":
    make_links()
