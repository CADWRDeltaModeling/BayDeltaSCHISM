#!/usr/bin/env python3
"""
Slice a NetCDF time-history file by date.

Reindexes the time coordinate as elapsed seconds since the requested
start time and updates CF ``time:units``/``time:calendar`` metadata.
Designed for SCHISM ``*.th.nc`` boundary-condition files but works with
any CF-compliant NetCDF that has a recognisable time coordinate.

CLI
---
::

    slice_th_nc --start 2012-02-10 --end 2015-05-12 \\
                -o elev2D_2012_2015.th.nc elev2D_2000_2025.th.nc

    # for files without time:units (e.g. bare SCHISM uv3D.th.nc):
    slice_th_nc --reftime 2000-01-01 --start 2012-02-10 --end 2015-05-12 \\
                -o uv3D_2012_2015.th.nc uv3D_2000_2025.th.nc
"""

from __future__ import annotations
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict

import click
import numpy as np
import pandas as pd
import xarray as xr

logger = logging.getLogger(__name__)


# ---------- helpers ----------
def _find_time_coord(ds: xr.Dataset) -> str:
    """
    Identify the name of the time coordinate in a dataset.

    Checks for a coordinate named ``'time'`` first, then looks for any
    1-D datetime-like coordinate, and finally for names that match common
    time-related patterns.

    Parameters
    ----------
    ds : xr.Dataset
        Input dataset to inspect.

    Returns
    -------
    str
        Name of the detected time coordinate.

    Raises
    ------
    ValueError
        If no time coordinate can be identified.
    """
    if "time" in ds.coords:
        return "time"
    for cname, coord in ds.coords.items():
        if coord.ndim == 1 and (
            np.issubdtype(coord.dtype, np.datetime64)
            or "datetime" in str(coord.dtype).lower()
        ):
            return cname
    for cname in ds.coords:
        if cname.lower() in ("time", "times", "date", "dates"):
            return cname
    raise ValueError(
        "Could not identify a time coordinate (expected 'time' or datetime-like)."
    )


def _to_datetime64(arr) -> np.ndarray:
    """
    Convert an array-like to a numpy datetime64 array.

    Returns the input unchanged if it is already datetime64; otherwise
    attempts conversion via :func:`pandas.to_datetime`.

    Parameters
    ----------
    arr : array-like
        Values to convert (datetime64, Timestamps, strings, cftime, etc.).

    Returns
    -------
    np.ndarray
        Array of ``numpy.datetime64`` values, or the original array if
        conversion is not possible.
    """
    vals = np.asarray(arr)
    if np.issubdtype(vals.dtype, np.datetime64):
        return vals
    try:
        return pd.to_datetime(vals).values
    except Exception:
        return vals  # cftime/etc.


def _seconds_between(t1, t0) -> float:
    """
    Compute the elapsed seconds from *t0* to *t1*.

    Accepts ``numpy.datetime64``, :class:`pandas.Timestamp`, or plain
    :class:`datetime.datetime` objects.

    Parameters
    ----------
    t1 : datetime-like
        Later timestamp.
    t0 : datetime-like
        Earlier (reference) timestamp.

    Returns
    -------
    float
        Elapsed seconds ``(t1 - t0)``.
    """
    if (isinstance(t1, np.datetime64) and isinstance(t0, np.datetime64)) or (
        np.issubdtype(type(t1), np.datetime64)
        and np.issubdtype(type(t0), np.datetime64)
    ):
        return float(((t1 - t0).astype("timedelta64[ns]").astype(np.int64)) / 1e9)
    if isinstance(t1, (pd.Timestamp, datetime)) and isinstance(
        t0, (pd.Timestamp, datetime)
    ):
        return (t1 - t0).total_seconds()
    t1p, t0p = pd.to_datetime([t1, t0])
    return float((t1p - t0p).total_seconds())


