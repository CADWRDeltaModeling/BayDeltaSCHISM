"""Script by Lily Tomkovic to take a net delta consumptive use and parse it into vsource and vsink"""

from vtools.functions.unit_conversions import CFS2CMS, CMS2CFS
from vtools.functions.interpolate import rhistinterp
from vtools.data.vtime import days
from schimpy.model_time import read_th, is_elapsed
from schimpy.th_calcs import calc_net_source_sink
from schimpy.util.yaml_load import yaml_from_file
from bdschism.read_dss import read_dss
from pathlib import Path
import pandas as pd
import numpy as np
import click
import os


def adjust_src_sink(src, sink, net_diff, sinkfrac=0.001, debug=False):
    """Distributes a perturbation to dataframe sc and sink

    Parameters
    ----------
    src : DataFrame
        DataFrame of positive sources.
    sink : DataFrame
        DataFrame of sinks. Must be all of the same sign. If positive, they are assumed to represent the the magnitude of the (latent) sinks. If they are negative, they are the sink values themselves. Return value will match the convention of the input.
    net_diff : Series
        Series representing a perturbation to be distributed proportionally over src and sink. Sign convention agrees with that of src.
        When net_diff is negative, it augments sink.
        When it is positive it reduces the sink until sinkfrac fraction of the sink is exhausted, after which the remainder augments the source.
    sinkfrac : float
        Fraction of sink that can be reduced in order to achieve the perturbation by reducing the sink. Remainder is applied by augmenting src. Has no effect on time steps when net_diff is negative.
    debug : bool
        If True, prints out debug information about the input src and sink DataFrames.

    Returns
    -------
    src : DataFrame
        DataFrame of adjusted sources, with the same sign convention as the input src.
    sink : DataFrame
        DataFrame of adjusted sinks, with the same sign convention as the input sink.
    """

    # convert so that sink is a magnitude and switch the sign so that it contributes to sink
    # deal with magnitudes and in terms of consumptive use as positive,
    # will undo at the end to match convention of the inputs

    if (sink > 0).any(axis=None):
        possink = True
        haspos = sink.loc[(sink > 0).any(axis=1), :]
        colswithpos = (haspos > 0).any(axis=0)
        if debug:
            hasneg.loc[:, colswithneg].to_csv("test_sink.csv")
            print("possink")
            print(sink.loc[(sink > 0).any(axis=1), :])
            print("Sink has all pos values")
        # SHOULD BE DataFrame of negative sinks
        sink = -sink
    else:
        possink = False
        if debug:
            print("Sink has all neg values")

    if (src < 0).any(axis=None):
        negsrc = True
        hasneg = src.loc[(src < 0).any(axis=1), :]
        colswithneg = (hasneg < 0).any(axis=0)
        if debug:
            hasneg.loc[:, colswithneg].to_csv("test_src.csv")
            print("negsrc")
            print(src.loc[(src < 0).any(axis=1), :])
            print("Source has all neg values")
        # SHOULD BE DataFrame of positive sources
        src = -src
    else:
        negsrc = False
        if debug:
            print("Source has all pos values")

    src_total = src.sum(axis=1)
    sink_total = sink.sum(axis=1)
    dcd_total = src_total + sink_total

    # Ensure proper formatting of net_diff
    if isinstance(net_diff, pd.DataFrame) and net_diff.shape[1] == 1:
        net_diff = net_diff.iloc[:, 0]
    if isinstance(net_diff.index, pd.PeriodIndex):
        net_diff.index = net_diff.index.to_timestamp()

    # Create perturbed dataframe for scaling and indexing
    pert = net_diff.reindex(
        dcd_total.index
    )  # using only the indices in dcd_total (from the src/sink inputs)
    # pert
    neg = pert <= 0.0
    pos = ~neg

    # For negative (e.g. more depletion) , achieve change by scaling all sinks
    scaleneg = (
        sink_total + pert
    ) / sink_total  # all quantities negative, so scaleneg > 1
    scaleneg = scaleneg.where(neg, 1.0)  # Ensure No effect in pos case

    # For positive adjustments, remove up to FRAC fraction of total sinks, then ...
    adjustmag = pert.where(pos, 0.0)  # total positive adjustment required
    FRAC = sinkfrac
    sinklimit = -FRAC * sink_total  # max amount done by reducing sink (this is pos)
    from_sink = adjustmag.clip(upper=sinklimit)
    residual = (
        adjustmag - from_sink
    )  # This should be nonnegative for pertinent cases where ~pos
    residual = residual.where(pos, 0.0)  # Just to clarify
    resscale = (residual + src_total) / src_total
    src = src.mul(resscale, axis=0)

    # Now put together the adjustments to sinks under both cases, pos and ~pos
    scalepos = (from_sink + sink_total) / sink_total  # for positive (source increase)
    scale = scalepos.where(pos, scaleneg)  # choose case
    sink = sink.mul(scale, axis=0)
    if possink:
        sink = -sink
        # sink.loc[sink==0.] = -0.0
    if negsrc:
        src = -src
        # sink.loc[sink==0.] = -0.0

    # drop NaN's from interpolations etc.
    sink = sink.dropna(axis=0, how="any")
    src = src.dropna(axis=0, how="any")

    return src, sink


