# -*- coding: utf-8 -*-
"""
This module contains polygon data holders and related operations.

@author: Kijin Nam, knam@water.ca.gov
"""

import numpy as np
# from base_io import *

class Polygon(object):
    """
    A simple container of polygon information.
    This class has geometry functions as well.
    """
    def __init__(self, points=None, name=None,
                 attribute=None, type_=None):
        """ Constructor

            Parameters
            ----------
            points: Numpy array
                the numpy array of the coordinates of vertices.
            name: String
                the name of the polygon
            attribute: Numpy array
                Value associated with the polygon. The shape of the array
                should be identical to points.shape[0].
        """
        self._p = np.array(points).reshape((-1, 2))
        self._name = name
        self._attribute = attribute
        self._type = type_

    def __str__(self):
        return str(self._name)

    @property
    def vertices(self):
        return self._p

    @property
    def attribute(self):
        return self._attribute

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._name

    def n_vertices(self):
        return len(self._p)

    def check_point_inside_polygon(self, pt):
        """ Check if the point is in this 2D polygon.
            It is based on ray-casting algorithm.

            Parameters
            ----------
            pt: array-like
                a point to test

            Returns
            -------
            bool
                True if the point is in the polygon, False otherwise.
        """
        inside = False
        ps = zip(self._p, np.roll(self._p, -1, axis=0))
        for p1, p2 in ps:
            if (((p1[1] <= pt[1] and pt[1] < p2[1]) \
               or (p2[1] <= pt[1] and pt[1] < p1[1])) \
               and (pt[0] < (p2[0] - p1[0]) * (pt[1] - p1[1]) \
                    / (p2[1] - p1[1]) + p1[0])):
                inside = not inside
        return inside

    def box(self):
        """ Provide a bounding box of this polygon.

            Returns
            -------
            a numpy array
                contains [x_min, x_max, y_min, y_max]
        """
        _box = np.array([self._p[0,0], self._p[0,1],
                         self._p[0,0], self._p[0,1]])
        for p in self._p:
            if p[0] < _box[0]:
                _box[0] = p[0]
            if p[0] > _box[1]:
                _box[1] = p[0]
            if p[1] < _box[2]:
                _box[2] = p[1]
            if p[1] > _box[3]:
                _box[3] = p[1]
        return _box


class PolygonIo(object):
    """ Polygon I/O
    """


class PolygonIoFactory(object):
    readers = {''}
    def get_reader(self, name):
        return self.readers['name']

# class PolygonIO(BaseIO):
#     """ Polygon file I/O class
#     """
#     def __init__(self):
#         """ Constructor
#         """
#         super(PolygonIO, self).__init__()

#     def read(self, fname):
#         """ Read in a polygon file.
#             fname = polygon file
#             return = list of polygon instances
#         """
#         polygons = []
#         f = open(fname, 'r')
#         # Get a default value
#         tokens, ok = self._read_and_parse_line(f, 1)
#         if tokens[0].upper() == "NONE":
#             default = None
#         else:
#             print tokens[0]
#             default = float(tokens[0])
#         # Get the number of polygons defined in the file
#         tokens, ok = self._read_and_parse_line(f, 1)
#         n_polygons = int(tokens[0])
#         for i in range(n_polygons):
#             # Read the number of vertices, one attributes, and name
#             tokens, ok = self._read_and_parse_line(f, 4)
#             if not ok:
#                 print "Fail to read polygon %d" % i
#                 print tokens
#                 raise VauleError("Polygon file corrupted.")

#             name = tokens[0]
#             n_vertices = int(tokens[1])
#             attribute = float(tokens[2])
#             if tokens[3].lower() == "none":
#                 type = None
#             else:
#                 type = tokens[3].lower()

#             # Read vertices.  The list does not repeat the first vertix.
#             vertices = []
#             for j in range(n_vertices):
#                 tokens, ok = self._read_and_parse_line(f, 2)
#                 vertex = (float(tokens[0]), float(tokens[1]))
#                 vertices.append(vertex)
#             polygons.append(Polygon(np.array(vertices), name, \
#                                     attribute, type))

#         f.close()
#         return polygons, default
