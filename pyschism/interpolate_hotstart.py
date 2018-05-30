#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" Script to interpolate SCHISM hotstart.in from one grid to another
"""
from __future__ import print_function
from schism_mesh import read_mesh
from schism_hotstart import read_hotstart, SchismHotstart
from scipy.interpolate import griddata
import numpy as np
import argparse


def create_arg_parser():
    """ Create an ArgumentParser for hotstart interpolator
    """
    import schism_yaml
    parser = schism_yaml.ArgumentParserYaml()
    parser.add_argument('--hgrid_in', required=True,
                        help="Horizontal grid of the base case")
    parser.add_argument('--vgrid_in', required=True,
                        help="Vertical grid of the base case")
    parser.add_argument('--hotstart_in', required=True,
                        help="hotstart.in of the base case")
    parser.add_argument('--hgrid_out', required=True,
                        help="Horizontal grid of the target case")
    parser.add_argument('--vgrid_out', required=True,
                        help="Vertical grid of the target case")
    parser.add_argument('--hotstart_out', required=True,
                        help="hotstart.in of the target case")
    return parser


def interpolate_hotstart(mesh_in, hotstart_in, mesh_out):
    hotstart_out = SchismHotstart(mesh_out)
    hotstart_out.time = hotstart_in.time
    hotstart_out.nodes_elev = griddata(
        mesh_in.nodes[:, :2], hotstart_in.nodes_elev, mesh_out.nodes[:, :2])
    hotstart_out.nodes_dry = griddata(
        mesh_in.nodes[:, :2], hotstart_in.nodes_dry, mesh_out.nodes[:, :2])
    points_base = mesh_in.get_coordinates_3d()
    values_base = hotstart_in.nodes
    points_target = mesh_out.get_coordinates_3d()
    for i in range(hotstart_in.n_tracers * 2 + 7):
        values_target = griddata(points_base, values_base[
                                 :, :, i].flatten(), points_target)
        hotstart_out.nodes[:, :, i] = values_target.reshape(
            (mesh_out.n_nodes(), mesh_out.n_vert_levels))
    hotstart_out.calculate_side_values_from_nodes()
    hotstart_out.elems_dry = griddata(mesh_in.get_centers_of_elements(),
                                      hotstart_in.elems_dry,
                                      mesh_out.get_centers_of_elements())
    hotstart_out.calculate_elem_values_from_nodes()
    return hotstart_out


def interpolate_hotstart_w_args(args):
    """ Interpolate hotstart.in with the given arguments
    """
    mesh_in = read_mesh(args.hgrid_in, args.vgrid_in)
    hotstart_in = read_hotstart(mesh_in)
    mesh_out = read_mesh(args.hgrid_out, args.vgrid_out)
    return interpolate_hotstart(mesh_in, hotstart_in, mesh_out)


def main():
    """ Main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()

    interpolate_hotstart_w_args(args)

if __name__ == '__main__':
    main()
