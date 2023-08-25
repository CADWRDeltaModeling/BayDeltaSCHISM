# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 11:12:19 2020

@author: zzhang
"""

import schimpy.schism_hotstart as sh
import matplotlib.pyplot as plt
import xarray as xr

yaml_fn = "./hotstart_tracer_age.yaml"
modules = ['TEM','SAL','GEN','AGE']
hotstart_fn = "hotstart_tracer_age.nc" # output hotstart file



#%% create a hotstart file for SCHISM
h = sh.hotstart(yaml_fn,modules=modules,
                crs ='EPSG:26910')
h.create_hotstart()
hnc = h.nc_dataset
  
#%% merge the two hotstart file
nc1 = xr.open_dataset("../../data_in/hotstart.nc")
var_list = ['tr_nd','tr_nd0','tr_el']
nc1 = nc1.drop_vars(var_list)
hnc_new = xr.merge([nc1, hnc[var_list]])
hnc_new.to_netcdf(hotstart_fn) 

#%% making a 2D surface plot
coll = h.mesh.plot_elems(hnc['tr_el'].values[:,0,-3]) #clim=[0,35])
cb = plt.colorbar(coll)
plt.axis('off')
plt.axis('equal')
plt.title('GEN_1')
plt.tight_layout(pad=1)



