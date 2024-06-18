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


# plt.style.use(['seaborn-talk','seaborn-colorblind'])
def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--salt_data_file', default=None,
                    help='path to salinity data harvested using read_xyz* utility, e.g. fort.18')   
    parser.add_argument('--start', default=None,
                    help='model start date, e.g. 2010-05-20')
    parser.add_argument('--x2route', 
                    help='X2 route file name in bp format with xyz plus extra column describing distance')
    parser.add_argument('--output', default=None,
                    help = 'path of csv output')
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

def process_x2(salt_data_file,route_file, model_start, output_file):
    """Process  x2 into a time series
    """
    print(f"salt_data_file: {salt_data_file} model_start={model_start} output_file={output_file}")
    ts_out = pd.read_csv(salt_data_file, sep="\s+", header=None,index_col=0)
    delta_t=(ts_out.index[1]-ts_out.index[0])*24*60
    freqstr=f"{int(delta_t)}min"
    #print(f"Detected frequency = {freqstr}")
    dr = pd.date_range(start=model_start+pd.Timedelta(days=ts_out.index[0]),
                       periods=ts_out.shape[0],freq=freqstr)
    ts_out.index=dr
    ts_out=ts_out.resample('1D').mean()

    if route_file.endswith("bp"):
        route_df = pd.read_csv(route_file,sep="\s+",index_col=0,skiprows=[1],header=0,comment="!")
    else: 
        raise ValueError("Build point file expected")
    
    ncols = ts_out.shape[1]
    nroute = len(route_df)
    if ncols != nroute:
        raise ValueError("Number of columns in salt output {ncols} must match number of locations in bp file {nroute}")

    ts_out.columns = route_df.distance
    x2_prelim = ts_out.apply(find_x2,axis=1) 
    x2_prelim.to_csv(output_file,float_format="%.1f")

def default_outname(bpname):
    if "x2route" in bpname:
        return bpname.replace("x2route","x2").replace("bp","csv")
    else:
        return "x2.csv"

def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    st = args.start
    model_start = parse(st)
    x2route = args.x2route
    outfile= args.output
    if outfile is None:
        outfile = default_outname(x2route)
    salt_out = args.salt_data_file
    process_x2(salt_out,x2route,model_start,outfile)

def main_hardwire():
    st = "2006-11-14" #args.start
    model_start = parse(st)
    x2_route_file = "x2route_sac.bp" #args.x2route
    x2out=default_outname(x2_route_file)
    salt_out = "fort.18"
    process_x2(salt_out,x2_route_file,model_start,x2out) 

if __name__ == "__main__":
    main()

