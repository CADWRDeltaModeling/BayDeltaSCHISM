#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xarray as xr
import pandas as pd

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
    
if __name__=="__main__":
    run_start = "2021-01-01"
    restart_time = "2021-04-25"
    dt=90.
    set_hotstart_date("hotstart.nc","hotstart",run_start,restart_time,dt)