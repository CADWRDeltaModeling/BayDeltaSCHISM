# -*- coding: utf-8 -*-
"""
Script to convert various data formats (from calsim, csv files) into
SCHISM flux, salt and temp time history (.th) files
"""
from vtools.functions.unit_conversions import CFS2CMS, ec_psu_25c
from vtools.functions.interpolate import rhistinterp
from vtools.functions.filter import ts_gaussian_filter
from vtools.data.vtime import minutes
from schimpy.util.yaml_load import yaml_from_file, csv_from_file
from bdschism.parse_cu import orig_pert_to_schism_dcd_yaml
from bdschism.read_dss import read_dss
import matplotlib.pylab as plt
import numpy as np
import pandas as pd
import tempfile
import string
import yaml
import os
import click
import json


def read_csv(file, var, name, dt, p=2.0, interp=True):
    """
    Reads in a csv file of monthly boundary conditions and interpolates
    Outputs an interpolated DataFrame of that variable
    """
    forecast_df = pd.read_csv(file, index_col=0, header=0, parse_dates=True)
    forecast_df.index = forecast_df.index.to_period("M")

    # Check for % sign and convert to fraction
    if forecast_df[var].dtype == "object":  # Ensure it's a string column
        forecast_df[var] = forecast_df[var].str.strip()  # Remove extra spaces
        forecast_df[var] = forecast_df[var].apply(
            lambda x: float(x.strip("%")) / 100.0 if "%" in x else float(x)
        )
    else:
        forecast_df[var] = forecast_df[var].astype("float")

    if interp:
        interp_series = rhistinterp(forecast_df[var].astype("float"), dt, p=p)
    else:
        forecast_df.index = forecast_df.index.to_timestamp()
        interp_series = forecast_df[var].resample(dt).ffill()
    interp_df = pd.DataFrame()
    interp_df[[name]] = pd.DataFrame({var: interp_series})
    return interp_df


def clean_df(in_df):
    keep_rows = [0]
    for r in range(1, len(in_df.index)):
        if not (list(in_df.iloc[r, :]) == list(in_df.iloc[r - 1, :])):
            # keep the row where something changes and the row before (for plotting)
            if not r - 1 in keep_rows:
                keep_rows.append(r - 1)
            keep_rows.append(r)
    out_df = in_df.iloc[keep_rows, :]

    return out_df


def set_gate_fraction(
    dts_in, op_var="height", ubound=10, lbound=0, increment="month_fraction"
):
    """Adjusts the values of a specified operation variable in a DataFrame to represent fractional gate operations per month.

    This function processes a DataFrame containing time-indexed gate operation data (e.g., gate heights), and for each month,
    it sets a fraction of the time steps to the lower bound (`lbound`) and the remainder to the upper bound (`ubound`),
    based on the initial value of the operation variable for that month. Only rows where the operation variable is not
    already at the upper or lower bound are modified.

    Parameters
    ----------
    dts_in : pandas.DataFrame
        The input DataFrame with a DateTimeIndex and an operation variable column.
    op_var : str, optional
        The name of the column representing the operation variable to adjust (default is "height").
    ubound : numeric, optional
        The upper bound value for the operation variable (default is 10).
    lbound : numeric, optional
        The lower bound value for the operation variable (default is 0).
    increment : str, optional
        The increment type for grouping. Default is "month_fraction". Other supported types:
        month_fraction - Need to take any Percentage between 0 and 100 and convert them to days of month open
        month_days - Need to take number of days in a month and operate per days of month

    Returns
    -------
    pandas.DataFrame
        The modified DataFrame with the operation variable adjusted according to the calculated monthly fractions.

    Notes
    -----
    - The function assumes the DataFrame index is a pandas DateTimeIndex.
    - Only rows where the operation variable is not equal to `ubound` or `lbound` are considered for adjustment.
    - The fraction is determined by the ratio of the first value of the operation variable in the group to `ubound`.
    """
    if increment == "month_fraction":
        # Filter rows where height is not 10 or 0
        fraction_mask = (dts[op_var] != ubound) & (dts[op_var] != lbound)

        # Apply the mask to filter the DataFrame
        filtered_dts = dts[fraction_mask]

        dts_out = dts_in.copy()

        # Group the filtered DataFrame by month
        for month, group in filtered_dts.groupby(filtered_dts.index.to_period("M")):
            # Calculate the fraction
            fraction = group[op_var].iloc[0] / ubound

            # Get the first fraction of the month
            fraction_point = int(len(group) * fraction)
            first_indices = group.index[:fraction_point]
            second_indices = group.index[fraction_point:]

            # Set the first half to lbound and the second half to ubound
            dts_out.loc[first_indices, op_var] = lbound
            dts_out.loc[second_indices, op_var] = ubound
    elif increment == "month_days":
        # dts_out: PeriodIndex with daily freq, dts_in: PeriodIndex with monthly freq
        dts_out = dts_in.copy()
        # Convert PeriodIndex to DatetimeIndex before resampling
        if isinstance(dts_out.index, pd.PeriodIndex):
            dts_out.index = dts_out.index.to_timestamp()
        dts_out = dts_out.resample("D").ffill()
        # Now dts_out.index is DatetimeIndex with daily freq
        for month, group in dts_out.groupby(dts_out.index.to_period("M")):
            if month.to_timestamp() in dts_in.index.to_timestamp():
                days_ubound = int(round(dts_in.loc[month, op_var]))
            else:
                continue
            month_indices = group.index
            dts_out.loc[month_indices[:days_ubound], op_var] = float(ubound)
            dts_out.loc[month_indices[days_ubound:], op_var] = float(lbound)

    return dts_out