def _detect_original_increment_seconds(time_vals) -> float:
    """
    Estimate the typical time step of a time coordinate in seconds.

    Uses the median of consecutive differences to be robust to occasional
    irregular steps.

    Parameters
    ----------
    time_vals : array-like
        Sequence of datetime-like values representing the time coordinate.

    Returns
    -------
    float
        Median inter-sample interval in seconds.  Returns ``0.0`` if fewer
        than two values are provided.
    """
    if len(time_vals) < 2:
        return 0.0
    vals = _to_datetime64(time_vals)
    deltas = [_seconds_between(vals[i], vals[i - 1]) for i in range(1, len(vals))]
    return float(np.median(deltas))


def _iso_without_z(dt_like) -> str:
    """
    Format a datetime-like value as an ISO 8601 string without a timezone suffix.

    Strips timezone information so the result can be embedded in CF
    ``units`` attributes (e.g. ``'seconds since 2012-02-10 00:00:00.000000'``).

    Parameters
    ----------
    dt_like : datetime-like
        Any value accepted by :class:`pandas.Timestamp`.

    Returns
    -------
    str
        ISO 8601 string with microsecond precision and no ``'Z'`` or
        ``'+00:00'`` suffix.
    """
    ts = pd.Timestamp(dt_like)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None) if hasattr(ts, "tz_convert") else ts.tz_localize(None)
    return ts.isoformat(sep=" ", timespec="microseconds")


def _parse_cf_units(units_str: str) -> Tuple[pd.Timestamp, float]:
    """
    Parse a CF ``units`` string of the form ``'<unit> since <epoch>'``.

    Parameters
    ----------
    units_str : str
        CF time units string, e.g. ``'seconds since 2000-01-01 00:00:00'``.

    Returns
    -------
    epoch : pd.Timestamp
        Reference time parsed from the string.
    seconds_per_unit : float
        Multiplier to convert raw coordinate values to seconds.

    Raises
    ------
    ValueError
        If the string cannot be parsed or the unit is not supported.
    """
    parts = units_str.strip().split(None, 2)
    if len(parts) < 3 or parts[1].lower() != "since":
        raise ValueError(f"Cannot parse CF units string: {units_str!r}")
    unit = parts[0].lower().rstrip("s")  # normalise plural: 'seconds' → 'second'
    _mult = {"second": 1.0, "minute": 60.0, "hour": 3600.0, "day": 86400.0}
    if unit not in _mult:
        raise ValueError(
            f"Unsupported time unit '{parts[0]}' in: {units_str!r}. "
            "Supported: seconds, minutes, hours, days."
        )
    return pd.to_datetime(parts[2]), _mult[unit]