def calc_net_diff(original_net, adjusted_net, cfs_to_cms=True):
    """
    Calculate the difference in net CU between original and adjusted data in cms.

    Parameters
    ----------
    original_net: pd.DataFrame
        DCD net source and sink data from original timeseries.
        Used to calculate difference in net CU to apply to SCHISM inputs.
        Entered as a DataFrame with a single column or Series with units of cfs by default.
    adjusted_net: pd.DataFrame
        DCD net source and sink data from adjusted timeseries.
        Used to calculate difference in net CU from original to apply to SCHISM inputs
        Entered as a DataFrame with a single column or Series with units of cfs by default.
    cfs_to_cms: bool
        Set to True if net data is in cfs and needs to be converted to cms for SCHISM.
        Only set to False if net data is in cms.

    Returns
    -------
    pd.Series
        Series of the net difference in CU between original and adjusted data.
    """
    if isinstance(adjusted_net, pd.DataFrame) and adjusted_net.shape[1] == 1:
        adjusted_net = adjusted_net.iloc[:, 0]

    common_index = adjusted_net.index.intersection(original_net.index)
    net_diff = adjusted_net.loc[common_index] - original_net.loc[common_index]

    if cfs_to_cms:
        net_diff = net_diff * CFS2CMS  # convert to cms

    return net_diff


