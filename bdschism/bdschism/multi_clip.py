#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime as dtm
from schimpy.model_time import multi_file_to_elapsed

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# User will need to change the start time and location of BayDeltaSCHISM
start=dtm.datetime(2009,2,10)
bds_home = "D:/Delta/BayDeltaSCHISM/"

th_repo = os.path.join(bds_home,"data/time_history/*.th")
multi_file_to_elapsed(th_repo,".",start)

# This changes salt and temp to the official schism input names
os.replace("salt.th","SAL_1.th")
os.replace("temp.th","TEM_1.th")

# Points to the channel depletions in BayDeltaSCHISM
# For some near-real time projects this needs to be updated more rapidly
dcd_repo = os.path.join(bds_home,"data/channel_depletion")
dcd_daily = ["vsink_dated.th",
             "vsource_dated.th",
             "msource_dated.th"]
inputs = [os.path.join(dcd_repo,fname) for fname in dcd_daily]
multi_file_to_elapsed(inputs,'.',start)

# At this point vsource.in is named vsource.in, which is the simplest treatment
# However, you may want to restore the versioned names to make the versions easier to figure
# out later. This will requre symbolic links.
for inp  in inputs:
    meta = None
    with open(inp,'r') as f:
        meta = f.readline()
        if not meta.startswith("# version"): 
            raise ValueError("Version expected in first line of file")
        meta = meta.split(":")[1].strip().replace("_dated","").replace("_daily","")
    orig = os.path.split(inp)[1].replace("_dated","").replace("daily","")
    print(f"Moving {orig} to {meta}")
    os.replace(orig,meta)    
 
