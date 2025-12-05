#!/usr/bin/env python
"""
Create synthetic HRRR forcing files by copying an existing repository
and shifting all dates forward by one year.

For each day in [sdate, edate], the script:

- Reads:  {source_repo}/{YEAR}/hrrr_YYYYMMDD00.nc
- Writes: {dest_repo}/{YEAR+1}/hrrr_{YEAR+1}{MM}{DD}00.nc

Leap-year handling
------------------
- If the source year is a leap year but the destination year is not:
    * Feb 29 is skipped.
- If the source year is not a leap year but the destination year is:
    * Feb 29 is created by copying Feb 28 and shifting the time one day.

The script also:
- Shifts the xarray Dataset `time` coordinate by +1 year (or +1 year +1 day
  for synthetic Feb 29).
- Updates `time.attrs["base_date"]` to reflect the new date.
- Adds provenance attributes:
    - "creator" = "CA DWR Delta Modeling Section"
    - "creation_method" = description of what was copied.

This is intended for creating synthetic “next-year” met forcing when you want
to reuse a prior year.
"""

import logging
import os
from pathlib import Path

import click
import pandas as pd
import xarray as xr


log = logging.getLogger(__name__)


def is_leap_year(year: int) -> bool:
    """Return True if *year* is a leap year (Gregorian rules)."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def configure_logging(verbose: bool) -> None:
    """Configure root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s - %(message)s",
    )

def _normalize_time_units(ds):
    """
    Ensure xarray's CF encoder doesn't choke on 'units' in time.attrs.

    - If time.attrs["units"] exists, move it into time.encoding["units"]
      and delete it from attrs.
    """
    if "time" not in ds:
        return ds

    time_var = ds["time"]

    # If units live in attrs, move them to encoding
    if "units" in time_var.attrs:
        units = time_var.attrs["units"]
        del time_var.attrs["units"]
        time_var.encoding["units"] = units

    return ds



