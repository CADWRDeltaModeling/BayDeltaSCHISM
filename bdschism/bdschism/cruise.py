import datetime as dtm
from .profile_plot import profile_plot
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager, FontProperties
import sys
import pandas as pd
import numpy as np
import os
import re
from dateutil import parser
import errno
from shutil import copyfile, which
import subprocess
import click
import textwrap

RED = (228 / 256.0, 26 / 256.0, 28 / 256.0)
BLUE = (55 / 256.0, 126 / 256.0, 184 / 256.0)

plt.style.use(["seaborn-v0_8-paper", "seaborn-v0_8-colorblind"])

PAPER_RC = {
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.titlesize": 9,
    "savefig.dpi": 600,
}

DEFAULT_START = "2011-03-29"
DEFAULT_OUTPUT_SUBDIR = "2011outputs"


def validate_out2d_time_variable(out2d_path):
    """Validate that SCHISM output file contains valid time dimension data.
    
    Checks that the out2d_*.nc file exists and contains a non-empty,
    non-NaN 'time' variable with numeric values. This validation ensures
    the file is suitable for SCHISM model extraction via read_output10_xyt.
    
    Parameters
    ----------
    out2d_path : str
        Path to SCHISM out2d_*.nc output file to validate.
    
    Raises
    ------
    FileNotFoundError
        If the specified out2d file does not exist.
    ValueError
        If time variable is missing, empty, or contains invalid/NaN values.
    """
    if not os.path.exists(out2d_path):
        raise FileNotFoundError(
            errno.ENOENT,
            os.strerror(errno.ENOENT),
            out2d_path,
        )

    def _check_time_values(time_values, source):
        if time_values.size == 0:
            raise ValueError(f"{source} contains an empty 'time' variable.")

        try:
            numeric_time = np.asarray(time_values, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{source} contains non-numeric values in the 'time' variable."
            ) from exc

        if not np.all(np.isfinite(numeric_time)):
            raise ValueError(
                f"{source} contains invalid 'time' values (NaN/Inf)."
            )

    # Try to validate with netCDF4 first, fallback to xarray.
    try:
        from netCDF4 import Dataset

        with Dataset(out2d_path, "r") as ds:
            if "time" not in ds.variables:
                raise ValueError(
                    f"{out2d_path} does not contain a 'time' variable required by read_output10_xyt."
                )
            _check_time_values(ds.variables["time"][:], out2d_path)
    except ImportError:
        try:
            import xarray as xr

            with xr.open_dataset(out2d_path) as ds:
                if "time" not in ds:
                    raise ValueError(
                        f"{out2d_path} does not contain a 'time' variable required by read_output10_xyt."
                    )
                _check_time_values(ds["time"].values, out2d_path)
        except ImportError as exc:
            raise ImportError(
                "Could not validate out2d_1.nc because neither netCDF4 nor xarray is installed. "
                "Install one of these packages to enable time-variable validation."
            ) from exc


def check_read_output10_xyt_available():
    """Check if read_output10_xyt executable is available in PATH.
    
    Verifies that the SCHISM read_output10_xyt utility is available in the
    system PATH. This executable is required for extracting model profiles
    from SCHISM output files.
    
    Raises
    ------
    FileNotFoundError
        If read_output10_xyt executable is not found in PATH, with a helpful
        error message instructing the user how to add it to their environment.
    """
    if which("read_output10_xyt") is None:
        raise FileNotFoundError(
            f"The 'read_output10_xyt' executable was not found in your system PATH.\n\n"
            f"This executable is required for extracting SCHISM model profiles.\n"
            f"To fix this issue:\n\n"
            f"1. Locate the SCHISM build directory containing the read_output10_xyt executable\n"
            f"2. Add it to your PATH by running one of the following:\n\n"
            f"   # Temporarily (for current session):\n"
            f"   export PATH=/path/to/schism/build/bin:$PATH\n\n"
            f"   # Permanently (add to ~/.bashrc or ~/.bash_profile):\n"
            f"   echo 'export PATH=/path/to/schism/build/bin:$PATH' >> ~/.bashrc\n"
            f"   source ~/.bashrc\n\n"
            f"Replace '/path/to/schism/build/bin' with the actual path to your SCHISM executable directory."
        )


def process_stations(station_file):
    """Load and process USGS cruise station metadata.
    
    Reads station information from CSV file and normalizes station IDs by
    removing trailing ".0" suffixes. Converts distance from meters to kilometers.
    Station data is indexed by ID for efficient lookup during cruise processing.
    
    Parameters
    ----------
    station_file : str
        Path to CSV file containing station metadata. Expected format:
        id, x, y, dist_km, elev_navd, name, depth_mllw
    
    Returns
    -------
    pd.DataFrame
        DataFrame indexed by station ID (str) with columns:
        x (longitude), y (latitude), dist_km (distance in km),
        elev_navd, name, depth_mllw.
        Distance values are converted from meters to kilometers.
    """
    sd = pd.read_csv(
        station_file,
        names=["id", "x", "y", "dist_km", "elev_navd", "name", "depth_mllw"],
        header=0,
        dtype={"id": pd.StringDtype()},
    )

    for i in range(sd.shape[0]):
        station = sd["id"][i]
        if station.endswith(".0"):
            station = station[:-2]
            sd.at[i, "id"] = station

    sd = sd.set_index("id")
    sd.dist_km = sd.dist_km / 1000.0
    return sd


