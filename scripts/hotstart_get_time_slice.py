# -*- coding: utf-8 -*-
"""
Create time slice of observed values for the Delta region
@author: zzhang
Note that the raw data is used: no filtering is performed and cdec data is excluded. 
"""

import os
import numpy as np
import pandas as pd
from schimpy import unit_conversions
from vtools.datastore.read_ts import *
from vtools.datastore import station_config

start_date = '2021-04-20'
end_date = '2021-04-21'

variables = ['temp','ec']
repo = "//cnrastore-bdo/Modeling_Data/continuous_station_repo_beta/formatted_1yr/"


station_lookup = station_config.config_file("station_dbase")
slookup = pd.read_csv(station_lookup,sep=",",comment="#",header=0,usecols=["id","agency",
                                                                            "agency_id","name",
                                                                            "x","y"]).squeeze()
obs_df = slookup[['id','x','y']].set_index('id')

for v in variables:    
    fns = [f for f in os.listdir(repo) if (v in f) and ('cdec' not in f) and ('@' not in f)]
    stns = set([f.split('_')[1] for f in fns])
    var_df = pd.DataFrame()
    stns_excl = []
    for s in stns:
        try:
            v_ts = read_ts(os.path.join(repo,"*_%s_*%s*.csv"%(s,v)),
                           start=start_date,end=end_date).interpolate(limit=4)
            if np.nanmean(v_ts)>40:
                v_ts = v_ts.apply(unit_conversions.fahrenheit_to_celsius)
            var_df[s] = v_ts['value']
        except KeyError:  # if reading file results in an error, skip the file
            stns_excl.append(s)
            print("Error reading station %s: excluded!"%s)    
    
    var_t = var_df.loc[pd.to_datetime(start_date)].dropna()
    if v =='temp':
        var_t.mask((var_t<1.) | (var_t>45),inplace=True) # temp
        name = 'temperature'
    elif v=='ec':
        var_t.mask((var_t<35.) | (var_t>60000.),inplace=True) # ec
        var_t = var_t.apply(unit_conversions.ec_psu_25c) #converting ec to salinity
        name = 'salinity'
        
    var_t = pd.merge(var_t.to_frame(name),obs_df,left_index=True,
                     right_index=True).drop_duplicates()
    var_t.to_csv("all_stations_%s_%s.csv"%(name,start_date))

