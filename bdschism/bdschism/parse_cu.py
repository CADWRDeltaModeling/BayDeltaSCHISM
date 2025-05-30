"""Script by Lily Tomkovic to take a net delta consumptive use and parse it into vsource and vsink"""

from vtools.functions.unit_conversions import CFS2CMS, ec_psu_25c
from vtools.data.vtime import days
from schimpy.model_time import read_th, is_elapsed
from dms_datastore.read_dss import read_dss
from pathlib import Path
import datetime as dt
import pandas as pd
import numpy as np
import click
import os


def adjust_src_sink(src, sink, perturb, sinkfrac=0.001):
    """Distributes a perturbation to dataframe sc and sink
    Parameters
    ----------

    src : DataFrame
        DataFrame of positive sources

    sink : DataFrame
        DataFrame of sinks. Must be all of the same sign. If positive, they are assumed to represent the
    the magnitude of the (latent) sinks. If they are negative, they are the sink values themselves. Return
    value will match the convention of the input.

    perturb : Series
        Series representing a perturbation to be distributed proportionally over src and sink. Sign convention
    agrees with that of src. When perturb is negative, it augments sink. When it is positive
    it reduces the sink until sinkfrac fraction of the sink
    is exhausted, after which the remainder augments the source.

    sinkfrac : float
        Fraction of sink that can be reduced in order to achieve the perturbation by reducing the sink. Remainder
    is applied by augmenting src. Has no effect on time steps when perturb is negative.

    """

    # convert so that sink is a magnitude and switch the sign so that it contributes to sink
    # deal with magnitudes and in terms of consumptive use as positive,
    # will undo at the end to match convention of the inputs

    if (sink > 0).any(axis=None):
        possink = True
        haspos = sink.loc[(sink > 0).any(axis=1), :]
        colswithpos = (haspos > 0).any(axis=0)
        hasneg.loc[:, colswithneg].to_csv("test_sink.csv")
        print("possink")
        print(sink.loc[(sink > 0).any(axis=1), :])
        print("Sink has all pos values")
        # SHOULD BE DataFrame of negative sinks
        sink = -sink
    else:
        possink = False
        print("Sink has all neg values")

    if (src < 0).any(axis=None):
        negsrc = True
        hasneg = src.loc[(src < 0).any(axis=1), :]
        colswithneg = (hasneg < 0).any(axis=0)
        hasneg.loc[:, colswithneg].to_csv("test_src.csv")
        print("negsrc")
        print(src.loc[(src < 0).any(axis=1), :])
        print("Source has all neg values")
        # SHOULD BE DataFrame of positive sources
        src = -src
    else:
        negsrc = False
        print("Source has all pos values")

    src_total = src.sum(axis=1)
    sink_total = sink.sum(axis=1)
    dcd_total = src_total + sink_total

    if "Timestamp" not in str(type(perturb.index[0])):
        perturb.index = perturb.index.to_timestamp()
    pert = perturb.reindex(
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
    return src, sink


def sch_dcd_from_dss_pert(
    original_net,
    adjusted_net,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    cfs_to_cms=True,
):
    """Convert adjusted DCD data from DSS into SCHISM-ready *.th inputs.
    Parameters
    ----------
    original_net: pd.DataFrame
        DCD net source and sink data from original timeseries.
        Used to calculate difference in net CU to apply to SCHISM inputs
    adjusted_net: pd.DataFrame
        DCD net source and sink data from adjusted timeseries.
        Used to calculate difference in net CU from original to apply to SCHISM inputs
    schism_vsource: str|Path
        input SCHISM vsource data, needs to be "dated" and not "elapsed.
    schism_vsink: str|Path
        input SCHISM vsink data, needs to be "dated" and not "elapsed.
    out_dir: str|Path
        Output directory to store the altered *.th files.
    version: str
        Specifies the tag to put on the output files (e.g. vsource.VERSION.dated.th)
    cfs_to_cms: bool
        Set to True if DSS data is in cfs and needs to be converted to cms for SCHISM.
        Only set to False if DSS data is in cms."""

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
        os.makedirs(os.path.dirname(out_dir), exist_ok=True)

    if isinstance(adjusted_net, pd.DataFrame) and adjusted_net.shape[1] == 1:
        adjusted_net = adjusted_net.iloc[:, 0]

    # Align indices before subtracting
    common_index = adjusted_net.index.intersection(original_net.index)
    perturb = adjusted_net.loc[common_index] - original_net.loc[common_index]
    if cfs_to_cms:
        perturb = perturb * CFS2CMS  # convert to cms

    # Read in SCHISM data to perturb.
    sch_src = read_th(schism_vsource)
    sch_sink = read_th(schism_vsink)

    ssrc, ssink = adjust_src_sink(
        sch_src, sch_sink, perturb
    )  # create the adjusted source/sink values to be used for this version in SCHISM
    ssrc.index = ssrc.index.strftime("%Y-%m-%dT00:00")
    ssink.index = ssink.index.strftime("%Y-%m-%dT00:00")

    fn_src = os.path.join(out_dir, f"vsource.{version}.dated.th")
    fn_sink = os.path.join(out_dir, f"vsink.{version}.dated.th")

    src = ssrc
    sink = ssink

    if (src.values < 0).any():
        raise ValueError(
            "There are negative values in the source dataframe! They should all be positive"
        )
    else:
        print(f"Writing source to {fn_src}")
        src.to_csv(fn_src, sep=" ", float_format="%.2f")
    if (sink.values > 0).any():
        raise ValueError(
            "There are positive values in the sink dataframe! They should all be negative"
        )
    else:
        print(f"Writing sink to {fn_sink}")
        sink.to_csv(fn_sink, sep=" ", float_format="%.2f")


def get_net_srcsnk_dsm2(dcd_dss_file, start_date=None, end_date=None, dt=days(1)):
    """Get net source and net sink timeseries from DCD DSS file.
    Parameters
    ----------
    dcd_dss_file: str|Path
        Path to the DCD DSS file. Contains DRAIN-FLOW, SEEP-FLOW, and DIV-FLOW data.
    start: pd.Timestamp
        Start date for the timeseries.
    end: pd.Timestamp
        End date for the timeseries.
    """

    df_div_dcd = read_dss(
        dcd_dss_file, "///DIV-FLOW////", start_date=start_date, end_date=end_date, dt=dt
    )
    df_seep_dcd = read_dss(
        dcd_dss_file,
        "///SEEP-FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
    )
    df_drain_dcd = read_dss(
        dcd_dss_file,
        "///DRAIN-FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
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

    src0 = df_drain_dcd.sum(axis=1)
    sink0 = df_div_dcd.sum(axis=1) + df_seep_dcd.sum(axis=1)

    return src0, sink0


def get_calsim_net(dcd_dss_calsim, start_date=None, end_date=None, dt=days(1)):
    net = read_dss(
        dcd_dss_calsim,
        "///DICU_FLOW////",
        start_date=start_date,
        end_date=end_date,
        dt=dt,
    )

    return net


def dsm2_calsim_schism_dcd(
    dcd_dss_dsm2,
    dcd_dss_calsim,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date=None,
    end_date=None,
    dt=days(1),
):
    # Read in DSS data and compute net difference from original
    print("Reading DCD data from DSM2 inputs...")
    src, sink = get_net_srcsnk_dsm2(
        dcd_dss_dsm2, start_date=start_date, end_date=end_date, dt=dt
    )  # source and sink for historical data

    print("Reading DCD data from CalSim outputs...")
    calsim_net = get_calsim_net(
        dcd_dss_calsim, start_date=start_date, end_date=end_date, dt=dt
    )
    calsim_net.columns = ["net"]

    dsm2_net = src - sink  # original net flow for source/sink
    dsm2_net.columns = ["net"]

    sch_dcd_from_dss_pert(
        dsm2_net,
        calsim_net,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
    )


def dsm2_dsm2_schism_dcd(
    dcd_dss_dsm2_original,
    dcd_dss_dsm2_perturbed,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date=None,
    end_date=None,
    dt=days(1),
):
    # Read in DSS data and compute net difference from original
    print("Reading DCD data from DSM2 inputs...")
    src, sink = get_net_srcsnk_dsm2(
        dcd_dss_dsm2_original, start_date=start_date, end_date=end_date, dt=dt
    )  # source and sink for historical data

    print("Reading perturbed DCD data from DSM2 inputs...")
    psrc, psink = get_net_srcsnk_dsm2(
        dcd_dss_dsm2_perturbed, start_date=start_date, end_date=end_date, dt=dt
    )  # source and sink for pertrubed data

    dsm2_net_original = src - sink  # original net flow for source/sink
    dsm2_net_original.columns = ["net"]

    dsm2_net_perturbed = psrc - psink  # perturbed net flow for source/sink
    dsm2_net_perturbed.columns = ["net"]

    sch_dcd_from_dss_pert(
        dsm2_net_original,
        dsm2_net_perturbed,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
    )


def strip_dpart(colname):
    parts = colname.split("/")
    parts[4] = ""
    return "/".join(parts)


@click.group(
    help=(
        "Uses consumptive use adjustments to historical data "
        "in order to determine what the adjusted values for vsource.th and vsink.th are"
    )
)
@click.help_option("-h", "--help")
def parse_cu_cli():
    """Main entry point for consumptive use - SCHISM commands."""
    pass


@parse_cu_cli.command("dsm2-dsm2")
@click.option(
    "--dcd-dss-dsm2-original",
    required=True,
    type=click.Path(exists=True),
    help="Path to original/historical DSM2 DCD DSS file.",
)
@click.option(
    "--dcd-dss-dsm2-perturbed",
    required=True,
    type=click.Path(exists=True),
    help="Path to perturbed DSM2 DCD DSS file.",
)
@click.option(
    "--schism-vsource",
    required=True,
    type=click.Path(exists=True),
    help="Path to SCHISM vsource.th file (dated format).",
)
@click.option(
    "--schism-vsink",
    required=True,
    type=click.Path(exists=True),
    help="Path to SCHISM vsink.th file (dated format).",
)
@click.option(
    "--out-dir",
    required=True,
    type=click.Path(),
    help="Output directory for adjusted SCHISM files.",
)
@click.option(
    "--version",
    required=True,
    type=str,
    help="Version tag for output files.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start date (YYYY-MM-DD).",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date (YYYY-MM-DD).",
)
@click.option(
    "--dt",
    type=float,
    default=1.0,
    help="Time step in days.",
)
def dsm2_dsm2_cmd(
    dcd_dss_dsm2_original,
    dcd_dss_dsm2_perturbed,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date,
    end_date,
    dt,
):
    """Adjust SCHISM vsource/vsink using two DSM2 DCD DSS files."""
    from vtools.data.vtime import days

    dsm2_dsm2_schism_dcd(
        dcd_dss_dsm2_original,
        dcd_dss_dsm2_perturbed,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
        start_date=start_date,
        end_date=end_date,
        dt=days(dt),
    )


@parse_cu_cli.command("dsm2-calsim")
@click.option(
    "--dcd-dss-dsm2",
    required=True,
    type=click.Path(exists=True),
    help="Path to DSM2 DCD DSS file.",
)
@click.option(
    "--dcd-dss-calsim",
    required=True,
    type=click.Path(exists=True),
    help="Path to CalSim DCD DSS file.",
)
@click.option(
    "--schism-vsource",
    required=True,
    type=click.Path(exists=True),
    help="Path to SCHISM vsource.th file (dated format).",
)
@click.option(
    "--schism-vsink",
    required=True,
    type=click.Path(exists=True),
    help="Path to SCHISM vsink.th file (dated format).",
)
@click.option(
    "--out-dir",
    required=True,
    type=click.Path(),
    help="Output directory for adjusted SCHISM files.",
)
@click.option(
    "--version",
    required=True,
    type=str,
    help="Version tag for output files.",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Start date (YYYY-MM-DD).",
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="End date (YYYY-MM-DD).",
)
@click.option(
    "--dt",
    type=float,
    default=1.0,
    help="Time step in days.",
)
def dsm2_calsim_cmd(
    dcd_dss_dsm2,
    dcd_dss_calsim,
    schism_vsource,
    schism_vsink,
    out_dir,
    version,
    start_date,
    end_date,
    dt,
):
    """Adjust SCHISM vsource/vsink using DSM2 and CalSim DCD DSS files."""
    from vtools.data.vtime import days

    dsm2_calsim_schism_dcd(
        dcd_dss_dsm2,
        dcd_dss_calsim,
        schism_vsource,
        schism_vsink,
        out_dir,
        version,
        start_date=start_date,
        end_date=end_date,
        dt=days(dt),
    )


if __name__ == "__main__":
    # dcd_dss_original = "D:/projects/delta_salinity/DSP_code/model/dsm2/2021DSM2FP_202301/timeseries/DCD_hist_Lch5.dss"
    # dcd_dss_adjusted = "D:/projects/delta_salinity/DSP_code/model/calsim/9.3.1_danube_adj/DSS/output/DCR2023_DV_9.3.1_v2a_Danube_Adj_v1.8.dss"
    # schism_in = "D:/python/repositories/BayDeltaSCHISM/data/channel_depletion"
    # schism_vsource = os.path.join(schism_in, "vsource_dated.th")
    # schism_vsink = os.path.join(schism_in, "vsink_dated.th")
    # version = "rt_v1"
    # out_dir = f"D:/projects/delta_salinity/DSP_code/model/schism/roundtrip/{version}"

    # dsm2_calsim_schism_dcd(
    #     dcd_dss_original,
    #     dcd_dss_adjusted,
    #     schism_vsource,
    #     schism_vsink,
    #     out_dir,
    #     version,
    #     start_date=pd.to_datetime("2015-01-01"),
    #     end_date=pd.to_datetime("2022-10-01"),
    # )  # get the net source/sink for both original and perturbed data
    parse_cu_cli()
