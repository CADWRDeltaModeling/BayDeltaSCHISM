# -*- coding: utf-8 -*-
"""
Setup and processes SCHISM Inputs
"""
from .base_io import *
from .schism_polygon import SchismPolygon, Point
from .schism_structure import *
from .schism_source import *
from .schism_input import *
from .schism_mesh import SchismMesh, read_mesh, write_mesh, BoundaryType
import yaml
import osgeo.ogr
import osgeo.osr
from scipy.interpolate import interp1d
import datetime
import numpy as np
import re
import math
from math import *
import copy
import os
import sys
import difflib
from shapely.ops import transform
from shapely.geometry import Point
import pyproj
from functools import partial


class SchismSetup(object):
    """
    A class to manage SCHISM input data
    """

    def __init__(self, logger=None):
        """ Constructor
        """
        self._logger = logger
        self._input = SchismInput(logger)

    @property
    def input(self):
        return self._input

    @property
    def mesh(self):
        """ Mesh

            :getter: Return the mesh.
        """
        return self._input.mesh

    @mesh.setter
    def mesh(self, value):
        """ Mesh setter
        """
        self._input.mesh = value

    def load(self, dir):
        """ Read SCHISM input

            Parameters
            ----------
            dir: String
                An directory where the SCHISM inputs reside
        """
        # Assuming we are dealing SCHISM format
        # Read the grid
        gr3_reader = Gr3IO()
        fname = os.path.join(dir, "hgrid.gr3")
        if not os.path.exists(fname):
            raise Exception("Grid file not found!")
        self._input.mesh = gr3_reader.read(fname)
        # Read hydraulics if exists
        fname = os.path.join(dir, "hydraulics.in")
        if os.path.exists(fname):
            structure_reader = SchismStructureIO(self._input)
            structure_reader.read(fname)

        # Read source if exists
        fname = os.path.join(dir, "source_sink.in")
        if os.path.exists(fname):
            source_reader = SchismSourceIO(self._input)
            source_reader.read(fname)

    def get_closest_node_i_from_new_mesh(self, mesh, node_i):
        old_node = self._input.mesh.nodes[node_i, ]
        return mesh.find_closest_nodes(old_node[:2], count=1, boundary=1)

    def adopt_new_mesh(self, fname):
        """ Adopt a new grid.
                fname = the file name of a new hgrid file
        """
        gr3_reader = Gr3IO()
        if not os.path.exists(fname):
            raise Exception("The given mesh file is not found")
        new_mesh = gr3_reader.read(fname, 1)

        mesh = self._input.mesh
        # Boundary build
        # First delete boundary information of the new mesh
        new_mesh.clear_boundary()
        if mesh.n_boundaries == 0:
            raise Exception("No boundary is in the original mesh.")
        # Open boundary
        for b in mesh.boundaries:
            # First Node
            node_1 = self.get_closest_node_i_from_new_mesh(
                new_mesh, b.nodes[0])
            # End Node
            node_2 = self.get_closest_node_i_from_new_mesh(
                new_mesh, b.nodes[-1])
            # Get a path between the two
            new_nodes = new_mesh.shortest_path(node_1, node_2, boundary_only=1)
            new_mesh.add_boundary(new_nodes, b.btype)

        # Structure adoption
        new_structures = []
        for struct in self._input.structures:
            # Ref node
            new_ref_pair = tuple(self.get_closest_node_i_from_new_mesh(
                new_mesh, node_i) for node_i in struct.reference_pair)

            # Node pairs.  This one is slightly trickier
            original_up = [node_i[0] for node_i in struct.node_pairs]
            original_down = [node_i[1] for node_i in struct.node_pairs]
            # Step 1: Create a new path of the upstream side
            node_prev = None
            new_up = None
            for node in original_up:
                if node_prev is None:
                    node_prev = node
                else:
                    path = list(new_mesh.shortest_path(node_prev, node))
                    if new_up is None:
                        new_up = path
                    else:
                        if new_up[-1] == path[0]:
                            new_up.extend(path[1:])
                        else:
                            raise Exception('Path segment does not match.')
                    node_prev = node
            # Step 2: Create a new downstream node pair
            new_down_inter = []
            for i in range(len(original_up)):
                path = list(new_mesh.shortest_path(original_up[i],
                                                   original_down[i]))
                new_down_inter.append(path[1])
            # Step 3: Build middle nodes of the downstream side
            node_prev = None
            new_down = None
            for node in new_down_inter:
                if node_prev is None:
                    node_prev = node
                else:
                    path = list(new_mesh.shortest_path(node_prev, node))
                    if new_down is None:
                        new_down = path
                    else:
                        if new_down[-1] == path[0]:
                            new_down.extend(path[1:])
                        else:
                            raise Exception('Path segment does not match.')
                    node_prev = node
            # Step 4: Check the pairs
            new_pairs = []
            if not len(new_up) == len(new_down):
                raise Exception('Number of pairs does not match')
            for i in range(len(new_up)):
                path = list(new_mesh.shortest_path(new_up[i], new_down[i]))
                if not len(path) == 2:
                    raise Exception('Having trouble with ')
                new_pairs.append((new_up[i], new_down[i]))

            # Create a new structure
            struct_new = copy.deepcopy(struct)
            struct_new.reference_pair = new_ref_pair
            struct_new.node_pairs = new_pairs
            new_structures.append(struct_new)

        # Source/sink adoption
        # TODO: This is tricky... I'll think more about this

        # Set the new mesh
        self._input.mesh = new_mesh
        # Set new structures
        self._structures = new_structures

    def write_hgrid(self, fname, attr=None, boundary=True):
        """ Write a hgrid file only.
            fname = the output file name
            attr = attribute array in numpy format. If None, original data
            will be kept.
            boundary = If True, boundary info will be appended at the end of
            the file. Otherwise, not appended.
        """
        schism_mesh.write_mesh(self._input.mesh, fname, attr, boundary)

    def write_hgrid_ll(self, fname, input_epsg=26910, output_epsg=4269):
        """ Write a hgrid.ll, lat-long mesh file, of the current mesh.

            Parameters
            ----------
            fname: str
                the output file name
            input_epsg: int, optional
                input EPSG. default value is 26910, NAD83/UTM10N.
            output_epsg: int, optional
                output EPSG. default value is 4269, NAD83
        """
        
        inSpatialRef = 'epsg:' + str(input_epsg)
        outSpatialRef = 'epsg:' + str(output_epsg)
        proj_in = pyproj.Proj(init=inSpatialRef)
        proj_out = pyproj.Proj(init=outSpatialRef)
        try:
            # More performant for pyproj > 2.1.0
            project = pyproj.Transformer.from_proj(proj_in, proj_out).transform
        except:
            # In case that isn't available in earlier versions
            # but orders of magnitude slow for pyproj 2.1.0
            project = partial(transform,proj_in,proj_out)

        new_mesh = SchismMesh()
        new_mesh._nodes = np.copy(self.mesh.nodes)
        new_mesh._elems = np.copy(self.mesh._elems)
        for i, node in enumerate(self.mesh.nodes):
            point = Point(node[0], node[1])
            point = transform(project, point)
            new_mesh.nodes[i, 0] = point.xy[0][0]
            new_mesh.nodes[i, 1] = point.xy[1][0]
        write_mesh(new_mesh, fname)


    def elements_on_linestring(self, coords):
        """List elements along linestring"""
        mesh = self._input.mesh
        line_segment = np.array(coords,dtype="d").flatten()
        print(line_segment)
        return mesh.find_intersecting_elems_with_line(line_segment)

    def create_flux_regions(self, linestrings, out_fname='fluxflag.prop'):
        """ Create and write flux_regions.gr3 with the given lines

            Parameters
            ----------
            linestrings: list
                A list containing information for flux regions.
                It must contains 'linestrings.'
            out_fname: str, optional
                Output file name
        """
        mesh = self._input.mesh
        assigned = set()
        flagval = 0
        flags = np.full((mesh.n_elems(), 1), -1, dtype='int')        
        for flagval,linestring in enumerate(linestrings):
            line = linestring.get('coordinates')
            name = linestring.get('name')
            if name is None:
                name = linestring.get('Name')
            npoint = len(line)
            for ip in range(npoint-1):
                line_segment = np.array(line[ip:ip+2],dtype='d').flatten()
                on_line,neighbors = mesh.find_neighbors_on_segment(line_segment)  
                #if not set(neighbors).isdisjoint(assigned): raise ValueError("Element assigned twice in fluxline:".format(name))
                #if not set(neighbors).isdisjoint(assigned): raise ValueError("Element assigned twice in fluxline:".format(name))
                #if not set(on_line).isdisjoint(assigned): raise ValueError("Element assigned twice in fluxline:".format(name))
                # techinically we could (?) survive on_line  members 
                # being assigned if it was assigned as online in previous group                
                flags[np.array(on_line,dtype='i')] = flagval + 1
                flags[np.array(neighbors,dtype='i')] = flagval 
                assigned.update(on_line + neighbors)

        index = np.arange(flags.shape[0]).reshape((-1, 1))
        index += 1
        elementflags = np.concatenate((index, flags), axis=1)
        np.savetxt(out_fname, elementflags, fmt='%d')

    def _area_of_poligon(x):
        """ Calculate area of a polygon based on shoelace formula

            Parameters
            ----------
            x: numpy.array
                array of coordinates for the polygon

            Returns
            -------
            float
                area of the polygon
        """
        area = 0.
        for i in range(len(x)):
            area += x[i][0] * x[i + 1][1] - x[i + 1][0] * x[i][1]

        return fabs(area) * .5

    def _clip(subjectPolygon, clipPolygon):
        """  Sutherland-Hodgman polygon clipping algorithm
             from Rosetta code
        """
        def inside(p):
            return(cp2[0] - cp1[0]) * (p[1] - cp1[1]) > (cp2[1] - cp1[1]) * (p[0] - cp1[0])

        def computeIntersection():
            dc = [cp1[0] - cp2[0], cp1[1] - cp2[1]]
            dp = [s[0] - e[0], s[1] - e[1]]
            n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
            n2 = s[0] * e[1] - s[1] * e[0]
            n3 = 1.0 / (dc[0] * dp[1] - dc[1] * dp[0])
            return [(n1 * dp[0] - n2 * dc[0]) * n3, (n1 * dp[1] - n2 * dc[1]) * n3]

        outputList = subjectPolygon
        cp1 = clipPolygon[-1]

        for clipVertex in clipPolygon:
            cp2 = clipVertex
            inputList = outputList
            outputList = []
            s = inputList[-1]

            for subjectVertex in inputList:
                e = subjectVertex
                if inside(e):
                    if not inside(s):
                        outputList.append(computeIntersection())
                    outputList.append(e)
                elif inside(s):
                    outputList.append(computeIntersection())
                s = e
            cp1 = cp2
        return(outputList)

    def creart_sources_from_user_input(self):
        """ Create a source from a user input
        """
        # Read a user input
        source_inputs = self._read_source_user_input()
        source_th_inputs = self._read_source_th_user_input()
        out_fname = 'source_sink.in'
        self._write_source_file(source_inputs, out_fname)
        out_fname = 'vsource.th'
        self._write_volume_source_history_file(out_fname)

    def _read_source_user_input(self, fname='source_sink.user'):
        """ Read in a user input
        """
        f = open(fname, 'r')
        inputs = []
        for l in f:
            l = l.strip()
            if l[0] == '#':
                continue
            tokens = l.split()
            if len(tokens) < 4:
                raise Exception('the file is corrupted.')
            name = tokens[0]
            coord = (float(tokens[1]), float(tokens[2]))
            if tokens[3].upper() == "SOURCE":
                type = 1
            elif tokens[3].upper() == "SINK":
                type = -1
            else:
                raise Exception('the file is corrupted.')
            inputs.append((name, coord, type))
        f.close()
        return inputs

    def _read_source_th_user_input(self, fname='source_sink_th.user'):
        """ Read in a user input for time history of source/sink
        """
        f = open(fname, 'r')

        f.close()

    def _write_source_file(self, inputs, fname='source_sink.in'):
        """ Write a source/sink file with the give user input data
        """
        f = open(fname, 'w')
        # Count the number of source/sink
        n_sources = sum(item[2] == 1 for item in inputs)
        n_sinks = sum(item[2] == -1 for item in inputs)
        # Sources
        buf = "%d   ! total # of elements with sources\n" % n_sources
        f.write(buf)
        for item in inputs:
            if item[2] == 1:
                element_i = self.mesh.find_elem(item[1])
                buf = "%d  ! %s\n" % (element_i, item[0])
                f.write(buf)
        # Sink
        buf = "%d   ! total # of elements with sinks\n" % n_sinks
        f.write(buf)
        for item in inputs:
            if item[2] == -1:
                element_i = self.mesh.find_elem(item[1])
                buf = "%d  ! %s\n" % (element_i, item[0])
                f.write(buf)

        f.flush()
        f.close()

    def _write_volume_source_history_file(self, fname='msource.th'):
        """ Write a time history file of sources/sinks.
        """
        pass

    def create_structures(self, structures, nudging=None):
        """ Create structures
        """
        self._input.clear_structures()
        self._input._nudging = nudging
        for item in structures:
            struct = SchismStructure()
            name = item.get('name')
            struct.name = name
            end_points = item.get('end_points')
            if end_points is None:
                self._logger.warning("No end_points in structure")
                continue
            struct.coords = np.array(end_points)
            struct.type = item['type'].lower()
            struct.properties = item['configuration']

            # Find node pairs
            up_path, down_path = \
                self.mesh.find_two_neighboring_node_paths(struct.coords)
            struct.node_pairs = list(zip(up_path, down_path))
            # Reference pair
            ref = item.get('reference', 'self')
            struct.reference = ref
            if ref == 'self':
                struct.reference_pair = self._generate_reference_pair(up_path,
                                                                      down_path)
            else:
                struct.reference_pair = None
            self._input.add_structure(struct)

        for struct in self._input.structures:
            if struct.reference_pair is None:
                found = False
                for i, item in enumerate(structures):
                    if struct.reference == item['name']:
                        struct.reference_pair = copy.deepcopy(
                            self._input.structures[i].reference_pair)
                        found = True
                        break
                if found is False:
                    self._logger.error("Reference name not found: %s",
                                       item['name'])
                    raise ValueError("Wrong reference name in structures")

    def write_structures(self, fname="hydraulics.in"):
        """ Write a SCHISM structure file
            fname = output file name
        """
        struct_writer = SchismStructureIO(self._input)
        struct_writer.write(fname)

    def _generate_reference_pair(self, up_path, down_path):
        """ Generate a new referece pair from the current node pairs.
            For now, it picks the neighboring nodes around the
            middle node pair.
            node_pairs = the list of node pairs
            return = the new reference pair
        """
        ref_up = self._find_reference_node(up_path, down_path)
        ref_down = self._find_reference_node(down_path, up_path)
        return (ref_up, ref_down)

    def _find_reference_node(self, path1, path2):
        # TODO: The safety of this code needs to check further
        mesh = self.mesh
        # path1
        center_node_i = path1[len(path1) // 2]
        neighbors = mesh.get_neighbor_nodes(center_node_i)
        candidates = []
        for n in neighbors:
            if not (n in path1 or n in path2):
                candidates.append(n)
        if len(candidates) < 1:
            raise Exception("No reference node founde")
        elif len(candidates) == 1:
            return candidates[0]
        else:
            # If there are multiple candidates, a most perpendicular one
            # to the line constructed by the two end points of the path1
            # is chosen.
            tangent = mesh.nodes[path1[-1]][:2] - mesh.nodes[path1[0]][:2]
            tangent /= np.linalg.norm(tangent)
            min = 1.
            hit = -1
            for c in candidates:
                vec = mesh.nodes[c][:2] - mesh.nodes[center_node_i][:2]
                vec /= np.linalg.norm(vec)
                dot = math.fabs(np.dot(vec, tangent))
                if dot < min:
                    min = dot
                    hit = c
            return hit

    def _parse_attribute(self, expr):
        """ Parse expression that can be understood by the tool
        """
        expr = re.sub(r"\bx\b", "node[0]", expr)
        expr = re.sub(r"\by\b", "node[1]", expr)
        expr = re.sub(r"\bz\b", "node[2]", expr)
        return expr

    def _partition_nodes_with_polygons(self, polygons, default):
        """ Partition the grid with the given polygons.
            Each node (not element) will be assigned with an integer ID
            which is the index of the polygons.
            If some polygons overlap, the latter one will trump the former one.
            The area that are not covered by any of the given polygons
            will have a default negative one attribute.

            Parameters
            ----------
            polygons: list
                a list of polygon dict (from YAML most of time)

            Returns
            -------
            numpy.ndarray
                attributes
        """
        import math
        mesh = self.mesh
        if default is None:
            # Use depth
            attr = np.copy(mesh.nodes[:, 2])
        else:
            # Fill default values
            attr = np.empty(mesh.n_nodes())
            attr.fill(float(default))
        for polygon in polygons:
            name = polygon.get('name')
            vertices = np.array(polygon.get('vertices'))
            if vertices.shape[1] != 2:
                raise ValueError(
                    'The number of coordinates in vertices are wrong.')
            vertices = np.array(vertices)
            poly_type = polygon['type'].lower() \
                if 'type' in polygon else "none"
            attribute = polygon['attribute']
            prop = {'name': name, 'type': poly_type, 'attribute': attribute}
            poly = SchismPolygon(shell=vertices,
                                 prop=prop)
            if isinstance(attribute, str):
                is_eqn = True
                expr = self._parse_attribute(attribute)
            else:
                expr = None
                is_eqn = False
            box = np.array(poly.bounds)[[0, 2, 1, 3]]
            nodes = mesh.find_nodes_in_box(box)
            empty = True
            for node_i in nodes:
                node = mesh.nodes[node_i]
                flag = poly.contains(Point(node[:2]))
                if flag:
                    if is_eqn:
                        try:
                            value = eval(expr)
                        except Exception as e:
                            msg = "Egn: %s" % attribute
                            self._logger.error(msg)
                            raise ValueError(
                                "The polygon equation does not seem to be well-formed for polygon: {} ".format(name))
                    else:
                        value = attribute
                    empty = False
                    if poly.type == "none":
                        attr[node_i] = value
                    elif poly.type == "min":
                        if attr[node_i] < value:
                            attr[node_i] = value
                    elif poly.type == "max":
                        if attr[node_i] > value:
                            attr[node_i] = value
                    else:
                        raise Exception("Not supported polygon type ({}) for polygon ({})".format(poly.type,name))
            if empty:
                msg = "This polygon contains no nodes: %s" % poly.name
                self._logger.error(poly)
                self._logger.error(msg)

        n_missed = sum(1 for i, a in enumerate(attr) if a == default)
        if n_missed > 0:
            msg = "There are %d nodes that do not belong " \
                  "to any polygon." % n_missed
            self._logger.warning(msg)
            if default is not None:
                msg = "Default value of %.f is used for them." % default
                self._logger.warning(msg)
        return attr

    def create_node_partitioning(self, gr3_fname, polygons, default):
        """ Create a gr3 file with node partitioning using
            polygons in the polygon file.
            gr3_fname = output gr3 file name
            polygons = polygons
        """
        # option_name = 'default'
        # if option_name in polygon_data.keys():
        #     default = polygon_data[option_name]
        # else:
        #     default = None
        attr = self._partition_nodes_with_polygons(polygons, default)
        if gr3_fname != 'hgrid.gr3':
            self.write_hgrid(gr3_fname, attr, False)
        else:
            self.write_hgrid(gr3_fname, attr)

    def create_prop_partitioning(self, prop_fname, polygons, default):
        """ Create a prop file with element partitioning using
            polygons in the polygon file.
            prop_fname = output prop file name
            polygons = polygons
        """
        # option_name = 'default'
        # # default = polygon_data[option_name]
        # polygons = polygon_data['polygons']
        attr = self._partition_nodes_with_polygons(polygons, default)
        mesh = self.mesh
        elementflags = np.empty((mesh.n_elems(), 1))
        elementflags.fill(0.)
        for elem_i in range(mesh.n_elems()):
            elem = mesh.elem(elem_i)
            flags = attr[elem]
            if np.amax(flags) == 1.:
                elementflags[elem_i] = 1.
        index = np.arange(mesh.n_elems()).reshape((mesh.n_elems(), 1))
        index += 1
        np.savetxt(prop_fname, np.concatenate(
            (index, elementflags), axis=1), fmt="%d")

    def modify_depth(self, polygon_data):
        """ Modify depth with the polygon information
        """
        polygons = polygon_data['polygons']
        attr = self._partition_nodes_with_polygons(polygons, None)
        self.mesh.nodes[:, 2] = attr

    def create_source_sink_in(self, source_sinks, out_fname='source_sink.in'):
        """ Create source_sink.in from source/sink location information
            in_fname = input file name
        """
        # TODO: I need to use a common source/sink I/O routines.
        key = 'sources'
        sources = source_sinks[key] if key in source_sinks else dict()
        key = 'sinks'
        sinks = source_sinks[key] if key in source_sinks else dict()

        fout = open(out_fname, 'w')
        buf = "%d ! total # of elems with sources\n" % len(sources)
        fout.write(buf)
        for name, coord in sources.items():
            element_i = self.mesh.find_elem(coord)
            if element_i is None:
                element_i = self.mesh.find_closest_elems(coord)
                buf = "%d ! %s, nudged\n" % (element_i + 1, name)
                fout.write(buf)
            else:
                buf = "%d ! %s\n" % (element_i + 1, name)
                fout.write(buf)

        buf = "\n%d ! total # of elems with sinks\n" % len(sinks)
        fout.write(buf)
        for name, coord in sinks.items():
            element_i = self.mesh.find_elem(coord)
            if element_i is None:
                element_i = self.mesh.find_closest_elems(coord)
                buf = "%d ! %s, nudged\n" % (element_i + 1, name)
                fout.write(buf)
            else:
                buf = "%d ! %s\n" % (element_i + 1, name)
                fout.write(buf)

        fout.flush()
        fout.close()

    def reorder_open_boundaries(self, order):
        """ Reorder open boundaries with the given order
            order = list of open boundary names
            TODO: How to put the name of the boundaries is not settled.
        """
        open_boundaries = list(boundary for boundary in self.mesh.boundaries
                               if boundary.btype == OPEN_BOUNDARY)
        names = []
        for boundary in open_boundaries:
            # extract names from the comments
            p1 = boundary.comment.find("\"")
            p2 = boundary.comment.find("\"", p1 + 1)
            name = boundary.comment[p1 + 1:p2]
            names.append(name)

        new_order = [names.index(i) for i in order]
        self.mesh.boundaries[:len(open_boundaries)] = \
            [open_boundaries[i] for i in new_order]

    def _interpolate(self, times, data, dt_out, out_fname):
        """ Interpolate tide data.
            The code is copied and modified from interpolate_elev.py.
            times = an array of time stamps
            data = an array of tide data
            dt_out = delta t for output
            out_fname = output file name

            TODO: The code may need to be cleaned up.
        """
        ntimes = times.shape[0]
        stime = times[0]
        etime = times[-1]
        dt_in = times[1] - times[0]

        new_times = np.arange(stime, etime, dt_out)
        nout = new_times.shape[0]
        self._logger.info("Interpolating to a new series of size %s" % nout)

        g = open(out_fname, 'w')

        # There is a limit on the size of the array for 1d
        # spline interpolation (interp1d).
        # Testing on PC indicates it will work up to 2500.
        # The larger the array, the slower the performance.
        # We use 1000 in this script.
        # To minimize edge effect, at 20% on each side.
        max_size_spline = 1000
        add_size = int(1000 * 0.2)

        dt_ratio = int(dt_in / dt_out)
        loop_step = max_size_spline * dt_ratio
        if nout % loop_step != 0:
            iloop = nout // loop_step + 1
        else:
            iloop = nout // loop_step

        msg = "number of loops required to convert the file: %s" % iloop
        self._logger.info(msg)
        msg = "steps per loop: %s" % loop_step
        self._logger.info(msg)

        for j in range(0, iloop):
            self._logger.info("working on loop %s out of %s" % (j + 1, iloop))

            if j == 0:
                iin_start = 0
            else:
                iin_start = j * max_size_spline - add_size

            if j == iloop - 1:  # for the last run of the loop
                iin_end = ntimes - 1  # set the end to the last input element
            else:
                iin_end = (j + 1) * max_size_spline + add_size
                if iin_end > (ntimes - 1):
                    iin_end = ntimes - 1

            iout_start = j * loop_step
            iout_end = iout_start + loop_step
            # to avoid "ValueError:
            # A value in x_new is above the interpolation range."
            # reduce output end time
            if iout_end * dt_out > (iin_end - 1) * dt_in:
                iout_end = (iin_end - 1) * dt_ratio

            spline = interp1d(times[iin_start:iin_end],
                              data[iin_start:iin_end], kind='cubic')
            est_times = new_times[iout_start:iout_end]
            new_data = spline(est_times)

            for i in range(len(new_data)):
                g.write("%s    %s\n" % (est_times[i] + dt_out, new_data[i]))

        g.close()

    def _adjust_ocean_bc(self):
        """
        """
        # Read ocean map
        fname = 'ocean.gr3'
        gr3io = Gr3IO()
        ocean_mesh = gr3io.read(fname)

        # Read ocean tide harmonics
        fname = 'ocean.ap'
        f = open(fname, 'r')
        f.readline()
        l = f.readline().strip()
        n_nodes = int(l)
        if n_nodes != ocean_mesh.n_nodes():
            raise Exception('Node numbers in the mesh and tide harmonic files'
                            ' are not identical.')
        l = f.readline().strip()
        n_harmonics = int(l)
        harmonics = {}
        for i in range(n_harmonics):
            l = f.readline().strip()
            name = l
            harmonic = np.empty([n_nodes, 2])
            for j in range(n_nodes):
                l = f.readline().strip()
                tokens = l.split()
                harmonic[j, ] = list(map(float, tokens))
            harmonics[name] = harmonic

        # Calculate weights
        # Get ocean boundary: Assume the first one is the ocean
        ocean_boundary = self.mesh.boundaries[0]
        for node_i in ocean_boundary.nodes:
            element_i = ocean_mesh.find_elem(self.mesh.nodes[node_i][:2])
            if element_i is None:
                element_i = ocean_mesh.find_elem_with_tolerance(
                    self.mesh.nodes[node_i][:2], 0.1)

    def interpolate_tide(self, time_start, time_end, dt,
                         in_fname, out_fname):
        """ Interpolate an observed tide time series with the given dt.
            time_start = start time in Python datetime
            time_end = end time in Python datetime
            dt = delta t for the interpolation output
            in_fname = input file name of tide records
            out_fname = output file name
        """
        # Read the tide input
        f = open(in_fname, 'r')
        # ignore first three header lines
        for i in range(3):
            f.readline()
        timestamps = []
        values = []
        hit = 0
        for l in f:
            # Parse it
            tokens = l.split(',')
            time_str = tokens[0] + "," + tokens[1]
            t = datetime.datetime.strptime(time_str, "%m/%d/%Y,%H:%M")
            if t < time_start:
                pass
            elif t <= time_end:
                delta = t - time_start
                delta_in_sec = delta.days * 86400 + delta.seconds
                timestamps.append(delta_in_sec)
                values.append(float(tokens[2]))
            else:
                break
        f.close()

        times = np.array(timestamps)
        data = np.array(values)

        # Interpolate
        self._interpolate(times, data, dt, out_fname)

    def create_open_boundaries(self, segments):
        """ Create open boundaries with linestrings
        """
        self.mesh.clear_boundaries()
        boundary_only = True
        linestrings = segments.get('linestrings')
        if linestrings is None:
            raise ValueError('Linestrings is required for open boundaries')
        for item in linestrings:
            name = item.get('name')
            if name is None:
                name = item.get('Name')
            p = np.array(item['coordinates'])
            start = self.mesh.find_closest_nodes(p[0], 1, boundary_only)
            end = self.mesh.find_closest_nodes(p[1], 1, boundary_only)
            path = self.mesh._build_boundary_node_string(
                start, end, boundary_only)
            comment = "! Open boundary \"%s\"" % name
            self.mesh.add_boundary(path, BoundaryType.OPEN, comment)

    def trim_to_left_of_mesh(self, line_segments):
        """ Trim mesh using line_segments.
            This function trims the mesh on the left sides
            of the line segments. The left side here means left when you look
            at the second end point of a line segment from the first one.
            An actual path to trimming is a nodal path that is on the
            right side of the line segment.
            To manage torus like mesh topology, the argument takes an array
            of line segments. The user need to provides a set of line segments
            to make sure the left side of the line segments does not
            cover the whole mesh.
            To trim multiple parts of a mesh, use this function
            multiple times.
            This function clears up any boundary definitions associated with
            the original grid. It is user's responsibility to create them
            again.

            line_segments = array of line segments defined by two end points
        """
        self._logger.info("Trimming the mesh...")
        paths = []
        for _, l in enumerate(line_segments):
            p = self.mesh.find_two_neighboring_paths(l)
            paths.append(p[0])
        self.mesh.trim_to_left(paths)
        self.mesh.clear_boundary()
        self._logger.info("Removed the old boundary information.")


def load_schism(dir):
    """ A load function
    """
    s = SchismSetup()
    s.load(dir)
    return s


def create_schism_setup(fname, logger=None):
    """ Read a mesh and return a SCHISM input set-up instance.

        Parameters
        ----------
        fname: str

        Returns
        -------
        SCHISM input set-up instance
    """
    s = SchismSetup(logger)
    # Read the grid
    if not os.path.exists(fname):
        raise Exception("Grid file not found: {}".format(fname))
    s.mesh = read_mesh(fname)
    return s


def check_similarity(testee, list_words):
    """ Check similarity of a word """
    seq = difflib.SequenceMatcher()
    for word in list_words:
        for reserved in list_words:
            seq.set_seqs(testee, reserved)
            ratio = seq.ratio()
            if ratio > 0.9:
                return reserved


def check_and_suggest(testees, list_words, logger=None):
    """ Check testtees in list_words and if not suggest something if possible
    """
    for keyword in testees:
        if keyword not in list_words:
            msg = "Unrecognizable key word: '%s'" % (keyword)
            if logger is not None:
                logger.error(msg)
            else:
                print(msg)
            similar_one = check_similarity(keyword, list_words)
            if not similar_one is None:
                msg = "-- Did it mean '%s'?" % similar_one
                if logger is not None:
                    logger.info(msg)
                else:
                    print(msg)
            msg = "Acceptable items in this section are: " + \
                  ', '.join(list_words)
            if logger is not None:
                logger.error(msg)
            else:
                print(msg)
            raise ValueError("Unrecognizable item")
