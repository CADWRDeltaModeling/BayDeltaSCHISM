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

def triangle_area(x1, y1, x2, y2, x3, y3):
    return abs(0.5*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2)))

def quad_area(x1, y1, x2, y2, x3, y3,x4,y4):
    a1=triangle_area(x1,y1,x2,y2,x4,y4)
    a2=triangle_area(x2,y2,x3,y3,x4,y4)
    return a1+a2

def fill_ele_area510():
    for k in range(face_num):
        node_id_lst=ele_table[k,:]
        
        i=node_id_lst[0]-1
        x1=node_x[i]
        y1=node_y[i]
        i=node_id_lst[1]-1
        x2=node_x[i]
        y2=node_y[i]
        i=node_id_lst[2]-1
        x3=node_x[i]
        y3=node_y[i]
        i=node_id_lst[3]-1
        if (i==-2): ## out2d use -1
            a=triangle_area(x1,y1,x2,y2,x3,y3)
            ele_area[k]=a
        else:
            
            x4=node_x[i]
            y4=node_y[i]
            a=quad_area(x1,y1,x2,y2,x3,y3,x4,y4)
            ele_area[k]=a
ele_table=0
ele_area=0
node_x=0
node_y=0
node_num   = 0
face_num   = 0
lsz_area=[]

squaremetertoacre=0.000247105

model_start=dtm.datetime(2009,2,10)

data_folder=".\\"

region_xy="region_pointsUTM.csv"
poly_xy_pd= pd.read_csv(region_xy,header = 0,sep=',')

zone_lst=poly_xy_pd.SUBREGION.unique()

output_path="subregion_hsi.nc"

polys=[]
poly_id=[]
pdb.set_trace()
for zone_id in zone_lst:
    poly_id.append(zone_id)

    point_x=poly_xy_pd.loc[poly_xy_pd['SUBREGION']==zone_id].POINT_X.values
    point_y=poly_xy_pd.loc[poly_xy_pd['SUBREGION']==zone_id].POINT_Y.values
    poly_xy=[(x,y) for x,y in zip(point_x,point_y)]
    poly_xy.append((point_x[0],point_y[0]))
    apoly=SchismPolygon(poly_xy)
    polys.append(apoly)

print (poly_id)





print ("done reading poly files")
    
dst=netCDF4.Dataset(output_path,'w',format="NETCDF4_CLASSIC")

start_day=149
    
nc_file=data_folder+"out2d_%d.nc"%start_day

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
    ele_area=np.zeros((face_num))
    fill_ele_area510()
    
    
        
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
        var.setncattr("i23d",4)
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
        region_area=0
        id_elem=np.zeros((face_num))
        for i in range(face_num):
            node_id_lst=ele_table[i,:]
            num_pt=3
            k=node_id_lst[3]-1
            if (k>-2):
                num_pt=4
            for kk in range(num_pt):
                 ii=ele_table[i,kk]-1
                 x=node_x[ii]
                 y=node_y[ii]
                 
                 if (poly.contains(np.array([x,y]))):
                    # print "ele"+str(i)+" in "+pid
                     id_elem[i]=id_num
                     region_area=region_area+ele_area[i]
                     break
        dst.variables[pid][:]=id_elem
        print( "done "+pid+" area: %f"%(region_area*squaremetertoacre)+" acre")
        id_num=id_num+1
    dst.close() 
        
        
else:
    raise Exception(nc_file+"is invalid")
            

    
    
    



    