def set_gate_ops(boundary_kind, var_df, name, formula):
    form, ubound, lbound, increment = [part.strip() for part in formula.split(";")]
    var_df = eval(form).to_frame(name)
    if "dcc" in boundary_kind:
        dts = set_gate_fraction(
            var_df, op_var=name, ubound=ubound, lbound=lbound, increment=increment
        )
    return dts


def create_schism_bc(config_yaml, kwargs={}):

    config = yaml_from_file(config_yaml, envvar=kwargs)

    # Add config['config'] to kwargs if it exists, with kwargs taking precedence
    if "config" in config:
        merged_kwargs = {**config["config"], **kwargs}
        kwargs = merged_kwargs

    dir = config["dir"]

    # Overwrite if historical data is manipulated.
    # If forecast data is being applied, overwrite should be False
    overwrite = config["param"]["overwrite"]

    # Read in parameters from the YAML file
    source_map_file = os.path.join(dir, config["file"]["source_map_file"])
    schism_flux_file = os.path.join(dir, config["file"]["schism_flux_file"])
    schism_salt_file = os.path.join(dir, config["file"]["schism_salt_file"])
    schism_temp_file = os.path.join(dir, config["file"]["schism_temp_file"])
    schism_dcc_gate_file = None
    if "schism_dcc_gate_file" in config["file"]:
        schism_dcc_gate_file = os.path.join(dir, config["file"]["schism_dcc_gate_file"])
    out_file_flux = os.path.join(config["file"]["out_file_flux"])
    out_file_salt = os.path.join(config["file"]["out_file_salt"])
    out_file_temp = os.path.join(config["file"]["out_file_temp"])
    out_file_dcc_gate = None
    if "out_file_dcc_gate" in config["file"]:
        out_file_dcc_gate = os.path.join(config["file"]["out_file_dcc_gate"])
    boundary_kinds = config["param"]["boundary_kinds"]
    sd = config["param"]["start_date"]
    ed = config["param"]["end_date"]

    dt = minutes(15)
    start_date = pd.Timestamp(sd)
    end_date = pd.Timestamp(ed)
    df_rng = pd.date_range(start_date, end_date, freq=dt)
    # Read and process the source_map file
    source_map = csv_from_file(
        source_map_file, envvar=kwargs
    )  # pd.read_csv(fmt_string_file(source_map_file, kwargs), header=0)

    # Read in the reference SCHISM flux, salt and temperature files
    # to be used as a starting point and to substitute timeseries not
    # available from other data sources.

    flux = pd.read_csv(
        schism_flux_file,
        index_col=0,
        parse_dates=[0],
        sep="\\s+",
        header=0,
        comment="#",
    )
    salt = pd.read_csv(
        schism_salt_file,
        header=0,
        parse_dates=True,
        index_col=0,
        sep="\\s+",
        comment="#",
    )
    temp = pd.read_csv(
        schism_temp_file,
        header=0,
        parse_dates=True,
        index_col=0,
        sep="\\s+",
        comment="#",
    )
    dcc_gate = None
    if "dcc_gate" in boundary_kinds:
        dcc_gate = pd.read_csv(
            schism_dcc_gate_file,
            header=0,
            parse_dates=True,
            index_col=0,
            sep="\\s+",
            comment="#",
        )

    for boundary_kind in boundary_kinds:

        source_map_bc = source_map.loc[source_map["boundary_kind"] == boundary_kind]

        if boundary_kind == "flow":
            dd = flux.copy().reindex(df_rng)
            out_file = out_file_flux
        elif boundary_kind == "ec":
            dd = salt.copy().reindex(df_rng)
            out_file = out_file_salt
        elif boundary_kind == "temp":
            dd = temp.copy().reindex(df_rng)
            out_file = out_file_temp
        elif boundary_kind == "dcc_gate":
            dd = dcc_gate.copy().reindex(df_rng)
            # Take existing values from the reference file (might only work on DCC gate)
            dd.iloc[:, dd.columns != "height"] = dcc_gate.iloc[
                0, dcc_gate.columns != "height"
            ]
            # enforce integer type else get schism error
            dd["install"] = dd["install"].astype(int)
            dd["ndup"] = dd["ndup"].astype(int)
            dd = dd.resample("D").first()
            out_file = out_file_dcc_gate
        else:
            raise ValueError(f"Unknown boundary kind: {boundary_kind}")

        for index, row in source_map_bc.iterrows():
            dfi = pd.DataFrame()
            name = row["schism_boundary"]
            source_kind = row["source_kind"]
            source_file = str(row["source_file"])
            derived = str(row["derived"]).capitalize() == "True"
            interp = str(row["interp"]).capitalize() == "True"
            var = row["var"]
            sign = row["sign"]
            convert = row["convert"]
            p = row["rhistinterp_p"]
            formula = row["formula"]
            print(f"processing {name}")

            if "gate" in boundary_kind:
                if source_kind == "CSV":
                    var_df = read_csv(source_file, var, name, dt, p=p, interp=interp)
                elif source_kind == "DSS":
                    var_df = pd.DataFrame()
                    b = var.split("/")[2]
                    var_df[[b]] = read_dss(
                        os.path.join(dir, source_file),
                        pathname=var,
                        p=p,
                    )
                else:
                    raise ValueError(f"source_kind={source_kind} is not yet supported")

                var_df = var_df[
                    (var_df.index.to_timestamp() >= start_date)
                    & (var_df.index.to_timestamp() <= end_date)
                ]
                # use formula to set gate fraction (month_fraction, month_days)
                dfi = set_gate_ops(boundary_kind, var_df.ffill(), name, formula)
                dfi[name] = pd.to_numeric(dfi[name], errors="coerce")

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
                        csv[[v]] = read_csv(
                            source_file, v, name, dt, p=p, interp=interp
                        )
                    dts = eval(formula).to_frame(name).reindex(df_rng)
                    if interp:
                        dfi = ts_gaussian_filter(dts, sigma=100)
                    else:
                        dfi = dts
                else:
                    dfi = read_csv(source_file, var, name, dt, p=p)
                    print(
                        f"Updating SCHISM {name} with interpolated monthly\
                        forecast {var}"
                    )

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
                            os.path.join(dir, source_file),
                            pathname=pn,
                            p=p,
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
                    if interp:
                        dfi = ts_gaussian_filter(dts, sigma=100)
                    else:
                        dfi = dts
                else:
                    print(f"Updating SCHISM {name} with DSS variable {var}")
                    dfi = read_dss(os.path.join(dir, source_file), pathname=var, p=p)

            elif source_kind == "CONSTANT":
                print(f"Updating SCHISM {name} with constant value of {var}")
                # Simply fill with a constant specified.
                dd[name] = float(var)
                dfi["datetime"] = df_rng
                dfi = dfi.set_index("datetime")

                dfi[name] = [float(var)] * len(df_rng)
                print(f"Updating SCHISM {name} with constant value of {var}")

            # Maintain the rounding preference of the formula
            if isinstance(formula, str) and "round" in formula:
                dfi = dfi.round(int(formula[-2]))

            if source_kind == "SCHISM":
                # Simplest case: use existing reference SCHISM data; do nothing
                print("Use existing SCHISM input")

            else:
                # Do conversions.
                if convert == "CFS_CMS":
                    dfi = dfi * CFS2CMS * sign
                elif convert == "EC_PSU":
                    dfi = ec_psu_25c(dfi) * sign

                # Trim dfi so that it starts where schism input file ends, so that dfi doesn't
                # overwrite any historical data
                if not overwrite:
                    dfi = dfi[dfi.index >= dd.index[-1]]

                # Update the dataframe.
                dd.update(dfi, overwrite=True)

        if out_file:
            # Format the outputs.
            dd.index.name = "datetime"

            # Remove excess/repetitive rows
            dd = clean_df(dd.ffill())

            output_path = os.path.join(dir, out_file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            print(f"Writing {boundary_kind} boundary conditions to {output_path}")
            dd.to_csv(
                output_path,
                header=True,
                date_format="%Y-%m-%dT%H:%M",
                float_format="%.4f",
                sep=" ",
            )

            dd.plot()
            plt.show()

    print("Done")


@click.command()
@click.argument("config_yaml", type=click.Path(exists=True))
@click.option(
    "--kwargs",
    type=str,
    default="{}",
    help="JSON string representing a dictionary of keyword arguments to populate format strings.",
)
@click.help_option("-h", "--help")
def port_boundary_cli(config_yaml, kwargs):
    """
    Command line interface for creating SCHISM boundary conditions.
    """
    kwargs_dict = json.loads(kwargs)
    create_schism_bc(config_yaml, kwargs_dict)


if __name__ == "__main__":
    port_boundary_cli()
