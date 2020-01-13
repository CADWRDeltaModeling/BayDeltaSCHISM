# -*- coding: utf-8 -*-
""" Hotstart.in memory model
"""

from struct import unpack, calcsize
import numpy as np
import os

__all__ = ['read_hotstart']


class SchismHotstart(object):
    """ Memory model of hotstart.in
        The immediate purpose of the memory model is
        containing one-to-one correspondence to the file model of
        hotstart.in in memory. This is not an efficient way to manage data
        but the best way to compare and manage the file model of
        hotstart.in.

        NOTE: No ICM, SED, HA Support yet
    """

    def __init__(self, mesh, n_tracers=2):
        self._mesh = mesh
        self.elems_dry = None
        self._elems = None
        self.sides_dry = None
        self._sides = None
        self._nodes_dry = None
        self.nodes_elev = None
        self._nodes = None
        self.time = None
        self.step = None
        self.n_tracers = n_tracers
        self.allocate()

    def allocate(self):
        """ Allocate memory
        """
        mesh = self._mesh
        vmesh = self._mesh.vmesh
        n_vert_levels = vmesh.n_vert_levels()
        if n_vert_levels < 1:
            raise ValueError(
                "The number of vertical layer must be larger than one.")
        n_elems = mesh.n_elems()
        self.elems_dry = np.empty((n_elems, ), dtype=int)
        # v & tracers. The maximum of the second index is bigger by one than
        # what is necessary. The first layer value is a dummy, which is
        # the same as the second. It is a hotstart convention.
        self._elems = np.empty((n_elems, n_vert_levels, 1 + self.n_tracers))
        n_edges = mesh.n_edges()
        self.sides_dry = np.empty((n_edges, ), dtype=int)
        # u, v and temp and salt
        self._sides = np.empty((n_edges, n_vert_levels, 4))
        n_nodes = mesh.n_nodes()
        # node: idx, eta, 0, (temp, salt, temp, salt, 0. * 7) * n_vert_levels
        self.nodes_dry = np.empty((n_nodes, ), dtype=int)
        self.nodes_elev = np.empty((n_nodes, ))
        self._nodes = np.empty(
            (n_nodes, n_vert_levels, 7 + 2 * self.n_tracers))

    def __eq__(self, other):
        """ Compare with equal operator
            This does not compare mesh or step.
        """
        return (self.time == other.time and
                np.allclose(self.elems_dry, other.elems_dry) and
                np.allclose(self._elems, other.elems, atol=1e-100) and
                np.allclose(self.sides_dry, other.sides_dry, atol=1e-100) and
                np.allclose(self._sides, other.sides, atol=1e-100) and
                np.allclose(self.nodes_dry, other.nodes_dry, atol=1e-100) and
                np.allclose(self.nodes_elev, other.nodes_elev, atol=1e-100) and
                np.allclose(self._nodes, other.nodes, atol=1e-100))

    @property
    def nodes(self):
        """ Get the node data array

            Returns
            -------
            numpy.ndarray
                Array of node values.
                The shape of the array is (n_nodes, n_vert_layers, n_tracers)
        """
        return self._nodes

    @property
    def sides(self):
        """ Get the node data array

            Returns
            -------
            numpy.ndarray
                Array of side values.
                The shape of the array is (n_nodes, n_vert_layers, n_tracers)
        """
        return self._sides

    @property
    def elems(self):
        """ Get the node data array

            Returns
            -------
            numpy.ndarray
                Array of element values.
                The shape of the array is (n_nodes, n_vert_layers, n_tracers)
        """

        return self._elems

    def calculate_side_values_from_nodes(self):
        """ Calculate side values from nodes values simply taking the average
        """
        for i, edge in enumerate(self._mesh.edges):
            # Tracers
            self._sides[i, :, 2:] = np.mean(
                self._nodes[edge[:2]][:, :, 2:self.n_tracers + 2], axis=0)

    def calculate_elem_values_from_nodes(self):
        """ Calculate side values from nodes values simply taking the average
        """
        for i, elem in enumerate(self._mesh.elems):
            for j in range(self._mesh.n_vert_levels - 1):
                self._elems[i, j + 1:, 1:] = np.mean(
                    np.mean(self._nodes[elem, j:j + 2, :2], axis=0), axis=0)
            self._elems[i, 0] = self._elems[i, 1]


