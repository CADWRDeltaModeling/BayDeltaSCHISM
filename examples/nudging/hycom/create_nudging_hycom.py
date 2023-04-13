# -*- coding: utf-8 -*-
"""
Created on Tue Jun  8 10:21:29 2021

@author: zzhang
"""

import os
from schimpy import nudging
from schimpy.schism_mesh import write_mesh, read_mesh
import xarray as xr
import datetime

from schimpy.geo_tools import ll2utm
from shapely.ops import cascaded_union
from shapely.geometry import Polygon

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

yaml_fn = 'nudge_hycom.yaml'

nudging = nudging.nudging(yaml_fn,proj4 ='EPSG:32610')
nudging.read_yaml()
nudging.create_nudging()

#%% plot temperature
nct = xr.open_dataset('TEM_nu_hycom.nc')

fig ,ax = plt.subplots(2,2,sharex=True,figsize=(10,8))
plt.sca(ax[0,0])
coll = nudging.plot(nct.map_to_global_node.values-1,nct.tracer_concentration.isel(
    time=-1,nLevels=-1,one=-1).values,clim=[0,22],ax=ax[0,0],edgecolor='face',
    linewidth=1.5)   #-1 is top 0 is bottom.
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_temp (top)")

wd = read_mesh('temperature_nudge.gr3')
plt.sca(ax[0,1])
v = wd.nodes[nct.map_to_global_node.values-1,2]
coll = nudging.plot(nct.map_to_global_node.values-1,nct.tracer_concentration.isel(
    time=-1,nLevels=-1,one=-1).values*v,clim=[0,0.0005],ax=ax[0,1],
    edgecolor='face', linewidth=1.5)
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_temp*weight (top)")

plt.sca(ax[1,0])
coll = nudging.plot(nct.map_to_global_node.values-1,nct.tracer_concentration.isel(
    time=-1,nLevels=0,one=-1).values,clim=[0,22],ax=ax[1,0],edgecolor='face',
    linewidth=1.5)   #-1 is top 0 is bottom.
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_temp (bottom)")

wd = read_mesh('temperature_nudge.gr3')
plt.sca(ax[1,1])
v = wd.nodes[nct.map_to_global_node.values-1,2]
coll = nudging.plot(nct.map_to_global_node.values-1,nct.tracer_concentration.isel(
    time=-1,nLevels=0,one=-1).values*v,clim=[0,0.0005],ax=ax[1,1],
    edgecolor='face', linewidth=1.5)
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_temp*weight (bottom)")

plt.tight_layout()



#%% plot salinity

ncs = xr.open_dataset('SAL_nu_hycom.nc')

fig ,ax = plt.subplots(2,2,sharex=True,figsize=(10,8))
plt.sca(ax[0,0])
coll = nudging.plot(ncs.map_to_global_node.values-1,ncs.tracer_concentration.isel(
    time=-1,nLevels=-1,one=-1).values,clim=[0,35],ax=ax[0,0],edgecolor='face',
    linewidth=1.5)   #-1 is top 0 is bottom.
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_salt (top)")
plt.text(670730,4300600,'psu',style='italic')

wd = read_mesh('temperature_nudge.gr3')
plt.sca(ax[0,1])
v = wd.nodes[ncs.map_to_global_node.values-1,2]
coll = nudging.plot(ncs.map_to_global_node.values-1,ncs.tracer_concentration.isel(
    time=-1,nLevels=-1,one=-1).values*v,clim=[0,0.0001],ax=ax[0,1],edgecolor='face',
    linewidth=1.5)
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_salt*weight (top)")
plt.text(670730,4300600,'psu',style='italic')

plt.sca(ax[1,0])
coll = nudging.plot(ncs.map_to_global_node.values-1,ncs.tracer_concentration.isel(
    time=-1,nLevels=0,one=-1).values,clim=[0,35],ax=ax[1,0],edgecolor='face',
    linewidth=1.5)   #-1 is top 0 is bottom.
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_salt (bottom)")

wd = read_mesh('temperature_nudge.gr3')
plt.sca(ax[1,1])
v = wd.nodes[ncs.map_to_global_node.values-1,2]
coll = nudging.plot(ncs.map_to_global_node.values-1,ncs.tracer_concentration.isel(
    time=-1,nLevels=0,one=-1).values*v,clim=[0,0.0001],ax=ax[1,1],edgecolor='face',
    linewidth=1.5)
cb = plt.colorbar(coll)
plt.axis('equal')
plt.axis('off')
plt.title("nu_salt*weight (bottom)")

plt.tight_layout()

plt.savefig('figures/nud_salt.png',dpi=300)

