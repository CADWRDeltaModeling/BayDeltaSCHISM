# -*- coding: utf-8 -*-
"""
Copy output nc file mesh, zcor, elev,. compute depth averaged  vel and
save to new nc files.

@author: qshu
"""

import numpy as np
import sys,pdb,os
import matplotlib.pyplot as plt
from matplotlib.colors import cnames
from matplotlib import animation
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import matplotlib.artist as artists
import netCDF4
import datetime as dtm
import numpy.ma as ma
import pandas as pd
from schimpy.schism_polygon import SchismPolygon


ele_table=0
ele_area=0
node_x=0
node_y=0
node_num   = 0
face_num   = 0
lsz_area=[]



model_start=dtm.datetime(2009,2,10)


#data_folder="G:\\schism\\simulations\\suisun_marsh_gate\\postprocess\\2012_jun14_reoperations\\"
data_folder="\\schism_out\\"

points_folder="\\"

zone_file=["cache_mzm_link_points.txt","north_arc_points.txt","suisun_bay_points.txt","delta_points.txt","suisun_marsh_points.txt"]

output_path="subregion.nc"

polys=[]
poly_id=[]

for fname in zone_file:
    fpath=points_folder+fname
    ii=fname.find("_points.txt")
    zone_id=fname[:ii]
    poly_id.append(zone_id)
    df=pd.read_csv(fpath)
    
    point_x=df['POINT_X'].values
    point_y=df['POINT_Y'].values
    poly_xy=[(x,y) for x,y in zip(point_x,point_y)]
    poly_xy.append((point_x[0],point_y[0]))
    apoly=SchismPolygon(poly_xy)
    polys.append(apoly)

print (poly_id)

print (polys[0].contains(np.array([601955.0,4213942.0])))



print ("done reading poly files")
    
dst=netCDF4.Dataset(output_path,'w',format="NETCDF4_CLASSIC")

start_day=149
    
nc_file=data_folder+"schout_%d.nc"%start_day

id_elem=0

#surface_salt_time_average=0
#bottom_salt_time_average=0

if(os.path.exists(nc_file)):
    src=netCDF4.Dataset(nc_file)
    node_dim  = src.dimensions["nSCHISM_hgrid_node"]
    face_dim =  src.dimensions["nSCHISM_hgrid_face"]
    node_num   = node_dim.size
    face_num   = face_dim.size
    ele_table  = np.empty((face_num,4))
    ele_table  = src.variables["SCHISM_hgrid_face_nodes"][:,:]
    id_elem=np.zeros((face_num))
    node_x=np.empty((node_num))
    node_y=np.empty((node_num))
    node_x=src.variables["SCHISM_hgrid_node_x"][:]
    node_y=src.variables["SCHISM_hgrid_node_y"][:]
    
   
    
    
        
    for name in src.ncattrs():
        dst.setncattr(name, src.getncattr(name))
    for name, dimension in src.dimensions.items():
        #if not(name=="time"):
        dst.createDimension(name, len(dimension))
       
    for pid,poly in zip(poly_id,polys):
        var=dst.createVariable(pid,'i2',("nSCHISM_hgrid_face",))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
    

    for name, variable in src.variables.items():
        if ( name in ["hvel_side","hvel","salt","elev","zcor"]):
             print  ("skip  var "+name)
      
        else:
            dst.createVariable(name, variable.datatype, variable.dimensions)
            dst.variables[name][:] = src.variables[name][:]
            #print dst.variables[name].ncattrs()
            for att_name in src.variables[name].ncattrs():
                if not(att_name[0]=="_"):
                    #print att_name
                    dst.variables[name].setncattr(att_name,src.variables[name].getncattr(att_name))
        
   
    src.close()
    
    #dst.variables["time"][k]=elapse_time[k]
    id_num=1
    for pid,poly in zip(poly_id,polys):
        id_elem=np.zeros((face_num))
        for i in range(face_num):
            node_id_lst=ele_table[i,:]
            num_pt=3
            k=node_id_lst[3]-1
            if (np.isfinite(k)):
                num_pt=4
            for kk in range(num_pt):
                 ii=ele_table[i,kk]-1
                 x=node_x[ii]
                 y=node_y[ii]
                 
                 if (poly.contains(np.array([x,y]))):
                    # print "ele"+str(i)+" in "+pid
                     id_elem[i]=id_num
                     break
        dst.variables[pid][:]=id_elem
        print( "done "+pid)
        id_num=id_num+1
    dst.close() 
        
        
else:
    raise nc_file+"is invalid"
            

    
    
    



    




