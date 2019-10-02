#!/usr/bin/env python
""" Script to read and interpolate monthly DICU data 
    The main function in this file is expand_dicu.
    An example of its use is given in the __main__ section
"""


import numpy as np
import os
import datetime as dtm
from vtools.datastore.transfer import *
from vtools.data.api import *
from vtools.functions.api import *
from vtools.datastore.dss.api import *
from scipy.ndimage.filters import gaussian_filter,gaussian_filter1d
from unit_conversions import *
import matplotlib.pyplot as plt

outflow_adj_file = "missing_outflow.txt"

def get_dicu_nodes(filename):
    dicu = []
    f = open(filename,"r")
    for line in [x.strip() for x in f.readlines()[1:] if x and "div" in x ]:
        (name,node,x,y) = line.split(",")
        label, flowtype, nnode = name.split("_")
        if int(node) != int(nnode):
            raise ValueError("Node and label mismatch: %s %s %s" % (label,flowtype,nnode))
        newnode = "%03d" % int(node)
        newname = "%s_%s_%s" % (label,flowtype,newnode)
        dicu.append((newname,int(node),x,y))

    dicu.sort()

    g = open("dicu_sorted.txt","w")
    for item in dicu:
        g.write("%s,%s,%s,%s\n" % item)
    g.close()
    print("Identified %s DICU nodes (using diversions)" % len(dicu))
    return [x[1] for x in dicu]


def extend_monthly_series(ts,start,end):
    sw = start
    ew = end
    if ts.start <= sw and ts.end >=ew: 
        return ts

    new_ts = rts_constant(sw,ew,months(1),np.nan)
    janndx = -1
    for i,el in enumerate(ts):
        if el.time.month == 1:
            janndx=i
            climate = ts.data[janndx:(janndx+12)]
            break
    assert janndx > -1
    sndx = int(new_ts.start.month - 1)
    new_ts_ndx = (np.arange(len(new_ts),dtype=int) + sndx) % 12
    new_ts.data = climate[new_ts_ndx]
    return new_ts
    
    
        

    

