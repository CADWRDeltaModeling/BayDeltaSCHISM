# -*- coding: utf-8 -*-
"""

This script read station x y from x2route.csv which is also used by
extract_x2_station_xyz.py to create x2_stations.bp. It need the fort.18
resulting from SCHISM read_output9_xyz to extract salinity on X2 stations.
It search along x2 stations along the Bay,MZM,Sac, and San Joaquin to
find two neiboring stations higher and lower than X2 criteria
(bottom or surface). A simple linear interpolation is done to get a exact
x2 location. If X2 retreat less than 65km from San Francisco, result will
be truncated at 65km.


usage: --start 2004-04-18 --x2route x2route.csv
output: x2 on surface and bottom location time series in csv format,
        bottom_x2.csv and surface_x2.csv

"""

import numpy as np
import argparse
# import matplotlib.pylab as plt

import datetime as dtm
# import matplotlib.dates as mdates

import pandas as pd
from dateutil.parser import parse

westmost_bay_dist = 65000
westmost_mzm_dist = 18000
eastmost_sac_dist = 25000
eastmost_sanjoaquin_dist = 25000


def interpolate_x2(ts_len, salt, x2_criteria):

    x2_dist = []
    x2_dist_sac = []
    x2_dist_sanjoaquin = []

    for i in range(0, ts_len):

        bay_salt = salt[i, 0:len_bay_pt]
        sanjoaquin_salt = salt[i, len_bay_pt:len_bay_pt + len_sanjoaquin_pt]
        sac_salt = salt[i, len_bay_pt + len_sanjoaquin_pt:len_bay_pt +
                   len_sanjoaquin_pt + len_sac_pt]
        mzm_salt = salt[i, len_bay_pt + len_sanjoaquin_pt +
                   len_sac_pt:len_bay_pt + len_sanjoaquin_pt +
                   len_sac_pt + len_mzm_pt]
        # search in bay stations first
        k = len(bay_salt) - np.searchsorted(bay_salt[::-1], x2_criteria)
        x2_loc = []
        if ((k > 0) and (k < len_bay_pt)):
            # then x2 in bay and mzm
            s1 = bay_salt[k - 1]
            s2 = bay_salt[k]
            d1 = bay_pt_meas[k - 1]
            d2 = bay_pt_meas[k]
            dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)

            x2_loc.append(dx2)
            x2_dist_sac.append(dx2)
            x2_dist_sanjoaquin.append(dx2)
            j = len(mzm_salt) - np.searchsorted(mzm_salt[::-1], x2_criteria)
            if ((j > 0) and (j < len_mzm_pt)):
                s1 = mzm_salt[j - 1]
                s2 = mzm_salt[j]
                d1 = mzm_pt_meas[j - 1]
                d2 = mzm_pt_meas[j]
                dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)
                x2_loc.append(dx2)
            else:
                x2_loc.append(mzm_distance)
            x2_loc.append(0.0)
            x2_loc.append(0.0)
        elif (k == 0):
            dx2 = westmost_bay_dist
            x2_loc.append(dx2)
            x2_dist_sac.append(dx2)
            x2_dist_sanjoaquin.append(dx2)
        else:
            # then x2 should in sac, sanjoaquin
            i1 = len(sanjoaquin_salt) - np.searchsorted(sanjoaquin_salt[::-1],
                                                        x2_criteria)
            x2_loc.append(0.0)
            x2_loc.append(0.0)

            if (i1 > 0):
                if (i1 == len(sanjoaquin_salt)):
                    # truncate for the limited extended of obs stations
                    dx2 = eastmost_sanjoaquin_dist
                    print("warning: sanjoaquin x2 truncated at:" +
                          str(dx2 + bay_distance))
                else:
                    s1 = sanjoaquin_salt[i1 - 1]
                    s2 = sanjoaquin_salt[i1]
                    d1 = sanjoaquin_pt_meas[i1 - 1]
                    d2 = sanjoaquin_pt_meas[i1]
                    dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)
            else:
                s1 = bay_salt[-1]
                s2 = sanjoaquin_salt[0]
                d1 = 0
                d2 = sanjoaquin_pt_meas[0]
                dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)

            x2_dist_sanjoaquin.append(dx2 + bay_distance)
            x2_loc.append(dx2 + bay_distance)

            i2 = len(sac_salt) - np.searchsorted(sac_salt[::-1], x2_criteria)
            if (i2 > 0):
                if (i2 == len(sac_salt)):
                    # truncate for the limited extended of obs stations
                    dx2 = eastmost_sac_dist
                    print("warning: sac x2 truncated at:" +
                          str(dx2 + bay_distance))
                else:
                    s1 = sac_salt[i2 - 1]
                    s2 = sac_salt[i2]
                    d1 = sac_pt_meas[i2 - 1]
                    d2 = sac_pt_meas[i2]
                    dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)
            else:
                s1 = bay_salt[-1]
                s2 = sac_salt[0]
                d1 = 0
                d2 = sac_pt_meas[0]
                dx2 = d1 + (x2_criteria - s1) * (d2 - d1) / (s2 - s1)

            x2_loc.append(dx2 + bay_distance)
            x2_dist_sac.append(dx2 + bay_distance)

        x2_dist.append(x2_loc)
        # print "step ",i

    return np.divide(x2_dist_sac, 1000.0), np.divide(x2_dist_sanjoaquin,
                                                     1000.0)


