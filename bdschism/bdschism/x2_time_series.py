# -*- coding: utf-8 -*-
"""

This script reads x2_route.bp as well as the fort.18
resulting from SCHISM read_output9_xyz to extract salinity on X2 stations.
It search along x2 stations to find two neiboring stations higher and lower 
than X2 criteria (bottom or surface).  If X2 retreat less than the minimum
stations along the transect, the X2 result will
be truncated at that point.


usage: --start 2004-04-18 --x2route x2route.bp
output: x2 on surface and bottom location time series in csv format,
        bottom_x2.csv and surface_x2.csv

"""

import numpy as np
import argparse

import datetime as dtm
import matplotlib.pyplot as plt
# import matplotlib.dates as mdates

import pandas as pd
from dateutil.parser import parse

import re
import os

# plt.style.use(['seaborn-talk','seaborn-colorblind'])
def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--salt_data_file', default=None,
                    help='path to salinity data harvested using read_xyz* utility, e.g. fort.18')   
    parser.add_argument('--start', default=None,
                    help='model extraction start date, e.g. 2010-05-20')
    parser.add_argument('--model_start', default=None,
                    help='model simulation start date, e.g. 2010-05-01')
    parser.add_argument('--x2route', 
                    help='X2 route file name in bp format with xyz plus extra column describing distance')
    parser.add_argument('--output', default=None,
                    help = 'path of csv output')
    parser.add_argument('--param', default=None,
                    help = 'path of param.nml file to extract start date')
    return parser

def find_x2(transect,thresh=2.,convert_km=0.001,distance_bias=0.0):
    """ 
    Given a series transect, indexed by distance, locate a distance with value is close to thresh
    """
    midpoints = (transect.index.to_series()+transect.index.to_series().shift(1))
    index_new = pd.concat((transect.index.to_series(), midpoints),axis=0).sort_values().iloc[0:-1]
    row_new=transect.reindex(index_new).interpolate().sort_values()
    index_x2=row_new.searchsorted(2.)
    index_x2=index_x2.clip(max=len(row_new)-1)
    x2=row_new.index[index_x2.clip(max=len(row_new)-1)]
    final_x2 = (x2*convert_km-distance_bias)
    return final_x2

def get_start_date_from_param(param_in):

    with open(param_in, 'r') as param:
        for line in param.readlines():
            if 'start_year' in line:
                sy =  int(re.findall(r'\b\d+\b', line)[0])
            elif 'start_month' in line:
                sm =  int(re.findall(r'\b\d+\b', line)[0])
            elif 'start_day' in line:
                sd =  int(re.findall(r'\b\d+\b', line)[0])
                
    start_date = dtm.datetime(sy, sm, sd)
    
    return start_date

def process_x2(salt_data_file,route_file, model_extract_date, output_file, param_in=None, model_start_date=None):
    """Process  x2 into a time series
    """
    if param_in is not None:
        model_start_date = get_start_date_from_param(param_in)
    elif model_start_date is not None and isinstance(model_start_date, str):
        st = model_start_date.split('-')
        model_start_date = dtm.datetime(int(st[0]),int(st[1]),int(st[2]))
    print(f"salt_data_file: {salt_data_file} model_start_date={model_start_date} output_file={output_file} model_extract_date={model_extract_date}")
    ts_out = pd.read_csv(salt_data_file, sep="\s+", header=None,index_col=0)
    delta_t=round((ts_out.index[1]-ts_out.index[0])*24*60)
    freqstr=f"{int(delta_t)}min"
    print(delta_t)
    if delta_t not in [1,2,3,5,6,10,15,20,30,60,120]:
        raise ValueError(f"Unexpected time step in file of {delta_t} minutes")
    #print(f"Detected frequency = {freqstr}")
    dr = pd.date_range(start=model_start_date+pd.Timedelta(days=ts_out.index[0]),
                       periods=ts_out.shape[0],freq=freqstr)
    ts_out.index=dr.round('min')
    ts_out=ts_out.resample('1D').mean()

    if ts_out.index[0].to_pydatetime() != model_extract_date:
        raise ValueError(f"The fort.18 file being evaluated is {ts_out.index[0].to_pydatetime()} and does not match expected extraction date {model_extract_date}")

    if route_file.endswith("bp"):
        route_df = pd.read_csv(route_file,sep="\s+",index_col=0,skiprows=[1],header=0,comment="!")
    else: 
        raise ValueError("Build point file expected")
    
    ncols = ts_out.shape[1]
    nroute = len(route_df)
    if ncols != nroute:
        raise ValueError(f"Number of columns in salt output {ncols} must match number of locations in bp file {nroute}")

    ts_out.columns = route_df.distance
    ts_out = ts_out.head(1)
    x2_prelim = ts_out.apply(find_x2,axis=1) 
    x2_prelim.index.name = "date"
    x2_prelim.name = "x2"
    x2_prelim.to_csv(output_file,float_format="%.1f")

def default_outname(bpname):
    if "x2route" in bpname:
        return bpname.replace("x2route","x2").replace("bp","csv")
    else:
        return "x2.csv"

def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    salt_out = args.salt_data_file
    x2route = args.x2route
    st = args.start.split('-')
    model_start = dtm.datetime(int(st[0]),int(st[1]),int(st[2]))
    outfile= args.output
    if outfile is None:
        outfile = default_outname(x2route)

    param_in = args.param
    model_start_date = args.model_start

    process_x2(salt_out,x2route,model_start,outfile,param_in=param_in, model_start_date=model_start_date)

def main_hardwire():
    model_out_dir = "/scratch/tomkovic/DSP_code/model/schism/azure_dsp_2024_lhc_v3/simulations/baseline_lhc_5/outputs"
    os.chdir(model_out_dir)
    
    salt_out = "fort.18"
    x2route = "x2_bay_sac.bp" #args.x2route
    st = "2006-11-15".split('-')
    model_start = dtm.datetime(int(st[0]),int(st[1]),int(st[2]))
    outfile = "x2out_x2_bay_sac_2.csv"

    param_in = None # "../param.nml.clinic"
    model_start_date = "2006-11-14" # None

    process_x2(salt_out,x2route,model_start,outfile,param_in=param_in, model_start_date=model_start_date) 

if __name__ == "__main__":
    main()

