# -*- coding: utf-8 -*-
"""
Extract station xyz from a x2 route UTM file. The resulting station file conforms to SCHISM
bp station format. Stations along bay route start from 65km from San Francisco and end at confluence,
Station along mzm start from 18km from Marinez end at confluence, Station along Sac starts from confluence
and end 25km upstream of sac river, Station along San Joaquin route starts from confluence and end 25km 
upstream of San Joaquin River. Their depth are defined as relativly to surface. ONLY surface or bottom
stations are available, surface station set elevation to 0 and bottom station set elevation to -10000.0.
station xyz are output as  Bay route, San Joaquin, Sac and MZM in order.

usage: --x2route x2route.csv 
output: x2 observation station xyz in SCHISM bp format
"""

import numpy as np
import datetime as dtm
import matplotlib.dates as mdates
import pandas as pd
import argparse



    
#plt.style.use(['seaborn-talk','seaborn-colorblind'])
parser = argparse.ArgumentParser()
parser.add_argument('--x2route', default=None,
                        help='X2 route in cvs format')

args = parser.parse_args()


x2_route_file=args.x2route
#x2_route_file="x2route.csv"


x2_route=pd.read_table(x2_route_file,sep=",")

if x2_route.empty:
    raise ValueError("no valid x2route.csv is given")


surface_x2_xyz=0
bottom_x2_xyz=0
westmost_bay_dist=65000
westmost_mzm_dist=18000
eastmost_sac_dist=25000
eastmost_sanjoaquin_dist=25000
bay_points=x2_route.loc[(x2_route['RID']=='bay')&(x2_route['MEAS']>westmost_bay_dist)]
mzm_points=x2_route.loc[(x2_route['RID']=='montezuma')&(x2_route['MEAS']>westmost_mzm_dist)]
sanjoaquin_points=x2_route.loc[(x2_route['RID']=='san_joaquin')&(x2_route['MEAS']<eastmost_sanjoaquin_dist)]
sac_points=x2_route.loc[(x2_route['RID']=='sacramento')&(x2_route['MEAS']<eastmost_sac_dist)]



bay_distance=bay_points.loc[:,"SHAPE_LENG"].values[0]
mzm_distance=mzm_points.loc[:,"SHAPE_LENG"].values[0]
sanjoaquin_distance=sanjoaquin_points.loc[:,"SHAPE_LENG"].values[0]
sac_distance=sac_points.loc[:,"SHAPE_LENG"].values[0]

bay_pt_every_200m=range(0,len(bay_points),200)
mzm_pt_every_500m=range(0,len(mzm_points),500)
sanjoaquin_pt_every_200m=range(0,len(sanjoaquin_points),200)
sac_pt_every_200m=range(0,len(sac_points),200)

len_bay_pt=len(bay_pt_every_200m)
len_mzm_pt=len(mzm_pt_every_500m)
len_sanjoaquin_pt=len(sanjoaquin_pt_every_200m)
len_sac_pt=len(sac_pt_every_200m)

surface_num_stations=len_bay_pt+len_mzm_pt+len_sanjoaquin_pt+len_sac_pt
bottom_num_stations=surface_num_stations


bay_pt_meas=bay_points.iloc[bay_pt_every_200m]['MEAS'].values
mzm_pt_meas=mzm_points.iloc[mzm_pt_every_500m]['MEAS'].values
sanjoaquin_pt_meas=sanjoaquin_points.iloc[sanjoaquin_pt_every_200m]['MEAS'].values
sac_pt_meas=sac_points.iloc[sac_pt_every_200m]['MEAS'].values

surface_out_frame=pd.concat([bay_points.iloc[bay_pt_every_200m],sanjoaquin_points.iloc[sanjoaquin_pt_every_200m],sac_points.iloc[sac_pt_every_200m],mzm_points.iloc[mzm_pt_every_500m]])

surface_out_frame["POINT_Z"]=0.0


bottom_out_frame=pd.concat([bay_points.iloc[bay_pt_every_200m],sanjoaquin_points.iloc[sanjoaquin_pt_every_200m],sac_points.iloc[sac_pt_every_200m],mzm_points.iloc[mzm_pt_every_500m]])

header=["POINT_X","POINT_Y","POINT_Z"]

#out_frame.to_csv('x2_surface_stations.bp',columns=header,sep=" ",header=False)
#print "total num of stations",len(out_frame)


bottom_out_frame.loc[:,"POINT_Z"]=-10000.0

x2_out_frame=pd.concat([surface_out_frame,bottom_out_frame])

new_id=range(1,2*len(surface_out_frame)+1)

x2_out_frame.index=new_id

x2_out_frame.to_csv('x2_stations.bp',columns=header,sep=" ",header=False)