def process_cruise(path):
    """Load and organize single cruise observation data from file.
    
    Reads cruise data from a text file, organizes observations by station,
    validates salinity values, and sorts depths in ascending order for each
    station. This function handles the temporary single-date format created
    from yearly CSV data.
    
    Parameters
    ----------
    path : str
        Path to cruise data file with CSV format:
        Date,Time,Station,Depth(m),Salinity (with header line)
    
    Returns
    -------
    dict
        Dictionary mapping station ID (str) to tuple of:
        (depth_array, salinity_array, observation_datetime).
        Both depth and salinity are numpy arrays sorted by depth (ascending).
    
    Raises
    ------
    ValueError
        If salinity values cannot be converted to float for a given station.
        That station is excluded and a warning is printed.
    """
    print("process_cruise")
    cruisefile = open(path, "r")
    cruisetxt = cruisefile.readlines()[1:]
    cruisefile.close()
    cruiselines = [line.strip().split(",") for line in cruisetxt if (line != "\n")]
    cruise_data = {}
    for entry in cruiselines:
        time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%Y-%m-%d %H:%M")
        station = entry[2]
        if station.endswith(".0"):
            station = station[:-2]

        if not station in cruise_data.keys():
            cruise_data[station] = ([], [], time)
        depth = float(entry[3])
        try:
            salinity = float(entry[4])
        except ValueError:
            print(
                path + " station no." + station + " has invalid salinity observation!"
            )
            cruise_data.pop(station, None)
            continue
        cruise_data[station][0].append(depth)
        cruise_data[station][1].append(salinity)
    for station in cruise_data.keys():
        time = cruise_data[station][2]
        depth = np.array(cruise_data[station][0])
        salinity = np.array(cruise_data[station][1])
        depthorder = np.argsort(depth)
        depth = depth[depthorder]
        salinity = salinity[depthorder]
        cruise_data[station] = (depth, salinity, time)
    return cruise_data


def process_cruise_yearly_csv(path, target_stations=None, depth_threshold_stations=None, model_start_time=None):
    """Process yearly USGS cruise data from CSV file.
    
    Parameters
    ----------
    path : str
        Path to yearly CSV file (e.g., usgs_cruise_2011.csv)
    target_stations : list, optional
        List of station IDs to include. If None, all stations are included.
        Expected format: list of strings like ['2', '3', ..., '649', '657']
    depth_threshold_stations : dict, optional
        Dictionary mapping station IDs to minimum depth threshold.
        E.g., {'7': 9, '8': 9, '9': 9} means stations 7, 8, 9 need depth > 9.
        If the maximum depth for a station on a given day is below threshold,
        ALL observations for that station on that day are excluded.
    model_start_time : datetime, optional
        Filter out observations made before this time and within 1 month after start.
        If None, no time filtering applied.
    
    Returns
    -------
    dict
        Dictionary of cruise records indexed by date string (YYYY-MM-DD format).
        Each value is a dict mapping station ID to (depth, salinity, time) tuple.
    """
    print("process_cruise_yearly_csv")
    
    # Default filtering: include stations 2-18, 649, 657
    if target_stations is None:
        target_stations = [str(i) for i in range(2, 19)] + ['649', '657']
    target_stations = set(target_stations)
    
    # Default depth thresholds: stations 7, 8, 9 need depth > 9
    if depth_threshold_stations is None:
        depth_threshold_stations = {'7': 9, '8': 9, '9': 9}
    
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Error reading CSV file {path}: {e}")
        return {}
    
    # First pass: collect all raw data and identify (date, station) pairs 
    # that have maximum depth below threshold
    invalid_date_station_pairs = set()
    raw_data_by_key = {}  # {(date_key, station): [depths, salinities, times]}
    
    # Calculate 1 month after model start for filtering
    one_month_after_start = None
    if model_start_time is not None:
        if model_start_time.month == 12:
            one_month_after_start = model_start_time.replace(year=model_start_time.year + 1, month=1)
        else:
            one_month_after_start = model_start_time.replace(month=model_start_time.month + 1)
    
    for idx, row in df.iterrows():
        try:
            date_str = row['Date']
            time_str = row['Time']
            
            # Parse datetime
            time = dtm.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
            # Filter out observations before model start time and within 1 month after start
            if one_month_after_start is not None and time < one_month_after_start:
                continue
            
            date_key = time.strftime("%Y-%m-%d")
            
            # Parse station
            station = str(row['Station']).strip()
            if station.endswith('.0'):
                station = station[:-2]
            
            # Check if station is in target set
            if station not in target_stations:
                continue
            
            # Parse depth and salinity
            try:
                depth = float(row['Depth (m)'])
            except (ValueError, TypeError):
                continue
            
            try:
                salinity = float(row['Salinity'])
            except (ValueError, TypeError):
                continue
            
            # Store raw data
            key = (date_key, station)
            if key not in raw_data_by_key:
                raw_data_by_key[key] = ([], [], [])
            raw_data_by_key[key][0].append(depth)
            raw_data_by_key[key][1].append(salinity)
            raw_data_by_key[key][2].append(time)
                    
        except Exception as e:
            continue
    
    # Check depth threshold for each (date, station) pair based on maximum depth
    for key, (depths, salinities, times) in raw_data_by_key.items():
        date_key, station = key
        if station in depth_threshold_stations:
            min_depth = depth_threshold_stations[station]
            max_depth = max(depths)
            if max_depth <= min_depth:
                # Mark this (date, station) pair as invalid
                invalid_date_station_pairs.add(key)
    
    # Second pass: build cruise_records from raw data, skipping invalid (date, station) pairs
    cruise_records = {}
    
    # Build cruise_records from raw data, skipping invalid (date, station) pairs
    for key, (depths, salinities, times) in raw_data_by_key.items():
        date_key, station = key
        
        # Skip if this (date, station) pair is invalid due to depth threshold
        if key in invalid_date_station_pairs:
            continue
        
        # Initialize cruise record for this date if not exists
        if date_key not in cruise_records:
            cruise_records[date_key] = {}
        
        # Use the first time as representative time for this station/day
        time = times[0]
        
        # Store depths and salinities
        cruise_records[date_key][station] = (depths, salinities, time)
    
    # Sort depth profiles for each station on each date
    for date_key in cruise_records:
        for station in list(cruise_records[date_key].keys()):
            time = cruise_records[date_key][station][2]
            depth = np.array(cruise_records[date_key][station][0])
            salinity = np.array(cruise_records[date_key][station][1])
            
            # Skip if no valid data
            if len(depth) == 0:
                del cruise_records[date_key][station]
                continue
            
            depthorder = np.argsort(depth)
            depth = depth[depthorder]
            salinity = salinity[depthorder]
            cruise_records[date_key][station] = (depth, salinity, time)
    
    # Filter: remove days that don't have all required stations
    required_stations = target_stations.copy()
    dates_to_remove = []
    
    for date_key in cruise_records:
        stations_on_day = set(cruise_records[date_key].keys())
        
        # Check if all required stations are present
        if not required_stations.issubset(stations_on_day):
            missing_stations = required_stations - stations_on_day
            print(f"Removing {date_key}: missing stations {sorted(missing_stations)}")
            dates_to_remove.append(date_key)
    
    for date_key in dates_to_remove:
        del cruise_records[date_key]
    
    return cruise_records


