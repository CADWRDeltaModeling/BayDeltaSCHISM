# -*- coding: utf-8 -*-
"""
A package to read a mesh in GR3 format.
@author: Kijin Nam, knam@water.ca.gov
"""

from schism_mesh import BoundaryType
import schism_mesh
import base_io
import numpy as np
import os

class Gr3IO(base_io.BaseIO):
    """ A class that manages I/O of GR3 files
    """

    def __init__(self, logger=None):
        """ Constructor
        """
        super(Gr3IO, self).__init__(logger=logger)
        self._mesh = None

    def read(self, gr3_fname="hgrid.gr3", mode=0):
        """ Read in a hgrid.gr3 file.
            If mode is 1, it does not read in boundary information.
        """
        if self._logger is not None:
            self._logger.info("Reading in a gr3 file: %s ..." % gr3_fname)
        # Create a new mesh
        self._mesh = schism_mesh.SchismMesh()
        try:
            f = open(gr3_fname)
        except:
            raise Exception("Grid file not found.")

        self._linecounter = 0
        # Mesh info
        self._read_header(f)
        if self._logger is not None:
            self._logger.info("Reading in nodes...")
        self._read_nodes(f)
        if self._logger is not None:
            self._logger.info("Reading in elements...")
        self._read_elems(f)

        # Build grid
        # if self._verbose > 1:
        #     print "Building a mesh..."
        # self._mesh.build_edges_from_elems()

        # Boundary info
        if not mode == 1:
            if self._logger is not None:
                self._logger.info("Reading in boundaries...")
            self._read_boundaries(f)

        ## Close
        f.close()
        if self._logger is not None:
            self._logger.info("Done reading a GR3 file.")
        return self._mesh

    def _read_header(self, f):
        ## Header
        # First line: ignored
        tokens, ok = self._read_and_parse_line(f, 0)
        if len(tokens) > 0:
            self._mesh.comment = tokens[0]
        # Second line: # of elements and # of nodes
        tokens, ok = self._read_and_parse_line(f, 2)
        if not ok:
            raise ValueError("The Header information of GR3 file is corrupted.")
        (n_elems, n_nodes) = list(map(int, tokens[:2]))
        if n_nodes <= 0 or n_elems <= 0:
            raise ValueError("The Header information of GR3 file is corrupted.")
        self._mesh.allocate(n_elems, n_nodes) # Allocate memory
        self._n_elems = n_elems
        self._n_nodes = n_nodes

    def _read_nodes(self, f):
        node_counter = 0
        for i in range(self._n_nodes):
            tokens, ok = self._read_and_parse_line(f, 4)
            if not ok:
                print("Line: {}".format(self.linecounter))
                raise ValueError("Node block is corrupt.")
            node_coords = list(map(float, tokens[1:4]))
            self._mesh.set_node(node_counter, node_coords)
            node_counter += 1

    def _read_elems(self, f):
        for elem_i in range(self._n_elems):
            tkn = f.readline().split()
            self.linecounter += 1
            if len(tkn) < 5:
                print("Line: {}".format(self.linecounter))
                raise ValueError("Element block is corrupt.")
            type_elem = int(tkn[1])
            if type_elem < 3 or type_elem > 4:
                raise ValueError("Currently only triangular and " \
                                 "quadrilateral are supported.")
            # Zero-based connectivities
            if type_elem == 3:
                connectivities = np.subtract(np.array(list(map(int, tkn[2:5]))), 1)
            elif type_elem == 4:
                connectivities = np.subtract(np.array(list(map(int, tkn[2:6]))), 1)
            else:
                raise ValueError("Not allowed element type is encountered.")
            self._mesh.set_elem(elem_i, connectivities)

    def _read_boundaries(self, f):
        """ Read boundary information
        """
        ## Assuming the order of the different boundary types are consitent
        ## Open boundaries
        # # of open boundaries
        tokens, ok = self._read_and_parse_line(f, 1)
        if not ok:
            self._logger.info("No boundary information is present?")
            return

        n_open_boundaries = int(tokens[0])
        # total # of open boundary nodes
        tokens, ok = self._read_and_parse_line(f, 1)
        if not ok:
            print("Line: {}".format(self.linecounter))
            raise Exception("The number of total open boundary nodes is not"\
                            " correctly provided.")
        n_open_boundary_nodes = int(tokens[0])

        # open boundaries
        for _ in range(n_open_boundaries):
            # # of nodes of this open boundary
            tokens, ok = self._read_and_parse_line(f, 1)
            if not ok:
                print("Line: {}".format(self.linecounter))
                raise Exception("The number of nodes for a boundary is not"\
                                " correctly provided.")
            # Comment
            comment = None
            if len(tokens) > 1:
                comment = tokens[1]

            n_nodes = int(tokens[0])
            nodes = []
            for _ in range(n_nodes):
                tokens, ok = self._read_and_parse_line(f, 1)
                if not ok:
                    print("Line: {}".format(self.linecounter))
                    raise ValueError("Node for boundary not"\
                                     " correctly provided.")

                node = int(tokens[0]) - 1 # Zero based
                nodes.append(node)
            self._mesh.add_boundary(nodes,
                                    BoundaryType.OPEN,
                                    comment)

        # land boundaries
        # I found out that there is no distinction between
        # land and island boundaries.
        tokens, ok = self._read_and_parse_line(f, 1)
        if not ok:
            self._logger.error("No land boundary presented?")
            return
        n_land_boundaries = int(tokens[0])
        # total # of land boundary nodes
        tokens, ok = self._read_and_parse_line(f, 1)
        if not ok:
            print("Line: {}".format(self.linecounter))
            raise Exception("The number of total land boundary nodes is " \
                            "not provided properly.")
        # n_land_boundary_nodes = int(tokens[0])
        for _ in range(n_land_boundaries):
            # # of nodes of this open boundary
            (tokens, ok) = self._read_and_parse_line(f,1)
            if not ok:
                print("Line: {}".format(self.linecounter))
                raise Exception("The number of nodes for a boundary is "\
                                "not provided properly.")
            # Comment
            comment = None
            if len(tokens) > 1:
                comment = tokens[1]

            n_nodes = int(tokens[0])
            nodes = []
            for _ in range(n_nodes):
                (tokens, ok) = self._read_and_parse_line(f, 1)
                if not ok:
                    print("Line: {}".format(self.linecounter))
                    raise Exception("Node for a boundary not correctly provided.")
                node = int(tokens[0]) - 1 # Zero based
                nodes.append(node)
            self._mesh.add_boundary(nodes, BoundaryType.LAND, comment)

    def write(self, mesh, fname, node_attr=None, boundary=False):
        """ Write a GR3 format grid.
            mesh = SCHISM mesh (schism_mesh) instance
            fname = output file name
            node_attr = a list of node attribute
            boundary = If true, boundary information will be added. Otherwise,
            it will not be appended.
        """
        if self._logger is not None:
            self._logger.info("Writing an gr3 file: %s" % fname)
        f = open(fname, 'w')
        # Header
