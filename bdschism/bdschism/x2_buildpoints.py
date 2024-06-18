# -*- coding: utf-8 -*-
"""
Extract station xyz from a x2 route UTM file. The resulting station file
conforms to SCHISM bp station format. Stations along bay route start from
65km from San Francisco and end at confluence, Station along mzm start
from 18km from Marinez end at confluence, Station along Sac starts from
confluence and end 25km upstream of sac river, Station along San Joaquin
route starts from confluence and end 25km upstream of San Joaquin River.
Their depth are defined as relativly to surface. ONLY surface or bottom
stations are available, surface station set elevation to 0 and bottom
station set elevation to -10000.0. station xyz are output as  Bay route,
San Joaquin, Sac and MZM in order.
"""

import numpy as np
import pandas as pd
import argparse
import pdb

def create_arg_parser():
    """ Create an argument parser
        return: argparse.ArgumentParser
    """

    # Read in the input file
    parser = argparse.ArgumentParser(
        description="""
                       Convert X2 route dense point to SCHISM bp station format
                       with specified sampling interval.

                    Usage:
                     x2_buildpoints.py --x2route_sac x2route_bay_sac.csv 
                      --x2route_alt x2route_bay_nysjr.csv 
                      --interval 200 --minkm 30
                     """)
    parser.add_argument(
        '--x2route_sac',
        help='csv file of x2 station location and distance representing the bay-sac route')
    
    parser.add_argument(
        '--x2route_alt',
        help='csv file containing eastern continuation of route')
        
    parser.add_argument(
        '--route_id',
        help='id of the route on the east side, it should be one of \
        "sac","nysjr","sjr","mzm", where "sjr" means the broad slough route')

    parser.add_argument('--bpout', default=None, required=False,
                        help='x2 schism station out file. If none, inferred from the route inputs')

    parser.add_argument(
        '--interval',
        default=200,
        required=False,
        type=float,
        help="sampling distance along original x2 route")
    
    parser.add_argument('--minkm',
                        default=35.,
                        type=float,
                        help='minimum X2km position to consider in output, to west will be truncated')

    return parser


x2_route_descr = {"sac":"Sacramento","nysjr":"New York Slough to SJR","sjr":"SJR on Broad Slough","mzm":"Montezuma Slough"}


def x2_route2_bp(x2_route_file,interval,route_id=None,bpout=None,minkm=35):
    x2_route_all = pd.read_csv(x2_route_file, sep=",", 
                           header=0,comment="#",
                           usecols=["path","distance","x","y"],
                           dtype={"distance":float})
    
    x2_route = x2_route_all.loc[x2_route_all.path.isin(["bay","sac"])]
    
    if bpout is None:
        bpout = f"x2_bay_{route_id}.bp"
    
    if route_id != "sac":       
        alt_route = x2_route_all.loc[x2_route_all.path == route_id]
        if len(alt_route)==0:
            raise ValueError(f"route_id {route_id} not found in alt route path column")        
        alt_start = alt_route.distance.min()
        x2_route = x2_route.loc[x2_route.distance<alt_start,:]
        x2_route = pd.concat([x2_route,alt_route])

    x2_route = x2_route.set_index("distance",drop=False)
    
    x2_route.to_csv("debug.csv")
    new_index = np.arange(x2_route.distance.min(),
                          x2_route.distance.max(),
                          interval,dtype=float)
    x2_route = x2_route.drop("path",axis=1)
    x2_route=x2_route.reindex(x2_route.index.union(new_index)).interpolate().loc[new_index]

    print(x2_route.index)
    bottom_elev = -10000.0
    x2_route['z'] = bottom_elev
    x2_route = x2_route.loc[x2_route.distance >= minkm*1000.]   
    x2_route=x2_route.reset_index(drop=True)
    x2_route.index = x2_route.index + 1 # one-based index
 
    print(x2_route.head())

    with open(bpout,"w",newline="\n",) as bp:
        bp.write(f"point x y z distance  ! X2 transect on route {x2_route_descr[route_id]}\n")
        bp.write(f"{len(x2_route)}  ! Number of points\n")
        x2_route[["x","y","z","distance"]].to_csv(bp, header=False,
                                                   sep=" ", index=True,
                                                   float_format="%.1f")
    return x2_route



def main():
    """ Main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    x2_route2_bp(args.x2route_sac, args.interval, args.route_id,args.bpout, args.minkm)

def main_fixed():
    x2_route2_bp("x2route.csv",200,route_id="sac",bpout=None,minkm=35)

if __name__ == "__main__":
    main()
