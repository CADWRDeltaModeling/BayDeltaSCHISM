"""Delta source/sink postprocessing functions for SCHISM channel depletion workflow.

Covers synthetic source/sink generation, south-delta flow flooring,
Paradise Cut salinity propagation, and inferred EC-to-PSU conversion.

All flow values in intermediate CSVs are in CFS. The CFS-to-CMS conversion
is applied when writing final ``.th`` files via ``write_source_sink_th``.
"""

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from vtools.functions.unit_conversions import CFS2CMS, ec_psu_25c

logger = logging.getLogger(__name__)

# Canonical data file locations within BayDeltaSCHISM
_BDS_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_BDS_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "bay_delta"
TPS_CULVERT_TH = _BDS_DATA_DIR / "time_history" / "tom_paine_sl_culvert.th"
SOURCE_MSS_YAML = _BDS_TEMPLATES_DIR / "source_mss.yaml"
SD_NODES_EXTRAN_CSV = _BDS_DATA_DIR / "channel_depletion" / "south_delta_nodes_extran.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_daily_index(sdate, edate):
    """Return a daily DatetimeIndex from *sdate* to *edate* inclusive."""
    return pd.date_range(start=sdate, end=edate, freq="d")


def added_src_sink_names(added_src_yaml):
    """Read MSS added-node names from a source YAML file.

    Parameters
    ----------
    added_src_yaml : str or Path
        YAML file mapping node names to coordinates (keys become the name list).

    Returns
    -------
    list of str
        Node names as listed in the YAML (source convention).
    """
    with open(added_src_yaml, "r") as f:
        spec = yaml.safe_load(f)
    return list(spec)


def tps_masks(ndx, cols="sink", tps_th_fname=None):
    """Build a boolean mask of Tom Paine Slough gate-closed periods.

    Parameters
    ----------
    ndx : DatetimeIndex
        Time index to reindex the gate operation record onto.
    cols : str, optional
        Column convention for location names: ``'sink'`` or ``'src'``.
        Default ``'sink'``.
    tps_th_fname : str or Path, optional
        Path to the TPS culvert time-history file. Defaults to the canonical
        copy in ``BayDeltaSCHISM/data/time_history/tom_paine_sl_culvert.th``.

    Returns
    -------
    tps_closed : Series of bool
        True when both up and down gates are closed, reindexed to *ndx*.
    tps_locations : list of str
        Location names for TPS nodes 151–160 using *cols* convention.
    """
    fname = tps_th_fname or TPS_CULVERT_TH
    tps_culvert = pd.read_csv(
        fname, sep=r"\s+", comment="#", index_col=0, parse_dates=[0]
    )
    tps_culvert["closed"] = (tps_culvert.op_up == 0) & (tps_culvert.op_down == 0)
    tps_closed = tps_culvert.closed.astype(int).reindex(ndx).ffill().astype(bool)
    tps_locations = [f"delta_{cols}_{x}" for x in range(151, 161)]
    return tps_closed, tps_locations


# ---------------------------------------------------------------------------
# Synthetic source/sink generation
# ---------------------------------------------------------------------------

def create_nullzone_sink(outfile, sdate, edate):
    """Create seasonal null-zone balancing sink CSV (CFS).

    Six null-zone sink locations receive a constant 50/6 CFS flow from
    May through October. Values are negative (sink convention).

    Parameters
    ----------
    outfile : str or Path
        Output CSV path.
    sdate : str or Timestamp
        Start date.
    edate : str or Timestamp
        End date.
    """
    index = _create_daily_index(sdate, edate)
    NULLFLOW_CFS = 50.0 / 6.0  # CFS per node
    cols = [
        "delta_null_sink_61a",
        "delta_null_sink_61b",
        "delta_null_sink_62a",
        "delta_null_sink_62b",
        "delta_null_sink_63a",
        "delta_null_sink_63b",
    ]
    df = pd.DataFrame(0.0, index=index, columns=cols)
    df.loc[df.index.month.isin(np.arange(5, 11)), :] = NULLFLOW_CFS
    df = -df  # negative = sink
    df.index.name = "datetime"
    df.to_csv(outfile, float_format="%.3f", date_format="%Y-%m-%dT%H:%M")
    logger.info("Wrote null-zone sink CSV to %s", outfile)


