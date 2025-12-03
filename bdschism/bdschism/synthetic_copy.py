## Script to create synthetic NARR files from existing hrrr repository by copying and shfiting dates forward by one year
## to a data folder. Reuslting data files of different year will be saved to correpsoinding folders. If from leap year to non-leap year,
## Feb 29 data will be skipped. If from non-leap year to leap year, Feb 29 data will be created by copying Feb 28 data and changing date to Feb 29.

import xarray as xr
import datetime as dtm
import numpy as np
import pandas as pd
import os
import click



def is_leap_year_manual(year):
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return True
    else:
        return False


@click.command(
    """
    Create synthetic NARR files from existing hrrr repository by copying and shfiting dates forward by one year
    to a data folder. Reuslting data files of different year will be saved to correpsoinding folders. If from leap year to non-leap year,
    Feb 29 data will be skipped. If from non-leap year to leap year, Feb 29 data will be created by copying Feb 28 data and changing date to Feb 29.
    Parameters
    ----------
    sdate : str, required
        Source Data file start date in format YEAR-MONTH-DAY (e.g., 2020-1-1).
        If not provided, defaults to run_start_date from config file.
    edate : str, required
        Source Data file end date in format YEAR-MONTH-DAY (e.g., 2022-2-2).
        If not provided, defaults to run_end_date from config file.
    source_repo : pathlib.Path, required
        Source folder where existing data files stored.
    dest_repo : pathlib.Path, required
        Destination folder where synthetic data files will be put.

    Notes
    -----

    Examples
    --------
    >>> synthetic_copy --source_repo //cnrastore-bdo/modeling_data/atmospheric/atmospheric_hrrr --dest_respo ./synthetic --sdate 2020-1-1 --edate 2020-2-2
    """
    help=(
        "Create synthetic NARR files from existing hrrr repository by copying and shfiting dates forward by one year \n\n"
        "Example:\n"
        "  synthetic_copy --source_repo //cnrastore-bdo/modeling_data/atmospheric/atmospheric_hrrr --dest_respo ./synthetic --sdate 2020-1-1 --edate 2020-2-2"
    )
)

@click.option(
    "--source_repo",
    required=False,
    default="./sflux",
    type=click.Path(exists=True, path_type=Path),
    help="folder where symbolic links will be put. [default: ./sflux]",
)


@click.option(
    "--dest_repo",
    required=False,
    default="./sflux",
    type=click.Path(exists=True, path_type=Path),
    help="folder where symbolic links will be put. [default: ./sflux]",
)


@click.option(
    "--sdate",
    required=False,
    type=str,
    help="data file start date in format YEAR-MONTH-DAY, e.g., 2020-1-1.",
)

@click.option(
    "--edate",
    required=False,
    type=str,
    help="data file end date in format YEAR-MONTH-DAY, e.g., 2022-2-2.",
)


def main(source_repo, dest_repo, sdate, edate):

   

    ## checkk if dest_repos exists, if not create it
    if not os.path.exists(dest_repo):
        os.makedirs(dest_repo) 

    startrt_date = pd.to_datetime(sdate) 
    endrt_date = pd.to_datetime(edate)
    infiles = []
    ## first create list of input files to be processed
    date_rng = pd.date_range(start=startrt_date, end=endrt_date, freq='D')
    year_lst = []
    for d in date_rng:   
        year = d.year
        if year not in year_lst:
            year_lst.append(year)   
        month = d.month
        day = d.day
        infile = f"{source_repo}/{year:4d}/hrrr_{year:4d}{month:02d}{day:02d}00.nc"
        infiles.append(infile)

    ## increase year in year_lst by 1 to create output years
    out_year_lst = [y+1 for y in year_lst]  

    ## create output year folder in dest_repos for each in out_year_lst
    for y in out_year_lst:
        out_year_folder = f"{dest_repo}/{y:4d}"
        if not os.path.exists(out_year_folder):
            os.makedirs(out_year_folder)    

    for infile,d in zip(infiles,date_rng):

        year = d.year+1
        month = d.month
        day = d.day
        outfile = f"{dest_repo}/{year:4d}/hrrr_{year:4d}{month:02d}{day:02d}00.nc"

        attr_synth = "creator"
        val_synth = "CA DWR Delta Modeling Section"
        attr_method = "creation_method"
        val_method = f"Filled missing date by copying {infile} and changing dates"

        with xr.open_dataset(infile) as ds:

            ## if infile year is a leap year and outfile year is not, skip Feb 29
            if (is_leap_year_manual(d.year)) and (d.month ==2) and (d.day ==29):
                print(f"Skipping Feb 29 for non-leap year {year}")
                continue

            ds.attrs[attr_synth] = val_synth
            ds.attrs[attr_method] = val_method

            bd = ds.time.attrs["base_date"] 
            bd[0]+=1
            ds['time'] = [t + pd.DateOffset(years=1) for t in ds.time.values]
            ds.time.attrs["base_date"] = bd 
            ds.time.attrs['long_name'] = 'Time'
            ds.to_netcdf(path=outfile,format='NETCDF4')

            ## if dest year is leap year and infile year is not, create Feb 29 by copying Feb 28 data
        if (is_leap_year_manual(year)) and (not is_leap_year_manual(d.year)) and (d.month ==2) and (d.day ==28):
            feb29_outfile = f"{dest_repo}/{year:4d}/hrrr_{year:4d}022900.nc"
            print(f"Creating Feb 29 for leap year {year} by copying Feb 28 data")
            with xr.open_dataset(infile) as ds_feb28:
                ds_feb28.attrs[attr_synth] = val_synth
                ds_feb28.attrs[attr_method] = f"Created Feb 29 by copying Feb 28 data from {infile} and changing date"
                bd = ds_feb28.time.attrs["base_date"] 
                bd[0]+=1
                bd[2]=29
                ds_feb28['time'] = [t + pd.DateOffset(years=1, days=1) for t in ds_feb28.time.values]
                ds_feb28.time.attrs["base_date"] = bd 
                ds_feb28.time.attrs['long_name'] = 'Time'
                ds_feb28.to_netcdf(path=feb29_outfile,format='NETCDF4') 

if __name__ == "__main__":
    main()
