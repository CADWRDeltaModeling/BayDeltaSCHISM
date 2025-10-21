#!/usr/bin/env python
import os
import datetime
import click
from pathlib import Path
import pandas as pd
from bdschism.settings import get_settings
from schimpy.schism_yaml import load
import shutil
import pdb


@click.command(
    help=(
        "The tool create symblic links to existing hrrr/narr/other sources containing air \
         pressure, solar radiation and precipitation data. Before year 2020, narr radiation \
         and precipitation and baydelta schism air pressure are linked. After 2020, hrrr \
         data are linked \n\n"
        "Example:\n"
        "  make_links_full --config sflux.yaml --dest ./sflux --sdate 2020-1-1 --edate 2022-2-2 "
    )
)

@click.option(
    "--config",
    required=False,
    type=click.Path(exists=True, path_type=Path),
    help="configuration file specifying source data folder, if not given, use sflux setting yaml in bdschism config.",
)

@click.option(
    "--dest",
    required=False,
    default="./sflux",
    type=click.Path(exists=True, path_type=Path),
    help="folder where symbolic links will be put. [default: ./sflux]",
)


@click.option(
    "--sdate",
    required=False,
    type=str,
    help="data file start date in format YEAR-MONTH-DAY, e.g., 2020-1-1.",
)

@click.option(
    "--edate",
    required=False,
    type=str,
    help="data file end date in format YEAR-MONTH-DAY, e.g., 2022-2-2.",
)

def make_links(sdate,edate,config,dest):

    ## first read in bds_config.yaml to get source folder
    
    settings = get_settings()

    ## if config is none, try trying to find config file from
    ## bdschism/bdschism/config/bds_config.yaml
    if config is None or not os.path.exists(config):
        if hasattr(settings, "sflux_config"):
            config = Path(settings.sflux_config)
            if not os.path.exists(config):
                raise FileNotFoundError(
                f"Configuration file {config} not found. Please provide a valid config file."
            )
    

    ## read in config file using schism_yaml
    f= open(config, "r")
    sflux_config = load(f)
    f.close()

    if sdate is None:
        sdate = sflux_config["run_start_date"]
    if edate is None:
        edate = sflux_config["run_end_date"]

    start = pd.to_datetime(sdate)
    dt = pd.Timedelta(days=1)
    end = pd.to_datetime(edate)
    current = start
    if (current >= end):
        print(f'ERROR: Start date {start.strftime("%b %d, %Y")} is after end date {end.strftime("%b %d, %Y")}')
    nfile = 0

    synthetic_start_date = sflux_config["synthetic_start_date"]
    transition_start = pd.to_datetime(synthetic_start_date)

    sflux_specification = sflux_config["sflux_specification"]
    link_dir = dest

    while (current <= end):
        for par in sflux_specification.keys():
            par_spec = sflux_specification.get(par, None)
            if par_spec is None:
                raise ValueError(f"Parameter {par} not found in sflux_specification.")
            ## retrieve list of sources for this parameeter and sort list index by use_after date
            use_dates = [s.get("use_after", "1900-01-01") for s in par_spec]
            use_dates = [pd.to_datetime(d) for d in use_dates]
            ## sort use_dates and get the indices
            sorted_dates = sorted(use_dates)
            sorted_indices = sorted(range(len(use_dates)), key=lambda i: use_dates[i])
            ## find out the insertion point of current date in sorted_dates
            insert_point = 0
            for i, d in enumerate(sorted_dates):
                if current >= d:
                    insert_point = i
                else:
                    break
            selected_index = sorted_indices[insert_point]
            selected_source = par_spec[selected_index]
            label = selected_source.get("label", None)
            directory = selected_source.get("directory", None)
            rel_path = selected_source.get("rel_path", None)
            if  directory is None or rel_path is None:
                raise ValueError(f"Parameter {par} source {label} is missing directory or rel_path.")
            src_str = os.path.join(directory, rel_path.format(year=current.year, month=current.month, day=current.day))
            nfile += 1
            link_str = os.path.join(link_dir, f"sflux_{par}_1.{nfile:04d}.nc")
            if not os.path.exists(link_str):
                ## if system is windows copy files
                if os.name == 'nt':    
                    shutil.copy(src_str, link_str)
                    print(f"Copying {src_str} to {link_str}")
                else:
                    os.symlink(src_str, link_str)
                    print(f"Linking {src_str} to {link_str}")
            else:
                print(f"Link {link_str} already exists. Skipping.")
        current += dt


if __name__ == "__main__":
    make_links()
