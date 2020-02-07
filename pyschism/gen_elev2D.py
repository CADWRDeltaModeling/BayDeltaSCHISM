#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate elev2D.th for a Bay-Delta SCHSIM model using tides at
Point Reyes and Monterey.

2015-06-16: Customized
"""

import sys
import pandas as pd

from netCDF4 import Dataset
import gdal
from separate_species import separate_species
from schism_mesh import read_mesh
from vtools.data.vtime import hours, days, seconds
from vtools.datastore.read_ts import read_noaa, read_ts
import numpy as np
from datetime import datetime
import struct, argparse, re
import time 

################# command line application #####################

def create_arg_parser():
    import textwrap
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
         ============== Example ==================
      > gen_elev2D.py --outfile elev2D.nc --stime=2009-03-12 --etime=2010-01-01 9415020_gageheight.csv 9413450_gageheight.csv
      """),
        description="""Script to create elev2D.th boundary condition from Point Reyes and Monterey NOAA file"""
    )
    parser.add_argument('--stime', default=None, required=False,
                        help="Start time in ISO-like format 2009-03-12T00:00:00. Time part and 'T' are optional.")
    parser.add_argument('--etime', default=None,
                        required=False, help='End time.')
    parser.add_argument('--hgrid', default='hgrid.gr3',
                        required=False, help='Name of hgrid file if not hgrid.gr3')
    parser.add_argument('--outfile', default='elev2D.th.nc',
                        help='Name of output file: either elev2D.th or elev2D.th.nc')
    parser.add_argument('--slr', default=0.0, type=float, required=False,
                        help='Scalar sea level rise increment')                        
    parser.add_argument('pt_reyes', default=None,
                        help='Pt Reyes data file, must have a buffer of 16 days at either end of series')
    parser.add_argument('monterey', default=None,
                        help='Monterey data file, must have a buffer of 16 days at either end of series')
    return parser

class THWriter(object):
    def __init__(self,path,size,starttime):
        pass
        #self.myfilehnandle = 
    
    def write_step(self,iter,time,vals):
        pass
    
    def write_all(self,times,vals):
        # if you get to this point
        pass
    
    def __del__(self):
        pass
        # tear down/close things
            
class BinaryTHWriter(THWriter):
    #super(THWriter, self).__init__(path)
    def __init__(self,fpath_out,nloc,starttime):
        self.outfile = open(fpath_out, 'wb')
        #self.myfilehnandle = 
        self.tformat="f"
        self.valformat="f"*nloc
    
    def write_step(self,iter,time,vals):
        print("Writing Output")
        buf = struct.pack(self.tformat, time)
        self.outfile.write(buf)
        buf = struct.pack(self.valformat, *vals)
        self.outfile.write(buf) 
   
    def write_all(self,times,vals):
        # if you get to this point
        pass
    
    def __del__(self):
        self.outfile.close()
        # tear down/close things
         
class NetCDFTHWriter(THWriter):
    def __init__(self,fpath_out,nloc,starttime,dt):
        self.outfile = Dataset(fpath_out, "w", format="NETCDF4_CLASSIC")
        fout = self.outfile

        time = fout.createDimension("time", None)
        nOpenBndNodes = fout.createDimension("nOpenBndNodes", nloc)
        nLevels = fout.createDimension("nLevels", 1)
        nComponents = fout.createDimension("nComponents", 1)
        one = fout.createDimension("one", 1)

        # create netCDF dimension variables and 
        self.times = fout.createVariable("time","f8", ("time",))
        #todo: what is timestep all about? Did we invent this? Why variable rather than attribute?
        #todo: what is timestep all about? Did we invent this? Why variable rather than attribute?
        self.timestep = fout.createVariable("time_step","f4", ("one",))
        self.timestep[0] = dt
        
        # create elevation time series data to be writen to netCDF file
        self.timeseries = fout.createVariable("time_series", "f4", ("time", "nOpenBndNodes", "nLevels", "nComponents"))
    
        # variable attributes
        self.times.long_name = "simulation time in seconds"
        self.times.units = "seconds since " +  str(starttime)
        self.timeseries.long_name = "water surface elevation at ocean boundary"
        self.timestep.long_name = "time step in seconds"
        self.timeseries.units = "meters NAVD88"

       # Global Attributes -- Metadata
        fout.description = "Water Surface Elevation Boundary Conditions at Ocean Boundary "
        fout.history = "Created " + str(datetime.now())
        fout.source = "gen_ elev2D.py"    
        
    def write_step(self,iter,time,vals):
        self.timeseries[iter,:,0,0]= vals
        self.times[iter]=time
          
    def write_all(self,times,vals):
        # if you get to this point
        pass
    
    def __del__(self):
        self.outfile.close()

