#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Routines to manage a table that links between station names and field
    date files.
"""
import os


def _single_out(array):
    """ If an array has one element, pull it out.

        Parameters
        ----------
        array: array-like
            Input array

        Returns
        -------
        element or array
            None if the array has no element.
            When the array has one element, the element is returned.
            When the array has more then one element, just return
            the array back.
    """
    if len(array) < 1:
        return None
    if len(array) == 1:
        return array[0]
    else:
        return array


class ObsLinks(object):
    """ Class that holds a link table between station names and field data files
    """

    def __init__(self, fname, base_dir=None):
        """ Constructor
        """
        self.links = {}
        self.data2d = {}
        if base_dir is None:
            base_dir = os.path.dirname(fname)
        with open(fname, "r") as f:
            for line in f:
                if line and len(line) > 2 and not line.startswith("#"):
                    station_id, subid, variable, path, selector, agency, unit, vdatum, tzone, voffset, vloc = line.strip().split(",")
                    vloc = int(vloc)
                    voffset = float(voffset)
                    path = os.path.join(base_dir, path)
                    self.links[(station_id, variable, vloc)] = (
                        station_id, variable, path, selector, agency, unit, vdatum, tzone, voffset, vloc)
                    self.data2d[(station_id, variable)] = (
                        station_id, variable, tzone, vdatum, voffset, agency, unit)

    def filename(self, station_id, variable, vert_pos=0):
        """
            station_id:
                Station name
        """
        if (station_id, variable, vert_pos) in self.links:
            return self.links[(station_id, variable, vert_pos)][2]
        else:
            return None

    def path(self, station_id, variable, vert_pos=0):
        """
            station_id:
                Station name
        """
        if (station_id, variable, vert_pos) in self.links:
            return self.links[(station_id, variable, vert_pos)][2]
        else:
            return None

    def stations_for_variable(self, variable):
        return [self.links[x] for x in self.links if x[1] == variable]

    def agency(self, station_id, variable):
        if (station_id, variable) in self.links2d:
            return self.data2d[(station_id, variable)][5]
        else:
            return None

    def item(self, station_id, variable, vert_pos, item):
        if (station_id, variable, vert_pos) in self.links:
            return self.links[(station_id, variable, vert_pos)][item]
        else:
            return None

    def item2d(self, station_id, variable, item):
        if (station_id, variable) in self.data2d:
            return self.data2d[(station_id, variable)][item]
        else:
            return None

    def agency(self, station_id, variable):
        return self.item2d(station_id, variable, 5)

    def unit(self, station_id, variable, vert_pos=None):
        return self.item2d(station_id, variable, 6)

    def vdatum(self, station_id, variable):
        return self.item2d(station_id, variable, 3)

    def time_zone(self, station_id, variable):
        return self.item2d(station_id, variable, 2)

    def adjustment(self, station_id, variable):
        return self.item2d(station_id, variable, 4)


def read_obs_links(fpath, base_dir=None):
    if base_dir is None:
        return ObsLinks(fpath)
    else:
        return ObsLinks(fpath, base_dir)
