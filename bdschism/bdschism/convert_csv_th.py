"""Convert dated CSV time series to SCHISM time-history (``.th``) format.

Handles auto-detection of headers, optional time clipping, and output in
either dated (ISO timestamp) or elapsed-seconds format.
"""

import logging
from pathlib import Path

import click
import pandas as pd

from vtools.data.timeseries import datetime_elapsed

logger = logging.getLogger(__name__)


def detect_header(infile):
    """Detect whether a CSV has a header row and the number of index columns.

    Skips comment lines starting with ``#``. Identifies a header by finding
    a row whose first column is not parseable as a timestamp but is followed
    by a row that is.

    Parameters
    ----------
    infile : str or Path
        Path to input CSV.

    Returns
    -------
    has_header : bool
        True if a header row was detected.
    index_size : int
        Number of header rows used as column index (0 or 1).

    Raises
    ------
    ValueError
        If a potential header row has no recognisable index name.
    """
    with open(infile, "r", newline="\n") as f:
        count = 0
        prev_line = ""
        for line in f:
            if line.lstrip().startswith("#"):
                continue
            count += 1
            first_part = line.strip().split(",")[0]
            try:
                pd.Timestamp(first_part)
                if any(
                    kw in prev_line.lower()
                    for kw in ["date", "time", "datetime"]
                ):
                    return True, 1 if count == 2 else count - 2
                elif prev_line == "":
                    raise ValueError(f"Bad or missing index name in {infile}")
                else:
                    return False, 0
            except ValueError:
                prev_line = line
                continue
    return False, 0


def convert_csv_th(infile, outfile, dated, reftime=None, start=None, end=None):
    """Convert a dated CSV to a SCHISM time-history file.

    Parameters
    ----------
    infile : str or Path
        Input CSV with a datetime index. Comment lines (``#``) are preserved
        in dated output mode.
    outfile : str or Path
        Output ``.th`` file path.
    dated : bool
        If True, write ISO timestamps (``%Y-%m-%dT%H:%M``). If False, convert
        the index to elapsed seconds from *reftime*.
    reftime : str or Timestamp, optional
        Reference time for elapsed conversion. Required when *dated* is False.
    start : str or Timestamp, optional
        Clip output to rows on or after this time.
    end : str or Timestamp, optional
        Clip output to rows on or before this time.

    Raises
    ------
    ValueError
        If *reftime* is not provided when *dated* is False, or if the detected
        index is not time-related.
    """
    has_header, index_size = detect_header(infile)
    h = list(range(index_size)) if (has_header and index_size > 1) else (0 if has_header else None)

    logger.debug("%s  header=%s  index_size=%d", infile, h, index_size)
    df = pd.read_csv(infile, comment="#", index_col=0, parse_dates=True, header=h)

    if index_size > 0:
        index_name = (df.index.name or "").lower()
        if not any(kw in index_name for kw in ["time", "datetime", "date"]):
            raise ValueError(
                f"Index of {infile} does not appear to be time-related. "
                "Check the input file."
            )

    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]

    if dated:
        with open(outfile, "w", newline="") as out_f:
            with open(infile, "r") as in_f:
                for line in in_f:
                    if line.startswith("#"):
                        out_f.write(line)
            df.to_csv(
                out_f,
                sep=" ",
                date_format="%Y-%m-%dT%H:%M",
                header=has_header,
            )
    else:
        if reftime is None:
            raise ValueError("reftime must be provided when dated=False")
        df_elapsed = datetime_elapsed(df, reftime=reftime)
        with open(outfile, "w", newline="") as out_f:
            df_elapsed.to_csv(out_f, sep=" ", header=False, lineterminator="\n")

    logger.info("Wrote %s", outfile)


@click.command("csv_to_th")
@click.argument("infile", type=click.Path(exists=True))
@click.argument("outfile")
@click.option(
    "--dated/--elapsed",
    default=True,
    show_default=True,
    help="Write dated ISO timestamps or elapsed seconds.",
)
@click.option(
    "--reftime",
    default=None,
    help="Reference datetime for elapsed output (required with --elapsed).",
)
@click.option("--start", default=None, help="Clip output to rows on or after this date.")
@click.option("--end", default=None, help="Clip output to rows on or before this date.")
@click.option("--logdir", default=None, type=click.Path(), help="Directory for log files.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
@click.help_option("-h", "--help")
def csv_to_th_cli(infile, outfile, dated, reftime, start, end, logdir, debug):
    """Convert a dated CSV time series to a SCHISM ``.th`` file.

    INFILE is the input CSV. OUTFILE is the output ``.th`` path.

    Typical usage::

        bds csv_to_th vsource_adj_dated.csv vsource_adj.th --elapsed --reftime 2008-01-01
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
    )
    convert_csv_th(infile, outfile, dated=dated, reftime=reftime, start=start, end=end)
