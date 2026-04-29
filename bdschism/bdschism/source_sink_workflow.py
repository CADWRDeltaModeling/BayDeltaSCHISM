"""End-to-end workflow for assembling SCHISM source/sink time-history files.

Orchestrates channel depletion NetCDF conversion, POTW and inferred-EC
preparation, synthetic source/sink generation, merge_th assembly, south-delta
flow flooring, and Paradise Cut salinity propagation.

All intermediate flow CSVs are in CFS. The CFS-to-CMS conversion is applied
in step 7 before writing both dated QC CSVs and elapsed ``.th`` files.

The workflow is driven by a single YAML config (``ss_workflow.yaml``) using
schimpy ``$variable`` substitution. Changing ``version`` in that file is
typically the only edit needed when a new channel depletion NetCDF arrives.
"""

import logging
import os
from pathlib import Path

import click
import pandas as pd
from dms_datastore.write_ts import write_ts_csv
from vtools.functions.unit_conversions import CFS2CMS

logger = logging.getLogger(__name__)


def _apply_scale_factor(dated_csv, scale):
    """Multiply all values in a dated CSV by *scale* and overwrite in place.

    Used to convert CFS merged CSVs to CMS before writing to ``.th`` when
    scale_factor support is not yet available in schimpy's merge_th.

    Parameters
    ----------
    dated_csv : str or Path
        Path to a dated CSV produced by merge_th (will be overwritten).
    scale : float
        Multiplicative scale factor (e.g. ``CFS2CMS = 0.028317``).
    """
    df = pd.read_csv(dated_csv, index_col=0, parse_dates=[0])
    (df * scale).to_csv(
        dated_csv, date_format="%Y-%m-%dT%H:%M", float_format="%.4f"
    )


