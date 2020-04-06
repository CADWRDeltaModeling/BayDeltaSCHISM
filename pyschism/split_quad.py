#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" PoC of quad splitting
"""


from . import schism_mesh
import copy
import numpy as np
import argparse
import os

import sys
if sys.version_info[0] < 3:
    import sets


__all__ = ['split_all_quads', ]

angle_e = np.array((np.pi / 3., np.pi * 2. / 3.))


def calculate_angle(a, b, ccw=True):
    """ Calculate an interior angle with two vectors

        Parameters
        ----------
        a, b: numpy.ndarry
            two vectors to calculate angle.
        ccw: bool, optional
            If true, it is assumed that a and b are created from nodes in the
            CCW ordering. Otherwise, CW.
        Returns
        -------
        float
            radian between 0 to 2 pi
    """
    numer = np.cross(a, b)
    denom = np.dot(a, b)
    if denom == 0:
        theta = np.pi * 0.5
    else:
        theta = np.arctan2(np.abs(numer), denom)
    if (ccw and numer > 0.) or (not ccw and numer < 0.):
        theta = 2. * np.pi - theta
    return theta


def calculate_internal_angles(nodes):
    """ Calculate internal angles of a polygon

        Parameters
        ----------
        nodes: array
            a list or array of node coordinates

        Returns
        -------
        Numpy array
            a list of internal angles in radian
    """
    angles = []
    for i in range(len(nodes)):
        node_a = nodes[i - 1]
        node_b = nodes[i]
        node_c = nodes[(i + 1) % len(nodes)]
        v_a = node_a[:2] - node_b[:2]
        v_b = node_c[:2] - node_b[:2]
        angle = calculate_angle(v_a, v_b)
        angles.append(angle)
    return np.array(angles)


def calculate_skewness(nodes):
    """ Calculate a skewness of an element with a list of nodes
        Skewness is defined by the ratio of the max interior angle divided
        by the min one.

        Parameters
        ----------
        nodes: array
            a list or array of node coordinates

        Returns
        -------
        float
            skewness of the given element
    """
    angles = calculate_internal_angles(nodes)
    if np.sum(angles) > (len(nodes) - 2) * np.pi + 1.e-5:
        return np.inf
    angle_min = np.min(angles)
    angle_max = np.max(angles)
    if angle_min == 0.:
        raise ValueError(
            'Minimum angle of a polygon is zero. Degenerate element.')
    return angle_max / angle_min


def split_quad(mesh, elems_to_split):
    """ Split given quad elements into two tri ones

        Parameters
        ----------
        mesh: SchismMesh
            a mesh with elements to split
        elems_to_split: sets
            a list of quadrilateral element indexes to split
    """
    split_index = [[[0, 1, 2], [0, 2, 3]], [[0, 1, 3], [1, 2, 3]]]  # CCW
    shape_ori = mesh._elems.shape
    mesh._elems.resize((shape_ori[0] + len(elems_to_split) * 2, shape_ori[1]))
    for i, elem_i in enumerate(elems_to_split):
        elem = np.array(mesh.elem(elem_i), dtype=int)
        if len(elem) != 4:
            raise ValueError('split_quad requires quad elements')
        skew = []
        for index1, index2 in split_index:
            re = np.max((calculate_skewness(mesh.nodes[elem[index1]]),
                         calculate_skewness(mesh.nodes[elem[index2]])))
            skew.append(re)
        for j, index in enumerate(split_index[np.argmin(np.array(skew))]):
            mesh._elems[shape_ori[0] + i * 2 +
                        j] = np.append(elem[index], np.iinfo(np.int32).min)
    for elem_i in elems_to_split:
        mesh.mark_elem_deleted(elem_i)
    mesh.renumber()


def split_all_quads(mesh):
    """
    Split all quad elements into triangular ones and return a new triangular
    mesh. This function maintains the original node indices.
    Currently this function does not add boundary information to the new mesh.

    Parameters
    ----------
    mesh: SchismMesh
        a mesh with elements to split

    Returns
    -------
    SchismMesh
        A new triangular mesh.
        It does not contain any extra information, e.g. boundary information.
    """
    tri = schism_mesh.SchismMesh()
    n_nodes = mesh.n_nodes()
    mask_elem_i_quad = (mesh._elems[:, 3] >= 0)
    tri.allocate(mesh.n_elems() + np.sum(mask_elem_i_quad), n_nodes)
    tri._nodes[:] = mesh._nodes
    split_index = [[[0, 1, 2], [0, 2, 3]], [[0, 1, 3], [1, 2, 3]]]  # CCW
    shape_ori = mesh._elems.shape

    j = shape_ori[0]
    for i, quad in enumerate(mask_elem_i_quad):
        if quad:
            skew = []
            elem = mesh._elems[i]
            for index1, index2 in split_index:
                re = np.max((calculate_skewness(mesh.nodes[elem[index1]]),
                             calculate_skewness(mesh.nodes[elem[index2]])))
                skew.append(re)
            index = split_index[np.argmin(np.array(skew))]
            tri._elems[i][:3] = elem[index[0]]
            tri._elems[j][:3] = elem[index[1]]
            j += 1
        else:
            tri._elems[i] = mesh._elems[i]
    return tri


def write_prop(elems_to_split, n_elems, fpath):
    """ Write a prop file with flags that show which elements are split
        in the input mesh
    """
    prop = np.zeros(n_elems)
    prop[list(elems_to_split)] = 1
    np.savetxt(fpath, np.hstack(((np.arange(n_elems) + 1).reshape(-1, 1),
                                 prop.reshape(-1, 1))),
               fmt='%d %d')


def create_arg_parser():
    """ Create an argument parser

        Returns
        -------
        argparse.ArgumentParser
    """
    description = "Split quadrilateral elements that have higher skewness " \
        "value than the given skewness into triangular elements."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('meshinput', type=str,
                        help="Mesh input file to process in GR3 format.")
    parser.add_argument('meshoutput', type=str,
                        help="Output mesh file name in GR3 format.")
    parser.add_argument('--skewness', dest='skewness', type=float,
                        help="Maximum skewness (not normalized.) to split. "
                        "If the skewness of an element is bigger than this, "
                        "the element will be split.")
    parser.add_argument('--minangle', dest='minangle', type=float,
                        help="Minimum angle to keep in quads. If any of "
                        "internal angles of a quad is smaller than mingangle, "
                        "the quad will be split.")
    parser.add_argument('--maxangle', dest='maxangle', type=float,
                        help="Minimum angle to keep in quads. If any of "
                        "internal angles of a quad is larger than maxgangle, "
                        "the quad will be split.")
    # parser.add_argument('--region_to_split', dest='polygon_split',
    #                     type=str,
    #                     help="Area to split quads")
    parser.add_argument('--prop', dest='prop', type=str,
                        help="Write a prop file that shows elements that are split")
    return parser


def main():
    """ main function for CLI
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    fpath_mesh_in = args.meshinput
    if not os.path.exists(fpath_mesh_in):
        raise ValueError('The given input file not found')
    fpath_mesh_out = args.meshoutput
    skewness = args.skewness
    if skewness is not None:
        if skewness < 0.:
            raise ValueError('Skewness must be bigger than zero')
    minangle = args.minangle
    maxangle = args.maxangle
    if minangle is not None:
        minangle = np.pi * minangle / 180.
    if maxangle is not None:
        maxangle = np.pi * maxangle / 180.
    if skewness is None and minangle is None and maxangle is None:
        raise ValueError('No splitting criteria are given')

    mesh = schism_mesh.read_mesh(fpath_mesh_in)
    if sys.version_info[0] < 3:
        elems_to_split = sets.Set()
    else:
        elems_to_split = set()
    n_elems_ori = mesh.n_elems()
    if skewness is not None:
        for elem_i, elem in enumerate(mesh.elems):
            if len(elem) == 4:
                # split
                skew = calculate_skewness(mesh.nodes[elem])
                if skew > skewness:
                    # split
                    elems_to_split.add(elem_i)
    if minangle is not None or maxangle is not None:
        for elem_i, elem in enumerate(mesh.elems):
            if len(elem) == 4:
                angles = calculate_internal_angles(mesh.nodes[elem])
                if minangle is not None:
                    angle_min = angles.min()
                    if angle_min < minangle:
                        elems_to_split.add(elem_i)
                if maxangle is not None:
                    angle_max = angles.max()
                    if angle_max > maxangle:
                        elems_to_split.add(elem_i)

    print("Found %d quad element(s) to spilt." % len(elems_to_split))

    if len(elems_to_split) < 1:
        print("No element to split.")
        return

    print("Start splitting...")
    split_quad(mesh, elems_to_split)
    print("Writing output file...")
    schism_mesh.write_mesh(mesh, fpath_mesh_out)
    if args.prop is not None:
        fpath_prop = args.prop
        write_prop(elems_to_split, n_elems_ori, fpath_prop)
    print("Done.")


if __name__ == '__main__':
    main()