class SchismHotstartReader(object):
    """ Reader to read in hotstart.in
    """
    SIZE_HEAD = 24

    def __init__(self):
        self.fpath = None
        self.hotstart = None

    def read(self, mesh, fpath='hotstart.in', n_tracers=2):
        """ Read hotstart.in

            Parameters
            ----------
            mesh: SchismMesh
                SCHISM mesh

            Returns
            -------
            SchismHotstart
        """
        if not os.path.exists(fpath):
            raise ValueError('Cannot find the hotstart file')
        self.n_tracers = n_tracers
        self.mesh = mesh
        self.n_vert_levels = mesh.vmesh.n_vert_levels()
        self.fpath = fpath
        self.format_elem_block()
        self.size_elem_block = calcsize(self.fmt_elem_block)
        self.format_side_block()
        self.size_side_block = calcsize(self.fmt_side_block)
        self.format_node_block()
        self.size_node_block = calcsize(self.fmt_node_block)
        self.hotstart = SchismHotstart(mesh, n_tracers)
        self.read_header()
        self.read_whole_elem_block()
        self.read_whole_side_block()
        self.read_whole_node_block()
        return self.hotstart

    def format_elem_block(self):
        fmt = '=3i'
        fmt += '{:d}d'.format(1 + self.n_tracers) * self.n_vert_levels
        fmt += 'i'
        self.fmt_elem_block = fmt

    def format_side_block(self):
        fmt = '=3i'
        fmt += '4d' * self.n_vert_levels
        fmt += 'i'
        self.fmt_side_block = fmt

    def format_node_block(self):
        fmt = '=2idi'
        # 2 * n_tracers and others like q2, xl, dfv, dfh, dfq1, dfq2, qnon
        fmt += '{:d}d'.format(2 * self.n_tracers + 7) * self.n_vert_levels
        fmt += 'i'
        self.fmt_node_block = fmt

    def read_header(self):
        with open(self.fpath, 'rb') as f:
            fmt = '=idiii'
            data = unpack(fmt, f.read(calcsize(fmt)))
            self.hotstart.time = data[1]
            self.hotstart.step = data[2]
            self.hotstart.stack = data[3]

    def seek_elem(self, fh, i=0):
        cursor = self.SIZE_HEAD + self.size_elem_block * i
        fh.seek(cursor)

    def seek_side(self, fh, i=0):
        cursor = self.SIZE_HEAD + self.size_elem_block * \
            self.mesh.n_elems() + self.size_side_block * i
        fh.seek(cursor)

    def seek_node(self, fh, i=0):
        cursor = (self.SIZE_HEAD + self.size_elem_block * self.mesh.n_elems() +
                  self.size_side_block * self.mesh.n_edges() +
                  self.size_node_block * i)
        fh.seek(cursor)

    def read_whole_elem_block(self):
        with open(self.fpath, 'rb') as f:
            self.seek_elem(f)
            n_elems = self.mesh.n_elems()
            for i in range(n_elems):
                data = unpack(self.fmt_elem_block,
                              f.read(self.size_elem_block))
                self.hotstart.elems_dry[i] = int(data[2])
                self.hotstart.elems[i, :] = np.array(
                    data[3:-1], dtype=float).reshape((self.n_vert_levels, -1))

    def read_whole_side_block(self):
        with open(self.fpath, 'rb') as f:
            self.seek_side(f)
            n_edges = self.mesh.n_edges()
            for i in range(n_edges):
                data = unpack(self.fmt_side_block,
                              f.read(self.size_side_block))
                self.hotstart.sides_dry[i] = int(data[2])
                self.hotstart.sides[i, :] = np.array(
                    data[3:-1], dtype=float).reshape((self.n_vert_levels, -1))

    def read_whole_node_block(self):
        with open(self.fpath, 'rb') as f:
            self.seek_node(f)
            n_nodes = self.mesh.n_nodes()
            for i in range(n_nodes):
                data = unpack(self.fmt_node_block,
                              f.read(self.size_node_block))
                self.hotstart.nodes_dry[i] = int(data[3])
                self.hotstart.nodes_elev[i] = data[2]
                self.hotstart.nodes[i, :] = np.array(
                    data[4:-1], dtype=float).reshape((self.n_vert_levels, -1))

    def read_elem_block(self, i):
        with open(self.fpath, 'rb') as f:
            self.seek_elem(f, i)
            data = unpack(self.fmt_elem_block, f.read(self.size_elem_block))
            return data


def read_hotstart(mesh, fpath='hotstart.in', n_tracers=2):
    """ Read hotstart.in

        Parameters
        ----------
        mesh: SchismMesh
            SCHISM mesh model
        fpath: str
            file name to read. default = 'hotstart.in'
        n_tracers: int
            number of tracers. default = 0

        Returns
        -------
        SchismHotstart
    """
    reader = SchismHotstartReader()
    return reader.read(mesh, fpath, n_tracers)
