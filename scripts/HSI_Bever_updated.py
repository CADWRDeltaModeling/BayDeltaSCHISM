# -*- coding: utf-8 -*-
"""
This script computes Bever's suitability index using SCHISM output and 
interpolated temperature and turbidity
"""

import numpy as np
import os

import netCDF4
import datetime as dtm
from math import exp
from osgeo import ogr
import json
import pandas as pd
from zone_utils import *

ele_table=0
ele_area=0
node_x=0
node_y=0
node_num   = 0
face_num   = 0
time_num   = 0

def records(file):  
    # generator 
    reader = ogr.Open(file)
    layer = reader.GetLayer(0)
    for i in range(layer.GetFeatureCount()):
        feature = layer.GetFeature(i)
        yield json.loads(feature.ExportToJson())



########----------MODIFY
data_folder="..\\"
path_to_quantile_files = ".\\interpolated_temp_turbidity_day_182_330\\"
map_file_path = "mapped_dwr.txt"
output_folder = ".\\"

model_start=dtm.datetime(2017,4,18)
average_period=[]
st=dtm.datetime(2017,7,1)
dt=dtm.timedelta(days=1)
et=dtm.datetime(2017,8,1)


quantiles = ['05','25','50','75']
quantile_factors = [0.0,0.25,0.5,0.75,1.0]  #first zero is for if none of the temps fall below the threshold


##########-----READ TURBIDITY QUANTILE DATA ON COARSE GRID-----#############
turbidity_time_quantiles = []
turbidity_data_quantiles = []

for q in quantiles:
    turbidity_file="{0}/ln_turbidity_quantile_{1}_fit.csv".format(path_to_quantile_files,q)
    #read turbidity data
    t_file = open(turbidity_file)
    turb_file_data = t_file.readlines()
    t_file.close()
    
    turbidity_date=st
    turbidity_time=[]
    turbidity_data=[]
    for ii in range(len(turb_file_data)):
       turbidity_time.append(turbidity_date)
       turbidity_date=turbidity_date+dt  
       turbidity_data.append([exp(float(i)) for i in turb_file_data[ii].split(",")])
    
    turbidity_time_quantiles.append(turbidity_time)
    turbidity_data_quantiles.append(turbidity_data)


##########-----READ TEMPERATURE QUANTILE DATA ON COARSE GRID-----#############
temperature_time_quantiles = []
temperature_data_quantiles = []

for qq in quantiles:
    temp_file="{0}/temperature_quantile_{1}_fit.csv".format(path_to_quantile_files,qq)
    #read turbidity data
    t_file = open(temp_file)
    temp_file_data = t_file.readlines()
    t_file.close()
    
    temperature_date=st
    temperature_time=[]
    temperature_data=[]
    for ii in range(len(temp_file_data)):
       temperature_time.append(temperature_date)
       temperature_date=temperature_date+dt  
       temperature_data.append([float(i) for i in temp_file_data[ii].split(",")])
    
    temperature_time_quantiles.append(temperature_time)
    temperature_data_quantiles.append(temperature_data)



##########-----READ GRID MAPPING DATA-----#############
map_f = open(map_file_path)
map_data = map_f.readlines()
map_f.close()

numNdElNds = []
ndElIDs = []
ndElWghts = []

for i in range(len(map_data)):  #number of nodes in hgrid
    temp_data = map_data[i].split()
    n_nodes = int(temp_data[1])
    numNdElNds.append(n_nodes)  
    elNodes = []
    elWeights = []
    for j in range(n_nodes):
        elNodes.append(int(temp_data[2+j])-1)
        elWeights.append(float(temp_data[2+n_nodes+j]))
        
    ndElIDs.append(elNodes)
    ndElWghts.append(elWeights)

#########################################################

##########-----MAP DATA-----#############
print("Mapping grids")
turbdq = np.array(turbidity_data_quantiles)
tempdq = np.array(temperature_data_quantiles)

mappedTurbidity = []
mappedTemperature = []

for j in range(len(map_data)):
    mappedvalues = np.average(turbdq[:,:,ndElIDs[j]],axis=2,weights=ndElWghts[j])
    mappedTurbidity.append(mappedvalues)
    
    mappedvalues = np.average(tempdq[:,:,ndElIDs[j]],axis=2,weights=ndElWghts[j])
    mappedTemperature.append(mappedvalues)
