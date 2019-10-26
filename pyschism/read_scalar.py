import csv
from numpy import cos as npcos
from numpy import sin as npsin
import pandas as pd
import numpy as np
#from vtools.data.api import *
#from vtools.functions.api import *
import matplotlib.pylab as plt
from vtools3.data.vtime import *
#from netCDF4 import *

#from error_detect import *
import datetime as dtm
#from read_ts import read_ts
from write_ts import *
import glob
#from unit_conversions import *

avelen = hours(1)
MPH2MS = 0.44704
KPH2MS = 1./3.6
ref_pressure = None


def ts_merge(series):
    # this concatenates, leaving redundant indices in df0, df1, df2
    dfmerge = pd.concat(series,sort=True)

    # finally, drop duplicate indices
    dfmerge = dfmerge.loc[~dfmerge.index.duplicated(keep='last')]    
    # Now apply, in priority order, each of the original dataframes to fill the original
    for ddf in series:
        dfmerge = dfmerge.combine_first(ddf)


    print(dfmerge)
    return dfmerge


def remove_isolated(ts,thresh):
    goodloc = np.where(np.isnan(ts.data),0,1)
    repeatgood = np.apply_along_axis(rep_size,0,goodloc)
    isogood = (goodloc==1) & (repeatgood < thresh)
    out = ts.copy()
    out.data[isogood] = np.nan
    return out




def load_corrections(fname):
    corrections = []
    with open(fname,"r") as f:
        for line in f:
            if len(line) > 10:
                parts = line.strip().split(",")
                path = parts[0]
                var = parts[1]
                start = parse_time(parts[2])
                end = parse_time(parts[3])
                corrections.append([path,var,start,end])
    return corrections
#corrections = load_corrections("corrections.csv")


def rep_size(x):
    from itertools import groupby
    isrep = np.zeros_like(x)
    diff = np.ediff1d(x,to_begin=1,to_end=1)
    lrep = (diff[:-1] == 0) | (diff[1:]==0)
    isrep[lrep] = 1
    reps = []
    
    xx = x.copy()
    xx[xx==0.]  = -0.123456789001
    for a, b in groupby(isrep*xx):
        lb = list(b)
        if a==0: # Where the value is 0, simply append to the list
            l = len(lb)
            reps.extend(lb)

        else: # Where the value is one, replace 1 with the number of sequential 1's
            l = len(lb)
            reps.extend([l]*l)
            #print reps
    outy = np.array(reps)
    return outy


def cdec_date_parser(*args):
    if len(args) == 2: 
        x = args[0] + args[1]     
        return dtm.datetime.strptime(x,"%Y%m%d%H%M")
    else:
        return dtm.datetime.strptime(args,"%Y%m%d%H%M")

def csv_retrieve_ts(fpat,fdir,start,end,selector=":",
                    qaqc_selector=None,
                    qaqc_accept=["G","U"],
                    parsedates=None,
                    indexcol=0,
                    skiprows=0,
                    dateparser=None,
                    comment = None,
                    extra_na = ["m","---",""," "],
                    prefer_age="new",                    
                    tz_adj=hours(0)):
    import os
    import fnmatch
    matches = []
    for root, dirnames, filenames in os.walk(fdir):
        for filename in fnmatch.filter(filenames, fpat):
            matches.append(os.path.join(root, filename))
     
    head = skiprows
    column_names = None
    
    

    #parsetime = lambda x: pd.datetime.strptime(x, '%Y-%m-%d%H%M')
    tsm = []
    
    if prefer_age != "new": raise NotImplementedError("Haven't implemented prefer = 'old' yet")
    
    # The matches are in lexicogrphical order. Reversing them puts the newer ones 
    # higher priority than the older ones for merging
    matches.reverse()
    if len(matches) < 1:
        raise ValueError("File pattern {} searched from dir {} returned no matches".format(fpat,fdir))
    for m in matches:
        dargs = {}
        if not dateparser is None: dargs["date_parser"] = dateparser
        if not comment is None: dargs["comment"] = comment
        #if not na_values is None: dargs["na_values"] = na_values
        dset = pd.read_csv(m,index_col=indexcol,header = head,parse_dates=parsedates,na_values=extra_na,keep_default_na=True,**dargs)
        if column_names is None:        
            dset.columns = [x.strip() for x in dset.columns]
            print(dset.columns)
        else:
            dset.columns = column_names
        if dset.shape[0] == 0: 
            #empty file
            continue
        # todo: may have to make this robust if it is a list
        if type(selector) == str:
            if selector.startswith("Var"): 
                selector = dset.columns[int(selector[3:])]
        if qaqc_selector is None:
            rowok = None
        else:
            
            qafilter = dset[qaqc_selector].isin(qaqc_accept)
            if ' ' in qaqc_accept or '' in qaqc_accept or u' ' in qaqc_accept:
                qafilter = dset[qaqc_selector].isna() | dset[qaqc_selector].isin(qaqc_accept)
            else:
                qafilter = dset[qaqc_selector].isin(qaqc_accept)
            dset.loc[~qafilter,selector] = np.nan

        tsm.append(dset[selector].astype(float))
        big_ts = ts_merge(tsm) #pd.concat(tsm)  # does this need to be outdented?
    return big_ts.to_frame()  #.to_xarray()      



if __name__ == "__main__":
    start = dtm.datetime(2003,1,1)
    end = dtm.datetime(2008,5,29)
    mdir = "//cnrastore-bdo/Modeling_Data/des_emp/raw"
    fpat="s33_cygnus_cyg_ec_inst_*.csv"
    #fpat="bll_blacklockriver_bll_ec_inst_2009_2019.csv"
    #fpat="s71_mzmroar_msl_ec_inst_*.csv"
    ts=csv_retrieve_ts(fpat,mdir,start,end,selector="VALUE",qaqc_selector="QAQC Flag",
                    parsedates=["DATETIME"],
                    indexcol=["DATETIME"],
                    skiprows=2,
                    dateparser=None,
                    comment = None,
                    prefer_age="new",                    
                    tz_adj=hours(0))  
    ts2 = ts.asfreq("15min")
    fig,ax = plt.subplots(1)
    (ts-10.).plot(ax=ax)
    ts2.plot(ax=ax)
    plt.legend(["Original", "Regular"])
    plt.show()
    ts2.to_csv("//cnrastore-bdo/BDO_HOME/SCHISM/fielddata/emp_ec_20190802/cyg.csv",date_format="%Y%m%d,%H%M",float_format="%.1f",na_rep="m")