#         if mesh.comment is None:
        buf = "%s\n" % os.path.basename(fname)
#         else:
#             buf = "%s !modified by the preprocessing tool\n" \
#                   % mesh.comment

        f.write(buf)
        n_elems = mesh.n_elems()
        n_nodes = mesh.n_nodes()
        buf = "%d %d ! # of elements and nodes \n" % (n_elems, n_nodes)
        f.write(buf)
        # Nodes
        for i in range(n_nodes):
            if not node_attr is None:
                buf = "%d %18.8f %18.8f %18.8f\n" % (i + 1, \
                                     mesh.nodes[i, 0], \
                                     mesh.nodes[i, 1], \
                                     node_attr[i])

            else:
                buf = "%d %18.8f %18.8f %18.8f\n" % (i + 1, \
                                     mesh.nodes[i, 0], \
                                     mesh.nodes[i, 1], \
                                     mesh.nodes[i, 2])
            f.write(buf)

        # Elements
        for elem_i in range(n_elems):
            elem = mesh.elem(elem_i) + 1
            n_nodes = len(elem)
            buf = '%d %d' % (elem_i + 1, n_nodes)
            fmt = ' %d' * n_nodes + '\n'
            buf += fmt % tuple(elem)
            f.write(buf)

        # Boundaries
        if boundary:
            # Open
            buf = "%d = Number of open boundaries\n" \
                  % mesh.n_boundaries(BoundaryType.OPEN)
            f.write(buf)
            buf = "%d = Total number of open boundary nodes\n" \
                  % mesh.n_boundary_nodes(BoundaryType.OPEN)
            f.write(buf)
            openbound_count = 0
            for boundary in mesh.boundaries:
                if boundary.btype == BoundaryType.OPEN:
                    openbound_count += 1
                    if boundary.comment is None:
                        buf = "%d = Number of nodes for open boundary %d\n" % \
                              (boundary.n_nodes(), openbound_count)
                    else:
                        buf = "%d %s\n" % (boundary.n_nodes(), boundary.comment)
                    f.write(buf)
                    buf = ""
                    for node_i in boundary.nodes:
                        buf += "%d\n" % (node_i + 1)
                    f.write(buf)
#             else:
#                 raise Exception("Unsupported boundary type.")

            # Land
            buf = "%d = Number of land boundaries\n" \
                  % (mesh.n_boundaries(BoundaryType.LAND))
            f.write(buf)
            buf = "%d = Total number of land boundary nodes\n" \
                  % (mesh.n_boundary_nodes(BoundaryType.LAND))
            f.write(buf)
            landbound_count = 0
            islandbound_count = 0
            for boundary in mesh.boundaries:
                if boundary.btype == BoundaryType.LAND:
                    landbound_count += 1
                    if boundary.comment is None:
                        buf = "%d = Number of nodes for land boundary %d\n" % \
                          (boundary.n_nodes(), landbound_count)
                    else:
                        buf = "%d %s\n" % (boundary.n_nodes(), boundary.comment)
                    f.write(buf)
                    buf = ""
                    for node_i in boundary.nodes:
                        buf += "%d\n" % (node_i + 1)
                    f.write(buf)
                # elif boundary.btype == BoundaryType.ISLAND:
                #     islandbound_count += 1
                #     if boundary.comment is None:
                #         buf = "%d = Number of nodes for island boundary %d\n" \
                #                % (boundary.n_nodes(), islandbound_count)
                #     else:
                #         buf = "%d %s\n" % (boundary.n_nodes(), boundary.comment)
                #     f.write(buf)
                #     buf = ""
                #     for node_i in boundary.nodes:
                #         buf += "%d\n" % (node_i + 1)
                #     f.write(buf)
#             else:
#                 raise Exception("Unsupported boundary type.")

        f.flush()
        f.close()

        if self._logger is not None:
            self._logger.info("Done writing a gr3 file.")
