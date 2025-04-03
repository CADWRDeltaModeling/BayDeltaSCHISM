#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Raymond Hoang (raymond.hoang@water.ca.gov)
# 20220728

"""
Script to convert various data formats (from calsim, csv files) into
SCHISM flux, salt and temp time history (.th) files
"""
from schimpy import model_time
from pyhecdss import get_ts
from schimpy.unit_conversions import CFS2CMS, ec_psu_25c
from vtools.functions.interpolate import rhistinterp
from vtools.functions.filter import ts_gaussian_filter
from vtools.data.vtime import minutes
import matplotlib.pylab as plt
import pandas as pd
from argparse import ArgumentParser
import yaml
import os
import click


def read_csv(file, var, name, p=2.0):
    """
    Reads in a csv file of monthly boundary conditions and interpolates
    Outputs an interpolated DataFrame of that variable
    """
    forecast_df = pd.read_csv(
        os.path.join(dir, file), index_col=0, header=0, parse_dates=True
    )
    forecast_df.index = forecast_df.index.to_period("M")
    interp_series = rhistinterp(forecast_df[var].astype("float"), dt, p=p)
    interp_df = pd.DataFrame()
    interp_df[[name]] = pd.DataFrame({var: interp_series})
    return interp_df


def read_dss(file, pathname, sch_name=None, p=2.0):
    """
    Reads in a DSM2 dss file and interpolates
    Outputs an interpolated DataFrame of that variable
    """
    ts15min = pd.DataFrame()
    print(pathname)
    ts = get_ts(os.path.join(dir, file), pathname)
    for tsi in ts:
        path_lst = (tsi[0].columns.values[0]).split("/")
        path_e = path_lst[5]
        tt = tsi[0][start_date:end_date]
        pidx = pd.period_range(start_date, tt.index[-1], freq=dss_e2_freq[path_e])
        ptt = pd.DataFrame(tt.values[:, 0], pidx)
        if p != 0:
            ts15min[[sch_name]] = rhistinterp(ptt, dt, p=p).reindex(df_rng)
        elif p == 0:
            ts15min[[sch_name]] = rhistinterp(ptt, dt).reindex(df_rng)
        else:
            ts15min[[sch_name]] = tsi[0]
    if ts15min.empty:
        raise ValueError(f"Warning: DSS data not found for {b}")
    return ts15min


