# -*- coding: utf-8 -*-
"""

This script read station x y from x2route.csv which is also used by
extract_x2_station_xyz.py to create x2_stations.bp. It need the fort.18
resulting from SCHISM read_output9_xyz to extract salinity on X2 stations.
It search along x2 stations along the Bay,MZM,Sac, and San Joaquin to
find two neiboring stations higher and lower than X2 criteria
(bottom or surface). A simple linear interpolation is done to get a exact
x2 location. If X2 retreat less than 65km from San Francisco, result will
be truncated at 65km.


usage: --start 2004-04-18 --x2route x2route.csv
output: x2 on surface and bottom location time series in csv format,
        bottom_x2.csv and surface_x2.csv

"""

import numpy as np
import argparse
from extract_x2_station_xyz import x2_route2_bp
# import matplotlib.pylab as plt

import datetime as dtm
import matplotlib.pyplot as plt
# import matplotlib.dates as mdates

import pandas as pd
from dateutil.parser import parse


# plt.style.use(['seaborn-talk','seaborn-colorblind'])
def create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--salt_data_file', default=None,
                    help='path to salinity data harvested using read_xyz* utility')   
    parser.add_argument('--start', default=None,
                    help='model start date, e.g. 2010-05-20')
    parser.add_argument('--x2route', 
                    help='X2 route in cvs format')
    parser.add_argument('--east_route_id', 
                    help='id of east side of route, one of sjr,sac and mzm')
    parser.add_argument('--output', default="x2.csv",
                    help = 'path of csv output')
    return parser

def find_x2(transect,thresh=2.,convert_km=0.001,distance_bias=0.75):
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

def process_x2(salt_data_file,rid,model_start,x2_route_file,output_file):
    """Process  x2, currently just along bay,sac path
    """
    print(f"salt_data_file: {salt_data_file} model_start={model_start} output_file={output_file}")
    ts_out = pd.read_csv(salt_data_file, sep="\s+", header=None,index_col=0)
    delta_t=(ts_out.index[1]-ts_out.index[0])*24*60
    freqstr=f"{int(delta_t)}min"
    print(f"Detected frequency = {freqstr}")
    dr = pd.date_range(start=model_start+pd.Timedelta(days=ts_out.index[0]),
                       periods=ts_out.shape[0],freq=freqstr)
    ts_out.index=dr
    ts_out=ts_out.resample('1D').mean()
    out = None    # This variable is output for the x2_rout2_pb routine, not this one
    sample_interval = 200
    bay_min_distance = 30000
    max_distance = 25000
    if rid=="mzm":
        max_distance = 60000 
    locs = x2_route2_bp(x2_route_file, out, sample_interval,
                        bay_min_distance,rid, max_distance)
    ts_out.columns = locs.index
    baypathbot = (locs.z < -200) & locs.path.isin(['bay','sac','sjr','mzm'])
    salt_sac = ts_out.loc[:,baypathbot]
    salt_locs = locs.loc[baypathbot]
    salt_sac.columns = salt_locs.distance

    x2_prelim = salt_sac.apply(find_x2,axis=1) 
    x2_prelim.to_csv(output_file,float_format="%.1f")
    #x2_prelim.plot()
    #plt.show()

def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    st = args.start
    model_start = parse(st)
    x2_route_file = args.x2route
    outfile= args.output
    salt_out = args.salt_data_file
    rid = args.east_route_id
    process_x2(salt_out,rid,model_start,x2_route_file,outfile)

def main_hardwire():
    st = "2010-05-20" #args.start
    model_start = parse(st)
    x2_route_file = "x2route_broad_slough.csv" #args.x2route
    rid = "sjr"
    x2out="testout.csv"
    salt_out = "fort.18"
    process_x2(salt_out,rid,st,x2_route_file,x2out) 

if __name__ == "__main__":
    main()

