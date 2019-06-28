
from numpy import cos as npcos
from numpy import sin as npsin
import pandas as pd
import numpy as np
from vtools.data.api import *
from vtools.functions.api import *
import matplotlib.pylab as plt
from netCDF4 import *

from error_detect import *
import datetime as dtm
from read_ts import read_ts
from write_ts import *
import glob
from unit_conversions import *

avelen = hours(1)
MPH2MS = 0.44704
KPH2MS = 1./3.6
ref_pressure = None

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




def csv_retrieve_ts(fpat,fdir,start,end,selector=":",
                    qaqc_selector=None,
                    parsedates=None,
                    indexcol=0,
                    skiprows=0,
                    dateparser=None,
                    comment = None,
                    prefer_age="new",                    
                    tz_adj=hours(0)):
    import os
    import fnmatch    
    matches = []
    for root, dirnames, filenames in os.walk(fdir):
        for filename in fnmatch.filter(filenames, fpat):
            matches.append(os.path.join(root, filename))
     
    head = skiprows
    qaqc_accept = ["G","U"]
    column_names = None


    #parsetime = lambda x: pd.datetime.strptime(x, '%Y-%m-%d%H%M')
    tsm = []
    
    if prefer_age != "new": raise NotImplementedError("Haven't implemented prefer = 'old' yet")
    
    # The matches are in lexicogrphical order. Reversing them puts the newer ones 
    # higher priority than the older ones for merging
    matches.reverse()
    for m in matches:
        dargs = {}
        if not dateparser is None: dargs["date_parser"] = dateparser
        if not comment is None: dargs["comment"] = comment
        #if not na_values is None: dargs["na_values"] = na_values
        dset = pd.read_csv(m,index_col=indexcol,header = head,parse_dates=parsedates,**dargs)
        if column_names is None:        
            dset.columns = [x.strip() for x in dset.columns]
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
             print dset.loc[~dset[qaqc_selector].isin(qaqc_accept),selector].count()
             print dset.count()                
             dset.loc[~dset[qaqc_selector].isin(qaqc_accept),selector] = np.nan
        
#            anyok = None
#            qa_flag = dset[qaqc_selector].as_matrix()
#            print("QAQC SEction: {}".format(qaqc_selector))
#            print qa_flag.shape
#            for okflag in qaqc_accept:
#                isok = np.equal(qa_flag,okflag)        #np.apply_along_axis(np.equal,0,qa_flag,okflag)
#                if anyok is None:
#                    anyok = isok
#                else:
#                    anyok |= isok
#            assert anyok.ndim <= 2
#            rowok =  anyok   #np.all(anyok,axis=anyok.ndim-1).flatten()
#            print("number flagged: {}".format(np.count_nonzero(rowok)))
#            print rowok.shape
            

        tsm.append(dset[selector])
        big_ts = pd.concat(tsm)
    return big_ts.to_xarray()      




    



if __name__ == "__main__":
    start = dtm.datetime(2003,1,1)
    end = dtm.datetime(2008,5,29)
    mdir = "//cnrastore-bdo/Modeling_Data/des_emp/raw"
    fpat="s21_sunrise_snc_ec_inst*.csv"
    ts=csv_retrieve_ts(fpat,mdir,start,end,selector="VALUE",qaqc_selector="QAQC Flag",
                    parsedates=["DATETIME],
                    indexcol=["DATETIME"],
                    skiprows=2,
                    dateparser=None,
                    comment = None,
                    prefer_age="new",                    
                    tz_adj=hours(0))  
    ts.plot()