def create_mss_minimum_srcsink(
    fname, var, nominal_cfs, locs, sdate, edate, sink_fraction=None
):
    """Create minimum 3-CFS source/sink exchange flows for added MSS nodes (CFS).

    For sink nodes, the flow is modulated by TPS gate state: when TPS gates
    are closed the full unmodulated flow is applied; otherwise a fractional
    sink balances the source.

    For source nodes, companion salinity and temperature files filled with
    -9999 are also written alongside *fname*.

    Parameters
    ----------
    fname : str or Path
        Output CSV path.
    var : str
        ``'src'`` (or ``'source'``) for source nodes, ``'sink'`` for sink nodes.
    nominal_cfs : float
        Nominal exchange flow magnitude in CFS (e.g. 3.0).
    locs : list of str
        Source location names (will be translated to sink names if var is ``'sink'``).
    sdate : str or Timestamp
        Start date.
    edate : str or Timestamp
        End date.
    sink_fraction : float, optional
        Ratio of sink to source for modulated (gate-open) periods. Required
        when *var* is ``'sink'``; ignored otherwise.

    Raises
    ------
    ValueError
        If *sink_fraction* is provided for a source variable.
    """
    index = _create_daily_index(sdate, edate)

    if var == "sink":
        node_names = [x.replace("src", "sink") for x in locs]
    else:
        if sink_fraction is not None:
            raise ValueError("sink_fraction is only relevant when var='sink'")
        node_names = locs

    if var == "sink":
        modulated = nominal_cfs * sink_fraction      # CFS magnitude
        unmodulated = nominal_cfs                    # CFS magnitude (gate closed → full flow)
        df = pd.DataFrame(modulated, index=index, columns=node_names)
        tps_closed, tps_locs = tps_masks(index, "sink")
        df.loc[tps_closed, tps_locs] = unmodulated
        df = -df.abs()   # sinks are negative convention
    else:
        df = pd.DataFrame(nominal_cfs, index=index, columns=node_names)

    df.index.name = "datetime"
    df.to_csv(fname, float_format="%.3f", date_format="%Y-%m-%dT%H:%M")
    logger.info("Wrote MSS minimum %s CSV to %s", var, fname)

    if var in ("src", "source"):
        out_dir = os.path.dirname(os.path.abspath(fname))
        for tracer_name, stub in [("salinity", "mss_added_salinity.csv"),
                                   ("temperature", "mss_added_temperature.csv")]:
            tracer = df.copy() * 0.0 - 9999.0
            tracer_path = os.path.join(out_dir, stub)
            tracer.to_csv(tracer_path, float_format="%.3f", date_format="%Y-%m-%dT%H:%M")
            logger.info("Wrote MSS added %s CSV to %s", tracer_name, tracer_path)


# ---------------------------------------------------------------------------
# Post-merge adjustments
# ---------------------------------------------------------------------------

def floor_source_sink_exchange(
    vsource_df,
    vsink_df,
    sd_nodes_fname=None,
    tps_th_fname=None,
    mincfs=3.0,
    sink_fraction=0.6,
):
    """Apply south-delta minimum flow floor and return adjusted CFS DataFrames.

    Clips south-delta sources to a minimum value, balances the added source
    with a fractional sink reduction, then applies special handling for Tom
    Paine Slough gate closures. All values remain in CFS.

    Parameters
    ----------
    vsource_df : DataFrame
        Merged source data (CFS, produced by merge_th).
    vsink_df : DataFrame
        Merged sink data (CFS, produced by merge_th).
    sd_nodes_fname : str or Path, optional
        CSV listing south-delta node IDs. Defaults to the canonical copy in
        ``BayDeltaSCHISM/data/channel_depletion/south_delta_nodes_extran.csv``.
    tps_th_fname : str or Path, optional
        Path to TPS culvert time-history. Defaults to canonical bdschism copy.
    mincfs : float, optional
        Minimum source flow in CFS. Default 3.0.
    sink_fraction : float, optional
        Fraction of added source applied as sink reduction. Default 0.6.

    Returns
    -------
    adj_source : DataFrame
        Adjusted source flows (CFS).
    adj_sink : DataFrame
        Adjusted sink flows (CFS).
    """
    sd_fname = sd_nodes_fname or SD_NODES_EXTRAN_CSV
    south_delta_nodes = pd.read_csv(sd_fname, header=0)
    if "node_id" not in south_delta_nodes.columns:
        south_delta_nodes["node_id"] = south_delta_nodes["id"]

    sdsrc = "delta_src_" + south_delta_nodes.node_id.astype(str)
    sdsink = "delta_sink_" + south_delta_nodes.node_id.astype(str)

    all_sources = vsource_df.copy()
    all_sinks = vsink_df.copy()

    # Clip south-delta sources to minimum (CFS)
    sd_sources = all_sources.loc[:, sdsrc]
    sd_sinks = all_sinks.loc[:, sdsink]
    sd_sources_clipped = sd_sources.clip(lower=mincfs)

    addsrc = (sd_sources_clipped - sd_sources).round(4)
    all_sources.update(sd_sources_clipped)

    addsink = addsrc * sink_fraction
    addsink.columns = [x.replace("src", "sink") for x in addsink.columns]
    all_sinks.update(sd_sinks - addsink)

    # Tom Paine: when gates are closed, avoid unbalanced flows changing levels
    tps_closed, tps_sink_locs = tps_masks(all_sources.index, "sink", tps_th_fname)
    tps_src_locs = [x.replace("sink", "src") for x in tps_sink_locs]
    logger.debug("TPS closed periods: %d of %d timesteps", tps_closed.sum(), len(tps_closed))

    all_sources.index.name = "datetime"
    all_sinks.index.name = "datetime"

    return all_sources, all_sinks


