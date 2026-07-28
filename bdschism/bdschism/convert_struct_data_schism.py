#!/usr/bin/env python
"""Convert processed structure gate products to SCHISM ``.th`` input files.

Currently supports Clifton Court Forebay radial gate data (``ccfb``).
"""

import logging
from pathlib import Path

import click
import pandas as pd
import vtools.functions.unit_conversions as units

from dms_datastore import read_ts_repo

logger = logging.getLogger(__name__)


STRUCTURE_MAP = {
    "ccfb": {
        "station_id": "ccfb",
        "variable": "height",
        "subloc": "radial",
        "repo": "structures_processed",
    }
}


def write_ccf_th(fname, df):
    """Write an ndup/height frame (height in feet) to a SCHISM *.th file."""
    df = df.copy()
    df.index.name = "datetime"
    df["height"] = df["height"] * units.FT2M
    df["elev"] = "-4.0244"
    df["width"] = "6.096"
    df["op_down"] = "1.0"
    df["op_up"] = "0.0"
    df["ndup"] = df.ndup.astype(int)
    df["install"] = int(1)
    df[["install", "ndup", "op_down", "op_up", "elev", "width", "height"]].to_csv(
        fname, sep=" ", float_format="%.3f", date_format="%Y-%m-%dT%H:%M"
    )


def convert_struct_data_schism(
    structure,
    output,
    start=None,
    end=None,
):
    """Convert one structure's processed gate product to SCHISM ``.th`` format."""
    spec = STRUCTURE_MAP[structure]
    height_ts = read_ts_repo(
        spec["station_id"],
        spec["variable"],
        subloc=spec["subloc"],
        repo=spec["repo"],
        force_regular=False,
        start=start,
        end=end,
    )

    output_path = Path(output)
    logger.info("Writing %s", output_path)
    logger.info("Last timestamp in source data: %s", height_ts.last_valid_index())
    write_ccf_th(output_path, height_ts)


@click.command("convert_struct_data_schism")
@click.option(
    "--structure",
    type=click.Choice(sorted(STRUCTURE_MAP.keys()), case_sensitive=False),
    required=True,
    help="Structure key to convert (currently: ccfb).",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to output SCHISM .th file.",
)
@click.option(
    "--start",
    default=None,
    help="Optional inclusive start datetime.",
)
@click.option(
    "--end",
    default=None,
    help="Optional inclusive end datetime.",
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
def convert_struct_data_schism_cli(structure, output, start, end, logdir, debug):
    """Convert processed structure gate series to SCHISM ``.th`` format.

    Example:
        convert_struct_data_schism --structure ccfb --output ccfb_radial.th
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="convert_struct_data_schism",
    )

    start_ts = pd.to_datetime(start) if start else None
    end_ts = pd.to_datetime(end) if end else None

    convert_struct_data_schism(
        structure=structure.lower(),
        output=output,
        start=start_ts,
        end=end_ts,
    )


if __name__ == "__main__":
    convert_struct_data_schism_cli()