def sch_dcd_net_diff(
    net_diff,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date=None,
    end_date=None,
    cfs_to_cms=True,
):
    """
    Convert adjusted DCD data from DataFrame into SCHISM-ready \*.th inputs.

    Parameters
    ----------
    net_diff: pd.DataFrame
        DCD net differences from historical or baseline. Used to apply to SCHISM inputs.
    schism_vsource: str|Path
        input SCHISM vsource data, needs to be "dated" and not "elapsed.
    schism_vsink: str|Path
        input SCHISM vsink data, needs to be "dated" and not "elapsed.
    out_dir: str|Path
        Output directory to store the altered \*.th files.
    version: str
        Specifies the tag to put on the output files (e.g. vsource.VERSION.dated.th)
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    cfs_to_cms: bool, optional
        Set to True if net data is in cfs and needs to be converted to cms for SCHISM.
        Only set to False if net data is in cms.
    """
    # Normalize paths
    schism_vsource = Path(schism_vsource)
    schism_vsink = Path(schism_vsink)
    out_dir = Path(out_dir)

    # Check inputs first
    if is_elapsed(schism_vsource):
        raise ValueError(
            f"SCHISM input is in elapsed format. Needs to be timestamped. File: f{schism_vsource}"
        )
    if is_elapsed(schism_vsink):
        raise ValueError(
            f"SCHISM input is in elapsed format. Needs to be timestamped. File: f{schism_vsink}"
        )

    if not os.path.exists(out_dir):
        print(f"Making directory: {out_dir}")
        os.makedirs(out_dir, exist_ok=True)

    # Read in SCHISM data to net_diff.
    sch_src = read_th(schism_vsource)
    sch_sink = read_th(schism_vsink)
    sch_delta_src = sch_src.loc[:, sch_src.columns.str.contains("delta", case=False)]
    sch_delta_sink = sch_sink.loc[:, sch_sink.columns.str.contains("delta", case=False)]

    ssrc, ssink = adjust_src_sink(
        sch_delta_src, sch_delta_sink, net_diff
    )  # create the adjusted source/sink values to be used for this version in SCHISM

    # Add the adjusted columns to the original SCHISM data
    src_out = sch_src.copy()
    src_out.update(ssrc)
    sink_out = sch_sink.copy()
    sink_out.update(ssink)
    src_out.index = src_out.index.strftime("%Y-%m-%dT00:00")
    sink_out.index = sink_out.index.strftime("%Y-%m-%dT00:00")

    fn_src = out_dir / f"vsource.{version}.dated.th"
    fn_sink = out_dir / f"vsink.{version}.dated.th"

    # Clip to desired daterange:
    if start_date is None:
        start_date = src_out.index[0]
    if end_date is None:
        end_date = src_out.index[-1]
    src_out = src_out[start_date:end_date]
    sink_out = sink_out[start_date:end_date]

    if (src_out.values < 0).any():
        raise ValueError(
            "There are negative values in the source dataframe! They should all be positive"
        )
    else:
        print(f"Writing source to {fn_src}")
        src_out.to_csv(fn_src, sep=" ", float_format="%.2f")
    if (sink_out.values > 0).any():
        raise ValueError(
            "There are positive values in the sink dataframe! They should all be negative"
        )
    else:
        print(f"Writing sink to {fn_sink}")
        sink_out.to_csv(fn_sink, sep=" ", float_format="%.2f")


def calc_srcsnk_dsm2(
    dcd_dss_file,
    start_date=None,
    end_date=None,
    dt=days(1),
    exclude_pathname="//TOTAL*/////",
):
    """Get net source and net sink timeseries from DCD DSS file.

    Parameters
    ----------
    dcd_dss_file: str|Path
        Path to the DCD DSS file. Contains DRAIN-FLOW, SEEP-FLOW, and DIV-FLOW data.
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation.
    exclude_pathname: str, optional
        Pathname parts to exclude, ex: '//TOTAL*/////'

    Returns
    -------
    src: pd.Series
        Series of net source flow in cfs.
    sink: pd.Series
        Series of net sink flow in cfs.
    """

    dcd_dss_file = Path(dcd_dss_file)

    df_div_dcd = read_dss(
        dcd_dss_file,
        "///DIV-FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        exclude_pathname=exclude_pathname,
    )
    df_seep_dcd = read_dss(
        dcd_dss_file,
        "///SEEP-FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        exclude_pathname=exclude_pathname,
    )
    df_drain_dcd = read_dss(
        dcd_dss_file,
        "///DRAIN-FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        exclude_pathname=exclude_pathname,
    )

    df_div_dcd = df_div_dcd.clip(lower=0.0)
    df_seep_dcd = df_seep_dcd.clip(lower=0.0)

    df_div_dcd.columns = [strip_dpart(col) for col in df_div_dcd.columns]
    df_seep_dcd.columns = [strip_dpart(col) for col in df_seep_dcd.columns]
    df_drain_dcd.columns = [strip_dpart(col) for col in df_drain_dcd.columns]

    use_cols = [col for col in df_div_dcd.columns if "total" not in col.lower()]
    df_div_dcd = df_div_dcd[use_cols]
    use_cols = [col for col in df_seep_dcd.columns if "total" not in col.lower()]
    df_seep_dcd = df_seep_dcd[use_cols]
    use_cols = [col for col in df_drain_dcd.columns if "total" not in col.lower()]
    df_drain_dcd = df_drain_dcd[use_cols]

    src = df_drain_dcd.sum(axis=1)
    sink = df_div_dcd.sum(axis=1) + df_seep_dcd.sum(axis=1)

    return src, sink


