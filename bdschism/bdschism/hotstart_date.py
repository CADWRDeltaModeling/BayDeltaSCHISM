#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Use example as command-line interface function:
# python hotstart_date.py --fn ./hotstart.nc --hotstart 2024-6-24 --runstart 2024-6-24

# or with bdschism in your environment::

# hot_date --fn ./hotstart.nc --hotstart 2024-6-24 --runstart 2024-6-24

import xarray as xr
import pandas as pd
import argparse
from pathlib import Path

def create_arg_parser():
    import textwrap
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
         ============== Example ==================
      > hot_date --fn ./hotstart.nc --run_start 2024-6-24 --restart_time 2024-6-24
      """),
        description="""The script will change the necessary date attributes"""
    )
    
    parser.add_argument('--fn', default='./hotstart.nc', required=False, type=Path,
                        help="hotstart *.nc filename")
    parser.add_argument('--run_start', default=None, required=True, type=str,
                        help="run start date in format YEAR-MONTH-DAY, ex: 2024-6-1")
    parser.add_argument('--restart_time', default=None, required=True, type=str, 
                        help="hotstart restart date in format YEAR-MONTH-DAY, ex: 2024-6-24")
    parser.add_argument('--outprefix', default="hotstart", required=False, type=str,
                        help='output prefix for the output .nc file. If hotprefix is just "hot" you would get hot.20240624.109440')
    parser.add_argument('--dt', default=90, required=False, type=int,
                        help="timestep, default is 90 seconds")
    return parser

def set_hotstart_date(filenm,outprefix,run_start,restart_time,dt):
    """ Change timestamp and date implied by hotstart 
    
    Arguments
    ---------
    filenm : str
    Original hotstart file name
    
    outprefix : str
    Prefix for output hotstart. Date and nsteps will be appended. So if hotprefix is just "hot" you 
    would get hot.20210425.109440
    
    run_start : str or Timestamp
    Timestamp representing nominal start of the run (=0 elapsed time)

    restart_time : str or Timestamp
    Time stamp you want to restart the model
    
    dt : float
    Time step of the model in seconds
    """
    run_start = pd.to_datetime(run_start)
    run_start_str = run_start.strftime("%Y-%m-%dT%H:%M")
    restart_time = pd.to_datetime(restart_time)
    
    
    restart_sec = (restart_time - run_start).total_seconds()
    restart_timestr = restart_time.strftime("%Y%m%d")
    nsteps = int(restart_sec/dt)
    outfile = f"{outprefix}.{restart_timestr}.{nsteps}.nc"
    print(f"Restarting on {restart_time}. nsteps (iterations) = {nsteps}, elapsed secs at restart = {restart_sec}")
    print(f"Time origin of run is {run_start_str}")
    print(f"Output file is {outfile}")
    
    with xr.open_dataset(filenm,   ) as ds:
        ds.variables["time"][:] = restart_sec
        ds.variables["nsteps_from_cold"][:] = nsteps
        ds.variables["iths"][:] = nsteps
        ds.variables["ifile"][:] = 1
        ds.attrs['time_origin_of_simulation'] = run_start_str
        ds.to_netcdf(outfile)
    

def main():
    parser = create_arg_parser()
    args = parser.parse_args()

    fn = args.fn
    run_start = args.run_start
    restart_time = args.restart_time
    dt = float(args.dt)
    outprefix = args.outprefix

    return set_hotstart_date(fn,outprefix,run_start,restart_time,dt)

if __name__=="__main__":
    main()