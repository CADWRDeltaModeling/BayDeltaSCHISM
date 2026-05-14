"""Command line tools for nudging data validation and splicing"""

import click
import numpy as np
import pandas as pd
import xarray as xr
import yaml
import os
import sys
import glob
import re
from datetime import datetime, timedelta
from vtools.functions.merge import ts_splice


def _extract_bad_data_details(var, data, bad_mask, time_var, depth_var, lat_var, lon_var, issue_type, limit=None):
    """
    Extract details of bad data points with coordinates.
    
    Parameters
    ----------
    var : str
        Variable name.
    data : ndarray
        Data array.
    bad_mask : ndarray
        Boolean mask of bad data.
    time_var, depth_var, lat_var, lon_var : xarray.DataArray or None
        Coordinate variables.
    issue_type : str
        Type of issue (e.g., 'negative', 'nan', 'inf', 'out_of_bounds', 'manual_spec').
    limit : int, optional
        Maximum number of bad data points to include. None means no limit.
    
    Returns
    -------
    list
        List of dicts with keys 'value', 'coords', 'time', 'depth', 'lat', 'lon' describing bad data points.
    """
    details = []
    indices = np.where(bad_mask)
    
    if len(indices[0]) == 0:
        return details
    
    # Get all indices if no limit, otherwise limit
    n_bad = len(indices[0])
    
    for i in range(n_bad):
        idx = tuple(ind[i] for ind in indices)
        value = data[idx]
        
        # Extract coordinates if available
        coords = []
        time_val = None
        depth_val = None
        lat_val = None
        lon_val = None
        
        if time_var is not None:
            try:
                t_idx = idx[0] if len(idx) > 0 else 0
                time_val = time_var.values[t_idx]
                coords.append(f"time={time_val}")
            except:
                pass
        
        if depth_var is not None:
            try:
                d_idx = idx[1] if len(idx) > 1 else 0
                depth_val = depth_var.values[d_idx]
                coords.append(f"depth={depth_val}")
            except:
                pass
        
        if lat_var is not None:
            try:
                la_idx = idx[2] if len(idx) > 2 else 0
                lat_val = lat_var.values[la_idx]
                coords.append(f"lat={lat_val:.4f}")
            except:
                pass
        
        if lon_var is not None:
            try:
                lo_idx = idx[3] if len(idx) > 3 else (idx[2] if len(idx) > 2 else 0)
                lon_val = lon_var.values[lo_idx]
                coords.append(f"lon={lon_val:.4f}")
            except:
                pass
        
        coord_str = ", ".join(coords) if coords else "indices: " + str(idx)
        details.append({
            "value": value,
            "coords": coord_str,
            "issue_type": issue_type,
            "time": time_val,
            "depth": depth_val,
            "lat": lat_val,
            "lon": lon_val
        })
    
    return details


def load_nc_series(nc_file):
    """

    Parameters
    ----------
    nc_file : str
        Path to NetCDF file.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame indexed by datetime with flattened spatial dimensions.
    ds : xarray.Dataset
        Original dataset used as template.
    """

    ds = xr.open_dataset(nc_file)

    time_seconds = ds["time"].values

    times = pd.to_timedelta(time_seconds, unit="s")

    data = ds["tracer_concentration"].values

    shape = data.shape

    flat = data.reshape(shape[0], -1)

    df = pd.DataFrame(flat, index=times)

    return df, ds