def calc_net_dsm2(
    dcd_dss_file,
    start_date=None,
    end_date=None,
    dt=days(1),
    exclude_pathname="//TOTAL*/////",
    **kwargs,
):
    """Get net timeseries from DCD DSS file.

    Parameters
    ----------
    dcd_dss_file: str|Path
        Path to the DCD DSS file. Contains DRAIN-FLOW, SEEP-FLOW, and DIV-FLOW data.
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation.
    exclude_pathname: str, optional
        Pathname parts to exclude, ex: '//TOTAL*/////'
    kwargs: dict, optional
        Additional keyword arguments to pass to the read_dss function. (unused in this function)

    Returns
    -------
    pd.Series
        Series of net consumptive use in cfs, calculated as source - sink.
    """

    dcd_dss_file = Path(dcd_dss_file)

    src, sink = calc_srcsnk_dsm2(
        dcd_dss_file,
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        exclude_pathname=exclude_pathname,
    )

    return src - sink


def calc_net_calsim(
    dcd_dss_calsim, start_date=None, end_date=None, dt=days(1), **kwargs
):
    """Get net consumptive use timeseries from Calsim DSS file.

    Parameters
    ----------
    dcd_dss_calsim: str|Path
        Path to the Calsim DSS file. Contains DICU_FLOW data.
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation.
    kwargs: dict, optional
        Additional keyword arguments to pass to the read_dss function. (unused in this function)

    Returns
    -------
    pd.DataFrame
        DataFrame with a single column named 'net' containing net consumptive use in cfs.
        The data is read from the DICU_FLOW path in the Calsim DSS file.
    """

    dcd_dss_calsim = Path(dcd_dss_calsim)

    net = read_dss(
        dcd_dss_calsim,
        "///DICU_FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
    )
    net.columns = ["net"]
    if isinstance(net, pd.DataFrame) and net.shape[1] == 1:
        net = net.iloc[:, 0]

    return -net


def calc_net_schism(schism_dir, start_date=None, end_date=None, dt=days(1), **kwargs):
    """Get net timeseries from SCHISM th files in cfs.

    Parameters
    ----------
    schism_dir: str|Path
        SCHISM directory where vsource.th and vsink.th files are found.
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation.
    kwargs: dict, optional
        Additional keyword arguments to pass to the SCHISM net calculation functions.
        For example, if the original data has a specific vsource file, you can pass
        `vsource_original='vsource_dated.th'` and it will be used in the calculation.
        You must use _original or _perturbed suffixes to distinguish between original and perturbed data.

    Returns
    -------
    pd.DataFrame
        DataFrame with a single column named 'net' containing net consumptive use in cfs.
        The data is calculated from the vsource and vsink files in the SCHISM directory.
    """
    schism_dir = Path(schism_dir)

    vsource = schism_dir / kwargs.get("vsource")
    vsink = schism_dir / kwargs.get("vsink")

    net, src, sink = calc_net_source_sink(
        vsource_file=vsource,
        vsink_file=vsink,
        search_term="delta",
        start_date=start_date,
        end_date=end_date,
    )

    net = rhistinterp(net, dt)
    net.columns = ["net"]
    net = net * CMS2CFS  # convert to cfs

    return net


def read_net_csv(csv_file, start_date=None, end_date=None, dt=days(1), **kwargs):
    """Read net timeseries from a CSV file.
    Parameters
    ----------
    csv_file: str|Path
        Path to the CSV file containing net consumptive use data.
    start_date: pd.Timestamp, optional
        Start date for the timeseries.
    end_date: pd.Timestamp, optional
        End date for the timeseries.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation.
    """
    csv_file = Path(csv_file)

    net = pd.read_csv(csv_file, index_col=0, parse_dates=[0])

    # clip to time constraint
    if start_date is None:
        start_date = net.index[0]
    if end_date is None:
        end_date = net.index[-1]
    net = net[start_date:end_date]

    # Convert DatetimeIndex to PeriodIndex if needed
    if isinstance(net.index, pd.DatetimeIndex):
        net.index = net.index.to_period("D")

    net = rhistinterp(net, dt)
    net.columns = ["net"]

    return net


