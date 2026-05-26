#!/usr/bin/env python
# -*- coding: utf-8 -*-import pandas as pd

# Use example as command-line interface function:
# python hotstart_nudging_data.py --start_date 2018-02-19  --nudge_len 300 --dest_dir . --repo_dir $repo_path
# or with bdschism in your environment::
# hot_nudge_data --start_date 2018-02-19  --nudge_len 300 --dest_dir . --repo_dir $repo_path

import matplotlib.pyplot as plt
from dms_datastore.read_ts import *
from dms_datastore.dstore_config import *
from dms_datastore.read_multi import *
from vtools.functions.unit_conversions import *
from vtools.data.vtime import days
import glob
import pathlib
import pandas as pd
import os
import logging
import click

logger = logging.getLogger(__name__)
from bdschism.logging_config import configure_logging, resolve_loglevel


stations = [
    "anh",
    "benbr",
    "hsl",
    "bts",
    "snc",
    "ibs",
    "cyg",
    "hun",
    "bdl",
    "fmb",
    "msl",
    "cse",
    "gzl",
    "ryc",
    "hon",
    "c24",
    "pct",
    "flt",
    "mrz",
    "pct",
    "mal",
    "pts",
    "carqb",
    "benbr",
    "co5",
    "ssi",
    "emm",
    "sdi",
    "blp",
    "jer",
    "sjj",
    "dsj",
    "frp",
    "fal",
    "bet",
    "hol2",
    "hll",
    "orq2",
    "frk",
    "holm",
    "bac",
    "mdm",
    "dbi",
    "ori",
    "oh4",
    "mab",
    "pri",
    "ppt",
    "trn",
    "rindg",
    "sjc",
    "rri",
    "sjg",
    "bdt",
    "dvi",
    "sjr",
    "orx",
    "pdup",
    "tpp",
    "uni",
    "sga",
    "gle",
    "old",
    "twa",
    "orm",
    "oad",
    "trp",
    "glc2",
    "wci",
    "vcu",
    "mab",
    "mtb",
    "rri2",
    "mdmzq",
    "sdc",
    "ges",
    "swe",
    "gss",
    "nmr",
    "sus",
    "sss",
    "sut",
    "snod",
    "gln",
    #"rye",
    "ryf",
    "rvb",
    "mir",
    "dws",
    "lib",
    "ucs",
    "has",
    "srh",
    "awb",
    "afo",
    "hst",
    "ist",
    "ssw",
    "von",
    "few",
    "fre",
    "wlk",
    "gys",
    "god",
    "sal",
]

# Stations where an "upper" and "lower" sublocation occur and we must distinguish the upper
add_upper = ["anh", "cse", "mrz", "emm", "mal", "pts"]