def process_xyt(path, casts, base_time):
    """Load SCHISM model output from fort.18 (xyt format) file.
    
    Parses SCHISM model salinity profiles extracted to fort.18 format,
    maps results to station IDs using the casts mapping, and organizes
    data by station with depths sorted in ascending order.
    
    Parameters
    ----------
    path : str
        Path to fort.18 model output file containing extracted salinity profiles.
    casts : dict
        Dictionary mapping cast number (int) to tuple:
        (x_coord, y_coord, elapsed_time, name, station_id).
        Typically generated by cruise_xyt().
    base_time : datetime.datetime
        Reference time for converting elapsed seconds in fort.18 to absolute times.
    
    Returns
    -------
    dict
        Dictionary mapping station ID (str) to tuple of:
        (depth_array, salinity_array, observation_time).
        Depths and salinities are numpy arrays sorted by depth.
    
    Raises
    ------
    ValueError
        If cast number in fort.18 is not found in casts mapping.
    """
    print("process_xyt")
    cruisefile = open(path, "r")
    cruisetxt = cruisefile.readlines()
    cruisefile.close()
    cruiselines = [line.strip().split() for line in cruisetxt if (line != "\n")]
    cruise_data = {}
    
    for entry in cruiselines:
        if "&" in entry:
            continue
        castno = int(entry[0])
        if "**" in entry[1]:
            continue
        salt = float(entry[1])
        depth = -float(entry[2])
        elapsed = 24.0 * 3600.0 * float(entry[4])
        time = base_time + dtm.timedelta(seconds=elapsed)
        if castno not in casts.keys():
            raise ValueError("Cast %s not in casts" % castno)

        station = casts[castno][4]

        if not station in cruise_data.keys():
            cruise_data[station] = ([], [], time)
        cruise_data[station][0].append(depth)
        cruise_data[station][1].append(salt)
    for station in cruise_data.keys():
        time = cruise_data[station][2]
        depth = np.array(cruise_data[station][0])
        salinity = np.array(cruise_data[station][1])
        depthorder = np.argsort(depth)
        depth = depth[depthorder]
        salinity = salinity[depthorder]
        cruise_data[station] = (depth, salinity, time)
    return cruise_data


def match_cruise(time, station, x, z, times, data):
    times = np.array(times)
    ndxR = np.searchsorted(times, time)
    ndxL = max(ndxR - 1, 0)
    if not (time >= times[0] and time <= times[-1]):
        raise ValueError(
            "Time %s (in days) is not in model file spanning from %s to %s"
            % (time, times[0], times[-1])
        )
    wl = (times[ndxR] - time) / (times[ndxR] - times[ndxL])
    wr = 1 - wl
    station_ndx = station.data_index
    profile = wl * data[ndxL, :, station_ndx] + wr * data[ndxR, :, station_ndx]

    xx = x[:, station_ndx]
    zz = z[:, station_ndx]
    ndx_farleft = max(ndxL - 2, 0)
    ndx_farright = min(ndxR + 3, len(times))
    surrounding_profiles = [(time, profile)]
    for n in range(ndx_farleft, ndx_farright):
        t = times[n]
        vals = data[n, :, station_ndx]
        surrounding_profiles.append((t, vals))
    return zz, surrounding_profiles


def do_depth_plot(
    station, cruise_data, surrounding_profiles, ax, xlabel, ylabel, add_legend=False
):

    profiles = []
    all_lines = []
    col = None
    i = 0
    for i, prof in enumerate(surrounding_profiles):
        p = np.array(prof[1])
        zz = np.array(prof[0])
        p = np.ma.masked_where(np.isnan(p), p)
        z_masked = np.ma.masked_where(np.isnan(p), zz)
        linestyle = "solid"
        if i == 0:
            col = BLUE
            label = "Model"
            wide = 2
        else:
            col = "0.55"
            wide = 1
            label = "Model +/- 3 hr" if label == "Model" else "_nolegend_"
            linestyle = "--"
        (line,) = ax.plot(p, z_masked, color=col, linewidth=wide, linestyle=linestyle)
        i += 1
        all_lines.append(line)

    depth, salinity, time = cruise_data
    (line,) = ax.plot(salinity, depth, color=RED, label="Observed", linewidth=2)
    all_lines.append(line)
    ax.set_ylim(max(z_masked), 0)
    min_data, max_data = ax.get_xlim()
    xcenter = (min_data + max_data) / 2
    xrange = max_data - min_data
    if xrange < 8.0:
        print(" > 8")
        # ax.set_xlim(max(0,min_data-3.5), min(35,max_data+3.5))
    if xlabel != None:
        ax.set_xlabel(xlabel, size=14)
    if ylabel != None:
        ax.set_ylabel("Depth (m)", size=14)
    if add_legend:
        leg = ax.legend(
            (all_lines[0], all_lines[1], all_lines[-1]),
            ("Model", "Model +/- 3 hr", "Observed"),
            loc="lower left",
            shadow=True,
            fancybox=True,
        )

        ltext = leg.get_texts()  # all the text.Text instance in the legend
        llines = leg.get_lines()  # all the lines.Line2D instance in the legend
        # frame.set_facecolor('0.80')      # set the frame face color to light gray
        # ax.setp(ltext, fontsize='small')    # the legend text fontsize
        # ax.setp(llines, linewidth=1.5)      # the legend linewidth

    # ax.set_xlim(0,35)