# Map type string to function
SRC_SNK_FUNC_MAP = {
    "dsm2": calc_net_dsm2,
    "calsim": calc_net_calsim,
    "schism": calc_net_schism,
    "csv": read_net_csv,
    # add more types as needed
}


def strip_dpart(colname):
    """Remove the 5th part of a DSS path, which is the D part.
    This is used to strip the D part from the column names in the DCD data.
    Parameters
    ----------
    colname: str
        The column name in the DSS path format.
    Returns
    -------
    str
        The column name with the D part removed.
    """
    parts = colname.split("/")
    parts[4] = ""
    return "/".join(parts)


# Main function
def orig_pert_to_schism_dcd(
    original_type,
    original_filename,
    perturbed_type,
    perturbed_filename,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date=None,
    end_date=None,
    dt=days(1),
    **kwargs,
):
    """
    Convert original and perturbed DCD data to SCHISM vsource and vsink inputs.

    Parameters
    ----------
    original_type: str
        Type of the original DCD data (e.g. 'dsm2', 'calsim', 'csv', 'schism').
    original_filename: str|Path
        Path to the original DCD data file. If DSS then enter the filename.
        If SCHISM then enter the directory where vsource.th and vsink.th are found.
    perturbed_type: str
        Type of the perturbed DCD data (e.g. 'dsm2', 'calsim', 'csv', 'schism').
    perturbed_filename: str|Path
        Path to the perturbed DCD data file. If DSS then enter the filename.
        If SCHISM then enter the directory where vsource.th and vsink.th are found.
    schism_vsource: str|Path
        Input SCHISM vsource data, needs to be "dated" and not "elapsed".
    schism_vsink: str|Path
        Input SCHISM vsink data, needs to be "dated" and not "elapsed".
    out_dir: str|Path
        Output directory to store the altered \*.th files.
    version: str
        Specifies the tag to put on the output files (e.g. vsource.VERSION.dated.th).
    start_date: pd.Timestamp, optional
        Start date for the timeseries. If None, uses the start date from the original data.
    end_date: pd.Timestamp, optional
        End date for the timeseries. If None, uses the end date from the original data.
    dt: float or pd.DateOffset, optional
        Time step in days for interpolation. Default is 1 day.
    **kwargs: dict
        Additional keyword arguments to pass to the SCHISM net calculation functions.
        For example, if the original data has a specific vsource file, you can pass
        `vsource_original='vsource_dated.th'` and it will be used in the calculation.
        You must use _original or _perturbed suffixes to distinguish between original and perturbed data.
    """
    original_filename = Path(original_filename)
    perturbed_filename = Path(perturbed_filename)
    schism_vsource = Path(schism_vsource)
    schism_vsink = Path(schism_vsink)
    out_dir = Path(out_dir)

    # Read in DSS data and compute net difference in the original case
    print(f"Reading Original DCD data from {original_type.upper()} inputs...")
    original_fxn = SRC_SNK_FUNC_MAP[
        original_type.lower()
    ]  # original net flow for source/sink
    # Look for 'original' in kwargs and pass to original_fxn
    original_kwargs = {
        k.replace("_original", ""): v for k, v in kwargs.items() if "original" in k
    }
    net_original = original_fxn(
        original_filename,
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        **original_kwargs,
    )

    # Read in DSS data and compute net difference in the perturbed case
    print(f"Reading Perturbed DCD data from {perturbed_type.upper()} inputs...")
    perturbed_fxn = SRC_SNK_FUNC_MAP[
        perturbed_type.lower()
    ]  # perturbed net flow for source/sink
    perturbed_kwargs = {
        k.replace("_perturbed", ""): v for k, v in kwargs.items() if "perturbed" in k
    }
    net_perturbed = perturbed_fxn(
        perturbed_filename,
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        **perturbed_kwargs,
    )

    # Calculate the net difference between original and perturbed
    net_diff = calc_net_diff(
        net_original,
        net_perturbed,
        cfs_to_cms=True,
    )  # net difference in cms

    # Apply differences to SCHISM inputs
    sch_dcd_net_diff(
        net_diff,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
    )


