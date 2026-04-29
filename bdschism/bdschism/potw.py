"""Convert POTW (Publicly Owned Treatment Works) flow and EC data for SCHISM sources.

Output flow is in CFS (no conversion). The CFS-to-CMS conversion is deferred
to the merge_th assembly step via ``scale_factor`` in the integration config.
Salinity output is in PSU.
"""

import logging
import os
from pathlib import Path

import click
import pandas as pd

from vtools.functions.unit_conversions import ec_psu_25c

logger = logging.getLogger(__name__)


def potw_to_schism(potw_file, output_dir):
    """Convert POTW CSV to salinity (PSU) and flow (CFS) output files.

    Reads a single POTW CSV whose columns are treated as both EC (uS/cm)
    and flow (CFS) — the same file is used for both derivations, consistent
    with the ``potw_ds_cnra_flow_extended`` format where EC columns are
    present alongside flow.

    Parameters
    ----------
    potw_file : str or Path
        Path to POTW CSV file. Comments starting with ``#`` are skipped.
        First column is parsed as a datetime index.
    output_dir : str or Path
        Directory for output CSVs. Created if it does not exist.

    Notes
    -----
    Output filenames are fixed as ``potw_south_delta_salinity.csv`` and
    ``potw_south_delta_flow.csv`` within *output_dir*.
    """
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(
        potw_file, comment="#", header=0, parse_dates=[0], index_col=0, sep=","
    )
    df = df.add_prefix("potw_")

    # EC → PSU
    sal = ec_psu_25c(df).clip(lower=0.01)
    sal_out = os.path.join(output_dir, "potw_south_delta_salinity.csv")
    sal.to_csv(sal_out, float_format="%.2f", sep=",", header=True)
    logger.info("Wrote POTW salinity to %s", sal_out)

    # Flow: CFS (no CFS2CMS conversion; merge_th scale_factor handles it)
    flow = df.clip(lower=0.0)
    flow_out = os.path.join(output_dir, "potw_south_delta_flow.csv")
    flow.to_csv(flow_out, float_format="%.2f", sep=",", header=True)
    logger.info("Wrote POTW flow (CFS) to %s", flow_out)


@click.command("potw_prep")
@click.option(
    "--potw-file",
    required=True,
    type=click.Path(exists=True),
    help="Path to POTW CSV file (flow and EC).",
)
@click.option(
    "--output-dir",
    default="processed",
    show_default=True,
    help="Directory for output CSVs.",
)
@click.option("--logdir", default=None, type=click.Path(), help="Directory for log files.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
@click.help_option("-h", "--help")
def potw_prep_cli(potw_file, output_dir, logdir, debug):
    """Convert POTW CSV to salinity (PSU) and flow (CFS) for SCHISM sources.

    Typical usage::

        bds potw_prep --potw-file potw_ds_cnra_flow_extended_202501.csv
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
    )
    potw_to_schism(potw_file, output_dir)