# ---------- core API you can import elsewhere ----------
def slice_nc(
    infile: str,
    outfile: str,
    start: str,
    end: str,
    *,
    time_coord: Optional[str] = None,
    reftime: Optional[str] = None,
) -> Tuple[int, str]:
    """
    Slice a NetCDF time-history file to a date range and reindex time.

    Reads *infile*, selects timesteps in ``[start, end]`` (inclusive),
    replaces the time coordinate with elapsed seconds since *start*, and
    writes the result to *outfile*.  CF ``time:units`` and ``time:calendar``
    metadata are updated accordingly; a ``history`` global attribute entry
    is appended.

    Parameters
    ----------
    infile : str
        Path to the input NetCDF file.
    outfile : str
        Path for the output NetCDF file.
    start : str
        ISO-like start datetime string (e.g. ``'2012-02-10'`` or
        ``'2012-02-10T00:00'``).  Elapsed time in the output is measured
        from this instant.
    end : str
        ISO-like end datetime string (inclusive).
    time_coord : str, optional
        Explicit name of the time coordinate.  When ``None`` (default),
        the coordinate is detected automatically via
        :func:`_find_time_coord`.
    reftime : str, optional
        Reference epoch for files whose time coordinate carries no CF
        ``units`` attribute (e.g. bare SCHISM ``uv3D.th.nc`` files).
        ISO-like string (e.g. ``'2000-01-01'``).  Raw time values are
        assumed to be elapsed seconds from this epoch.  When both
        *reftime* and a ``units`` attribute are present, *reftime*
        determines the epoch and the unit multiplier is taken from
        ``units`` if parseable, otherwise seconds are assumed.  The
        supplied value is stored as the ``reftime`` global attribute in
        the output file.

    Returns
    -------
    status : int
        ``0`` on success, ``2`` on any error.
    message : str
        Human-readable status or error description.

    Notes
    -----
    * The output time array contains ``float64`` values representing seconds
      elapsed since *start*, matching typical SCHISM ``*.th.nc`` conventions.
    * Only a safe subset of encoding attributes is forwarded to the writer
      to avoid backend incompatibilities.
    * A datestamped entry is appended to the dataset's ``history`` global
      attribute.
    * When *reftime* is provided it is stored verbatim as the ``reftime``
      global attribute of the output file.
    """
    # Parse
    t_start = pd.to_datetime(start)
    t_end = pd.to_datetime(end)
    if pd.isna(t_start) or pd.isna(t_end) or (t_end < t_start):
        return 2, "ERROR: invalid --start/--end."

    # Open
    try:
        ds = xr.open_dataset(infile, decode_times=True)
    except Exception as e:
        return 2, f"ERROR: Unable to open dataset '{infile}': {e}"

    # Time name
    try:
        tname = time_coord or _find_time_coord(ds)
    except Exception as e:
        ds.close()
        return 2, f"ERROR: {e}"

    # Resolve epoch for files whose time coordinate is raw float seconds
    tcoord = ds[tname]
    if not np.issubdtype(tcoord.dtype, np.datetime64):
        units_str = tcoord.attrs.get("units", "")
        if reftime is not None:
            epoch = pd.to_datetime(reftime)
            mult = 1.0
            if units_str:
                try:
                    _, mult = _parse_cf_units(units_str)
                except ValueError:
                    pass  # fall back to seconds
        elif units_str:
            try:
                epoch, mult = _parse_cf_units(units_str)
            except ValueError as e:
                ds.close()
                return 2, f"ERROR: {e}"
        else:
            ds.close()
            return 2, (
                f"ERROR: time coordinate '{tname}' has no 'units' attribute; "
                "provide --reftime."
            )
        raw_s = tcoord.values.astype("float64") * mult
        abs_ns = (
            np.datetime64(pd.Timestamp(epoch).to_datetime64())
            + (raw_s * 1e9).astype("int64").astype("timedelta64[ns]")
        )
        ds = ds.assign_coords({tname: abs_ns})

    # Original increment (just for reporting)
    try:
        original_inc_s = _detect_original_increment_seconds(ds[tname].values)
    except Exception as e:
        ds.close()
        return 2, f"ERROR: Could not detect original time increment: {e}"

    # Slice inclusive
    try:
        ds_slice = ds.sel({tname: slice(t_start, t_end)})
    except Exception as e:
        ds.close()
        return 2, f"ERROR: Failed to slice dataset: {e}"

    if ds_slice.sizes.get(tname, 0) == 0:
        ds.close()
        return 2, "ERROR: Slice produced no data (check --start/--end)."

    # Work on a copy
    ds_out = ds_slice.copy()

    # Preserve time attrs
    time_attrs = dict(ds_out[tname].attrs) if ds_out[tname].attrs is not None else {}
    calendar = time_attrs.get("calendar", None)

    # Build new time coord as elapsed seconds since the **requested** start
    vals64 = _to_datetime64(ds_out[tname].values)
    t0 = pd.to_datetime(start)
    t0_64 = np.datetime64(t0.to_datetime64())
    delta_ns = (vals64 - t0_64).astype("timedelta64[ns]").astype(np.int64)
    new_time_vals = delta_ns.astype("float64") / 1e9

    # Assign / attrs / encoding
    new_units = f"seconds since {_iso_without_z(t0)}"
    ds_out = ds_out.assign_coords({tname: (tname, new_time_vals)})
    ds_out[tname].attrs.update(time_attrs)
    ds_out[tname].attrs["units"] = new_units
    if calendar is not None:
        ds_out[tname].attrs["calendar"] = calendar

    ds_out[tname].encoding = dict(ds_out[tname].encoding or {})
    ds_out[tname].encoding["units"] = new_units
    if calendar is not None:
        ds_out[tname].encoding["calendar"] = calendar
    ds_out[tname].encoding["dtype"] = ds[tname].encoding.get("dtype", "f8")

    # Append to global history
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    prev_hist = ds_out.attrs.get("history", "")
    if prev_hist:
        if not prev_hist.endswith((";", ".", " ")):
            prev_hist += ";"
        ds_out.attrs["history"] = f"{prev_hist} sliced to new dates {now_local}"
    else:
        ds_out.attrs["history"] = f"sliced to new dates {now_local}"

    if reftime is not None:
        ds_out.attrs["reftime"] = _iso_without_z(pd.to_datetime(reftime))

    # Backend-safe encodings
    try:
        supported = {
            "szip_coding",
            "endian",
            "blosc_shuffle",
            "contiguous",
            "_FillValue",
            "chunksizes",
            "szip_pixels_per_block",
            "complevel",
            "zlib",
            "compression",
            "least_significant_digit",
            "fletcher32",
            "shuffle",
            "dtype",
            "quantize_mode",
            "significant_digits",
        }
        encoding: Dict[str, Dict] = {}
        for v in ds_out.data_vars:
            enc = dict(ds_out[v].encoding or {})
            if enc:
                encoding[v] = {k: enc[k] for k in enc.keys() & supported}

        tenc = dict(ds_out[tname].encoding or {})
        ds_out[tname].encoding = {k: tenc[k] for k in tenc.keys() & supported}

        ds_out.to_netcdf(outfile, encoding=encoding)
    except Exception as e:
        ds.close()
        ds_out.close()
        return 2, f"ERROR: Failed to write output '{outfile}': {e}"
    finally:
        try:
            ds.close()
            ds_out.close()
        except Exception:
            pass

    n = ds_slice.sizes[tname]
    msg = (
        f"OK: wrote '{outfile}'. Sliced {tname} from {start} to {end} "
        f"(n={n}, increment\u2248{original_inc_s:.6g}s). Units: {new_units}"
    )
    logger.info(
        "Wrote '%s': %s \u2192 %s  n=%d  increment\u2248%.6gs",
        outfile, start, end, n, original_inc_s,
    )
    return 0, msg


