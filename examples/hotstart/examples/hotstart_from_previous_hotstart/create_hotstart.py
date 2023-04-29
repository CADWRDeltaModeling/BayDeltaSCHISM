# -*- coding: utf-8 -*-
"""
Hotstart example for a basic schism run with TEMP and SALT as tracers.
"""

import schimpy.schism_hotstart as sh
import matplotlib.pyplot as plt

yaml_fn = "./hotstart_from_prev_hotstart.yaml"
modules = ['TEM','SAL']
hotstart_fn = "hotstart.nc" # output hotstart file

# create a hotstart file for SCHISM
h = sh.hotstart(yaml_fn,modules=modules,
                crs ='EPSG:26910')
h.create_hotstart()
hnc = h.nc_dataset
hnc.to_netcdf(hotstart_fn)   

#%% making a 2D surface plot
coll = h.mesh.plot_elems(hnc['tr_el'].values[:,0,0], clim=(14,18)) #clim=[0,35])
cb = plt.colorbar(coll)
plt.axis('off')
plt.axis('equal')
plt.title('Regional Temperature')
plt.tight_layout(pad=1)

#%% converting hotstart file to schism output format so that it can be viewd by VisIt
sh.hotstart_to_outputnc(hotstart_fn,str(h.date),hgrid_fn='../../data_in/hgrid.gr3', 
                          vgrid_fn='../../data_in/vgrid.in.3d',vgrid_version=h.vgrid_version,
                          outname="schout_hotstart.nc")

