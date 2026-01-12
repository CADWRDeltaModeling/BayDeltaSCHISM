#!/usr/bin/env python
import os
import datetime
import click
from pathlib import Path
import pandas as pd
from bdschism.settings import get_settings
from schimpy.schism_yaml import load
import shutil
import platform


op_dic = {"symlink": os.symlink, "copy": shutil.copy}
os_name = platform.system().lower()

@click.command(
    """
    Create symbolic links to existing meteorological data sources.
    This command-line tool creates symbolic links to existing HRRR/NARR/other sources
    containing air pressure, solar radiation, and precipitation data. The tool handles
    different data sources based on temporal transitions:
    - Before 2020: NARR radiation and precipitation, plus BayDelta SCHISM air pressure
    - After 2020: HRRR data
    Parameters
    ----------
    sdate : str, optional
        Data file start date in format YEAR-MONTH-DAY (e.g., 2020-1-1).
        If not provided, defaults to run_start_date from config file.
    edate : str, optional
        Data file end date in format YEAR-MONTH-DAY (e.g., 2022-2-2).
        If not provided, defaults to run_end_date from config file.
    config : pathlib.Path, optional
        Path to configuration file specifying source data folders.
        If not provided, attempts to use sflux_config from bdschism config directory.
    dest : pathlib.Path, optional
        Destination folder where symbolic links will be created.
        Default is './sflux'. Must be an existing directory.
    Raises
    ------
    FileNotFoundError
        If the configuration file is not found or does not exist.
    ValueError
        If a parameter is not found in sflux_specification or if a source
        is missing required 'directory' or 'rel_path' fields.
    Notes
    -----
    The function reads configuration from a YAML file that specifies:
    - Source data directories
    - Relative paths with date formatting
    - Use dates for transitioning between data sources
    Linked files are named with pattern: sflux_{parameter}_{index}.{counter:04d}.nc
    Examples
    --------
    >>> make_links --config sflux.yaml --dest ./sflux --sdate 2020-1-1 --edate 2022-2-2
    """,
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
    """
    Make links for synthetic flux data based on the specified date range and configuration.
    Parameters
    ----------
    sdate : str or None
        The start date for the linking process in 'YYYY-MM-DD' format. If None, the start date will be taken from the configuration file.
    edate : str or None
        The end date for the linking process in 'YYYY-MM-DD' format. If None, the end date will be taken from the configuration file.
    config : str or None
        The path to the configuration file (YAML format). If None or the file does not exist, it will attempt to find the configuration file from the default location.
    dest : str
        The destination directory where the links will be created.
    Raises
    ------
    FileNotFoundError
        If the configuration file is not found at the specified path or default location.
    ValueError
        If a parameter in the sflux specification is missing required fields (label, directory, or rel_path).
    Exception
        If the start date is after the end date.
    Notes
    -----
    This function reads the configuration from a YAML file, retrieves the necessary parameters, and creates symbolic links for the synthetic flux data files based on the specified date range. The linking operation is determined by the link style specified in the configuration.
    """

    ## first read in bds_config.yaml to get source folder   
    settings = get_settings()

    ## if config is none, try trying to find config file from
    ## bdschism settings
    if config is None:
        if hasattr(settings, "sflux_config"):
            config = Path(settings.sflux_config)
            if not os.path.exists(config):
                raise FileNotFoundError(
                f"Configuration file {config} not found. Please provide a valid config file."
            )
        else:
            raise FileNotFoundError(
                "No configuration file not provided and sflux_config not found in bds_config.yaml. Please provide a valid config file."
            )
    
    ## if config is given but file does not exist, raise error
    else:
        if not os.path.exists(config):
            raise FileNotFoundError(
                f"Configuration file {config} not found. Please provide a valid config file."
            )

    ## read in config file using schism_yaml
    f= open(config, "r")
    sflux_config = load(f)
    f.close()

    if sdate is None:
        ## check run_start_date in sflux_config 
        ## if not found, raise error
        if not( hasattr(settings, "run_start_date")):
            raise ValueError("run_start_date is not provided, and not found in User Env,BDSCHISM or Local Setting." \
            " Please provide run_start_date.")
        sdate = settings.run_start_date
    if edate is None:
        if not(hasattr(settings, "run_end_date")):
            raise ValueError("run_end_date is not provided, and not found in User Env,BDSCHISM or Local Setting." \
            " Please provide run_end_date.")
        edate = settings.run_end_date
    start = pd.to_datetime(sdate)
    dt = pd.Timedelta(days=1)
    end = pd.to_datetime(edate)
    current = start
    if (current >= end):
        print(f'ERROR: Start date {start.strftime("%b %d, %Y")} is after end date {end.strftime("%b %d, %Y")}')
    nfile = 1


    sflux_specification = sflux_config["sflux_specification"]
    link_dir = dest

    link_style = settings.get("link_style")
    op = op_dic["symlink"]
    if link_style is None:
        print("no link style specified in bds_config.yaml, using symlink as default")  
    else:
        op_id = link_style[os_name]
        op = op_dic[op_id]
        print(f"Using {link_style[os_name]} as link style on {os_name} system")
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
            
            link_str = os.path.join(link_dir, f"sflux_{par}_1.{nfile:04d}.nc")
            if not os.path.exists(link_str):
                op(src_str, link_str)
                print(f"Linking {src_str} to {link_str}")
            else:
                print(f"Link {link_str} already exists. Skipping.")
        nfile += 1
        current += dt


if __name__ == "__main__":
    make_links()
