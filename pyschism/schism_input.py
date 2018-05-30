# -*- coding: utf-8 -*-
"""
This module handles SCHISM input data which are a mesh, structures,
and sources/sinks.
@author: Kijin Nam, knam@water.ca.gov
 """

import schism_mesh
import schism_structure
import schism_source

class SchismInput(object):
    def __init__(self, logger=None):
        self._logger = logger
        # Mesh
        self._mesh = None
        # Structures
        self._nudging = 0.01
        self._structures = []
        self._sources = []
        self._time_start = None

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        self._mesh = value
#        self.adopt_new_mesh(value)

    @property
    def structures(self):
        return self._structures

    def n_structures(self):
        return len(self._structures)

    def clear_structures(self):
        self._structures = []

    @property
    def nudging(self):
        return self._nudging

    @property
    def sources(self):
        return self._sources

    def n_sources(self):
        return self._countmatching(self._sources, lambda a: a.type == schism_source.SOURCE)

    def n_sinks(self):
        return self._countmatching(self._sources, lambda a: a.type == schism_source.SINK)

    @property
    def time_start(self):
        return self._time_start

    @time_start.setter
    def time_start(self, value):
        self._time_start = value

    def _countmatching(self, iterable, predicate):
        v = 0
        for e in iterable:
            if predicate(e):
                v += 1
        return v

    def add_structure(self, value):
        self._structures.append(value)

    def n_structures(self):
        return len(self._structures)
    
