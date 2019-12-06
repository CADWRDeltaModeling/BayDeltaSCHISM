#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Create a mesh file with the number of vertical levels as nodal value
"""
from schism_mesh import read_mesh, write_mesh
import numpy as np


def create_arg_parser():
    """ Create an argument parser
    """
    import argparse
    description = ("Create a mesh file with the number of vertical levels",
                   " as nodal values ")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--hgrid', default='hgrid.gr3',
                        help="Horizontal grid name")
    parser.add_argument('--vgrid', default='vgrid.in',
                        help="Vertical grid file name")
    parser.add_argument('--output', default='n_levels.gr3',
                        help="Output file name")
    return parser


def main():
    """ Just a main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    mesh = read_mesh(args.hgrid, args.vgrid)
    print(mesh.vmesh.n_vert_levels())
    n_levels = mesh.vmesh.n_vert_levels() - np.array(mesh.vmesh.kbps)
    write_mesh(mesh, args.output, node_attr=n_levels)


if __name__ == '__main__':
    main()