def longitudinal(
    cruise_data,
    station_data,
    ax,
    context_label=None,
    add_labels=False,
    xlabel=None,
    xmin=None,
    xmax=None,
    max_depth=None,
    ylabel=True,
    show_xticklabels=True,
):
    print("Longitudinal")
   
    maxdepth = 0
    stations = []
    station_dists = []
    bedx = []
    bed = []
    for item in cruise_data.keys():
        if station_data.loc[item].dist_km > 0.0:
            # print "Station %s" % item
            # print cruise_data[item]
            maxdepth = max(maxdepth, max(cruise_data[item][0]))

            stations.append(item)
            station_dists.append(station_data.loc[item].dist_km)
            bedx.append(station_data.loc[item].dist_km)
            bed.append(-max(cruise_data[item][0]))
    station_dists = np.array(station_dists)
    stations = np.array(stations)
    sorted_dists = np.argsort(station_dists)
    stations = stations[sorted_dists]
    station_dists = station_dists[sorted_dists]
    nstation = len(station_dists)
    ndepth = int(maxdepth + 1)
    salt = np.ones((ndepth, nstation), dtype=float) * np.nan
    zloc = np.ones((ndepth, nstation), dtype=float) * np.nan
    from scipy.interpolate import griddata

    for i in range(nstation):
        item = stations[i]
        depth, salinity, time = cruise_data[item]
        salt[:, i] = griddata(depth, salinity, np.arange(ndepth, dtype=float))
        if np.isnan(salt[0, i]):
            salt[0, i] = salt[1, i]
        # zloc[0:len(salinity),i] = depth

    xloc, zloc = np.meshgrid(station_dists, np.arange(ndepth, dtype=float))
    im, cs, ttxt = profile_plot(
        xloc,
        zloc,
        salt,
        ax,
        context_label=context_label,
        add_labels=add_labels,
        xlabel=xlabel,
        xmin=xmin,
        xmax=xmax,
        max_depth=max_depth,
        ylabel=ylabel,
        show_xticklabels=show_xticklabels,
    )

    return cs


def model_data_for_longitude(
    cruise_data, station_data, x, z, times, model_data, base_date
):
    maxdepth = 0
    stations = []
    station_dists = []
    # todo: this is boilerplate
    for item in cruise_data.keys():
        if station_data[item].dist_km > 0.0:
            maxdepth = max(maxdepth, max(cruise_data[item][0]))
            stations.append(item)
            station_dists.append(station_data[item].dist_km)

    station_dists = np.array(station_dists)
    stations = np.array(stations)
    sorted_dists = np.argsort(station_dists)
    stations = stations[sorted_dists]
    station_dists = station_dists[sorted_dists]
    nstation = len(station_dists)
    ndepth = int(maxdepth + 1)

    long_data = {}
    for station_id in stations:
        cruise_profile = cruise_data[station_id]
        cruise_time = cruise_profile[2]
        rt = (cruise_time - base_date).total_seconds() / (24 * 3600)
        zz, profiles = match_cruise(
            rt, station_data[station_id], x, z, times, model_data
        )
        prof = profiles[0]
        long_data[station_id] = (zz, prof[1], prof[0])

    return long_data


def cruise_xyt(path, station_data, base_time, outfile):
    """Generate SCHISM model extraction request file (xyt format) from cruise data.
    
    Creates a request file for SCHISM's read_output10_xyt utility, specifying
    which model casts to extract based on cruise observation station locations
    and times. Each unique station on the cruise is mapped to a model cast request.
    
    Parameters
    ----------
    path : str
        Path to cruise observation file with format:
        Date,Time,Station,Depth,Salinity (with header)
    station_data : pd.DataFrame
        Station metadata DataFrame from process_stations(), indexed by station ID.
        Must contain columns: x, y, name
    base_time : datetime.datetime
        Reference time for computing elapsed seconds in model output.
    outfile : str
        Output path where xyt request file will be written.
    
    Returns
    -------
    dict
        Dictionary mapping cast number (int, 1-indexed) to tuple:
        (x_coord, y_coord, elapsed_seconds, station_name, station_id)
    \n    Notes
    -----
    The xyt format is used by SCHISM's read_output10_xyt utility to extract
    model profiles at specific cast locations and times.
    """
    print("cruise_xyt")

    cruisefile = open(path, "r")
    cruisetxt = cruisefile.readlines()[1:]
    cruisefile.close()
    cruiselines = [line.strip().split(",") for line in cruisetxt if (line != "\n")]
    cruise_locs = []
    processed = []
    casts = {}
    for entry in cruiselines:
        if len(entry) < 2:
            continue
        time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%Y-%m-%d %H:%M")
        elapsed = (time - base_time).total_seconds()
        station = entry[2]
        if station.endswith(".0"):
            station = station[:-2]
        if not station in processed:
            sd = station_data.loc[station]
            processed.append(station)
            cruise_locs.append((sd.x, sd.y, elapsed, sd.name, station))

    with open(outfile, "w") as out:
        out.write("Cruise cast model requests\n%s\n" % len(cruise_locs))
        for i, loc in enumerate(cruise_locs):
            jj = i + 1
            locentries = (jj, loc[0], loc[1], loc[2], loc[3])
            out.write("%s %s %s %s   ! %s\n" % locentries)
            # out.write("%s %s %s      ! %s\n"  % loc)
            # print (locentries)
            casts[jj] = loc

    return casts


