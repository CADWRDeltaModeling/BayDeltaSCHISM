# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 10:46:35 2020
Example script to generate a hotstart file for a sediment transport run
@author: zzhang
"""

import schimpy.schism_hotstart as sh
import matplotlib.pyplot as plt

yaml_fn = "hotstart_sed.yaml"
modules = ['TEM','SAL','SED']
hotstart_fn = "hotstart_sed.nc" # output hotstart file

#%% convert mesh from latlon to utm coordinate system. 
# from schimpy.schism_mesh import read_mesh, write_mesh
# mesh1 =  read_mesh('./data_in/hgrid.gr3',
#                    crsSG:26910')   # utm coordinates
# mesh2 =  read_mesh('./data_in/hgrid2.gr3',
#                    crs='EPSG:4326 ')   # lat, lon coordinates
# mesh2_new = sh.project_mesh(mesh2,'EPSG:26910')
# write_mesh(mesh2_new,'./data_in/hgrid2_new.gr3')
#%% create a hotstart file for SCHISM
h = sh.hotstart(yaml_fn,modules=modules,
                crs ='EPSG:26910')
h.create_hotstart()
hnc = h.nc_dataset
hnc.to_netcdf(hotstart_fn)   

#%% making a 2D surface plot
coll = h.mesh.plot_elems(hnc['tr_el'].values[:,-1,0],clim=(15,22))
cb = plt.colorbar(coll)
plt.axis('off')
plt.axis('equal')
plt.title('Regional Temperature')
plt.tight_layout(pad=1)

#%% converting hotstart file to schism output format so that it can be viewd by VisIt
# sh.hotstart_to_outputnc(hotstart_fn,ini_date,hgrid_fn='./hgrid.gr3', 
#                          vgrid_fn='./vgrid.in.3d',
#                          outname="schout_hotstart_sed.nc")

