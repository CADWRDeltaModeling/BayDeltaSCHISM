#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Raymond Hoang (raymond.hoang@water.ca.gov)
# 20220728

"""
Script to convert various data formats (from calsim, csv files) into
SCHISM flux, salt and temp time history (.th) files
"""
import os
import yaml
from argparse import ArgumentParser
import pandas as pd
import matplotlib.pylab as plt
from vtools.data.vtime import minutes
from vtools.functions.filter import ts_gaussian_filter
from vtools.functions.interpolate import rhistinterp
from schimpy.unit_conversions import CFS2CMS, ec_psu_25c
from pyhecdss import get_ts
from schimpy import model_time

dir = os.path.dirname(__file__)
    
source_map_file = '../examples/port_boundary_examples/port_boundary_map.csv'
schism_flux_file = '../data/time_history/flux.th'
schism_salt_file = '../data/time_history/salt.th'
schism_temp_file = '../data/time_history/temp.th'
out_file_flux = 'flux.th.ported'
out_file_salt = 'salt.th.ported'
out_file_temp = 'temp.th.ported'
boundary_kinds = ['flux']
sd = [2014,1,1]
ed = [2014,12,31]

dt = minutes(15)
start_date = pd.Timestamp(sd[0], sd[1], sd[2])
end_date = pd.Timestamp(ed[0], ed[1], ed[2])
df_rng = pd.date_range(start_date, end_date, freq=dt)
source_map = pd.read_csv(source_map_file, header=0)

def read_csv(file, var, name,p=2.):
    """
    Reads in a csv file of monthly boundary conditions and interpolates
    Outputs an interpolated DataFrame of that variable
    """
    forecast_df = pd.read_csv(os.path.join(dir,file), index_col=0, header=0,
                              parse_dates=True)
    forecast_df.index = forecast_df.index.to_period('M')
    interp_series = rhistinterp(forecast_df[var].astype('float'),
                                dt, p=p)
    interp_df = pd.DataFrame()
    interp_df[[name]] = pd.DataFrame({var: interp_series})
    return interp_df

def read_dss(file,pathname,sch_name=None,p=2.):
    """
    Reads in a DSM2 dss file and interpolates
    Outputs an interpolated DataFrame of that variable
    """
    ts15min = pd.DataFrame()
    ts=get_ts(os.path.join(dir,file), pathname = pathname)
    for tsi in ts:
        b=(tsi[0].columns.values[0]).split("/")[2]
        c=(tsi[0].columns.values[0]).split("/")[3]
        f=(tsi[0].columns.values[0]).split("/")[6]
        if p != 0:
            ts15min[[sch_name]]=rhistinterp(tsi[0],dt,p=p).reindex(df_rng)
        else:
            ts15min[[sch_name]]= tsi[0]
        print("Reading " + b + " " + f)
    if ts15min.empty:
        raise ValueError(f'Warning: DSS data not found for {b}')
    return ts15min

for boundary_kind in boundary_kinds:

    source_map = source_map.loc[source_map['boundary_kind'] == boundary_kind]
    
    """
    Read in the reference SCHISM flux, salt and temperature files 
    to be used as a starting point and to substitute timeseries not 
    available from other data sources.
    
    """
    if boundary_kind == 'flux':
        flux = pd.read_csv(schism_flux_file,index_col=0,parse_dates=[0],
                           sep="\\s+",header=0)
        dd = flux.copy().reindex(df_rng)
        out_file = out_file_flux
    elif boundary_kind == 'ec':
        salt = pd.read_csv(schism_salt_file,header=0,parse_dates=True,
                           index_col=0,sep="\s+")
        dd = salt.copy().reindex(df_rng)
        out_file = out_file_salt
    elif boundary_kind == 'temp':
        temp = pd.read_csv(schism_temp_file,header=0,parse_dates=True,
                           index_col=0,sep="\s+")
        dd = temp.copy().reindex(df_rng)
        out_file = out_file_temp

    for index, row in source_map.iterrows():
        dfi = pd.DataFrame()
        name = row['schism_boundary']
        source_kind = row['source_kind']
        source_file = str(row['source_file'])
        derived = str(row['derived']).capitalize()=='True'
        var = row['var']
        sign = row['sign']
        convert = row['convert']
        p = row['rhistinterp_p']
        formula = row['formula']
        print(f"processing {name}")

        if source_kind == 'SCHISM':
            # Simplest case: use existing reference SCHISM data; do nothing
            print("Use existing SCHISM input")

        elif source_kind == 'CSV':
            # Substitute in an interpolated monthly forecast
            if derived:
                print(f"Updating SCHISM {name} with derived timeseries\
                    expression: {formula}")
                csv = pd.DataFrame()
                vars = var.split(';')
                for v in vars:
                    csv[[v]] = read_csv(source_file, v, name,p = p)
                dts = eval(formula).to_frame(name).reindex(df_rng)
                dfi = ts_gaussian_filter(dts, sigma=100)
            else:
                print(f"Updating SCHISM {name} with interpolated monthly\
                    forecast {var}")
                dfi = read_csv(source_file, var, name,p = p)

        elif source_kind == 'DSS':
            # Substitute in CalSim value.
            if derived:
                vars = var.split(';')
                print(f"Updating SCHISM {name} with derived timeseries\
                    expression: {formula}")
                dss = pd.DataFrame()
                for pn in vars:
                    b = pn.split("/")[2]
                    dss[[b]] = read_dss(source_file,pathname = pn,
                                        sch_name = name,p = p)
                dts = eval(formula).to_frame(name).reindex(df_rng)
                dfi = ts_gaussian_filter(dts, sigma=100)
            else:        
                print(f"Updating SCHISM {name} with DSS variable {var}")
                dfi = read_dss(source_file,pathname = var,sch_name = name,p = p)

        elif source_kind == 'CONSTANT':
            # Simply fill with a constant specified.
            dd[name] = float(var)
            print(f"Updating SCHISM {name} with constant value of {var}")

        # Do conversions.
        if convert == 'CFS_CMS':
            dfi = dfi*CFS2CMS*sign
        elif convert == 'EC_PSU':
            dfi = ec_psu_25c(dfi)*sign
        else:
            dfi = dfi
        
        # Update the dataframe.
        dd.update(dfi, overwrite=True)

    print(dd)

    # Format the outputs.
    dd.index.name = 'datetime'
    dd.to_csv(
        os.path.join(
            dir,
            out_file),
        header=True,
        date_format="%Y-%m-%dT%H:%M",
        float_format="%.4f",
        sep=" ")

    dd.plot()
    

print('Done')
plt.show()