def validate_nudging_files(
    input_path, min_salt, max_salt, min_temp, max_temp, yaml_file=None, quick=False
):
    """
    Validate nudging data files for completeness and data quality.

    Checks that:
    - All files between earliest and latest dates exist (daily interval)
    - No data contains NaN or infinity
    - Temperature and salinity values are within specified bounds

    Supports multiple filename conventions:
    - hycom_interpolated_hourly_pst20181206.nc
    - cencoos_hourly_pst20140108.nc
    - ca_subSFB_fcst_hourly_pst20050119.nc

    Parameters
    ----------
    input_path : str
        Path to either a directory containing .nc files or a single .nc file.
    min_salt : float
        Minimum acceptable salinity value.
    max_salt : float
        Maximum acceptable salinity value.
    min_temp : float
        Minimum acceptable temperature value.
    max_temp : float
        Maximum acceptable temperature value.
    yaml_file : str, optional
        Path to YAML file with include/exclude polygon specifications.
    quick : bool, optional
        If True, checks all criteria for each variable, then moves to the next variable.
        Once any criterion fails for a variable, remaining criteria are skipped for that variable (default: False).
        This identifies bad files quickly without detailed reporting.

    Returns
    -------
    bool
        True if all validations pass, False otherwise.
    dict
        Dictionary with validation results and details about any failures.
    """
    results = {
        "success": True,
        "missing_files": [],
        "files_with_invalid_data": [],
        "date_range": None,
        "files_found": 0,
        "files_checked": 0,
        "input_path": input_path,
        "is_single_file": False,
        "quick_mode": quick,
    }

    # Handle both directory and file inputs
    if os.path.isfile(input_path):
        files = [input_path]
        results["is_single_file"] = True
    elif os.path.isdir(input_path):
        search_pattern = os.path.join(input_path, "*.nc")
        files = sorted(glob.glob(search_pattern))
    else:
        results["success"] = False
        results["error"] = f"Input path does not exist: {input_path}"
        return False, results

    if not files:
        results["success"] = False
        results["error"] = f"No .nc files found in: {input_path}"
        return False, results

    results["files_found"] = len(files)

    dates = []
    for filepath in files:
        basename = os.path.basename(filepath)
        match = re.search(r"(\d{8})", basename)
        if match:
            date_str = match.group(1)
            try:
                dt = datetime.strptime(date_str, "%Y%m%d")
                dates.append((dt, filepath))
            except ValueError:
                pass

    if not dates:
        results["success"] = False
        results["error"] = (
            "No valid dates found in filenames (expected YYYYMMDD format)"
        )
        return False, results

    dates.sort(key=lambda x: x[0])
    min_date, _ = dates[0]
    max_date, _ = dates[-1]
    results["date_range"] = {
        "start": min_date.isoformat(),
        "end": max_date.isoformat(),
    }

    date_dict = {dt: filepath for dt, filepath in dates}
    current_date = min_date
    expected_interval = timedelta(days=1)

    while current_date <= max_date:
        if current_date not in date_dict:
            results["missing_files"].append(current_date.isoformat())
            results["success"] = False
        current_date += expected_interval

    for dt, filepath in dates:
        try:
            ds = xr.open_dataset(filepath)
            results["files_checked"] += 1

            file_issues = []
            # Organize bad data by variable and issue type
            bad_data_by_var_type = {}

            # Get coordinate variables
            time_var = ds.get("time", None)
            depth_var = ds.get("depth", None)
            lat_var = ds.get("lat", None)
            lon_var = ds.get("lon", None)

            for var in ["temperature", "salinity", "temp", "salt"]:
                if var in ds.data_vars:
                    data = ds[var].values
                    data = np.asarray(data, dtype=float)
                    
                    # In quick mode, track if this variable has ANY issues
                    var_has_issue = False

                    # Check for NaN
                    if np.any(np.isnan(data)):
                        bad_mask = np.isnan(data)
                        count = np.sum(bad_mask)
                        issue_label = f"{var} has NaN values"
                        file_issues.append(issue_label)
                        key = (var, "nan")
                        bad_data_by_var_type[key] = {
                            "label": issue_label,
                            "count": 1 if quick else count,
                            "details": _extract_bad_data_details(
                                var, data, bad_mask, time_var, depth_var, lat_var, lon_var, "nan"
                            ) if not quick else []
                        }
                        var_has_issue = True

                    # Check for infinity (skip in quick mode if variable already has issue)
                    if (not quick or not var_has_issue) and np.any(np.isinf(data)):
                        bad_mask = np.isinf(data)
                        count = np.sum(bad_mask)
                        issue_label = f"{var} has infinite values"
                        file_issues.append(issue_label)
                        key = (var, "inf")
                        bad_data_by_var_type[key] = {
                            "label": issue_label,
                            "count": 1 if quick else count,
                            "details": _extract_bad_data_details(
                                var, data, bad_mask, time_var, depth_var, lat_var, lon_var, "inf"
                            ) if not quick else []
                        }
                        var_has_issue = True

                    # Check for values ending in .0 (manually specified placeholders)
                    # Skip in quick mode if variable already has issue
                    if not quick or not var_has_issue:
                        valid_mask = np.isfinite(data)
                        valid_data = data[valid_mask]
                        values_ending_in_zero = np.sum(
                            np.logical_and(valid_data == valid_data.astype(int), valid_data != 0)
                        )
                        if values_ending_in_zero > 0:
                            pct_zeros = (values_ending_in_zero / data.size) * 100
                            if pct_zeros > 1:  # Flag if > 1% of values end in .0
                                # Create mask for all data (not just valid)
                                bad_mask = np.logical_and(
                                    np.logical_and(
                                        data == np.floor(data),  # Use floor instead of cast
                                        data != 0
                                    ),
                                    np.isfinite(data)  # Only for finite values
                                )
                                count = np.sum(bad_mask)
                                issue_label = f"{var} has {values_ending_in_zero} values ({pct_zeros:.1f}%) ending in .0 (possible manual specification)"
                                file_issues.append(issue_label)
                                key = (var, "manual_spec")
                                bad_data_by_var_type[key] = {
                                    "label": issue_label,
                                    "count": 1 if quick else count,
                                    "details": _extract_bad_data_details(
                                        var,
                                        data,
                                        bad_mask,
                                        time_var,
                                        depth_var,
                                        lat_var,
                                        lon_var,
                                        "manual_spec",
                                    ) if not quick else []
                                }
                                var_has_issue = True

                    if "temp" in var.lower():
                        # Skip in quick mode if variable already has issue
                        if not quick or not var_has_issue:
                            bad_mask = np.logical_or(
                                data < min_temp, data > max_temp
                            )
                            if np.any(bad_mask):
                                count = np.sum(bad_mask)
                                issue_label = f"{var} has values outside bounds [{min_temp}, {max_temp}]"
                                file_issues.append(issue_label)
                                key = (var, "out_of_bounds")
                                bad_data_by_var_type[key] = {
                                    "label": issue_label,
                                    "count": 1 if quick else count,
                                    "details": _extract_bad_data_details(
                                        var,
                                        data,
                                        bad_mask,
                                        time_var,
                                        depth_var,
                                        lat_var,
                                        lon_var,
                                        "out_of_bounds",
                                    ) if not quick else []
                                }
                                var_has_issue = True

                    if "sal" in var.lower():
                        # Skip in quick mode if variable already has issue
                        if not quick or not var_has_issue:
                            bad_mask = np.logical_or(
                                data < min_salt, data > max_salt
                            )
                            if np.any(bad_mask):
                                count = np.sum(bad_mask)
                                issue_label = f"{var} has values outside bounds [{min_salt}, {max_salt}]"
                                file_issues.append(issue_label)
                                key = (var, "out_of_bounds")
                                bad_data_by_var_type[key] = {
                                    "label": issue_label,
                                    "count": 1 if quick else count,
                                    "details": _extract_bad_data_details(
                                        var,
                                        data,
                                        bad_mask,
                                        time_var,
                                        depth_var,
                                        lat_var,
                                        lon_var,
                                        "out_of_bounds",
                                    ) if not quick else []
                                }
                                var_has_issue = True

            if file_issues:
                results["files_with_invalid_data"].append(
                    {
                        "file": os.path.basename(filepath),
                        "issues": file_issues,
                        "bad_data_by_var_type": bad_data_by_var_type,
                    }
                )
                results["success"] = False

            ds.close()

        except Exception as e:
            results["files_with_invalid_data"].append(
                {
                    "file": os.path.basename(filepath),
                    "issues": [f"Error reading file: {str(e)}"],
                    "bad_data_by_var_type": {},
                }
            )
            results["success"] = False

    return results["success"], results