def _write_dated_th(df, fname, metadata):
    """Write a space-separated ``.th`` file with a dms-style metadata header.

    Uses ``_prepare_single_metadata_header`` from dms_datastore to produce the
    same ``# format: dwr-dms-1.0`` / ``# units:`` / ... header as
    ``write_ts_csv``, then writes the data with ``sep=" "``.
    """
    from dms_datastore.write_ts import _prepare_single_metadata_header

    header = _prepare_single_metadata_header(metadata, "dwr-dms-1.0")
    with open(fname, "w", newline="\n", encoding="utf-8") as f:
        f.write(header)
        df.to_csv(
            f, sep=" ", header=True,
            date_format="%Y-%m-%dT%H:%M:%S", float_format="%.4f",
            lineterminator="\n",
        )


def write_source_sink_th(
    vsource_df,
    vsink_df,
    vsource_th_fname,
    vsink_th_fname,
    sdate,
    edate,
    vsource_dated_th_fname=None,
    vsink_dated_th_fname=None,
    metadata=None,
):
    """Write CMS source/sink DataFrames as elapsed ``.th`` files.

    Optionally also writes dated ``.th`` files (full period, with header)
    for QC and diffing.

    Parameters
    ----------
    vsource_df : DataFrame
        Adjusted source flows (m^3/s, datetime index).
    vsink_df : DataFrame
        Adjusted sink flows (m^3/s, datetime index).
    vsource_th_fname : str or Path
        Output path for elapsed source ``.th`` file (no header).
    vsink_th_fname : str or Path
        Output path for elapsed sink ``.th`` file (no header).
    sdate : str or Timestamp
        Start date (elapsed reference and window start).
    edate : str or Timestamp
        End date for output window.
    vsource_dated_th_fname : str or Path, optional
        Output path for dated source ``.th`` file (with header, full period).
    vsink_dated_th_fname : str or Path, optional
        Output path for dated sink ``.th`` file (with header, full period).
    metadata : dict, optional
        Metadata written to the header of dated ``.th`` files.
    """
    from dms_datastore.write_ts import _prepare_single_metadata_header
    from vtools.data.timeseries import datetime_elapsed

    sdate = pd.Timestamp(sdate)
    edate = pd.Timestamp(edate)

    if vsource_dated_th_fname is not None:
        _write_dated_th(vsource_df, vsource_dated_th_fname, metadata)
        logger.info("Wrote %s", vsource_dated_th_fname)

    if vsink_dated_th_fname is not None:
        _write_dated_th(vsink_df, vsink_dated_th_fname, metadata)
        logger.info("Wrote %s", vsink_dated_th_fname)

    src_window = vsource_df.loc[sdate:edate, :]
    src_elapsed = datetime_elapsed(src_window, reftime=sdate)
    src_elapsed.to_csv(vsource_th_fname, header=False, float_format="%.4f", sep=" ")
    logger.info("Wrote %s", vsource_th_fname)

    sink_window = vsink_df.loc[sdate:edate, :]
    sink_elapsed = datetime_elapsed(sink_window, reftime=sdate)
    sink_elapsed.to_csv(vsink_th_fname, header=False, float_format="%.4f", sep=" ")
    logger.info("Wrote %s", vsink_th_fname)