def _cruise_label(cruise_time):
    return cruise_time.strftime("%d-%b-%Y")


def gen_profile_plot(
    base_date,
    cruise_time,
    survey_file,
    model_file,
    station_file,
    xytfile,
    ax_obs=None,
    ax_model=None,
    is_top=True,
    xmin=20,
    xmax=104,
    max_depth=30,
):
    """Generate comparison profile plot of observed vs. model salinity along transect.

    Creates a contour plot comparing observed cruise salinity (left) with
    SCHISM model salinity (right) along a transect for a single cruise date.
    If axes are provided, adds plots to shared figure; otherwise creates
    standalone figure and saves as PNG (600 dpi) and PDF.

    Parameters
    ----------
    base_date : datetime.datetime
        SCHISM model start date (for elapsed time calculation).
    cruise_time : datetime.datetime
        Date/time of cruise observations.
    survey_file : str
        Path to temporary cruise observation file (single date format).
    model_file : str
        Path to model output fort.18 file (date-specific).
    station_file : str
        Path to station metadata CSV file.
    xytfile : str
        Path to xyt model extraction request file.
    ax_obs : matplotlib.axes.Axes, optional
        Axes for observation plot. If None, creates standalone figure.
    ax_model : matplotlib.axes.Axes, optional
        Axes for model plot. If None, creates standalone figure.
    is_top : bool, optional
        Whether this is the top row (used for label placement).
    xmin, xmax : float, optional
        Distance range limits in km (default 20-104 km).
    max_depth : float, optional
        Maximum depth to display (default 30 m).

    Returns
    -------
    matplotlib.contourf or None
        Contour collection from model plot (used for colorbar).
        Returns None if plot is not standalone.
    """
    
    station_data = process_stations(station_file)
    cruise_data = process_cruise(survey_file)

    casts = cruise_xyt(survey_file, station_data, base_date, xytfile)
    model_data = process_xyt(model_file, casts, base_date)

    standalone = ax_obs is None or ax_model is None
    if standalone:
        with plt.rc_context(PAPER_RC):
            fig, axes = plt.subplots(1, 2, sharex=True, sharey=True, figsize=(7.2, 2.6))
            ax_obs, ax_model = axes
            
            cs_obs = longitudinal(
                cruise_data,
                station_data,
                ax_obs,
                context_label=None,
                add_labels=True,
                xlabel="Distance from Golden Gate (km)",
                xmin=xmin,
                xmax=xmax,
                max_depth=max_depth,
            )
            cs_model = longitudinal(
                model_data,
                station_data,
                ax_model,
                context_label=_cruise_label(cruise_time),
                add_labels=True,
                xlabel="Distance from Golden Gate (km)",
                xmin=xmin,
                xmax=xmax,
                max_depth=max_depth,
            )
            ax_obs.set_title("Observed")
            ax_model.set_title("Model")
            ax_model.set_ylabel("")
            _add_top_colorbar(fig, cs_model)
            _save_figure(fig, "salinity_profile_" + cruise_time.strftime("%Y%m%d"))
            plt.close(fig)
            return cs_model

    xlabel = "Distance from Golden Gate (km)" if not is_top else None
    show_xticklabels = not is_top

    cs_obs = longitudinal(
        cruise_data,
        station_data,
        ax_obs,
        context_label=None,
        add_labels=is_top,
        xlabel=xlabel,
        xmin=xmin,
        xmax=xmax,
        max_depth=max_depth,
        show_xticklabels=show_xticklabels,
    )
    cs_model = longitudinal(
        model_data,
        station_data,
        ax_model,
        context_label=_cruise_label(cruise_time),
        add_labels=is_top,
        xlabel=xlabel,
        xmin=xmin,
        xmax=xmax,
        max_depth=max_depth,
        ylabel=False,
        show_xticklabels=show_xticklabels,
    )
    return cs_model


def _add_top_colorbar(fig, contour_set):
    """Add one horizontal colorbar across the top of the figure."""
    cbar = fig.colorbar(
        contour_set,
        ax=fig.axes,
        orientation="horizontal",
        location="top",
        fraction=0.055,
        pad=0.035,
        aspect=45,
    )
    cbar.set_label("Salinity (psu)")
    cbar.ax.invert_xaxis()
    cbar.ax.xaxis.set_ticks_position("top")
    cbar.ax.xaxis.set_label_position("top")
    return cbar


def _save_figure(fig, stem):
    """Save high-resolution raster and vector outputs for paper use."""
    fig.savefig(stem + ".png", dpi=600, bbox_inches="tight")
    fig.savefig(stem + ".pdf", bbox_inches="tight")