def orig_pert_to_schism_dcd_yaml(yaml_fn, envvar=None):
    """
    Convert original and perturbed DCD data to SCHISM vsource and vsink inputs from yaml input file.

    Parameters
    ----------
    yaml_fn: str|Path
        Path to the YAML file containing configuration.
    envvar: dict or None, optional
        Optional dictionary of environment variables or overrides. If None, no overrides are applied.
    """

    yaml_content = yaml_from_file(yaml_fn, envvar=envvar)

    cu_inputs = yaml_content["cu"]

    # Build a dict of all arguments, with envvar overriding cu_inputs
    all_args = {**cu_inputs, **(envvar or {})}
    # Remove process key if present (not an argument for orig_pert_to_schism_dcd)
    all_args.pop("process", None)

    # Optionals from envvar or default
    start_date = (
        cu_inputs.get("start_date") if cu_inputs and "start_date" in cu_inputs else None
    )
    end_date = (
        cu_inputs.get("end_date") if cu_inputs and "end_date" in cu_inputs else None
    )
    dt = cu_inputs.get("dt") if cu_inputs and "dt" in cu_inputs else days(1)

    cfs_to_cms = (
        cu_inputs.get("cfs_to_cms") if cu_inputs and "cfs_to_cms" in cu_inputs else True
    )
    # Remove any duplicate keys that are not needed
    for k in ["start_date", "end_date", "dt"]:
        if k in all_args and locals()[k] is not None:
            all_args[k] = locals()[k]

    if cu_inputs["process"] == "orig_pert_to_schism":
        # Required arguments
        required_keys = [
            "original_type",
            "original_filename",
            "perturbed_type",
            "perturbed_filename",
            "schism_vsource",
            "schism_vsink",
            "out_dir",
            "version",
        ]
        missing = [k for k in required_keys if k not in cu_inputs]
        if missing:
            raise KeyError(
                f"Missing required keys in cu_inputs: {missing}\n\tAll keys needed are: {required_keys}"
            )

        orig_pert_to_schism_dcd(**all_args)

    elif cu_inputs["process"] == "net_diff_to_schism":
        # Required arguments
        required_keys = [
            "net_diff_filename",
            "schism_vsource",
            "schism_vsink",
            "out_dir",
            "version",
        ]
        missing = [k for k in required_keys if k not in cu_inputs]
        if missing:
            raise KeyError(
                f"Missing required keys in cu_inputs: {missing}\n\tAll keys needed are: {required_keys}"
            )

        # Read net difference from the specified file
        net_diff = read_net_csv(
            cu_inputs["net_diff_filename"],
            start_date=start_date,
            end_date=end_date,
            dt=dt,
            **kwargs,
        )

        sch_dcd_net_diff(
            net_diff,
            cu_inputs["schism_vsource"],
            cu_inputs["schism_vsink"],
            cu_inputs["out_dir"],
            cu_inputs["version"],
            cfs_to_cms=cfs_to_cms,
        )
    else:
        raise ValueError(
            f"Unknown process {cu_inputs['process']} in cu_inputs. "
            "Expected 'orig_pert_to_schism' or 'net_diff_to_schism'."
        )


@click.command(
    help=(
        "Transfer hotstart data from one grid to another'\n\n"
        "Arguments:\n"
        "  YAML  Path to the YAML file."
        "For instance hotstart_from_hotstart.yaml (found in examples/hotstart/examples)"
    )
)
@click.argument("yaml_fn")
@click.help_option("-h", "--help")
@click.argument("extra", nargs=-1)
def parse_cu_yaml_cli(
    yaml_fn: str,
    extra=(),
):
    """
    Command-line interface for transferring hotstart data from one grid to another.
    Arguments
    ---------
        yaml_fn      Path to the YAML file (e.g., parse_cu.yaml).
    """

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

    orig_pert_to_schism_dcd_yaml(yaml_fn, envvar=envvar if envvar else None)