def expand_dicu(source, saltsource, tempsource, nodelist, window):
    ## giving a existing datasource.

    allnodes = get_dicu_nodes(nodelist)
    allnodes=allnodes
    
    sinks = []
    sources = []
    ec = []
    temp = []
    winleft = align(window[0],months(1),-1)
    winright = align(window[1]+days(31),months(1),1)+minutes(1)
    getwindow = (winleft,winright)
    for n in allnodes:
        select_div  ="B=%s,C=DIV-FLOW"  % (n)
        select_seep="B=%s,C=SEEP-FLOW" % (n)
        select_drain="B=%s,C=DRAIN-FLOW" % (n)
        select_ec  = "B=%s,C=DRAIN-EC" % (n)
        select_temp  = "B=%s,C=DRAIN-TEMP" % (n)
        ts_div=dss_retrieve_ts(source,select_div,getwindow,unique=True)
        ts_seep=dss_retrieve_ts(source,select_seep,getwindow,unique=True)
        ts_salt = dss_retrieve_ts(saltsource,select_ec,getwindow,unique=True)
        sources.append(dss_retrieve_ts(source,select_drain,getwindow,unique=True))
        sinks.append(ts_div+ts_seep)
        ec.append(ts_salt)
        if tempsource: 
            # todo: had to get rid of getwindow here. 
            # For reasons I don't understand, the returned series lengths were not consistent
            ts_temp = dss_retrieve_ts(tempsource,select_temp,unique=True)
            ts_temp = extend_monthly_series(ts_temp,getwindow[0],getwindow[1]).window(*getwindow)
            temp.append(ts_temp)

    nnode = len(sinks)
    assert nnode == len(sources)
    ts = sinks[0]
    interval=hours(1)
    stime = window[0]
    etime = window[1]
    print("Creating instantaneous data at interval %s " % interval)
    ts2=interpolate_ts(ts,interval,method=PREVIOUS).window(stime,etime)
    ntime=len(ts2)
    print("Number of steps at this interval: %s " % ntime)


    tnames = [ (sources,"source"), 
               (sinks,"sink"),  
               (ec,"salinity")]
    if tempsource:
        tnames.append((temp,"temperature"))
    ntype = len(tnames)
    tname_ndx = {'source': 0, 'sink' : 1, 'salinity' : 2, 'temperature' : 3}

    dicu_data = np.zeros((ntype,ntime,nnode+1),dtype=np.float64)
    for ivar in range(ntype):
        dicu_data[ivar,:,0] = ts2.ticks - ts2.ticks[0]    
    
    for tslist, tname in tnames:
        itype = tname_ndx[tname]
        print("Interpolating %s" % tname)
        for inode,s in enumerate(tslist):
            if s.interval == months(2):
                if tname == "sink":
                    x = -interpolate_ts(-s,interval,method=RHIST).window(stime,etime)
                else:
                    x = interpolate_ts(s,interval,method=RHIST).window(stime,etime)
            elif s.interval == months(1):
                x = interpolate_ts(s,interval,method=PREVIOUS).window(stime,etime)
                x.data=gaussian_filter(x.data,sigma = 200)
            elif s.interval == days(1):
                x = interpolate_ts(s,interval,method=RHIST).window(stime,etime)
            else:
                raise ValueError("Input time series interval is unexpected")            
            if (tname == 'salinity'): 
                x.data = np.maximum(x.data,100.)            
                x.data = ec_psu_25c(x.data)
            elif (tname == 'sink'):
                x *= -CFS2CMS
                x.data = np.minimum(x.data,0.)
            elif (tname == 'source'):
                x *= CFS2CMS
                x.data = np.maximum(x.data,0.)
            elif (tname == 'temperature'):
                x.data = np.maximum(x.data,0.)
                
            dicu_data[itype,:,(inode+1)] = x.data        
    #write it out    
    write_data = None
    for tname in tname_ndx:
        thfile = "dcd_%s.th" % tname
        tndx=tname_ndx[tname]
        f0 = open(thfile,"w")
        print("Writing %s" % tname)
        write_data=None
        writefmt = "%0.2f"
        if tname in ['source','sink']:
            write_data=dicu_data[tndx,:,:]
        elif tname == 'temperature':
            continue
        else:
            times = dicu_data[tndx,:,0]
            salt = dicu_data[tndx,:,1:]
            if tempsource:
                print("Temperature provided")
                temp = dicu_data[tname_ndx['temperature'],:,1:]
            else:
                print("Temperature not provided, assumed to be -9999")
                temp = np.ones_like(salt)*-9999.
            write_data = np.hstack((times[:,np.newaxis],temp,salt))
        np.savetxt(f0,write_data,fmt=writefmt,delimiter=" ")
        print("Write complete")
        f0.close()        
   

def create_arg_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start',default = None, required=True,help = 'Start time in ISO-like format 2009-03-12T00:00:00. Time part is optional.')
    parser.add_argument('--end',default = None, required=True,help = 'Start time in ISO-like format 2009-03-12T00:00:00. Time part is optional.')    
    parser.add_argument('--loc_file', default = None, type=str, help = 'CSV file with four columns: name, node, x, y')
    parser.add_argument('--flow_file', default = None, type=str, help = 'DSS file with source/sink flows (water)')
    parser.add_argument('--wq_file', default = None, type=str, help = 'DSS file with source/sink water quality')
    parser.add_argument('--temp_file', default = None, required = False, type=str, help = 'DSS file with source/sink water temperature')     
    return parser
 
def test_extend(): 
    ts = rts([0.,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,11.,0.,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.,11.],dtm.datetime(2004,5,1),months(1))
    ts2 = extend_monthly_series(ts,dtm.datetime(2005,1,1),dtm.datetime(2006,6,1)) 
    for el in ts2:
        print(el)

if __name__ == "__main__":
    parser = create_arg_parser()
    args = parser.parse_args()
    sdtime=dtm.datetime(*list(map(int, re.split('[^\d]', args.start)))) # convert start time string input to datetime
    "DICU/DCD start time given: %s" % sdtime
    edtime=dtm.datetime(*list(map(int, re.split('[^\d]', args.end)))) # convert start time string input to datetime
    "DICU/DCD end time given: %s" % edtime    

    flow_file = args.flow_file
    wq_file = args.wq_file
    temp_file = args.temp_file
    loc_file = args.loc_file
    expand_dicu(flow_file,wq_file,temp_file,loc_file,
                window = (sdtime,edtime))


                
                
                