def gen_multi_profile_plot(
    base_date,
    cruise_records,
    station_file,
    output_stem="salinity_profiles",
    xmin=20,
    xmax=104,
    max_depth=30,
):
    """Create multi-panel paper figure comparing observed vs. model profiles.

    Generates a publication-quality figure with one row per cruise date,
    comparing observed salinity (left column) with SCHISM model salinity
    (right column). Handles layout, colorbars, and file saving automatically.

    Parameters
    ----------
    base_date : datetime.datetime
        SCHISM model start date (for elapsed time calculation).
    cruise_records : list of dict
        Each record has keys ``time``, ``obs_file``, ``model_file``, ``xyt_file``.
        Each row becomes one date/cruise comparison in the figure.
    station_file : str
        Path to station metadata CSV file.
    output_stem : str, optional
        Output filename stem for saved figures (default: "salinity_profiles").
        Figures saved as <stem>.png and <stem>.pdf.
    xmin, xmax : float, optional
        Distance range limits in km (default 20-104 km).
    max_depth : float, optional
        Maximum depth to display (default 30 m).

    Returns
    -------
    None
        Saves figures to disk as PNG and PDF files using _save_figure().

    Raises
    ------
    ValueError
        If cruise_records is empty.
    """
    nrow = len(cruise_records)
    if nrow == 0:
        raise ValueError("No cruise records were supplied for plotting")

    with plt.rc_context(PAPER_RC):
        # Height is compact but scales enough to keep labels readable.
        fig_height = max(2.4, 1.55 * nrow + 0.55)
        fig, axes = plt.subplots(
            nrow,
            2,
            sharex=True,
            sharey=True,
            figsize=(7.2, fig_height),
            squeeze=False,
            constrained_layout=False,
        )

        last_cs = None
        for i, record in enumerate(cruise_records):
            last_cs = gen_profile_plot(
                base_date,
                record["time"],
                record["obs_file"],
                record["model_file"],
                station_file,
                record["xyt_file"],
                ax_obs=axes[i, 0],
                ax_model=axes[i, 1],
                is_top=(i == 0),
                xmin=xmin,
                xmax=xmax,
                max_depth=max_depth,
            )

        axes[0, 0].set_title("Observed")
        axes[0, 1].set_title("Model")
        for i in range(nrow):
            axes[i, 1].set_ylabel("")

        fig.subplots_adjust(
            left=0.08,
            right=0.985,
            bottom=0.08,
            top=0.86,
            hspace=0.12,
            wspace=0.06,
        )
        _add_top_colorbar(fig, last_cs)
        _save_figure(fig, output_stem)
        plt.close(fig)


def main(base_date, cruise_time, obs_file, model_file, station_file, xytfile):
    filename = obs_file
    station_data = process_stations(station_file)
    cruise_data = process_cruise(filename)

    casts = cruise_xyt(filename, station_data, base_date, xytfile)
    model_data = process_xyt(model_file, casts, base_date)
    fig, axes = plt.subplots(2, 2, sharex=True)

    # x,z,times,model_data = process_data(station_data,model_outfile)
    choices = ["657", "649", "2", "3"]
    # choices = ["10","13","14","15"]

    nchoice = len(choices)
    for ichoice in range(nchoice):
        ax = axes[ichoice % 2, int(ichoice / 2)]
        choice = choices[ichoice]
        cruise_profile = cruise_data[choice]
        cruise_time = cruise_profile[2]
        station = station_data.loc[choice]
        model_profile = model_data[choice]
        # ax = axes[ichoice%2,ichoice/2]
        title = station.name + "(%s km) " % np.round(station.dist_km)
        ax.set_title(title)
        xlabel = "Salinity (psu)" if ichoice in (1, 3) else None
        ylabel = "Depth (m)" if ichoice in (0, 1) else None
        print("ichoice: %s %s" % (ichoice, xlabel))
        # add_legend = (ichoice == (nchoice - 1))
        add_legend = ichoice == 0
        surrounding_profiles = [model_profile]
        do_depth_plot(
            station,
            cruise_profile,
            surrounding_profiles,
            ax,
            xlabel,
            ylabel,
            add_legend,
        )
    plt.show()


def gen_station_xyt(base_date, cruise_time, survey_file, station_file, xytfile):
    """Generate xyt request file from cruise observation data.
    
    Convenience wrapper that loads station data, reads cruise observations,
    and generates the xyt model extraction request file. This is used to create
    station-specific model extraction files for SCHISM output post-processing.
    
    Parameters
    ----------
    base_date : datetime.datetime
        Reference date for SCHISM model start time (for elapsed time calculation).
    cruise_time : datetime.datetime
        Time of cruise observations (used to compute elapsed time from base_date).
    survey_file : str
        Path to cruise observation data file.
    station_file : str
        Path to station metadata CSV file.
    xytfile : str
        Output path for xyt request file.
    
    Returns
    -------
    None
        Generates xytfile as side effect. xytfile contains station locations
        and times formatted for SCHISM's read_output10_xyt utility.
    """
    filename = survey_file
    station_data = process_stations(station_file)
    cruise_data = process_cruise(filename)
    casts = cruise_xyt(filename, station_data, base_date, xytfile)