def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    monterey_fpath = args.monterey
    pt_reyes_fpath = args.pt_reyes
    hgrid_fpath = args.hgrid
    fpath_out = args.outfile
    slr = args.slr
    stime = args.stime
    etime = args.etime
    
    return gen_elev2D(hgrid_fpath,fpath_out,pt_reyes_fpath,monterey_fpath,stime,etime,slr)

    
    
    
def gen_elev2D(hgrid_fpath,outfile,pt_reyes_fpath,monterey_fpath,start,end,slr):
    max_gap = 5
    stime = start
    etime = end
    fpath_out = outfile
    
    #todo: hardwire 
    nnode = 83
    
    tbuf = days(16)              
    # convert start time string input to datetime       
    sdate = pd.Timestamp(stime)

    if not etime is None:
        # convert start time string input to datetime
        edate = pd.Timestamp(etime)
        bufend = edate + tbuf
    else:
        edate = None
        bufend = None

   

    # UTM positions of Point Reyes, Monterey, SF
    pos_pr = np.array([502195.03, 4205445.47])
    pos_mt = np.array([599422.84, 4051630.37])
    pos_sf = np.array([547094.79, 4184499.42])

    var_subtidal = np.array([0.938, 0.905, 0.969])  # pr, mt, sf
    var_semi = np.array([0.554, 0.493, 0.580])

    # Assume 45 degree from north-west to south-east
    tangent = np.array([1, -1])
    tangent = tangent / np.linalg.norm(tangent)  # Normalize
    # Rotate 90 cw to get normal vec
    normal = np.array([tangent[1], -tangent[0]])
    print("tangent: {}".format(tangent))
    print("normal: {}".format(normal))

    mt_rel = pos_mt - pos_pr
    x_mt = np.dot(tangent, mt_rel)  # In pr-mt direction
    y_mt = np.dot(normal, mt_rel)  # Normal to x-direction to the 
    
    # Grid
    #todo: what is the difference between this and m = read_grid()??
    mesh = read_mesh(hgrid_fpath)
    
    ocean_boundary = mesh.boundaries[0]  # First one is ocean
 
    # Data
    print("Reading Point Reyes...")
    pt_reyes = read_noaa(pt_reyes_fpath, start=sdate - tbuf, end=bufend, force_regular=True)
    pt_reyes.interpolate(limit=max_gap,inplace=True)
    if pt_reyes.isna().any(axis=None):
        raise ValueError("pt_reyes has gaps larger than fill limit")
    ts_pr_subtidal, ts_pr_diurnal, ts_pr_semi, noise = separate_species(pt_reyes,noise_thresh_min=150)
        
      
    del noise

    print("Reading Monterey...")
    monterey = read_noaa(monterey_fpath, start=sdate - tbuf, end=bufend, force_regular=True)
    monterey.interpolate(limit=max_gap,inplace=True)
    if pt_reyes.isna().any(axis=None):
        raise ValueError("monterey has gaps larger than fill limit")
    
    if pt_reyes.index.freq  != monterey.index.freq:
        raise ValueError(
            "Point Reyes and Monterey time step must be the same in gen_elev2D.py")

    ts_mt_subtidal, ts_mt_diurnal, ts_mt_semi, noise = separate_species(monterey,noise_thresh_min=150)
    del noise


    dt = monterey.index.freq/seconds(1)

    print("Done Reading")

    print("Interpolating and subsetting Point Reyes")
    # interpolate_ts(ts_pr_subtidal.window(sdate,edate),step)
    ts_pr_subtidal = ts_pr_subtidal.loc[sdate:edate]
    ts_pr_diurnal = ts_pr_diurnal.loc[sdate:edate]
    # interpolate_ts(ts_pr_semi.window(sdate,edate),step)
    ts_pr_semi = ts_pr_semi.loc[sdate:edate]
    
    print("Interpolating and subsetting Monterey")
    # interpolate_ts(ts_mt_subtidal.window(sdate,edate),step)
    ts_mt_subtidal = ts_mt_subtidal.loc[sdate:edate]
    # interpolate_ts(ts_mt_diurnal.window(sdate,edate),step)
    ts_mt_diurnal = ts_mt_diurnal.loc[sdate:edate]
    # interpolate_ts(ts_mt_semi.window(sdate,edate),step)
    ts_mt_semi = ts_mt_semi.loc[sdate:edate]

    print("Creating writer")  # requires dt be known for netcdf
    if fpath_out.endswith("th"):
        thwriter = BinaryTHWriter(fpath_out,nnode,None)
    elif fpath_out.endswith("nc"):
        thwriter = NetCDFTHWriter(fpath_out,nnode,sdate,dt)
    else:
        raise ValueError("File extension for output not recognized in file: {}".format(fpath_out))    
    
    
    
    # Grid
    boundaries = mesh.nodes[ocean_boundary.nodes]
    pos_rel = boundaries[:, :2] - pos_pr

    # x, y in a new principal axes
    x = np.dot(pos_rel, tangent.reshape((2, -1)))
    y = np.dot(pos_rel, normal.reshape((2, -1)))
    theta_x = x / x_mt
    theta_x_comp = 1. - theta_x
    theta_y = y / y_mt
    theta_y_comp = 1. - theta_y

    var_y = (theta_y_comp * var_semi[0] + theta_y * var_semi[1])

    # adj_subtidal_mt = 0.08  # Adjustment in Monterey subtidal signal
    # scaling_diurnal_mt = 0.95 # Scaling of Monterey diurnal signal (for K1/Q1)
    # Used this up to v75
    adj_subtidal_mt = 0.  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 1.  # Scaling of Monterey diurnal signal (for K1/Q1)
    # New trial for LSC2 with v75
    adj_subtidal_mt = -0.07  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.95  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.03

    adj_subtidal_mt = -0.14  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.90  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.07

    adj_subtidal_mt = 0.10  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.90  # Scaling of Monterey diurnal signal (for K1/Q1)
    scaling_semidiurnal_mt = 1.03

    adj_subtidal_mt = 0.10  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.97  # Scaling of Monterey diurnal signal (for K1/Q1)
    # Scaling of Point Reyes diurnal signal (for K1/Q1)
    scaling_diurnal_pr = 0.97
    scaling_semidiurnal_mt = 1.025  # Scaling at Monterey semi-diurnal signal

    adj_subtidal_mt = 0.09  # Adjustment in Monterey subtidal signal
    scaling_diurnal_mt = 0.94  # Scaling of Monterey diurnal signal (for K1/Q1)
    # Scaling of Point Reyes diurnal signal (for K1/Q1)
    scaling_diurnal_pr = 0.94
    scaling_semidiurnal_mt = 1.0  # Scaling at Monterey semi-diurnal signal


    if ts_pr_semi.isna().any(axis=None):
        print(ts_pr_semi[ts_pr_semi.isna()])
        raise ValueError('Above times are missing in Point Reyes data')


    for i in range(len(ts_pr_semi)):
        t = float(dt * i)
        # semi-diurnal
        # Scaling
        pr = ts_pr_semi.iloc[i,0]
        mt = ts_mt_semi.iloc[i,0] * scaling_semidiurnal_mt

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")

        eta_pr_side = var_y / var_semi[0] * pr
        eta_mt_side = var_y / var_semi[1] * mt
        eta = eta_pr_side * theta_x_comp + eta_mt_side * theta_x

        # diurnal
        # Interpolate in x-direction only to get a better phase
        pr = ts_pr_diurnal.iloc[i,0] * scaling_diurnal_pr
        mt = ts_mt_diurnal.iloc[i,0] * scaling_diurnal_mt
        #if i < 5:
        #    print("yu")
        #    print(pr)
        #    print(mt)

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")

        eta += pr * theta_x_comp + mt * theta_x

        # Subtidal
        # No phase change in x-direction. Simply interpolate in
        # y-direction.
        pr = ts_pr_subtidal.iloc[i,0]
        mt = ts_mt_subtidal.iloc[i,0] + adj_subtidal_mt 

        if np.isnan(pr) or np.isnan(mt):
            raise ValueError("One of values is numpy.nan.")
        eta += pr * theta_y_comp + mt * theta_y + slr
        
        # write data to netCDF file   
        thwriter.write_step(i,t,eta)

    # Delete class
    del thwriter
  
          

if __name__ == "__main__":
    main()