def run_source_sink_workflow(config_file, set_vars=None, force=False):
    """Run the complete source/sink postprocessing workflow.

    Steps
    -----
    1. Convert delta channel depletion NetCDF → CFS CSVs.
    2. Convert Suisun channel depletion NetCDF → CFS CSVs.
    3. Convert POTW CSV → flow (CFS) + salinity (PSU).
    4. Convert inferred EC CSV → salinity (PSU).
    5. Generate synthetic source/sink CSVs (skipped if outputs exist and not forced).
    6. Run ``merge_th`` to assemble per-component CFS CSVs into dated merged CSVs.
    7. Floor south-delta sources; write adjusted CFS dated CSVs and CMS ``.th``.
    8. Propagate Paradise Cut salinity; write adjusted dated CSV and ``.th``.

    Parameters
    ----------
    config_file : str or Path
        Path to ``ss_workflow.yaml``.
    set_vars : dict, optional
        Variable overrides for ``$variable`` substitution in all sub-configs,
        e.g. ``{'version': '20260101'}``.
    force : bool, optional
        If True, regenerate synthetic files even if outputs already exist.
        Default False.
    """
    from schimpy.merge_th import merge_th
    from schimpy.schism_yaml import load as yaml_load

    from bdschism.channel_depletion import convert_channel_depletion
    from bdschism.potw import potw_to_schism
    from bdschism.source_sink_postprocess import (
        added_src_sink_names,
        copy_paradise_up,
        create_mss_minimum_srcsink,
        create_nullzone_sink,
        floor_source_sink_exchange,
        write_source_sink_th,
        inferred_to_psu,
        SOURCE_MSS_YAML,
    )

    if set_vars is None:
        set_vars = {}

    with open(config_file, "r") as f:
        cfg = yaml_load(f, envvar=set_vars)

    c = cfg["config"]
    version = str(c["version"])
    work_dir = c.get("work_dir", "processed")
    output_dir = c.get("output_dir", ".")
    start_time = str(c["start_time"])
    end_time = str(c["end_time"])
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Build the set_vars dict passed down to sub-configs; merge with
    # top-level config values so version stamps propagate automatically.
    sub_vars = {str(k): str(v) for k, v in c.items()}
    sub_vars.update(set_vars)

    # Derive suisun_mod from the suisun convert config so it stays in sync
    # with scale_sink_mult / scale_sink_add rather than being duplicated.
    cd_suisun_cfg_path = cfg["channel_depletion"]["suisun"]["config"]
    with open(cd_suisun_cfg_path, "r") as f:
        _suisun_cfg = yaml_load(f, envvar=sub_vars)
    _fopts = _suisun_cfg.get("flow_options", {})
    _mult = _fopts.get("scale_sink_mult", 1.0)
    _add = _fopts.get("scale_sink_add", 0.0)
    label = ""
    if float(_mult) != 1.0:
        label += f"_{_mult}"
    if float(_add) != 0.0:
        label += f"-{_add}"
    suisun_mod = label.lstrip("_") or "1.0-0.0"
    sub_vars["suisun_mod"] = suisun_mod
    logger.info("Derived suisun_mod=%s from suisun convert config", suisun_mod)

    # ------------------------------------------------------------------
    # Step 1–2: Channel depletion NetCDF conversion
    # ------------------------------------------------------------------
    logger.info("Step 1: Converting delta channel depletion NetCDF")
    cd_delta_cfg = cfg["channel_depletion"]["delta"]["config"]
    convert_channel_depletion(cd_delta_cfg, sub_vars)

    logger.info("Step 2: Converting Suisun channel depletion NetCDF")
    convert_channel_depletion(cd_suisun_cfg_path, sub_vars)

    # ------------------------------------------------------------------
    # Step 3: POTW
    # ------------------------------------------------------------------
    logger.info("Step 3: Converting POTW data")
    potw_to_schism(c["potw_file"], work_dir)

    # ------------------------------------------------------------------
    # Step 4: Inferred EC → PSU
    # ------------------------------------------------------------------
    logger.info("Step 4: Converting inferred EC to PSU salinity")
    inferred_ec_stem = Path(c["inferred_ec_file"]).stem   # e.g. deltacd_ec_inferred_20250502
    inferred_ec_stamp = inferred_ec_stem.split("_")[-1]   # e.g. 20250502
    sub_vars["inferred_ec_stamp"] = inferred_ec_stamp
    inferred_out = os.path.join(
        work_dir, f"deltacd_salinity_inferred_{inferred_ec_stamp}.csv"
    )
    inferred_to_psu(c["inferred_ec_file"], inferred_out)

    # ------------------------------------------------------------------
    # Step 5: Synthetic source/sink generation
    # ------------------------------------------------------------------
    src_out = os.path.join(work_dir, "mss_added_source.csv")
    sink_out = os.path.join(work_dir, "mss_added_sink.csv")
    null_out = os.path.join(work_dir, "nullzone_sink.csv")

    synthetic_cfg = cfg.get("synthetic", {})
    skip_if_exists = synthetic_cfg.get("skip_if_exists", True)
    existing = all(os.path.exists(p) for p in (src_out, sink_out, null_out))
    if skip_if_exists and not force and existing:
        logger.info(
            "Step 5: Synthetic files exist — skipping (pass force=True to regenerate)"
        )
    else:
        logger.info("Step 5: Creating synthetic source/sink files")
        locs = added_src_sink_names(SOURCE_MSS_YAML)
        nominal_cfs = float(synthetic_cfg.get("nominal_cfs", 3.0))
        sink_fraction = float(synthetic_cfg.get("sink_fraction", 0.333))
        syn_sdate = pd.Timestamp(c.get("synthetic_start", "2000-01-01"))
        syn_edate = pd.Timestamp(c.get("synthetic_end", "2027-01-01"))

        create_nullzone_sink(null_out, syn_sdate, syn_edate)
        create_mss_minimum_srcsink(
            src_out, "src", nominal_cfs, locs, syn_sdate, syn_edate
        )
        create_mss_minimum_srcsink(
            sink_out, "sink", nominal_cfs, locs, syn_sdate, syn_edate,
            sink_fraction=sink_fraction,
        )

    # ------------------------------------------------------------------
    # Step 6: merge_th — first pass, produces CFS dated CSVs
    # ------------------------------------------------------------------
    logger.info("Step 6: Running merge_th (CFS intermediates)")
    merge_th_cfg_path = cfg["merge_th"]["config"]
    with open(merge_th_cfg_path, "r") as f:
        merge_th_cfg = yaml_load(f, envvar=sub_vars)
    merge_th(merge_th_cfg)

    # ------------------------------------------------------------------
    # Step 7: Floor source/sink exchange (CFS → adj CSVs) + write .th
    # ------------------------------------------------------------------
    logger.info("Step 7: Applying south-delta floor and Tom Paine handling")
    vsource_dated = os.path.join(work_dir, f"vsource_dated_{version}.csv")
    vsink_dated = os.path.join(work_dir, f"vsink_dated_{version}_{suisun_mod}.csv")
    vsource_adj_dated = os.path.join(work_dir, f"vsource_adj_{version}_dated.csv")
    vsink_adj_dated = os.path.join(
        work_dir, f"vsink_adj_{version}_dated_{suisun_mod}.csv"
    )
    vsource_adj_th = os.path.join(output_dir, f"vsource_adj_{version}.th")
    vsink_adj_th = os.path.join(output_dir, f"vsink_adj_{version}_{suisun_mod}.th")
    vsource_adj_dated_th = os.path.join(output_dir, f"vsource_adj_{version}_dated.th")
    vsink_adj_dated_th = os.path.join(output_dir, f"vsink_adj_{version}_{suisun_mod}_dated.th")

    floor_cfg = cfg.get("floor", {})
    sdate = pd.Timestamp(floor_cfg.get("sdate", start_time))
    edate = pd.Timestamp(floor_cfg.get("edate", end_time))

    vsource_df = pd.read_csv(
        vsource_dated, sep=r"\s+", header=0, index_col=0, parse_dates=[0], dtype=float
    )
    vsink_df = pd.read_csv(
        vsink_dated, sep=r"\s+", header=0, index_col=0, parse_dates=[0], dtype=float
    )
    adj_source, adj_sink = floor_source_sink_exchange(vsource_df, vsink_df)

    # Convert to CMS once here — used for both dated QC CSVs and elapsed .th
    adj_source_cms = adj_source * CFS2CMS
    adj_sink_cms = adj_sink * CFS2CMS

    _config_text = Path(config_file).read_text(encoding="utf-8")
    _flow_meta = {
        "units": "m^3/s",
        "postprocess_config": _config_text,
        "version": version,
        "suisun_mod": suisun_mod,
    }
    write_ts_csv(adj_source_cms, vsource_adj_dated, metadata=_flow_meta, float_format="%.4f")
    write_ts_csv(adj_sink_cms, vsink_adj_dated, metadata=_flow_meta, float_format="%.4f")

    write_source_sink_th(
        adj_source_cms, adj_sink_cms,
        vsource_adj_th, vsink_adj_th,
        sdate, edate,
        vsource_dated_th_fname=vsource_adj_dated_th,
        vsink_dated_th_fname=vsink_adj_dated_th,
        metadata=_flow_meta,
    )

    # ------------------------------------------------------------------
    # Step 8: Paradise Cut salinity propagation
    # ------------------------------------------------------------------
    logger.info("Step 8: Propagating Paradise Cut salinity")
    msource_dated = os.path.join(work_dir, f"msource_dated_{version}.csv")
    msource_adj_dated = os.path.join(work_dir, f"msource_adj_{version}_dated.csv")
    msource_adj_th = os.path.join(output_dir, f"msource_adj_{version}.th")
    msource_adj_dated_th = os.path.join(output_dir, f"msource_adj_{version}_dated.th")

    _tracer_meta = {
        "units": "psu_or_degC",
        "postprocess_config": _config_text,
        "version": version,
    }
    copy_paradise_up(
        msource_dated,
        msource_adj_dated,
        msource_adj_th,
        metadata=_tracer_meta,
        msource_adj_dated_th_fname=msource_adj_dated_th,
    )

    logger.info(
        "Workflow complete. SCHISM inputs written to %s:\n  %s\n  %s\n  %s",
        output_dir,
        vsource_adj_th,
        vsink_adj_th,
        msource_adj_th,
    )


@click.command("source_sink_workflow")
@click.option(
    "--config",
    "config_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to ss_workflow.yaml.",
)
@click.option(
    "--set",
    "set_vars",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override a config $variable (repeatable, e.g. --set version=20260101).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Regenerate synthetic files even if they already exist.",
)
@click.option("--logdir", default="logs", type=click.Path(), help="Directory for log files.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
@click.help_option("-h", "--help")
def source_sink_workflow_cli(config_file, set_vars, force, logdir, debug):
    """Run the full source/sink postprocessing workflow end-to-end.

    Changing ``version`` in ``ss_workflow.yaml`` (or via ``--set version=...``)
    is typically the only step needed when a new channel depletion NetCDF arrives.

    Typical usage::

        bds source_sink_workflow --config ss_workflow.yaml --set version=20260101
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="source_sink_workflow",
    )
    kv = dict(s.split("=", 1) for s in set_vars)
    run_source_sink_workflow(config_file, set_vars=kv, force=force)