# plt.style.use(['seaborn-talk','seaborn-colorblind'])

parser = argparse.ArgumentParser()
parser.add_argument('--start', default=None,
                    help='model start datetime')
parser.add_argument('--x2route', default=None,
                    help='X2 route in cvs format')

args = parser.parse_args()
st = args.start
model_start = parse(st)

x2_route_file = args.x2route
# x2_route_file="x2route.csv"
x2_route = pd.read_table(x2_route_file, sep=",")
surface_x2_xyz = 0
bottom_x2_xyz = 0

bay_points = x2_route.loc[(x2_route['RID'] == 'bay') & (x2_route['MEAS']
                                                        > westmost_bay_dist)]
mzm_points = x2_route.loc[(x2_route['RID'] == 'montezuma') & (x2_route['MEAS']
                                                        > westmost_mzm_dist)]
sanjoaquin_points = x2_route.loc[(x2_route['RID'] == 'san_joaquin')
                            & (x2_route['MEAS'] < eastmost_sanjoaquin_dist)]
sac_points = x2_route.loc[(x2_route['RID'] == 'sacramento') &
                           (x2_route['MEAS'] < eastmost_sac_dist)]


bay_distance = bay_points.loc[:, "SHAPE_LENG"].values[0]
mzm_distance = mzm_points.loc[:, "SHAPE_LENG"].values[0]
sanjoaquin_distance = sanjoaquin_points.loc[:, "SHAPE_LENG"].values[0]
sac_distance = sac_points.loc[:, "SHAPE_LENG"].values[0]

bay_pt_every_200m = range(0, len(bay_points), 200)
mzm_pt_every_500m = range(0, len(mzm_points), 500)
sanjoaquin_pt_every_200m = range(0, len(sanjoaquin_points), 200)
sac_pt_every_200m = range(0, len(sac_points), 200)

len_bay_pt = len(bay_pt_every_200m)
len_mzm_pt = len(mzm_pt_every_500m)
len_sanjoaquin_pt = len(sanjoaquin_pt_every_200m)
len_sac_pt = len(sac_pt_every_200m)

surface_num_stations = len_bay_pt + len_mzm_pt + len_sanjoaquin_pt + len_sac_pt
bottom_num_stations = surface_num_stations


bay_pt_meas = bay_points.iloc[bay_pt_every_200m]['MEAS'].values
mzm_pt_meas = mzm_points.iloc[mzm_pt_every_500m]['MEAS'].values
sanjoaquin_pt_meas = sanjoaquin_points.iloc[sanjoaquin_pt_every_200m]
['MEAS'].values
sac_pt_meas = sac_points.iloc[sac_pt_every_200m]['MEAS'].values


surface_x2_criteria = 1.36
bottom_x2_criteria = 2.00


salt_out = "fort.18"
ts_out = pd.read_csv(salt_out, sep="\s+", header=None)

if ts_out.empty:
    raise ValueError("SCHISM salt output file fort.18 is not valid")

ts_times = ts_out.iloc[:, 0]
ts_dtime = [model_start + dtm.timedelta(days=dt) for dt in ts_times]


surface_salt = ts_out.iloc[:, 1:surface_num_stations + 1].values
surface_x2_out_f = "surface_x2.csv"
x2_out_dic = {}
x2_out_dic['time'] = ts_dtime

x2_dist_sac, x2_dist_sanjoaquin = interpolate_x2(len(ts_dtime), surface_salt,
                                                 surface_x2_criteria)

x2_out_dic['x2_sac'] = x2_dist_sac
x2_out_dic['x2_sanjoaquin'] = x2_dist_sanjoaquin
x2_data = pd.DataFrame(data=x2_out_dic)
x2_data.to_csv(surface_x2_out_f)

bottom_salt = ts_out.iloc[:, surface_num_stations +
              1:surface_num_stations + bottom_num_stations + 1].values
bottom_x2_out_f = "bottom_x2.csv"
x2_out_dic = {}
x2_out_dic['time'] = ts_dtime

x2_dist_sac, x2_dist_sanjoaquin = interpolate_x2(len(ts_dtime),
                                 bottom_salt, bottom_x2_criteria)
x2_out_dic['x2_sac'] = x2_dist_sac
x2_out_dic['x2_sanjoaquin'] = x2_dist_sanjoaquin
x2_data = pd.DataFrame(data=x2_out_dic)
x2_data.to_csv(bottom_x2_out_f)