@click.command()
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(),
    help="Path to a directory containing .nc files or a single .nc file to validate.",
    show_default=False,
)
@click.option(
    "--min-salt",
    default=0.0,
    type=float,
    help="Minimum acceptable salinity value.",
    show_default=True,
)
@click.option(
    "--max-salt",
    default=50.0,
    type=float,
    help="Maximum acceptable salinity value.",
    show_default=True,
)
@click.option(
    "--min-temp",
    default=0.0,
    type=float,
    help="Minimum acceptable temperature value.",
    show_default=True,
)
@click.option(
    "--max-temp",
    default=40.0,
    type=float,
    help="Maximum acceptable temperature value.",
    show_default=True,
)
@click.option(
    "--yaml",
    default=None,
    type=click.Path(exists=True),
    help="Optional YAML file with include/exclude polygon specifications.",
    show_default=True,
)
@click.option(
    "--report-file",
    default=None,
    help="Optional output file for validation report. If not specified, report is printed to console.",
    show_default=True,
)
@click.option(
    "--quick",
    is_flag=True,
    default=False,
    help="Quick mode: stops checking each criteria once first bad point is found. Identifies bad files quickly without detailed reporting.",
    show_default=True,
)

def check_nudging_data_cli(
    input_path, min_salt, max_salt, min_temp, max_temp, yaml, report_file, quick
):
    """
    Validate nudging data files for completeness and data quality.

    Checks that:
    - All files between earliest and latest dates exist (daily interval)
    - No data contains NaN or infinity
    - Temperature and salinity values are within specified bounds

    Supports multiple filename conventions with YYYYMMDD format:
    - hycom_interpolated_hourly_pst20181206.nc
    - cencoos_hourly_pst20140108.nc
    - ca_subSFB_fcst_hourly_pst20050119.nc

    Example (directory):
        bds check_nudging_data --input ./nudging_data \\
            --min-salt 0 --max-salt 40 --min-temp 5 --max-temp 30
    
    Example (single file):
        bds check_nudging_data --input ./nudging_data/hycom_2024_01_15.nc \\
            --min-salt 0 --max-salt 40 --min-temp 5 --max-temp 30
    
    Example (quick mode):
        bds check_nudging_data --input ./nudging_data --quick \\
            --min-salt 0 --max-salt 40 --min-temp 5 --max-temp 30
    """

    success, results = validate_nudging_files(
        input_path, min_salt, max_salt, min_temp, max_temp, yaml, quick=quick
    )

    # Determine if output is to console or file
    to_file = report_file is not None
    # Limit for console display
    limit_console = 5

    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("NUDGING DATA VALIDATION REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Input Path: {input_path}")
    report_lines.append(f"Temperature Bounds: [{min_temp}, {max_temp}]")
    report_lines.append(f"Salinity Bounds: [{min_salt}, {max_salt}]")
    report_lines.append("")

    if "error" in results:
        report_lines.append(f"ERROR: {results['error']}")
    else:
        report_lines.append(f"Files Found: {results['files_found']}")
        report_lines.append(f"Files Checked: {results['files_checked']}")
        
        # Only show date range for multiple files
        if not results["is_single_file"] and results["date_range"]:
            report_lines.append(
                f"Date Range: {results['date_range']['start']} to {results['date_range']['end']}"
            )
        elif results["is_single_file"] and results["date_range"]:
            # For single file, show just the date in human-friendly format
            try:
                start_date = datetime.fromisoformat(results['date_range']['start'])
                formatted_date = start_date.strftime("%A, %B %d, %Y")
                report_lines.append(f"File Date: {formatted_date}")
            except:
                report_lines.append(f"File Date: {results['date_range']['start']}")
        
        report_lines.append("")

        # Only show missing files for multiple files
        if not results["is_single_file"] and results["missing_files"]:
            max_missing = len(results["missing_files"]) if to_file else limit_console
            report_lines.append(
                f"Missing Files ({len(results['missing_files'])} dates):"
            )
            for date in results["missing_files"][:max_missing]:
                report_lines.append(f"  - {date}")
            if len(results["missing_files"]) > max_missing:
                report_lines.append(
                    f"  ... and {len(results['missing_files']) - max_missing} more"
                )
            report_lines.append("")

        if results["files_with_invalid_data"]:
            if to_file:
                # File output: tabulated format
                report_lines.append("")
                report_lines.append("=" * 70)
                report_lines.append("DETAILED BAD DATA BY FILE")
                report_lines.append("=" * 70)
                report_lines.append("")
                
                for item in results["files_with_invalid_data"]:
                    report_lines.append(f"File: {item['file']}")
                    
                    # Include bad data details organized by variable and criteria
                    if "bad_data_by_var_type" in item and item["bad_data_by_var_type"]:
                        first_var_in_file = True
                        for (var, issue_type), issue_data in item["bad_data_by_var_type"].items():
                            details = issue_data["details"]
                            count = issue_data.get("count", len(details))
                            
                            if first_var_in_file:
                                first_var_in_file = False
                            else:
                                report_lines.append("")
                            
                            report_lines.append(f"Variable: {var}")
                            report_lines.append(f"Bad Points: {count}")
                            report_lines.append(f"{'time':<15} {'depth':<12} {'lat':<12} {'lon':<12} {'value':<12}")
                            report_lines.append("-" * 63)
                            
                            for detail in details:
                                time_str = str(detail['time']) if detail['time'] is not None else "N/A"
                                depth_str = f"{detail['depth']:.4f}" if detail['depth'] is not None else "N/A"
                                lat_str = f"{detail['lat']:.4f}" if detail['lat'] is not None else "N/A"
                                lon_str = f"{detail['lon']:.4f}" if detail['lon'] is not None else "N/A"
                                value_str = f"{detail['value']:.4f}" if not np.isnan(detail['value']) else "NaN"
                                
                                report_lines.append(
                                    f"{time_str:<15} {depth_str:<12} {lat_str:<12} {lon_str:<12} {value_str:<12}"
                                )
                    report_lines.append("")
                    report_lines.append("")
            else:
                # Console output: tabulated form with limited entries (3 per variable/criteria)
                # OR simple format for quick mode
                console_limit = 3
                report_lines.append(f"Files with Invalid Data ({len(results['files_with_invalid_data'])} files):")
                for item in results["files_with_invalid_data"][:10]:
                    report_lines.append(f"  File: {item['file']}")

                    if "bad_data_by_var_type" in item and item["bad_data_by_var_type"]:
                        if quick:
                            # Quick mode: just show what issues were found
                            for (var, issue_type), issue_data in item["bad_data_by_var_type"].items():
                                label = issue_data["label"]
                                report_lines.append(f"    ✗ {label}")
                        else:
                            # Normal mode: show tabulated data
                            for (var, issue_type), issue_data in item["bad_data_by_var_type"].items():
                                details = issue_data["details"]
                                count = issue_data.get("count", len(details))

                                report_lines.append(f"    Variable: {var}")
                                report_lines.append(f"    Bad Points: {count}")
                                # Tab-separated header aligned with data columns
                                report_lines.append("    time\t\tdepth\t\tlat\t\tlon\t\tvalue")
                                report_lines.append("    " + "-" * 70)

                                # show up to console_limit entries
                                for detail in details[:console_limit]:
                                    time_str = str(detail['time']) if detail['time'] is not None else "N/A"
                                    depth_str = f"{detail['depth']:.4f}" if detail['depth'] is not None else "N/A"
                                    lat_str = f"{detail['lat']:.4f}" if detail['lat'] is not None else "N/A"
                                    lon_str = f"{detail['lon']:.4f}" if detail['lon'] is not None else "N/A"
                                    val = detail['value']
                                    value_str = f"{val:.4f}" if not (val is None or (isinstance(val, float) and np.isnan(val))) else "NaN"
                                    report_lines.append(f"    {time_str}\t\t{depth_str}\t\t{lat_str}\t\t{lon_str}\t\t{value_str}")

                                if len(details) > console_limit:
                                    report_lines.append(f"    ... and {len(details) - console_limit} more {var} points with {issue_type} issues")
                                report_lines.append("")
                    else:
                        # If no structured bad data, fall back to listing issues
                        for issue in item.get('issues', [])[:5]:
                            report_lines.append(f"    - {issue}")

                if len(results["files_with_invalid_data"]) > 10:
                    report_lines.append(f"  ... and {len(results['files_with_invalid_data']) - 10} more files with issues")
                report_lines.append("")

    report_lines.append("=" * 70)
    if success:
        report_lines.append("STATUS: VALIDATION PASSED ✓")
    else:
        report_lines.append("STATUS: VALIDATION FAILED ✗")
    report_lines.append("=" * 70)

    report_text = "\n".join(report_lines)

    if report_file:
        os.makedirs(os.path.dirname(os.path.abspath(report_file)) or ".", exist_ok=True)
        with open(report_file, "w") as f:
            f.write(report_text)
        click.echo(f"Report written to: {report_file}")
    else:
        click.echo(report_text)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    check_nudging_data_cli()