def cruise_plot(
    data_path,
    start=DEFAULT_START,
    schism_output_path=None,
    output_stem="salinity_profiles",
    xmin=20,
    xmax=104,
    max_depth=30,
    use_yearly_format=True,
    target_stations=None,
    depth_thresholds=None,
):
    """Main work function: Process USGS cruise data and generate comparison plots.

    This is the primary work function (as distinguished from CLI wrapper).
    It orchestrates the complete workflow:

    1. Load and filter USGS cruise observations (yearly or daily format)
    2. For yearly format: apply multi-pass filtering (stations, depth, time)
    3. For each valid date: generate date-specific xyt model extraction request
    4. Extract model salinity profiles from SCHISM output
    5. Generate publication-quality comparison figures (observed vs. model)

    Parameters
    ----------
    data_path : str
        Path to folder containing cruise data and station metadata.
    start : str, optional
        SCHISM model start date (default: 2011-03-29). Used as reference for
        elapsed time calculations and filtering observations (excludes spinup period).
    schism_output_path : str, optional
        Path to SCHISM output folder. If None, defaults to <data_path>/2011outputs.
    output_stem : str, optional
        Output file stem for plots (default: 'salinity_profiles').
        PNG and PDF files will be written.
    xmin, xmax : float, optional
        Distance range limits in km (default: 20-104 km).
    max_depth : float, optional
        Maximum depth to plot (default: 30 m).
    use_yearly_format : bool, optional
        If True, expects yearly CSV files (usgs_cruise_yyyy.csv) with multi-pass
        filtering. If False, expects daily files (usgs_cruise_yyyymmdd.txt or .csv).
    target_stations : list of str, optional
        Station IDs to include. Defaults to ['2', '3', ..., '20', '649', '657'].
    depth_thresholds : dict, optional
        Depth thresholds for specific stations (yearly format only).
        E.g., {'7': 9, '8': 9, '9': 9} requires depth > 9 meters.
        Defaults to {'7': 9, '8': 9, '9': 9}.

    Returns
    -------
    None
        Generates output figures as PNG and PDF files in data_path.

    Raises
    ------
    FileNotFoundError
        If required files are missing: vgrid.in, read_output_xyt.in,
        usgs_cruise_stations.csv, cruise data files, or if read_output10_xyt
        executable is not found in PATH.
    ChildProcessError
        If read_output10_xyt command fails during model extraction.

    Notes
    -----
    Expected file layout for yearly format::

        <data_path>/usgs_cruise_2011.csv (or other years)
        <data_path>/usgs_cruise_stations.csv
        <data_path>/2011outputs/vgrid.in
        <data_path>/2011outputs/read_output_xyt.in
        <data_path>/2011outputs/out2d_1.nc

    For yearly format, a date is included only if ALL target stations have
    valid observations. Temporary files are cleaned up after plotting.
    """
    # Check if read_output10_xyt is available in PATH
    check_read_output10_xyt_available()
    
    data_folder = data_path
    base_date = parser.parse(start)
    if schism_output_path is None:
        schism_output_folder = os.path.join(data_folder, DEFAULT_OUTPUT_SUBDIR)
    else:
        schism_output_folder = schism_output_path

    schism_vgrid_in = os.path.join(schism_output_folder, "vgrid.in")
    if not os.path.exists(schism_vgrid_in):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), schism_vgrid_in
        )
    schism_output_in = os.path.join(schism_output_folder, "read_output_xyt.in")
    if not os.path.exists(schism_output_in):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), schism_output_in
        )

    station_file = os.path.join(data_folder, "usgs_cruise_stations.csv")
    if not os.path.exists(station_file):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), station_file)

    cruise_records = []
    temp_cruise_files = []
    if use_yearly_format:
        # Process yearly CSV files like usgs_cruise_2011.csv
        # Strategy: Create ONE comprehensive xyt file for all dates and run read_output10_xyt ONCE
        usgs_cruise_match = re.compile(r"usgs_cruise_(?P<year>[0-9]{4})\.csv$")
        
        # First pass: collect all cruise data
        all_yearly_records = {}
        for file_name in sorted(os.listdir(data_folder)):
            match_re = usgs_cruise_match.match(file_name)
            if not match_re:
                continue

            print("loading yearly cruise data " + file_name)
            obs_file = os.path.join(data_folder, file_name)
            
            # Load all cruise data from yearly file
            all_cruise_records = process_cruise_yearly_csv(
                obs_file, 
                target_stations=target_stations,
                depth_threshold_stations=depth_thresholds,
                model_start_time=base_date
            )
            
            all_yearly_records.update(all_cruise_records)
        
        if not all_yearly_records:
            raise FileNotFoundError(
                errno.ENOENT,
                "No cruise data found in yearly files",
                data_folder,
            )
        
        # For yearly format: In the fourth pass, we generate date-specific xyt and model files
        # This ensures model data extraction matches exactly with observation data for each date
        
        # Fourth pass: process each date for plotting (generate date-specific xyt and model files)
        temp_cruise_files = []
        min_stations_for_plot = 2  # Need at least 2 stations to create contour plot
        
        station_data = process_stations(station_file)
        
        for date_str in sorted(all_yearly_records.keys()):
            cruise_data_dict = all_yearly_records[date_str]
            # Skip dates with insufficient stations for contour plotting
            num_stations = len(cruise_data_dict)
            if num_stations < min_stations_for_plot:
                print(f"Skipping {date_str}: only {num_stations} station(s), need at least {min_stations_for_plot}")
                continue
            
            # Extract cruise_time from the first station's observation (all stations on same day)
            first_station = next(iter(cruise_data_dict.keys()))
            _, _, cruise_time = cruise_data_dict[first_station]
            
            # Create temporary single-date format for observation data
            date_yyyymmdd = cruise_time.strftime("%Y%m%d")
            temp_cruise_file = os.path.join(data_folder, f"temp_cruise_{date_yyyymmdd}.txt")
            local_xyt = os.path.join(data_folder, f"station_{date_yyyymmdd}.xyt")
            output_xyt_date = os.path.join(schism_output_folder, "station.xyt")
            
            try:
                # Write temporary cruise file with only this date's observations
                with open(temp_cruise_file, "w") as f:
                    f.write("Date,Time,Station,Depth,Salinity\n")
                    for station, (depths, salinities, time) in cruise_data_dict.items():
                        for depth, salinity in zip(depths, salinities):
                            f.write(f"{time.strftime('%Y-%m-%d')},{time.strftime('%H:%M')},{station},{depth},{salinity}\n")
                
                # Generate date-specific xyt file and extract model data for this date
                gen_station_xyt(base_date, cruise_time, temp_cruise_file, station_file, local_xyt)
                copyfile(local_xyt, output_xyt_date)
                
                out2d_file = os.path.join(schism_output_folder, "out2d_1.nc")
                validate_out2d_time_variable(out2d_file)

                print(f"running read_output10_xyt for {date_str}")
                cmd = ["read_output10_xyt"]
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=schism_output_folder)
                for line in p.stdout:
                    print(line.decode(errors="replace").rstrip())
                p.wait()
                if p.returncode:
                    raise ChildProcessError("Fail to extract SCHISM outputs")

                model_salt = f"salt_{date_yyyymmdd}"
                model_file_date = os.path.join(schism_output_folder, model_salt)
                copyfile(os.path.join(schism_output_folder, "fort.18"), model_file_date)
                
                temp_cruise_files.append(temp_cruise_file)
                cruise_records.append(
                    {
                        "time": cruise_time,
                        "obs_file": temp_cruise_file,
                        "model_file": model_file_date,
                        "xyt_file": output_xyt_date,
                    }
                )
            except Exception as e:
                print(f"Error processing date {date_str}: {e}")
                continue
    else:
        # Original behavior: process daily files
        usgs_cruise_match = re.compile(r"usgs_cruise_(?P<date>[0-9]{8})\.(?:txt|csv)$")
        for file_name in sorted(os.listdir(data_folder)):
            match_re = usgs_cruise_match.match(file_name)
            if not match_re:
                continue
            
            print("processing cruise data " + file_name)
            cruise_time = parser.parse(match_re.group("date"))
            xyt_file = "station_" + match_re.group("date") + ".xyt"
            local_xyt = os.path.join(data_folder, xyt_file)
            output_xyt = os.path.join(schism_output_folder, "station.xyt")
            obs_file = os.path.join(data_folder, file_name)

            gen_station_xyt(base_date, cruise_time, obs_file, station_file, local_xyt)
            copyfile(local_xyt, output_xyt)

            out2d_file = os.path.join(schism_output_folder, "out2d_1.nc")
            validate_out2d_time_variable(out2d_file)

            cmd = ["read_output10_xyt"]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd=schism_output_folder)
            for line in p.stdout:
                print(line.decode(errors="replace").rstrip())
            p.wait()
            if p.returncode:
                raise ChildProcessError("Fail to extract SCHISM outputs")

            model_salt = "salt_" + match_re.group("date")
            model_file = os.path.join(schism_output_folder, model_salt)
            copyfile(os.path.join(schism_output_folder, "fort.18"), model_file)

            cruise_records.append(
                {
                    "time": cruise_time,
                    "obs_file": obs_file,
                    "model_file": model_file,
                    "xyt_file": output_xyt,
                }
            )
    
    if not cruise_records:
        raise FileNotFoundError(
            errno.ENOENT,
            "No cruise data files were found",
            data_folder,
        )

    gen_multi_profile_plot(
        base_date,
        cruise_records,
        station_file,
        output_stem=os.path.join(data_folder, output_stem),
        xmin=xmin,
        xmax=xmax,
        max_depth=max_depth,
    )
    
    # Clean up temporary files created for yearly format after plotting is complete
    if use_yearly_format:
        for temp_file in temp_cruise_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)