#%% plot a comparison between nudging and hycom for water surface 
temp_mesh = read_mesh('temperature_nudge.gr3')
weights_temp = temp_mesh.nodes[:,2]
weights_elem = np.asarray([weights_temp[el].mean(axis=0) for el in nudging.mesh.elems])
 
poly_coll = [Polygon(nudging.mesh.nodes[el][:,:2]) for el in 
             nudging.mesh.elems]
poly_coll = np.array(poly_coll)[weights_elem>0]
boundary_poly = cascaded_union(poly_coll)

#%%

date = pd.Timestamp(2022,8,2,12,0,0)
datestr1 = date.date().strftime("%Y%m%d") 
dest = r'\\cnrastore-bdo\Modeling_Data\hycom\processed'
ncfn = os.path.join(dest,"hycom_interpolated_hourly_pst"+datestr1+".nc")

ncdata = xr.open_dataset(ncfn)
                  
rtemp = ncdata.temp.sel(time=date).isel(depth=0).transpose('lon','lat')  # 0 is surface for ROMS
rsalt = ncdata.salt.sel(time=date).isel(depth=0).transpose('lon','lat')

t = (pd.to_datetime(date) - pd.to_datetime(nudging.start_date)).total_seconds()
stemp = nct.tracer_concentration.sel(time=t,nLevels=-1,one=0).values # last is the surface for schism
ssalt = ncs.tracer_concentration.sel(time=t,nLevels=-1,one=0).values

mesht = read_mesh("temperature_nudge.gr3")
weights_t = mesht.nodes[:,2]
lat = rtemp.lat.values
lon = rtemp.lon.values
lat, lon = np.meshgrid(lat,lon)
utmxy = ll2utm([lon, lat])
utmx = utmxy[0]
utmy = utmxy[1]

# minx = max(utmx.min(), nudging.mesh.nodes[:,0].min())
# maxx = min(utmx.max(), nudging.mesh.nodes[:,0].max())
# miny = max(utmy.min(), nudging.mesh.nodes[:,1].min())
# maxy = min(utmy.max(), nudging.mesh.nodes[:,1].max())

minx = 475000
maxx = 575000
miny = 410e4
maxy = 423e4


fig ,ax = plt.subplots(2,2,sharex=True,figsize=(10,8))
plt.sca(ax[0,0])
imap_temp = nct.map_to_global_node.values-1
inpoly = weights_t>0
coll = nudging.plot(imap_temp,stemp,ax=ax[0,0],clim=(12,18.4)) 
#coll = nudging.mesh.plot_nodes(stemp,ax=ax[0,0],inpoly=inpoly,clim=(9,13))  
cb = plt.colorbar(coll)
plt.plot(boundary_poly.boundary.xy[0],boundary_poly.boundary.xy[1])
plt.axis('equal')
plt.axis('off')
ax[0,0].set_xlim((minx,maxx))
ax[0,0].set_ylim((miny,maxy))
plt.title('Nudging temp')
plt.text(580000,4222000,'$^o$C',style='italic')


plt.sca(ax[0,1])
plt.pcolor(utmx,utmy, rtemp.values,vmin=12,vmax=18.4)
plt.colorbar()
plt.plot(boundary_poly.boundary.xy[0],boundary_poly.boundary.xy[1],'k')
plt.axis('equal')
plt.axis('off')
ax[0,1].set_xlim((minx,maxx))
ax[0,1].set_ylim((miny,maxy))
plt.title('HYCOM temp')
#rtemp.plot(ax=ax[0,1])
plt.text(580000,4222000,'$^o$C',style='italic') 

plt.sca(ax[1,0])
imap_salt = ncs.map_to_global_node.values-1
coll = nudging.plot(imap_salt,ssalt,ax=ax[1,0],clim=(32,33.6)) 
cb = plt.colorbar(coll)
plt.plot(boundary_poly.boundary.xy[0],boundary_poly.boundary.xy[1])
plt.axis('equal')
plt.axis('off')
ax[1,0].set_xlim((minx,maxx))
ax[1,0].set_ylim((miny,maxy))
plt.title('Nudging salt')
plt.text(580000,4222000,'$^o$C',style='italic')

plt.sca(ax[1,1])
plt.pcolor(utmx,utmy, rsalt.values,vmin=32,vmax=33.6)
plt.colorbar()
plt.plot(boundary_poly.boundary.xy[0],boundary_poly.boundary.xy[1],'k')
plt.axis('equal')
plt.axis('off')
ax[1,1].set_xlim((minx,maxx))
ax[1,1].set_ylim((miny,maxy))
plt.title('HYCOM salt')
#rtemp.plot(ax=ax[0,1])
plt.text(580000,4222000,'$^o$C',style='italic') 

# plt.savefig("figures/hycom_%s.png"%datestr1,dpi=300)
