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
                     extract_x2_station_xyz.py x2route.csv --out x2_stations.bp
                      --sampling_interval 200 --bay_min_distance 30000
                      --sac_max_distance 25000 --sjr_max_distance 25000
                     """)
    parser.add_argument(
        'x2route',
        help='csv file of x2 station location and distance')
    
    parser.add_argument(
        'route_id',
        help='id of the route on the east side, it should be one of \
        "sac","sjr" "mzm"')

    parser.add_argument('--out', default="x2_station.bp", required=False,
                        help='x2 schism station out file')

    parser.add_argument(
        '--sampling_interval',
        default=200,
        required=False,
        type=float,
        help="sampling distance along original x2 route for SCHISM output \
        stations in meter")

    parser.add_argument(
        '--bay_min_distance',
        default=30000.0,
        type=float,
        required=False,
        help='starting distance to sample station in the Bay measuring \
            from San Francisco in meter')

    parser.add_argument(
        '--east_max_distance',
        default=25000,
        type=float,
        required=False,
        help='end sampling distance distance to sample station in the \
            east side of X2 route measuring from the Confluence in meter')


    return parser


def x2_route2_bp(x2_route_file, out, sample_interval, bay_min_distance,rid,
                 max_distance):
    #x2_route_file = "x2route.csv"
    x2_route = pd.read_table(x2_route_file, sep=",", skiprows=1)
    bay_points_dist = x2_route.loc[(x2_route['path'] == 'bay')]["distance"]

    bay_route_length = np.max(bay_points_dist)
    bay_route_npt = len(bay_points_dist)
    print(f"original bay route nump points {bay_route_npt} and length {bay_route_length}")

    max_distance = max_distance+bay_route_length

    bay_points = x2_route.loc[(x2_route['path'] == 'bay') & (
        x2_route['distance'] > bay_min_distance)]

    east_route_points = x2_route.loc[(x2_route['path'] == rid) & (
        x2_route['distance'] < max_distance)]

    east_route_npt = len(east_route_points)
    print(f"original sjr route nump points {east_route_npt} and length {max_distance}")

    bay_pt_every_interval = range(0, len(bay_points), sample_interval)
    east_route_pt_every_interval = range(0, len(east_route_points), sample_interval)
    surface_out_frame = pd.concat([bay_points.iloc[bay_pt_every_interval],
                                  east_route_points.iloc[east_route_pt_every_interval]]
                                  )

    surface_elev = 0.0
    surface_out_frame["z"] = surface_elev

    bottom_out_frame = pd.concat([bay_points.iloc[bay_pt_every_interval],
                                 east_route_points.iloc[east_route_pt_every_interval]]
                                )

    header = ["x", "y", "z"]

    bottom_elev = -10000.0

    bottom_out_frame.loc[:, "z"] = bottom_elev

    x2_out_frame = pd.concat([surface_out_frame, bottom_out_frame])

    new_id = range(1, 2*len(surface_out_frame)+1)

    x2_out_frame.index = new_id
    print(x2_out_frame)
    print(f"writing to {out}")

    x2_out_frame.to_csv(out, columns=header, sep=" ", header=False)
    return x2_out_frame



def main():
    """ Main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    x2_route2_bp(args.x2route, args.out, args.sampling_interval,
                 args.bay_min_distance, args.route_id, args.east_max_distance)


if __name__ == "__main__":
    main()