@click.command()
@click.argument("config_yaml", type=click.Path(exists=True))
def main(config_yaml):

    with open(config_yaml, "r") as f:
        config = yaml.safe_load(f)

    dir = config["dir"]

    # Read in parameters from the YAML file
    source_map_file = os.path.join(dir, config["file"]["source_map_file"])
    schism_flux_file = os.path.join(dir, config["file"]["schism_flux_file"])
    schism_salt_file = os.path.join(dir, config["file"]["schism_salt_file"])
    schism_temp_file = os.path.join(dir, config["file"]["schism_temp_file"])
    out_file_flux = os.path.join(config["file"]["out_file_flux"])
    out_file_salt = os.path.join(config["file"]["out_file_salt"])
    out_file_temp = os.path.join(config["file"]["out_file_temp"])
    boundary_kinds = config["param"]["boundary_kinds"]
    sd = config["param"]["start_date"]
    ed = config["param"]["end_date"]

    dt = minutes(15)
    start_date = pd.Timestamp(year=sd[0], month=sd[1], day=sd[2])
    end_date = pd.Timestamp(year=ed[0], month=ed[1], day=ed[2])
    df_rng = pd.date_range(start_date, end_date, freq=dt)
    source_map = pd.read_csv(source_map_file, header=0)

    # Read in the reference SCHISM flux, salt and temperature files
    # to be used as a starting point and to substitute timeseries not
    # available from other data sources.

    flux = pd.read_csv(
        schism_flux_file, index_col=0, parse_dates=[0], sep="\\s+", header=0
    )
    salt = pd.read_csv(
        schism_salt_file, header=0, parse_dates=True, index_col=0, sep="\\s+"
    )
    temp = pd.read_csv(
        schism_temp_file, header=0, parse_dates=True, index_col=0, sep="\\s+"
    )

    dss_e2_freq = {"1HOUR": "H", "1DAY": "D"}

    for boundary_kind in boundary_kinds:

        source_map = source_map.loc[source_map["boundary_kind"] == boundary_kind]

        if boundary_kind == "flow":
            dd = flux.copy().reindex(df_rng)
            out_file = out_file_flux
        elif boundary_kind == "ec":
            dd = salt.copy().reindex(df_rng)
            out_file = out_file_salt
        elif boundary_kind == "temp":
            dd = temp.copy().reindex(df_rng)
            out_file = out_file_temp

        for index, row in source_map.iterrows():
            dfi = pd.DataFrame()
            name = row["schism_boundary"]
            source_kind = row["source_kind"]
            source_file = str(row["source_file"])
            derived = str(row["derived"]).capitalize() == "True"
            var = row["var"]
            sign = row["sign"]
            convert = row["convert"]
            p = row["rhistinterp_p"]
            formula = row["formula"]
            print(f"processing {name}")

            if source_kind == "SCHISM":
                # Simplest case: use existing reference SCHISM data; do nothing
                print("Use existing SCHISM input")

            elif source_kind == "CSV":
                # Substitute in an interpolated monthly forecast
                if derived:
                    print(
                        f"Updating SCHISM {name} with derived timeseries\
                        expression: {formula}"
                    )
                    csv = pd.DataFrame()
                    vars = var.split(";")
                    for v in vars:
                        csv[[v]] = read_csv(source_file, v, name, p=p)
                    dts = eval(formula).to_frame(name).reindex(df_rng)
                    dfi = ts_gaussian_filter(dts, sigma=100)
                else:
                    print(
                        f"Updating SCHISM {name} with interpolated monthly\
                        forecast {var}"
                    )
                    dfi = read_csv(source_file, var, name, p=p)

            elif source_kind == "DSS":
                # Substitute in CalSim value.
                if derived:
                    vars_lst = var.split(";")
                    print(
                        f"Updating SCHISM {name} with derived timeseries\
                        expression: {formula}"
                    )
                    dss = pd.DataFrame()

                    for pn in vars_lst:
                        b = pn.split("/")[2]
                        dss[[b]] = read_dss(
                            source_file, pathname=pn, sch_name=name, p=p
                        )
                    ## quick fix for to use last year pattern as formula
                    ## input
                    clip_1ybackward_start = start_date - pd.DateOffset(years=1)
                    clip_1ybackward_end = end_date - pd.DateOffset(years=1)
                    flux_clipped = flux[clip_1ybackward_start:clip_1ybackward_end]
                    ## reset clipped flux index to dss year
                    flux_clipped.index = flux_clipped.index.map(
                        lambda x: x.replace(year=start_date.year)
                    )
                    dts = eval(formula).to_frame(name).reindex(df_rng)
                    dfi = ts_gaussian_filter(dts, sigma=100)
                else:
                    print(f"Updating SCHISM {name} with DSS variable {var}")
                    dfi = read_dss(source_file, pathname=var, sch_name=name, p=p)

            elif source_kind == "CONSTANT":
                # Simply fill with a constant specified.
                dd[name] = float(var)
                dfi["datetime"] = df_rng
                dfi = dfi.set_index("datetime")

                dfi[name] = [float(var)] * len(df_rng)
                print(f"Updating SCHISM {name} with constant value of {var}")

            # Do conversions.
            if convert == "CFS_CMS":
                dfi = dfi * CFS2CMS * sign
            elif convert == "EC_PSU":
                dfi = ec_psu_25c(dfi) * sign
            else:
                dfi = dfi

            # Trim dfi so that it starts where flux ends, so that dfi doesn't
            # overwrite any historical data
            dfi = dfi[dfi.index >= flux.index[-1]]

            # Update the dataframe.
            dd.update(dfi, overwrite=True)

            # print(dfi)

        # print(dd)

        # Format the outputs.
        dd.index.name = "datetime"
        dd.to_csv(
            os.path.join(dir, out_file),
            header=True,
            date_format="%Y-%m-%dT%H:%M",
            float_format="%.4f",
            sep=" ",
        )

        dd.plot()

    print("Done")
    plt.show()


if __name__ == "__main__":
    main()