def copy_paradise_up(
    msource_dated_fname,
    msource_adj_dated_fname,
    msource_adj_th_fname,
    metadata=None,
    msource_adj_dated_th_fname=None,
):
    """Propagate salinity from Paradise Cut midpoint to its head nodes.

    Copies salinity from node 807 to nodes 166, 805, 806 and from node 802
    to nodes 162, 163.

    Parameters
    ----------
    msource_dated_fname : str
        Path to merged source tracer dated CSV (multi-index: variable × location).
    msource_adj_dated_fname : str
        Output path for adjusted dated CSV (comma-sep, with metadata header).
    msource_adj_th_fname : str
        Output path for adjusted elapsed ``.th`` file (space-sep, no header).
    metadata : dict, optional
        Metadata dict passed to ``write_ts_csv`` (units, config path, etc.).
    msource_adj_dated_th_fname : str or Path, optional
        Output path for dated ``.th`` file (space-sep, with header, full period).
    """
    msource = pd.read_csv(
        msource_dated_fname, sep=r"\s+", header=[0, 1], parse_dates=[0], index_col=0
    )

    # Copy salinity from Paradise Cut midpoint (807) to head nodes
    for dest in ["delta_src_166", "delta_src_805", "delta_src_806"]:
        msource.loc[:, ("salinity", dest)] = msource.loc[:, ("salinity", "delta_src_807")]
    for dest in ["delta_src_162", "delta_src_163"]:
        msource.loc[:, ("salinity", dest)] = msource.loc[:, ("salinity", "delta_src_802")]

    # Write adjusted dated CSV
    from dms_datastore.write_ts import write_ts_csv
    write_ts_csv(
        msource,
        msource_adj_dated_fname,
        metadata=metadata,
        float_format="%.4f",
        overwrite_conventions=True,  # multi-index columns
    )
    logger.info("Wrote %s", msource_adj_dated_fname)

    if msource_adj_dated_th_fname is not None:
        _write_dated_th(msource, msource_adj_dated_th_fname, metadata)
        logger.info("Wrote %s", msource_adj_dated_th_fname)

    # Write elapsed .th (salinity/temperature — no unit conversion needed)
    msource_elapsed = msource.copy()
    msource_elapsed.index = (
        msource_elapsed.index - msource_elapsed.index[0]
    ).total_seconds()
    msource_elapsed.to_csv(
        msource_adj_th_fname, sep=" ", float_format="%.4f", header=False
    )
    logger.info("Wrote %s", msource_adj_th_fname)


# ---------------------------------------------------------------------------
# EC / salinity conversion
# ---------------------------------------------------------------------------

def inferred_to_psu(infile, outfile):
    """Convert inferred delta EC CSV to PSU salinity, adding ``delta_src_`` prefix.

    Parameters
    ----------
    infile : str or Path
        Input CSV with EC columns (no prefix; rows are timestamps).
    outfile : str or Path
        Output CSV path for PSU salinity.
    """
    df_ec = pd.read_csv(
        infile, comment="#", header=0, parse_dates=[0], index_col=0, sep=","
    )
    df_ec = df_ec.add_prefix("delta_src_")
    df_salt = ec_psu_25c(df_ec)
    os.makedirs(os.path.dirname(os.path.abspath(outfile)), exist_ok=True)
    df_salt.to_csv(outfile, float_format="%.2f", sep=",", header=True)
    logger.info("Wrote inferred salinity to %s", outfile)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

import click  # noqa: E402  (after module-level code above)


@click.command("postprocess_source_sink")
@click.option(
    "--config",
    "config_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to source/sink postprocessing workflow YAML.",
)
@click.option(
    "--set",
    "set_vars",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override a config $variable (repeatable).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Regenerate synthetic files even if they already exist.",
)
@click.option("--logdir", default=None, type=click.Path(), help="Directory for log files.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
@click.help_option("-h", "--help")
def postprocess_source_sink_cli(config_file, set_vars, force, logdir, debug):
    """Run the full source/sink postprocessing workflow.

    Orchestrates channel depletion conversion, synthetic generation, merge,
    floor exchange, and Paradise Cut salinity propagation. All file paths and
    version stamps are driven by the workflow YAML config.

    Typical usage::

        bds postprocess_source_sink --config ss_workflow.yaml --set version=20260101
    """
    from bdschism.logging_config import configure_logging
    from bdschism.source_sink_workflow import run_source_sink_workflow

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
    )
    kv = dict(s.split("=", 1) for s in set_vars)
    run_source_sink_workflow(config_file, set_vars=kv, force=force)