@click.command()
@click.option(
    "--data_path",
    required=True,
    help="Path containing downloaded USGS cruise water quality data and location usgs_cruise_stations.csv.",
)
@click.option(
    "--start",
    type=str,
    default=DEFAULT_START,
    show_default=True,
    help="Starting date and time basis for SCHISM model output.",
)
@click.option(
    "--schism_output_path",
    required=False,
    default=None,
    help="Path containing SCHISM output data, vgrid and read_output_xyt.in.",
)
@click.option(
    "--output_stem",
    default="salinity_profiles",
    show_default=True,
    help="Output file stem. PNG and PDF are both written.",
)
@click.option("--xmin", default=20.0, show_default=True, help="Minimum distance in km.")
@click.option("--xmax", default=104.0, show_default=True, help="Maximum distance in km.")
@click.option("--max_depth", default=30, show_default=True, help="Maximum plotted depth in m.")
@click.option(
    "--use_yearly_format",
    type=bool,
    default=True,
    show_default=True,
    help="Use yearly CSV format (usgs_cruise_yyyy.csv) instead of daily files.",
)
@click.option(
    "--legacy_daily_format",
    is_flag=True,
    default=False,
    help="Use legacy daily file format (usgs_cruise_yyyymmdd.txt) instead of yearly.",
)
def cruise_plot_cli(data_path, start, schism_output_path, output_stem, xmin, xmax, max_depth, use_yearly_format, legacy_daily_format):
    """ This tool generates comparison plots of observed USGS cruise salinity profile against SCHISM model output.

    This is the click-decorated CLI function that serves as the entry point
    for the command-line utility. It parses arguments and delegates to the
    cruise_plot() work function.

    Uses yearly CSV format (usgs_cruise_yyyy.csv) by default. Use --legacy_daily_format
    to revert to the original daily file format (usgs_cruise_yyyymmdd.txt).

    With yearly format, data is filtered to include only:
    - Stations 2-20, 649, and 657
    - For stations 7, 8, 9: maximum depth > 9 meters
    - Requires all stations present on a given day (complete cruises only)

    This function follows the coding standard pattern where the CLI wrapper
    gathers arguments and calls the work function with explicit named parameters.
    See cruise_plot() for implementation details.
    """

    # Override use_yearly_format if legacy flag is set
    if legacy_daily_format:
        use_yearly_format = False

    cruise_plot(
        data_path, 
        start, 
        schism_output_path, 
        output_stem, 
        xmin, 
        xmax, 
        max_depth,
        use_yearly_format=use_yearly_format
    )


if __name__ == "__main__":
    cruise_plot_cli()