@click.command(
    help=(
        "Uses consumptive use adjustments to historical data "
        "in order to determine what the adjusted values for vsource.th and vsink.th are"
        "\n\nExample Usages:"
        "\n\n\tbds parse_cu dsm2 ./dsm2/DCD_hist_Lch5.dss calsim ./calsim/DCR2023_DV_9.3.1_v2a_Danube_Adj_v1.8.dss ./schism/vsource_dated.th ./schism/vsink_dated.th ./out_dir dsm2_calsim_v1"
        "\n"
        "\n\tbds parse_cu schism ./schism/ dsm2 ./dsm2/DCD_hist_Lch5.dss ./schism/simulation/vsource_dated.th ./schism/simulation/vsink_dated.th ./out_dir schism_dsm2_v1 --param vsource_original vsource_2023.th vsink_original vsink_2023.th"
    )
)
@click.help_option("-h", "--help")
@click.argument(
    "original_type",
    type=click.Choice(["dsm2", "calsim", "csv", "schism"], case_sensitive=False),
)
@click.argument(
    "original_filename",
    type=click.Path(exists=True),
)
@click.argument(
    "perturbed_type",
    type=click.Choice(["dsm2", "calsim", "csv", "schism"], case_sensitive=False),
)
@click.argument(
    "perturbed_filename",
    type=click.Path(exists=True),
)
@click.argument("schism_vsource", type=click.Path(exists=True))
@click.argument("schism_vsink", type=click.Path(exists=True))
@click.argument("out_dir", type=click.Path())
@click.argument("version", type=str)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date (YYYY-MM-DD)",
)
@click.option("--dt", type=int, default=1, help="Time step in days.")
@click.option(
    "--param",
    type=(str, str),
    multiple=True,
    help=(
        "Extra key-value parameters to pass to the net calculation functions, "
        "e.g. --param vsource_original vsource_dated.th vsource_perturbed vsource_2023.th"
    ),
)
def parse_cu_cli(
    original_type,
    original_filename,
    perturbed_type,
    perturbed_filename,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date,
    end_date,
    dt,
    param,
):
    """Main entry point for consumptive use - SCHISM commands.
    Arguments
    ---------
    original_type : str
        Type of the original DCD data (e.g. 'dsm2', 'calsim', 'csv', 'schism').
    original_filename : str
        Path to the original DCD data file. If DSS then enter the filename.
        If SCHISM then enter the directory where vsource.th and vsink.th are found.
    perturbed_type : str
        Type of the perturbed DCD data (e.g. 'dsm2', 'calsim', 'csv', 'schism').
    perturbed_filename : str
        Path to the perturbed DCD data file. If DSS then enter the filename.
        If SCHISM then enter the directory where vsource.th and vsink.th are found.
    schism_vsource : str
        Input SCHISM vsource data, needs to be "dated" and not "elapsed".
    schism_vsink : str
        Input SCHISM vsink data, needs to be "dated" and not "elapsed".
    out_dir : str
        Output directory to store the altered *.th files.
    version : str
        Specifies the tag to put on the output files (e.g. vsource.VERSION.dated.th).

    Options
    -------
    --start-date : str
        Start date (YYYY-MM-DD).
    --end-date : str
        End date (YYYY-MM-DD).
    --dt : int
        Time step in days.
    --param : (str, str)
        Extra key-value parameters to pass to the net calculation functions.
        e.g. --param vsource_original vsource_dated.th vsource_perturbed vsource_2023.th
    """
    # Convert paths to Path objects
    original_filename = Path(original_filename)
    perturbed_filename = Path(perturbed_filename)
    schism_vsource = Path(schism_vsource)
    schism_vsink = Path(schism_vsink)
    out_dir = Path(out_dir)
    # Ensure out_dir exists
    print(f"Creating output directory: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Convert param tuples to a dict
    extra_kwargs = dict(param)
    # Pass extra_kwargs to orig_pert_to_schism_dcd
    orig_pert_to_schism_dcd(
        original_type,
        original_filename,
        perturbed_type,
        perturbed_filename,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
        start_date=start_date,
        end_date=end_date,
        dt=dt,
        **extra_kwargs,
    )


if __name__ == "__main__":
    parse_cu_cli()