print("Done Mapping")
        
##############STORING DATETIME FOR PERIOD################
while (st<=et):
    average_period.append(st)
    st=st+dt

elapse_time=[(d-model_start).total_seconds() for d in average_period]
k=0

start_date=average_period[k]
end_date=average_period[k+1]
    

##### 1. Get basic info from first nc file
start_day=(start_date-model_start).days+1
end_day=(end_date-model_start).days+1

nc_file=data_folder+"schout_%d.nc"%start_day
nc_file_510=data_folder+"out2d_%d.nc"%start_day

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
if is_510_format:
     fill_ele_area510(face_num,ele_table,node_x,node_y,ele_area)
else:
     fill_ele_area(face_num,ele_table,node_x,node_y,ele_area)
max_node_in_a_cell=4
neibor_ele_table,max_ele_at_node=gen_node_neibor_ele(ele_table,max_node_in_a_cell,face_num,node_num)


##### 2. Output path
s1=average_period[0]
s2=average_period[-1]
output_path=output_folder+"habitat_"+s1.strftime("%m-%d-%Y")+"_"+s2.strftime("%m-%d-%Y")+".nc"
dst=netCDF4.Dataset(output_path,'w',format="NETCDF4_CLASSIC")



##### 3. Perform calcs over period    
for k in range(len(average_period)-1):    
    start_date=average_period[k]
    end_date=average_period[k+1]
    print(start_date)
    
    start_day=(start_date-model_start).days+1
    end_day=(end_date-model_start).days+1
    
    
    salt_time_depth_average=0
    salt_time_frac_less_6=0

    wetdry_elem=0
    wetdry_node=0
    
    #Set variables, attributes for output file
    if(k==0):
        
        for name in src.ncattrs():
            dst.setncattr(name, src.getncattr(name))
        for name, dimension in src.dimensions.items():
            if not(name=="time"):
                dst.createDimension(name, len(dimension))
            else:
                dst.createDimension(name, len(elapse_time)-1)
                
        var=dst.createVariable('time','f4',("time",))
        for att_name in src.variables['time'].ncattrs():
            if not(att_name[0]=="_"):
                var.setncattr(att_name,src.variables['time'].getncattr(att_name))

        
        # Salt variables
        var=dst.createVariable('lsz','i2',("time","nSCHISM_hgrid_face",))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)  
        var=dst.createVariable("average_salt",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("average_salt_entire_period",'f4',("nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("salt_time_frac_less_6",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("salt_time_frac_less_6_entire_period",'f4',("nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        
        # Wetness variables
        var=dst.createVariable("wetdry_elem",'i2',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)   
        var=dst.createVariable("wetdry_node",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1)
        var=dst.createVariable("dry_elem_any_instant",'i2',("time","nSCHISM_hgrid_face")) 
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)
        var=dst.createVariable("dry_elem_any_instant_in_entire_period",'i2',("time","nSCHISM_hgrid_face")) 
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)

        # Temperature
        for l in quantiles:
            var=dst.createVariable("temperature_q{0}".format(l),'f4',("time","nSCHISM_hgrid_node"))
            var.setncattr("mesh","SCHISM_hgrid")
            var.setncattr("data_horizontal_center","node")
            var.setncattr("data_vertical_center","full")
            var.setncattr("i23d",1)
            var.setncattr("ivs",1)
            
            
        # Turbidity
        for l in quantiles:
            var=dst.createVariable("turbidity_q{0}".format(l),'f4',("time","nSCHISM_hgrid_node"))
            var.setncattr("mesh","SCHISM_hgrid")
            var.setncattr("data_horizontal_center","node")
            var.setncattr("data_vertical_center","full")
            var.setncattr("i23d",1)
            var.setncattr("ivs",1)       
 
                            
        # Speed     
        var=dst.createVariable("hvel_mag_max",'f4',("time","nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1) 
        
        var=dst.createVariable("hvel_mag_max_entire_period",'f4',("nSCHISM_hgrid_node"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","node")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",1)
        var.setncattr("ivs",1) 
        
        # --------------Suitability Indices----------------
        var=dst.createVariable("SI_Temp",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)    
        
        var=dst.createVariable("SI_Turb",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 

        var=dst.createVariable("SI_Speed",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1)
        
        var=dst.createVariable("SI_Salinity",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 
        
        var=dst.createVariable("HSI_B",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 
        
        var=dst.createVariable("HSI_B_entire_period",'f4',("nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 
        
        var=dst.createVariable("HSI_B_masked",'f4',("time","nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 
                   
        var=dst.createVariable("HSI_B_entire_period_masked",'f4',("nSCHISM_hgrid_face"))
        var.setncattr("mesh","SCHISM_hgrid")
        var.setncattr("data_horizontal_center","elem")
        var.setncattr("data_vertical_center","full")
        var.setncattr("i23d",4)
        var.setncattr("ivs",1) 
            
        #transfer over other variables from schout
        for name, variable in src.variables.items():
            if ( name in ["hvel_side","hvel","salt","wetdry_elem","wetdry_node","elev","zcor","time"]): ## below 5.10 format
                 print ( "skip var "+name)
            elif( name in ["dryFlagNode","dryFlagElement","dryFlagSide","elevation"]): ## 5.10 format id
                 print ("skip var "+name)
            else:
                dst.createVariable(name, variable.datatype, variable.dimensions)
                dst.variables[name][:] = src.variables[name][:]
                
                for att_name in src.variables[name].ncattrs():
                    if not(att_name[0]=="_"):
                        #print att_name
                        dst.variables[name].setncattr(att_name,src.variables[name].getncattr(att_name))
                
        src.close()
   
    
    #initialize arrays
    salt_time_depth_average=np.zeros((node_num))
    salt_time_frac_less_6=np.zeros((node_num))
    max_hvel = np.zeros((node_num))
                
    wetdry_elem=np.zeros((face_num))
    wetdry_node=np.zeros((node_num))        
    elementdryanyinstant=np.zeros((face_num))
    
    
    #Computation for daily metrics for salt and speed
    for i in range(start_day,end_day):
        nc_file=data_folder+"schout_%d.nc"%i
        out2d_file=""
        z_file=""
        hvelX_file=""
        hvelY_file=""
        if (is_510_format):
            nc_file=data_folder+"salinity_%d.nc"%i
            out2d_file=data_folder+"out2d_%d.nc"%i
            z_file=data_folder+"zCoordinates_%d.nc"%i
            hvelX_file=data_folder+"horizontalVelX_%d"%i
            hvelY_file=data_folder+"horizontalVelY_%d"%i
        if(os.path.exists(nc_file)):
            src=netCDF4.Dataset(nc_file)
            out2d_src=None
            z_src=None
            xvel_src=None
            yvel_src=None
            if(is_510_format):
                out2d_src=netCDF4.Dataset(out2d_file)
                z_src=netCDF4.Dataset(z_file)
                xvel_src=netCDF4.Dataset(hvelX_file)
                yvel_src=netCDF4.Dataset(hvelY_file)
            
            layer_dim = src.dimensions["nSCHISM_vgrid_layers"]
            time_dim  = src.dimensions["time"]
            node_dim  = src.dimensions["nSCHISM_hgrid_node"]
            two_dim   = src.dimensions["two"]       
            total_levels=layer_dim.size

            node_num   = node_dim.size
            face_dim =  src.dimensions["nSCHISM_hgrid_face"]
            face_num   = face_dim.size
            num_step=time_dim.size
            node_dry=np.zeros((num_step,node_num)) 
            z=None
            salt=None
            hvel0=None
            hvel1=None
            if(is_510_format):
                node_bottom_level=out2d_src.variables["bottom_index_node"]
                elem_dry= np.array(out2d_src.variables["dryFlagElement"])
                node_dry= np.array(out2d_src.variables["dryFlagNode"])
                z=z_src.variables["zCoordinates"][:,:,:]
                salt=src.variables["salinity"][:,:,:,]
                hvel0=xvel_src.variables["horizontalVelX"][:,:,:]
                hvel1=yvel_src.variables["horizontalVelY"][:,:,:]
            else:
                node_bottom_level=src.variables["node_bottom_index"]
                elem_dry= np.array(src.variables["wetdry_elem"])
                gen_node_wet_dry(node_dry,elem_dry,num_step,node_num,max_ele_at_node,neibor_ele_table)
                z=src.variables["zcor"][:,:,:]
                salt=src.variables["salt"][:,:,:,]
                hvel0=src.variables["hvel"][:,:,:,0]
                hvel1=src.variables["hvel"][:,:,:,1]  
                     
            
            eps=1.e-10
            dz=z[:,:,1:]-z[:,:,:-1]+eps              
                                
            #Salt Comps           
            salt_aver=0.5*(salt[:,:,1:]+salt[:,:,:-1])
            salt_depth_average=np.average(salt_aver[:,:,:],axis=2,weights=dz)            
            less_than_6=np.where(salt_depth_average<=6.0,1.0,0.0)
            less_than_6_sum=np.sum(less_than_6,0)
            salt_time_frac_less_6=salt_time_frac_less_6+less_than_6_sum/(time_dim.size)/(end_day-start_day)             
            salt_time_average=np.average(salt_depth_average[:,:],axis=0)                                                
            
            #wetting-drying elements
            elem_dry_frequency=np.mean(elem_dry,axis=0)            
            elementdryanyinstant=np.where(elem_dry_frequency>0.0,1,0)
           
            #horizontal velocity
      
            hvel_mag=np.hypot(hvel0,hvel1)
        
            hvel_aver=0.5*(hvel_mag[:,:,1:]+hvel_mag[:,:,:-1])
            hvel_depth_average=np.average(hvel_aver[:,:,:],axis=2,weights=dz)
            hvel_da_max=np.amax(hvel_depth_average,axis=0)              
            
            print ("done with ",nc_file)
            
            src.close()
    
    # Save daily data for time, salt and speed
    dst.variables["time"][k]=elapse_time[k]
    
    dst.variables["average_salt"][k,:]=salt_time_average    
    dst.variables["salt_time_frac_less_6"][k,:]= salt_time_frac_less_6
    
    dst.variables["dry_elem_any_instant"][k,:]=elementdryanyinstant
    
    dst.variables["hvel_mag_max"][k,:]=hvel_da_max
    
    
    # get daily interpolated turbidity data 
    date = dtm.datetime(start_date.year,start_date.month,start_date.day)
    
        
    ii = turbidity_time_quantiles[0].index(date) 
    for qq in range(len(quantiles)):
        nodeTurbData=[]
        nodeTempData=[]
        for j in range(node_num):
            nodeTurbData.append(mappedTurbidity[j][qq][ii])
            nodeTempData.append(mappedTemperature[j][qq][ii])
            
        dst.variables["turbidity_q{0}".format(quantiles[qq])][k,:]=nodeTurbData
        dst.variables["temperature_q{0}".format(quantiles[qq])][k,:]=nodeTempData
        
             

#salt fraction over entire period
salt_frac_dataset = dst.variables["salt_time_frac_less_6"][:,:]
dst.variables["salt_time_frac_less_6_entire_period"][:]=np.mean(salt_frac_dataset,axis=0)

#salt average over entire period
salt_avg_dataset = dst.variables["average_salt"][:,:]
dst.variables["average_salt_entire_period"][:]=np.mean(salt_avg_dataset,axis=0)
   
#wetness
deaip = dst.variables["dry_elem_any_instant"][:,:]
deaip_mean=np.mean(deaip,axis=0)
dst.variables["dry_elem_any_instant_in_entire_period"][:]=np.where(deaip_mean>0.0,1,0)

#peak current speed
hvel_dataset=dst.variables["hvel_mag_max"][:,:]
dst.variables["hvel_mag_max_entire_period"][:]=np.amax(hvel_dataset,axis=0)

#turbidity over period
turbidity_quantile_datasets=[]
for qq in quantiles:
    turbidity_dataset = dst.variables["turbidity_q{0}".format(qq)][:,:]
    turbidity_quantile_datasets.append(turbidity_dataset)
    
#temperature over period
temperature_quantile_datasets=[]
for qq in quantiles:
    temperature_dataset = dst.variables["temperature_q{0}".format(qq)][:,:]
    temperature_quantile_datasets.append(temperature_dataset)

#-----------HSI--------
print("Calculating Suitability Indices")
salt_frac_face=face_aver_inst(salt_frac_dataset,node_num,face_num,ele_table)

vel_face=face_aver_inst(hvel_dataset,node_num,face_num,ele_table)

#Temperature factors
tempface = face_aver_inst(temperature_quantile_datasets[0],node_num,face_num,ele_table)
level = np.where(tempface<24.0,1,0)
for qq in range(1,len(quantiles)):
    tempface = face_aver_inst(temperature_quantile_datasets[qq],node_num,face_num,ele_table)
    level += np.where(tempface<24.0,1,0)
    
temperature_face = np.select([level==0,level==1, level==2, level==3, level==4],quantile_factors)    
dst.variables["SI_Temp"][:,:] = temperature_face


#Turbidity factors
turbface_quantiles = []
turbface = face_aver_inst(turbidity_quantile_datasets[0],node_num,face_num,ele_table)
level = np.where(turbface>12.0,1,0)
turbface_quantiles.append(turbface)
for qq in range(1,len(quantiles)):
    turbface = face_aver_inst(turbidity_quantile_datasets[qq],node_num,face_num,ele_table)
    level += np.where(turbface>12.0,1,0)
    turbface_quantiles.append(turbface)
    
turbidity_face = np.select([level==0,level==1, level==2, level==3, level==4],quantile_factors)    
dst.variables["SI_Turb"][:,:] = turbidity_face

print("Calculating Current Speed Sc")
level = np.where(vel_face<0.5,0,1)
level += np.where(vel_face<0.71,0,1)
level += np.where(vel_face<0.82,0,1)
level += np.where(vel_face<0.89,0,1)
level += np.where(vel_face<1.02,0,1)
level += np.where(vel_face<1.1,0,1)

conditions = [level==0,level==1, level==2, level==3, level==4, level==5, level==6]
choices = [1.0, -0.4655*vel_face+1.233, -1.8608*vel_face+2.228, -3.0193*vel_face+3.179, -1.5059*vel_face+1.836, -2.4432*vel_face+2.792, -0.0859*vel_face+0.194]
V = np.select(conditions,choices)
V = np.where(V>1.0,1.0,V)
V = np.where(V<0.0,0.0,V)
dst.variables["SI_Speed"][:]=V


#Sc - Salinity
print("Calculating Salinity Sc")
level = np.where(salt_frac_face<0.195,0,1)
level += np.where(salt_frac_face<0.448,0,1)
level += np.where(salt_frac_face<0.723,0,1)
level += np.where(salt_frac_face<0.802,0,1)
level += np.where(salt_frac_face<0.839,0,1)
level += np.where(salt_frac_face<0.949,0,1)

conditions = [level==0,level==1, level==2, level==3, level==4, level==5, level==6]
choices = [0.1537*salt_frac_face+0.069, 0.7937*salt_frac_face-0.055, 0.7273*salt_frac_face-0.025, 2.5386*salt_frac_face-1.334, 5.3637*salt_frac_face-3.600, 0.8902*salt_frac_face+0.155, 1.0]
S = np.select(conditions,choices)
dst.variables["SI_Salinity"][:]=S


#--------Bever Based on Daily Data----------------
HSIB_1=0.67*salt_frac_face+0.33*vel_face
HSIB_2=HSIB_1*0.42

# estimate probability of being penalized for turbidity
probability_50_75 = (12.0-turbface_quantiles[2])/(turbface_quantiles[3]-turbface_quantiles[2])*0.25+0.5
probability_25_50 = (12.0-turbface_quantiles[1])/(turbface_quantiles[2]-turbface_quantiles[1])*0.25+0.25
probability_05_25 = (12.0-turbface_quantiles[0])/(turbface_quantiles[1]-turbface_quantiles[0])*0.20+0.05

#special cases
probability_75_100 = (12.0-turbface_quantiles[3])/(turbface_quantiles[3]-turbface_quantiles[2])*0.25+0.75
probability_00_05 = probability_50_75*0.0

probabilities = [probability_75_100,probability_50_75,probability_25_50,probability_05_25,probability_00_05]
prob_penalized = np.select([level==0,level==1, level==2, level==3, level==4],probabilities) 
prob_penalized = np.where(prob_penalized>1.0,1.0,prob_penalized) 
prob_penalized = np.where(prob_penalized<0.0,0.0,prob_penalized)
v2 = 0.25*HSIB_1+0.75*HSIB_2
v3 = 0.5*HSIB_1+0.5*HSIB_2
v4 = 0.75*HSIB_1+0.25*HSIB_2
v5 = 0.95*HSIB_1+0.05*HSIB_2

w1 = [HSIB_2, v2, v3, v4, v5]
w2 = [v2, v3, v4, v5,HSIB_1]

weighted = []
for i in range(len(w1)):
    weighted.append(0.5*(w1[i][:,:]+w2[i][:,:]))

#HSIB=np.select([level==0,level==1, level==2, level==3, level==4],weighted) 
#HSIB=HSIB*temperature_face
#HSIB_time_averaged=np.mean(HSIB,axis=0)

#weighted index
HSIB=prob_penalized*HSIB_2 + (1.0-prob_penalized)*HSIB_1
#Temperature adjustment and time-averaging
HSIB=HSIB*temperature_face
HSIB_time_averaged=np.mean(HSIB,axis=0)



dst.variables["HSI_B"][:,:]=HSIB
dst.variables["HSI_B_entire_period"][:]=HSIB_time_averaged

# do subregion weighted averging over the period

region_xy="region_pointsUTM.csv"
region_flag="subregion_hsi.nc"
sub_regions=netCDF4.Dataset(region_flag)

poly_xy_pd= pd.read_csv(region_xy,header = 0,sep=',')

zone_lst=poly_xy_pd.SUBREGION.unique()

subregion_ele_lst=[]
subregion_ele_area=[]
for zone_id in zone_lst:
    
    val=sub_regions.variables[zone_id][:]
    ele_lst=np.sort(np.argwhere(val))
    subregion_ele_lst.append(ele_lst)
    sub_area=ele_area[ele_lst]
    subregion_ele_area.append(sub_area)

sub_regions.close()
group_hsib={}
group_turb={}
group_temp={}

for zone,ele_id,sub_area in zip(zone_lst,subregion_ele_lst,subregion_ele_area):

    region_hsib_val=HSIB[:,ele_id]
    region_temp_val=temperature_face[:,ele_id]
    region_turb_val=turbidity_face[:,ele_id]
    this_sub_hsib_area_product=np.dot(region_hsib_val[:,:,0],sub_area[:,0])
    this_sub_temp_area_product=np.dot(region_temp_val[:,:,0],sub_area[:,0])
    this_sub_turb_area_product=np.dot(region_turb_val[:,:,0],sub_area[:,0])
    total_sub_area=np.sum(sub_area[:,0])
    
    area_weighted_hsib_average_this_region=this_sub_hsib_area_product/total_sub_area
    area_weighted_turb_average_this_region=this_sub_turb_area_product/total_sub_area
    area_weighted_temp_average_this_region=this_sub_temp_area_product/total_sub_area
    group_hsib[zone]=area_weighted_hsib_average_this_region
    group_turb[zone]=area_weighted_turb_average_this_region
    group_temp[zone]=area_weighted_temp_average_this_region
	
group_hsib["time"]=average_period[0:len(average_period)-1]
group_turb["time"]=average_period[0:len(average_period)-1]
group_temp["time"]=average_period[0:len(average_period)-1]


import pdb
pdb.set_trace()


lsz_out_file="hsib_area.csv"
df=pd.DataFrame(group_hsib)
df=df.set_index("time")
group_hsib_month_mean=df.resample("M").mean()
df.to_csv(lsz_out_file)

lsz_out_file="temp_area.csv"
df=pd.DataFrame(group_temp)
df=df.set_index("time")
group_temp_month_mean=df.resample("M").mean()
df.to_csv(lsz_out_file)

lsz_out_file="turb_area.csv"
df=pd.DataFrame(group_turb)
df=df.set_index("time")
group_turb_month_mean=df.resample("M").mean()
df.to_csv(lsz_out_file)











#-------------MASKING----------------
temp0  = np.ma.masked_where(deaip>0.0,HSIB)
temp1 = np.ma.masked_where(deaip_mean>0.0,HSIB_time_averaged)

HSIB_masked = temp0.filled(np.nan)
HSIB_time_averaged_masked = temp1.filled(np.nan)
dst.variables["HSI_B_masked"][:]=HSIB_masked
dst.variables["HSI_B_entire_period_masked"][:]=HSIB_time_averaged_masked

dst.close() 