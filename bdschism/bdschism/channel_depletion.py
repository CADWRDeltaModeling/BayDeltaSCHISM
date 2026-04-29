"""Convert channel depletion model NetCDF output to source/sink CSVs.

Output flows are in CFS. The CFS-to-CMS conversion is deferred to the
merge_th assembly step via ``scale_factor`` in ``source_sink_integration.yaml``.
DSS format is not supported.
"""

import logging
import os
from pathlib import Path

import click
import pandas as pd

logger = logging.getLogger(__name__)


def convert_nc_flow(
    infile,
    start_date,
    output_dir,
    outfile_prefix,
    col_prefix,
    scale_sink_mult=1.0,
    scale_sink_add=0.0,
):
    """Convert channel depletion NetCDF to per-component CSV files (CFS).

    Writes individual component files (div, drain, seep) and combined
    source and sink CSVs. All flow values are in CFS. Sinks are negative.

    Parameters
    ----------
    infile : str
        Path to NetCDF file containing diversion, drainage, and seepage variables.
    start_date : str
        Clip output to timestamps on or after this date (ISO format).
    output_dir : str or Path
        Directory for CSV output files. Created if it does not exist.
    outfile_prefix : str
        Prefix for output filenames (e.g. ``'dcd_20251111'``).
    col_prefix : str
        Column name prefix (e.g. ``'delta'``, ``'suisun'``).
    scale_sink_mult : float, optional
        Multiplier applied to combined sink (div+seep) in CFS before writing.
        Default 1.0.
    scale_sink_add : float, optional
        Constant (CFS) added to sink after multiplier. Default 0.0.
    """
    import xarray as xr

    logger.info("Reading %s", infile)
    ds = xr.open_dataset(infile)
    nodes = ds["node"].values
    times = ds["time"].values

    var_outnames = {"diversion": "div", "drainage": "drain", "seepage": "seep"}
    dfs = {}
    os.makedirs(output_dir, exist_ok=True)

    for var, varout in var_outnames.items():
        outfile = os.path.join(output_dir, f"{outfile_prefix}_{varout}.csv")
        logger.info("Writing %s component to %s", varout, outfile)
        h = ds[var].values
        df = pd.DataFrame(h, columns=nodes, index=times)
        df.index.name = "datetime"
        dfs[varout] = df[start_date:]
        dfs[varout].to_csv(outfile, float_format="%.2f", date_format="%Y-%m-%dT%H:%M")

    # Source = drainage in CFS, no unit conversion
    source = dfs["drain"].copy()
    source.columns = [f"{col_prefix}_src_{c}".lower() for c in source.columns]

    # Sink = div + seep, optional scaling, negative CFS convention
    sink = dfs["div"] + dfs["seep"]
    label = ""
    if scale_sink_mult != 1.0:
        sink = sink * scale_sink_mult
        label += f"_{scale_sink_mult}"
    if scale_sink_add != 0.0:
        sink = sink + scale_sink_add
        label += f"-{scale_sink_add}"
    sink = -sink.abs()
    sink.columns = [f"{col_prefix}_sink_{c}".lower() for c in sink.columns]

    src_out = os.path.join(output_dir, f"{outfile_prefix}_source.csv")
    sink_out = os.path.join(output_dir, f"{outfile_prefix}_sink{label}.csv")
    source.to_csv(src_out, float_format="%.2f", date_format="%Y-%m-%dT%H:%M")
    sink.to_csv(sink_out, float_format="%.2f", date_format="%Y-%m-%dT%H:%M")
    logger.info("Wrote %s and %s", src_out, sink_out)


def convert_channel_depletion(config_file, set_vars=None):
    """Load YAML config with ``$variable`` substitution and run NetCDF conversion.

    Parameters
    ----------
    config_file : str or Path
        Path to conversion config YAML (e.g. ``convert_config_delta.yml``).
    set_vars : dict, optional
        Variable overrides applied during ``$variable`` substitution,
        e.g. ``{'version': '20260101'}``.

    Raises
    ------
    ValueError
        If required config keys are missing or ``mode`` is not ``'flow'``.
    """
    from schimpy.schism_yaml import load as yaml_load

    if set_vars is None:
        set_vars = {}
    with open(config_file, "r") as f:
        config = yaml_load(f, envvar=set_vars)

    required = ["start_date", "infile", "output_dir", "outfile_prefix"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    mode = config.get("mode", "flow").lower()
    if mode != "flow":
        raise ValueError(
            f"channel_depletion only supports mode: flow (NetCDF). "
            f"Got '{mode}'. DSS is not supported."
        )

    flow_opts = config.get("flow_options", {})
    convert_nc_flow(
        config["infile"],
        config["start_date"],
        config["output_dir"],
        config["outfile_prefix"],
        config.get("col_prefix", ""),
        scale_sink_mult=flow_opts.get("scale_sink_mult", 1.0),
        scale_sink_add=flow_opts.get("scale_sink_add", 0.0),
    )


@click.command("cd_prep")
@click.option(
    "--config",
    "config_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to channel depletion conversion config YAML.",
)
@click.option(
    "--set",
    "set_vars",
    multiple=True,
    metavar="KEY=VALUE",
    help="Override a config $variable (repeatable, e.g. --set version=20260101).",
)
@click.option(
    "--logdir",
    default=None,
    type=click.Path(),
    help="Directory for log files.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging.",
)
@click.help_option("-h", "--help")
def cd_prep_cli(config_file, set_vars, logdir, debug):
    """Convert channel depletion NetCDF to source/sink CSVs (CFS output).

    DSS format is not supported. Typical usage::

        bds cd_prep --config convert_config_delta.yml --set version=20260101
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
    )
    kv = dict(s.split("=", 1) for s in set_vars)
    convert_channel_depletion(config_file, kv)
