# -*- coding: utf-8 -*-
"""

This script summarize low salinity zone ts from schism outputs

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

squaremetertoacre=0.000247105

ele_table=0
ele_area=0
node_x=0
node_y=0
node_num   = 0
face_num   = 0
time_num   = 0
lsz_area=[]

def gen_node_neibor_ele(mesh_node,max_node_in_a_cell,num_ele,num_node):
    num_ele_at_node=(np.zeros((num_node))).astype(int)
    for i in range(num_ele):
        for j in range(max_node_in_a_cell):
            if(mesh_node[i][j]>0):
                nodeid=mesh_node[i][j]-1
                num_ele_at_node[nodeid]=num_ele_at_node[nodeid]+1

    max_ele_at_node=int(np.max(num_ele_at_node))
    num_ele_at_node[:]=np.zeros((num_node)).astype(int)
    out_neibor_ele=np.empty((num_node,max_ele_at_node))
    out_neibor_ele[:,:]=np.nan
    for i in range(num_ele):
        for j in range(max_node_in_a_cell):
            if(mesh_node[i][j]>0):
                nodeid=mesh_node[i][j]-1
                loc=num_ele_at_node[nodeid]
                out_neibor_ele[nodeid,loc]=i
                num_ele_at_node[nodeid]=loc+1
    return out_neibor_ele,max_ele_at_node


def gen_node_wet_dry(node_wet_dry,ele_wet_dry,num_step,num_node,max_ele_at_node,el):
    
    for t in range(num_step):
        for i in range(num_node):
            all_dry=True
            for j in range(max_ele_at_node):

                if(not(np.isnan(el[i,j]))):
                    dry=ele_wet_dry[t,int(el[i,j])]
                    if(dry==0):
                        all_dry=False
                        break
            if(all_dry):
                node_wet_dry[t,i]=1
            else:
                node_wet_dry[t,i]=0
   

def face_aver(node_depth_average,node_num,face_num):
    a1=np.zeros((face_num))
    a2=np.zeros((face_num))
    a3=np.zeros((face_num))
    a4=np.zeros((face_num))
    id1=ele_table[:,0]-1
    id2=ele_table[:,1]-1
    id3=ele_table[:,2]-1
    id4=ele_table[:,3]-1
    a1=node_depth_average[id1]
    a2=node_depth_average[id2]
    a3=node_depth_average[id3]
    node_num=np.where(id4<0,3.0,4.0)
    a4=np.select([id4<0,id4>=0],[0.0,node_depth_average[id4]])
    face_val=(a1+a2+a3+a4)/node_num
    return face_val

def face_aver_inst(inst_node_depth_average,node_num,face_num):
    a1=np.zeros((face_num))
    a2=np.zeros((face_num))
    a3=np.zeros((face_num))
    a4=np.zeros((face_num))
    id1=ele_table[:,0]-1
    id2=ele_table[:,1]-1
    id3=ele_table[:,2]-1
    id4=ele_table[:,3]-1
    a1=inst_node_depth_average[:,id1]
    a2=inst_node_depth_average[:,id2]
    a3=inst_node_depth_average[:,id3]
    node_num=np.where(id4<0,3.0,4.0)
    a4=np.zeros(a3.shape)
    at=np.zeros((a3.shape[0]))
    for i in range(a3.shape[0]):
        at=inst_node_depth_average[i,:]
        a4[i,:]=np.select([id4<0,id4>=0],[0.0,at[id4]])
    face_val=(a1+a2+a3+a4)/node_num
    return face_val

def triangle_area(x1, y1, x2, y2, x3, y3):
    return abs(0.5*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2)))

def quad_area(x1, y1, x2, y2, x3, y3,x4,y4):
    a1=triangle_area(x1,y1,x2,y2,x4,y4)
    a2=triangle_area(x2,y2,x3,y3,x4,y4)
    return a1+a2

def fill_ele_area():
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
        if not(np.isfinite(i)):
            a=triangle_area(x1,y1,x2,y2,x3,y3)
            ele_area[k]=a
        else:
            
            x4=node_x[i]
            y4=node_y[i]
            a=quad_area(x1,y1,x2,y2,x3,y3,x4,y4)
            ele_area[k]=a

model_start=dtm.datetime(2021,4,20)

data_folder="./sample_nc/"
title="base"

big_salt=9999.0

average_period=[]
st=dtm.datetime(2021,6,11)
dt=dtm.timedelta(days=1)
et=dtm.datetime(2021,6,14)

st=dtm.datetime(2022,6,16)
dt=dtm.timedelta(days=1)
et=dtm.datetime(2022,6,18)

while (st<et):
    average_period.append(st)
    st=st+dt

elapse_time=[(d-model_start).total_seconds() for d in average_period]
k=0
start_date=average_period[k]
end_date=average_period[k+1]
    
start_day=(start_date-model_start).days+1
end_day=(end_date-model_start).days+1
    
nc_file=data_folder+"schout_%d.nc"%start_day
nc_file_510=data_folder+"out2d_%d.nc"%start_day
print(nc_file_510)
neibor_ele_table=0
max_ele_at_node=1
src=None
is_510_format=False
if(os.path.exists(nc_file)):
    src=netCDF4.Dataset(nc_file)
elif (os.path.exists(nc_file_510)):
    src=netCDF4.Dataset(nc_file_510)
    is_510_format=True
else:
    raise Exception("No valid output file exists\n")

node_dim  = src.dimensions["nSCHISM_hgrid_node"]
face_dim =  src.dimensions["nSCHISM_hgrid_face"]
node_num   = node_dim.size
face_num   = face_dim.size
ele_table  = np.empty((face_num,4))
ele_table  = src.variables["SCHISM_hgrid_face_nodes"][:,:]
time_dim  = src.dimensions["time"]
time_num=time_dim.size
ele_area=np.zeros((face_num))
node_x=np.empty((node_num))
node_y=np.empty((node_num))
node_x=src.variables["SCHISM_hgrid_node_x"][:]
node_y=src.variables["SCHISM_hgrid_node_y"][:]
fill_ele_area()
max_node_in_a_cell=4
neibor_ele_table,max_ele_at_node=gen_node_neibor_ele(ele_table,max_node_in_a_cell,face_num,node_num)

    
zone_file=["cache_mzm_link_points.txt","north_arc_points.txt","suisun_bay_points.txt","delta_points.txt","suisun_marsh_points.txt"]

subregion_path="./subregion_2021.nc"

sub_regions=netCDF4.Dataset(subregion_path)

zone_lst=[]
subregion_ele_lst=[]
subregion_ele_area=[]
for fname in zone_file:
    ii=fname.find("_points.txt")
    zone_id=fname[:ii]
    zone_lst.append(zone_id)
    val=sub_regions.variables[zone_id][:]
    ele_lst=np.sort(np.argwhere(val))
    subregion_ele_lst.append(ele_lst)
    sub_area=ele_area[ele_lst]
    subregion_ele_area.append(sub_area)
    
sub_regions.close()

print("done load subregion element list")



habitat="lsz"

s1=average_period[0]
s2=average_period[-1]
output_path=data_folder+"habitat_"+s1.strftime("%m-%d-%Y")+"_"+s2.strftime("%m-%d-%Y")+".nc"
dst=netCDF4.Dataset(output_path,'w',format="NETCDF4_CLASSIC")


time_frac_less_6=np.zeros((face_num)) 
    
for k in range(len(average_period)-1):
    
    start_date=average_period[k]
    end_date=average_period[k+1]
    
    start_day=(start_date-model_start).days+1
    end_day=(end_date-model_start).days+1
    
    
    salt_time_depth_average=0
    #time_frac_less_6=0
    wetdry_elem=0
    wetdry_node=0
    #surface_salt_time_average=0
    #bottom_salt_time_average=0
    
   
        #surface_salt_time_average=np.zeros((node_num))
        #bottom_salt_time_average=np.zeros((node_num))
        
    if(k==0):
        
        for name in src.ncattrs():
            dst.setncattr(name, src.getncattr(name))
        for name, dimension in src.dimensions.items():
            if not(name=="time"):
                dst.createDimension(name, len(dimension))
            else:
                dst.createDimension(name, len(elapse_time))
                
        var=dst.createVariable('time','f4',("time",))
        for att_name in src.variables['time'].ncattrs():
            if not(att_name[0]=="_"):
                var.setncattr(att_name,src.variables['time'].getncattr(att_name))
        var=dst.createVariable(habitat,'i2',("time","nSCHISM_hgrid_face",))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)
        var=dst.createVariable("wetdry_elem",'i2',("time","nSCHISM_hgrid_face",))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("average_salt",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("wetdry_node",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("time_frac_less_6",'f4',("nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)
        for name, variable in src.variables.items():
            if ( name in ["hvel_side","hvel","salt","wetdry_elem","wetdry_node","elev","zcor","time"]): ## below 5.10 format
                 print ( "skip var "+name)
            elif( name in ["dryFlagNode","dryFlagElement","dryFlagSide","elevation"]): ## 5.10 format id
                 print ("skip var "+name)
            else:
                dst.createVariable(name, variable.datatype, variable.dimensions)
                dst.variables[name][:] = src.variables[name][:]
                #print dst.variables[name].ncattrs()
                for att_name in src.variables[name].ncattrs():
                    if not(att_name[0]=="_"):
                        #print att_name
                        dst.variables[name].setncattr(att_name,src.variables[name].getncattr(att_name))
                
        src.close()
   
    salt_time_depth_average=np.zeros((node_num))
   
    wetdry_elem=np.zeros((face_num))
    wetdry_node=np.zeros((node_num))
        
    for i in range(start_day,end_day):
        nc_file=data_folder+"schout_%d.nc"%i
        out2d_file=""
        z_file=""
        if (is_510_format):
            nc_file=data_folder+"salinity_%d.nc"%i
            out2d_file=data_folder+"out2d_%d.nc"%i
            z_file=data_folder+"zCoordinates_%d.nc"%i
        if(os.path.exists(nc_file)):
            src=netCDF4.Dataset(nc_file)
            out2d_src=None
            z_src=None
            #depth_average_vel_file=output_path+"depth_average_vel_%d.nc"%i
            if(is_510_format):
                out2d_src=netCDF4.Dataset(out2d_file)
                z_src=netCDF4.Dataset(z_file)
                
            layer_dim = src.dimensions["nSCHISM_vgrid_layers"]
            time_dim  = src.dimensions["time"]
            node_dim  = src.dimensions["nSCHISM_hgrid_node"]
            two_dim   = src.dimensions["two"]       
            total_levels=layer_dim.size
            #node_bottom_level=src.variables["node_bottom_index"]
            #node_dry= np.array(src.variables["wetdry_node"])
            #elem_dry= np.array(src.variables["wetdry_elem"])
            node_num   = node_dim.size
            face_dim =  src.dimensions["nSCHISM_hgrid_face"]
            face_num   = face_dim.size
            num_step=time_dim.size
            node_dry=np.zeros((num_step,node_num)) 
            z=None
            salt=None
            if(is_510_format):
                node_bottom_level=out2d_src.variables["bottom_index_node"]
                elem_dry= np.array(out2d_src.variables["dryFlagElement"])
                node_dry= np.array(out2d_src.variables["dryFlagNode"])
                z=z_src.variables["zCoordinates"][:,:,:]
                salt=src.variables["salinity"][:,:,:,]
            else:
                node_bottom_level=src.variables["node_bottom_index"]
                elem_dry= np.array(src.variables["wetdry_elem"])
                gen_node_wet_dry(node_dry,elem_dry,num_step,node_num,max_ele_at_node,neibor_ele_table)
                z=src.variables["zcor"][:,:,:]
                salt=src.variables["salt"][:,:,:,]
            
            wetdry_node=wetdry_node+np.sum(node_dry,0)
            wetdry_elem=wetdry_elem+np.sum(elem_dry,0)
            mask=np.ones(z.shape,dtype=np.int8)
             
            for i in range(node_num):
               bottom=node_bottom_level[i]-1
               mask[:,i,bottom:]=0
             #pdb.set_trace()
            mask_with_dry=mask+node_dry[:,:,np.newaxis]
           
            #zmasked=ma.array(src.variables["zcor"][:,:,:],mask=mask_with_dry)
            zmasked=ma.array(z,mask=mask_with_dry)
            layer_thickness=np.diff(zmasked,axis=2)
            print (np.where(layer_thickness==0))
           
            salt_aver=0.5*(salt[:,:,1:]+salt[:,:,:-1])
            dry_nodes=np.where(wetdry_node>0)
            #pdb.set_trace()
            salt_aver[:,dry_nodes[0],:]=big_salt
            #
            depth_average=np.average(salt_aver[:,:,:],axis=2,weights=layer_thickness)
            ele_depth_average_inst=face_aver_inst(depth_average,node_num,face_num)
            less_than_6=np.where(ele_depth_average_inst<6.0,1.0,0.0)
            less_than_6_sum=np.sum(less_than_6,0)
            time_frac_less_6=time_frac_less_6+less_than_6_sum/(time_dim.size)/len(average_period)
            time_average=np.average(depth_average[:,:],axis=0)
            salt_time_depth_average=salt_time_depth_average+time_average/(end_day-start_day) 
            print ("done with ",nc_file)
            
            src.close()
    
    errarr=np.where(salt_time_depth_average>100) 

    
    face_salt_val=face_aver(salt_time_depth_average,node_num,face_num)
    dry_faces=np.where(wetdry_elem>0)
    face_salt_val[dry_faces[0]]=big_salt
    is_lsz=np.where(face_salt_val<6.0,1,0)
    this_lsz_area=np.dot(is_lsz,ele_area)
    total_lsz_area=np.sum(this_lsz_area)
    is_lsz2=np.where((face_salt_val<7.0)&(face_salt_val>6.0),2,0)
    this_lsz_area2=np.dot(is_lsz2,ele_area)
    total_lsz_area2=np.sum(this_lsz_area2)
    is_lsz=is_lsz+is_lsz2
    row_temp=[average_period[k].strftime("%Y-%m-%d")]

    for zone,ele_id,sub_area in zip(zone_lst,subregion_ele_lst,subregion_ele_area):

        region_salt_val=face_salt_val[ele_id]
        sub_is_lsz=np.where(region_salt_val<6.0,1,0)
        this_sub_lsz_area=np.dot(sub_is_lsz[:,0],sub_area[:,0])
        total_sub_lsz_area=np.sum(this_sub_lsz_area)
        sub_is_lsz2=np.where((region_salt_val<7.0)&(region_salt_val>6.0),1,0)
        this_sub_lsz_area2=np.dot(sub_is_lsz2[:,0],sub_area[:,0])
        total_sub_lsz_area2=np.sum(this_sub_lsz_area2)
        row_temp.append(total_sub_lsz_area*squaremetertoacre)
        row_temp.append((total_sub_lsz_area+total_sub_lsz_area2)*squaremetertoacre)
    row_temp.append(total_lsz_area*squaremetertoacre)
    row_temp.append((total_lsz_area+total_lsz_area2)*squaremetertoacre)
    lsz_area.append(row_temp)
    dst.variables[habitat][k,:] = is_lsz
    dst.variables["average_salt"][k,:]=salt_time_depth_average
    dst.variables["time_frac_less_6"][:]= time_frac_less_6
    node_wetdry_t=np.where(wetdry_node>0,1,0)
    elem_wetdry_t=np.where(wetdry_elem>0,1,0)
    dst.variables["wetdry_node"][k,:]= node_wetdry_t
    dst.variables["wetdry_elem"][k,:]= elem_wetdry_t
    dst.variables["time"][k]=elapse_time[k]
    
dst.close() 

col_id=['time']

for zone in zone_lst:
    col_id.append(zone+"(<6psu)")
    col_id.append(zone+"(<7psu)")
col_id.append('total_lsz_area1')
col_id.append('total_lsz_area2')

lsz_out_file=data_folder+"lsz_area.csv"

df=0

df=pd.DataFrame(lsz_area,columns=col_id)

df.to_csv(lsz_out_file)

ax=plt.gca()


for col in col_id[1:]:
    ax.plot(df['time'],df[col],label=title+"_"+col)


ax.grid('on')
ax.legend()

plt.show()
            
   
    
    