# ---------- CLI ----------
@click.command("slice_th_nc")
@click.argument("infile", type=click.Path(exists=True))
@click.option("-o", "--out", required=True, help="Output NetCDF filename.")
@click.option(
    "--start",
    required=True,
    help="Start datetime (e.g. 2012-02-10 or 2012-02-10T00:00).",
)
@click.option(
    "--end",
    required=True,
    help="End datetime inclusive (e.g. 2015-05-12 or 2015-05-12T23:59).",
)
@click.option(
    "--reftime",
    default=None,
    metavar="DATETIME",
    help=(
        "Reference epoch for files whose time coordinate has no CF 'units' "
        "attribute (e.g. bare SCHISM uv3D.th.nc). "
        "Raw time values are assumed to be elapsed seconds since this date. "
        "Stored as the 'reftime' global attribute in the output file."
    ),
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
def slice_th_nc_cli(infile, out, start, end, reftime, logdir, debug):
    """Slice a NetCDF time-history file to a date range.

    Time is reindexed as elapsed seconds since START, and CF time
    metadata is updated.  INFILE is the input NetCDF file.

    Typical usage::

        bds slice_th_nc elev2D_2000_2026.th.nc -o elev2D_2012_2015.th.nc \\
            --start 2012-02-10 --end 2015-05-12

        bds slice_th_nc uv3D.th.nc -o uv3D_2012_2015.th.nc \\
            --reftime 2000-01-01 --start 2012-02-10 --end 2015-05-12
    """
    from bdschism.logging_config import configure_logging

    configure_logging(
        package_name="bdschism",
        level=logging.DEBUG if debug else logging.INFO,
        logdir=Path(logdir) if logdir else None,
        logfile_prefix="slice_th_nc",
    )
    code, msg = slice_nc(infile, out, start, end, reftime=reftime)
    if code:
        raise click.ClickException(msg.removeprefix("ERROR: "))


if __name__ == "__main__":
    slice_th_nc_cli()