def hotstart_nudge_data(sdate, ndays, dest, repo = "screened"):

    t0 = sdate
    nudgelen = pd.Timedelta(days=ndays)


    ##
    station_df = station_dbase()

    buf = days(5)
    sdata = t0 - buf
    edata = t0 + nudgelen + buf

    station_df = station_df.loc[stations]

    no_such_file = []
    tndx = pd.date_range(t0, t0 + nudgelen, freq="h")
    all_vars = ["temperature", "salinity"]
    used_stations = set()
    nudging_dfs = {}
    accepted_loc = []
    for label_var in all_vars:
        var = {"temperature": "temp", "salinity": "ec"}[
            label_var
        ]  # working variable for data
        logger.info(f"Working on variable: {label_var},{var}")
        vals = []
        accepted = {}

        for ndx, row in station_df.iterrows():
            x = row.x
            y = row.y
            fndx = ndx + "@upper" if ndx in add_upper else ndx

            try:
                subloc = "upper" if ndx in add_upper else None
                logger.info(f"Reading {var} data for {ndx} with subloc={subloc}")
                ts = read_ts_repo(
                    ndx, var, subloc=subloc, repo=repo
                )
                ts = ts.loc[sdata:edata]
                ts = ts.interpolate(limit=4)
                if ts.shape[1] > 1:
                    ts = ts.mean(axis=1)
                    ts.name = "value"
                else:
                    ts = ts.squeeze()
                if var == "temp":
                    topquant = ts.quantile(q=0.25)
                    if topquant > 35:
                        logger.warning("Transforming F to C: 25th percentile > 35 deg, assuming Fahrenheit")
                        ts = fahrenheit_to_celsius(ts)
                    if ndx in ["clc"] and (ts < 0.0).all():
                        ts = celsius_to_farenheit(ts)
                elif var == "ec":
                    ts = ec_psu_25c(ts)
                else:
                    raise ValueError(
                        f"Haven't worked out transforms needed except for {var}, only salt/temp"
                    )

                val = ts.at[t0]
                if not np.isnan(val):
                    vals.append((ndx, x, y, val))

                # This is the fraction of missing data
                ts = ts.reindex(tndx)
                gap_frac = ts.isnull().sum() / len(ts)
                logger.debug(f"Fraction of missing data for {ndx} {var}: {gap_frac:.3f}")
                if gap_frac < 0.25:
                    logger.info(f"Accepted {ndx} {var}")
                    ts.columns = [ndx]
                    ts = ts.fillna(-9999.0)
                    accepted[ndx] = ts
                    if ndx not in used_stations:
                        accepted_loc.append((ndx, x, y))
                        used_stations.add(ndx)

            except Exception as err:
                logger.warning(f"Error processing {ndx} {var}: {err}")
        var_df = pd.DataFrame(data=vals, columns=("station", "x", "y", f"{label_var}"))
        var_df.set_index("station")
        var_df.to_csv(
            os.path.join(dest, f"hotstart_data_{label_var}.csv"),
            sep=",",
            float_format="%.2f",
        )

        # Check if accepted is empty. If so, throw an exception
        if accepted == {}:
            raise ValueError(f"No data found for {label_var} in {repo}")
        else:
            nudging_df = pd.concat(accepted, axis=1)
        nudging_df.index.name = "datetime"
        nudging_dfs[label_var] = nudging_df
        logger.info(nudging_df)

    obs_xy = pd.DataFrame(data=accepted_loc, columns=["site", "x", "y"])
    logger.info("Writing nudging data files")

    for label_var in all_vars:
        nudging_dfs[label_var].to_csv(
            os.path.join(dest, f"nudging_data_{label_var}.csv"),
            sep=",",
            float_format="%.2f",
        )
        # Deprecated
        # nudging_dfs[label_var].reindex(columns=obs_xy.site).to_csv(f"nudging_data_{label_var}_b.csv",sep=",",float_format="%.2f")

    obs_xy = obs_xy.set_index("site", drop=True)
    obs_xy.to_csv(os.path.join(dest, f"obs_xy.csv"), sep=",", float_format="%.2f")

    if no_such_file:
        logger.info("No data files found for: %s", no_such_file)


@click.command(help="""\n
    Download station data from repo and save in csv format for hotstart nudging.\n
    Usage:\n
    bds hot_nudge_data --start_date 2018-02-19 --nudge_len 300 --dest_dir . --repo_dir $repo_path\n
    """)
@click.option(
    "--start_date",
    required=True,
    help="starting date of SCHISM model, must be \
                    format like 2018-02-19",
)
@click.option(
    "--nudge_len",
    required=True,
    type=int,
    help="number of days to be downloaded \
                        from starting date",
)
@click.option(
    "--dest_dir",
    default=".",
    help="folder to store downloaded obs nudging data. \
                        Default is current folder",
)
@click.option(
    "--repo",
    default="screened",
    help="repo of observed time series. \
                        Default is screened",
)
@click.option("--logdir", type=click.Path(path_type=pathlib.Path), default="logs")
@click.option("--debug", is_flag=True)
@click.option("--quiet", is_flag=True)
@click.help_option("-h", "--help")
def hotstart_nudge_data_cli(
    start_date, nudge_len, dest_dir, repo, logdir, debug, quiet
):
    """
    Command-line interface for the hotstart_nudge_data function.
    """

    level, console = resolve_loglevel(
        debug=debug,
        quiet=quiet,
    )
    configure_logging(
        package_name="bdschism",
        level=level,
        console=console,
        logdir=logdir,
        logfile_prefix="hotstart_nudge_data",
    )

    try:
        sdate = pd.to_datetime(start_date)
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    hotstart_nudge_data(sdate, nudge_len, dest_dir, repo)


if __name__ == "__main__":
    hotstart_nudge_data_cli()
