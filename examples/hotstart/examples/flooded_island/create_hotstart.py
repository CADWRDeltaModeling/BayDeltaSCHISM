# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 11:12:19 2020

@author: zzhang
"""

import schimpy.schism_hotstart as sh
import matplotlib.pyplot as plt

yaml_fn = "./hotstart_flooded_island.yaml"
modules = ['TEM','SAL']
hotstart_fn = "hotstart.nc" # output hotstart file

# create a hotstart file for SCHISM
h = sh.hotstart(yaml_fn,modules=modules,
                crs ='EPSG:26910')
h.create_hotstart()
hnc = h.nc_dataset
hnc.to_netcdf(hotstart_fn)   

#%% making a 2D surface plot

eta = hnc.eta2.values
z = h.mesh.nodes[:,2]*-1-0.1

fig,ax = plt.subplots(1,2,sharex=True)
coll = h.mesh.plot_nodes(eta, clim=(1.5,2),ax=ax[0]) #clim=[0,35])
plt.axis('off')
plt.axis('equal')
coll = h.mesh.plot_nodes(z,clim=(1.5,2),ax=ax[1])
plt.axis('off')
plt.axis('equal')
plt.title('Water level')
plt.tight_layout(pad=1)