@click.command(
    help=(
        "Create synthetic HRRR files by copying an existing repository and "
        "shifting dates forward by one year.\n\n"
        "Example:\n"
        "  synthetic_copy \\\n"
        "    --source-repo //cnrastore-bdo/modeling_data/atmospheric/atmospheric_hrrr \\\n"
        "    --dest-repo   ./synthetic \\\n"
        "    --sdate 2020-01-01 --edate 2020-02-02\n"
    )
)
@click.option(
    "--source-repo",
    "source_repo",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing existing HRRR files, organized as YEAR/hrrr_YYYYMMDD00.nc.",
)
@click.option(
    "--dest-repo",
    "dest_repo",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory where synthetic shifted files will be written.",
)
@click.option(
    "--sdate",
    required=True,
    type=str,
    help="Start date (inclusive) in format YYYY-MM-DD, e.g. 2020-01-01.",
)
@click.option(
    "--edate",
    required=True,
    type=str,
    help="End date (inclusive) in format YYYY-MM-DD, e.g. 2020-02-02.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    show_default=True,
    help="If set, only show what would be done; do not write any files.",
)
@click.option(
    "--strict/--no-strict",
    default=True,
    show_default=True,
    help=(
        "If strict, missing source files cause the script to abort. "
        "If not strict, they are logged and skipped."
    ),
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable debug-level logging.",
)
def main(source_repo, dest_repo, sdate, edate, dry_run, strict, verbose):
    """
    Entry point for the synthetic_copy CLI.
    """
    configure_logging(verbose)

    source_repo = source_repo.resolve()
    dest_repo = dest_repo.resolve()

    log.info("Source repo : %s", source_repo)
    log.info("Dest repo   : %s", dest_repo)
    log.info("Date range  : %s to %s", sdate, edate)
    log.info("Dry run     : %s", dry_run)
    log.info("Strict mode : %s", strict)

    # Create dest root if needed
    if not dry_run and not dest_repo.exists():
        log.info("Creating destination directory %s", dest_repo)
        dest_repo.mkdir(parents=True, exist_ok=True)

    # Build date range
    try:
        start_date = pd.to_datetime(sdate).normalize()
        end_date = pd.to_datetime(edate).normalize()
    except Exception as exc:
        raise click.ClickException(f"Failed to parse dates: {exc}")

    if end_date < start_date:
        raise click.ClickException("edate must be on or after sdate.")

    date_rng = pd.date_range(start=start_date, end=end_date, freq="D")

    # Pre-create all destination year folders
    src_years = sorted({d.year for d in date_rng})
    dest_years = [y + 1 for y in src_years]

    for y in dest_years:
        out_year_dir = dest_repo / f"{y:04d}"
        if dry_run:
            log.info("[DRY-RUN] Would ensure directory exists: %s", out_year_dir)
        else:
            if not out_year_dir.exists():
                log.debug("Creating output year directory %s", out_year_dir)
                out_year_dir.mkdir(parents=True, exist_ok=True)

    # Main loop over days
    for d in date_rng:
        src_year = d.year
        dest_year = src_year + 1
        month = d.month
        day = d.day

        # Leap → non-leap: skip Feb 29
        if is_leap_year(src_year) and not is_leap_year(dest_year):
            if month == 2 and day == 29:
                log.info(
                    "Skipping Feb 29 %d (source leap year to non-leap dest year %d)",
                    src_year,
                    dest_year,
                )
                continue

        src_dir = source_repo / f"{src_year:04d}"
        src_file = src_dir / f"hrrr_{src_year:04d}{month:02d}{day:02d}00.nc"

        dest_dir = dest_repo / f"{dest_year:04d}"
        dest_file = dest_dir / f"hrrr_{dest_year:04d}{month:02d}{day:02d}00.nc"

        if not src_file.exists():
            msg = f"Missing source file: {src_file}"
            if strict:
                log.error(msg)
                raise click.ClickException(msg)
            else:
                log.warning("%s (skipping due to --no-strict)", msg)
                continue

        log.info("Processing %s  ->  %s", src_file, dest_file)

        if dry_run:
            continue

        # Open source dataset and shift by 1 year
        with xr.open_dataset(src_file) as ds:
            ds = ds.load()  # ensure data in memory before context close

        # Set/adjust attributes
        attr_synth = "creator"
        val_synth = "CA DWR Delta Modeling Section"
        attr_method = "creation_method"
        val_method = f"Filled missing date by copying {src_file} and changing dates"

        ds.attrs[attr_synth] = val_synth
        ds.attrs[attr_method] = val_method


        # Adjust time attributes only: shift origin by +1 year
        if "time" not in ds:
            raise click.ClickException(f"'time' coordinate not found in {src_file}")

        bd = ds.time.attrs.get("base_date", None)
        if bd is None:
            raise click.ClickException(
                f"'time.base_date' attribute not found in {src_file}"
            )

        bd = list(bd)
        old_year, month, day = bd[0], bd[1], bd[2]

        # shift base_date year by +1
        new_year = old_year + 1
        bd[0] = new_year
        ds.time.attrs["base_date"] = bd

        # update units to match new base_date
        ds.time.attrs["units"] = f"days since {new_year}-{month}-{day} 00:00 UTC"
        ds.time.attrs["long_name"] = "Time"

        # IMPORTANT: do NOT modify ds["time"].values here.
        # The numeric values remain the same (0.. <1 day), but their origin moved by 1 year.


        # Write out the shifted file
        ds = _normalize_time_units(ds)
        ds.to_netcdf(path=dest_file, format="NETCDF4")
        ds.to_netcdf(path=dest_file, format="NETCDF4")

        # Non-leap → leap: create Feb 29 from Feb 28
        if is_leap_year(dest_year) and not is_leap_year(src_year):
            # When current source date is Feb 28, synthesize Feb 29.
            if month == 2 and day == 28:
                feb29_dest_file = dest_dir / f"hrrr_{dest_year:04d}022900.nc"
                log.info(
                    "Creating synthetic Feb 29 %d by copying Feb 28 data -> %s",
                    dest_year,
                    feb29_dest_file,
                )

                with xr.open_dataset(src_file) as ds_feb28:
                    ds_feb28 = ds_feb28.load()

                ds_feb28.attrs[attr_synth] = val_synth
                ds_feb28.attrs[attr_method] = (
                    f"Created Feb 29 by copying Feb 28 data from {src_file} and changing date"
                )

                bd29 = ds_feb28.time.attrs.get("base_date", None)
                if bd29 is None:
                    raise click.ClickException(
                        f"'time.base_date' attribute not found in {src_file} (for Feb 29 creation)"
                    )

                bd29 = list(bd29)
                old_year, month, _ = bd29[0], bd29[1], bd29[2]

                new_year = old_year + 1
                bd29[0] = new_year   # +1 year
                bd29[2] = 29         # day = 29
                ds_feb28.time.attrs["base_date"] = bd29

                # Update units to reflect Feb 29 as the new origin
                ds_feb28.time.attrs["units"] = f"days since {new_year}-{month}-29 00:00 UTC"
                ds_feb28.time.attrs["long_name"] = "Time"

                ds_feb28 = _normalize_time_units(ds_feb28)
                ds_feb28.to_netcdf(path=feb29_dest_file, format="NETCDF4")


if __name__ == "__main__":
    main()
