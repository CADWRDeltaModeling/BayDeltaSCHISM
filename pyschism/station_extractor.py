# -*- coding: UTF-8 -*-
""" Routines to read in SCHISM STAOUT_* and flux.dat files.
"""

from schism_yaml import load_raw
from vtools.data.timeseries import *
import numpy as np
import collections
import math
import datetime
import re
import csv
import sys
import os

__all__ = ['station_extractor', 'flow_extractor', 'station_variables']
station_variables = ["elev", "air pressure", "wind_x", "wind_y",
                     "temp", "salt", "u", "v", "w"]

# Ordered Dict YAML
# From http://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts
def dict_representer(dumper, data):
    return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, iter(data.items()))


def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))


class StationReader(object):
    """ SCHISM STAOUT reader
    """
    def __init__(self, working_dir, time_basis):
        """ Constructor

            Parameters
            ----------

            working_dir: A working directory where STAOUT_* reside

            time_basis: A time basis of the STAOUT_*
        """
        self._working_dir = working_dir
        self._time_basis = time_basis
        self._station_variables = station_variables
        self._variable_table = {"S": "salt", "T": "temp", "windx": "wind_x",
                                "windy": "wind_y"}
        self.data = list([None for _ in range(len(self._station_variables))])
        self._output_items = None
        self._stations = None
        self._item_dimension = [2, 2, 2, 2, 3, 3, 3, 3, 3]
        # TODO: Need to check the unit
        self._item_units = ["meter", "N/sqm", "m/s", "m/s", "deg C", "PSU",
                            "m/s", "m/s", "m/s"]
        self._station_id_to_index = None

    @property
    def stations(self):
        """ Station getter """
        return self._stations

    def read_station_in(self, fpath):
        """ Read in 'station.in.'
            'station.in' should contains station IDs and description.

            Parameters
            ----------
            fpath: a file path of 'station.in' to read
        """
        stations = list()
        print("Reading {}".format(fpath))
        
        with open(fpath, 'r') as f:
            # First line, output items
            tkns = f.readline().split()
            if len(tkns) < 9:
                raise ValueError("Not enough items in the first line.")
            items = list(map(int, tkns[:9]))
            self._output_items = items
            # Second line, # of output locations
            tkns = f.readline().split()
            if len(tkns) < 1:
                raise ValueError("Not enough items in the second line.")
            n_stations = int(tkns[0])
            pattern = r"^(\s*\w+\s+[-\w.]+\s+[-\w.]+\s+[-\w.]+)\s+!?\s*(.*)"
            pattern_annotation = r"(\w+)\s*(.+)*"
            # Loop through stations
            for i in range(n_stations):
                line = f.readline()
                matched = re.match(pattern, line)
                if matched is None:
                    print("Error in line %d: %s" % (i + 3, line))
                    raise ValueError("station.in is not well formatted.")
                tkns = line.split()
                coords = tuple(map(float, tkns[1:4]))
                annotation = matched.group(2).strip()
                name = None
                desc = None
                matched = re.match(pattern_annotation, annotation)
                if matched is not None:
                    g = matched.groups()
                    name = g[0]
                    desc = g[1] if g[1] != "" else None
                else:
                    name = 'ST_%d' % (i + 1)
                    desc = 'Station %d' % (i + 1)
                station = {"coords": coords,
                           "name": name,
                           "desc": desc}
                stations.append(station)
        self._stations = stations
        self._map_station_ids()
        self._sort_stations_by_depth()
        self._check_integrity_stations()
        print("Done reading station.in.")

    def _map_station_ids(self):
        station_ids = dict()
        for index, station in enumerate(self._stations):
            station_id = station["name"]
            if station_id is not None:
                if station_id in station_ids:
                    station_ids[station_id] .append(index)
                else:
                    station_ids[station_id] = [index]
        self._station_id_to_index = station_ids

    def _sort_stations_by_depth(self):
        """ Sort stations with the same id.
        """
        for station_id, indices in self._station_id_to_index.items():
            if len(indices) > 1:
                depths = [(self._stations[i]["coords"][2], i) for i in indices]
                depths = sorted(depths, reverse=True)
                self._station_id_to_index[station_id] = list(zip(*depths))[1]
                for i, index in \
                    enumerate(self._station_id_to_index[station_id]):
                    self._stations[index]["vert_pos"] = i
            else:
                self._stations[indices[0]]["vert_pos"] = 0


    def _check_integrity_stations(self):
        """ Check integrity of stations """
        # Check station coords per ID
        for station_id, indices in self._station_id_to_index.items():
            if station_id is not None and len(indices) > 1:
                all_coords = [self._stations[i]["coords"][:2] for i in indices]
                counted = collections.Counter(all_coords)
                if len(counted) != 1:
                    print("WARNING: These stations have the same name " \
                          "but do not have an identical horizontal position.")
                    print("  Station:", station_id, ", indices:", indices)

        # Check duplicate coords
        all_coords = [station["coords"] for station in self._stations]
        counted = collections.Counter(all_coords)
        for coords, count in counted.items():
            if count > 1:
                stations = list()
                for index, station in enumerate(self._stations):
                    if station["coords"] == coords:
                        stations.append((index, station["name"]))
                print("WARNING: These stations have an identical position.")
                print("  Pos: %f, %f, %f" % coords)
                for station in stations:
                    print("  %d: %s" % (station[0], station[1]))

    def set_tss_prop(self, tss, unit):
        for ts in tss:
            ts.props['timestamp'] = 'INST-VAL'
            ts.props['aggregation'] = 'INST-VAL'
            ts.props['unit'] = unit

    def retrieve_ts(self, variable, index=None, name=None, depth=None):
        """ Retrieve a time series of an output constituent for a station
            NOTE: For output with extra vertical outputs.

            Parameters
            ----------
            variable:
                A variable to read in. Currently, it should be one of
                elev, salt.
            index:
                index of the station in station.in. Zero-based.
            name:
                station ID
            depth:
                depth of the station

            Returns
            -------
            a time series
        """
        try:
            if variable in self._variable_table:
                variable = self._variable_table[variable]
            var_index = self._station_variables.index(variable)
        except IndexError:
            msg = "Not supported variable name: %s\n" % variable
            sys.stderr.write(msg)
            raise ValueError()
        if index is None:
            if name is None:
                raise ValueError("Coord or station ID must be provided.")
            if not name in self._station_id_to_index:
                # raise ValueError("No matching station for %s" % name)
                print("Warning: No matching station for %s in station.in" \
                      % name)
                return None
            indices = self._station_id_to_index[name]
            if len(indices) == 1:
                index = indices[0]
            else:
                if self._item_dimension[var_index] == 3:
                    if depth is None:
                        raise ValueError("Coord or station ID and depth "
                                         "must be provided.")
                    else:
                        index = self._station_id_to_index[name][depth]
                else:  # 2D
                    index = indices[0]

        if self.data[var_index] is not None:
            return self.data[var_index][index]
        fname = "staout_%d" % (var_index + 1)
        fname = os.path.join(self._working_dir, fname)
        tss = self.read_stdout(fname)
        print("Reading %s..." % fname)

        if len(tss) != len(self._stations):
            raise ValueError("# of stations in station.in ({}) and staout ({}) do not "
                              "correspond.".format(len(self._stations),len(tss)))
        unit = self._item_units[var_index]
        self.set_tss_prop(tss, unit)
        self.data[var_index] = tss
        return self.data[var_index][index]

    def read_stdout(self, fname):
        """ Read the whole staout into the memory.
            Each column will be converted into
            vtools.data.timeseries.TimeSeries.
        """
        raw = np.loadtxt(fname)
        # Get the first time stamp
        ts_begin = datetime.timedelta(seconds=raw[0, 0])
        # Get dt
        for i in range(raw.shape[0]):
            dt = raw[i+1, 0] - raw[i, 0]
            if dt > 0.:
                if i > 0:
                    raw = raw[::i+1]
                dt = datetime.timedelta(seconds=dt)
                break
        # Remove dry spots
        raw[raw < -100.] = np.nan
        # Convert into Vtools time series
        tss = list()
        for i in range(1, raw.shape[1]):
            ts = rts(raw[:, i], self._time_basis + ts_begin, dt)
            tss.append(ts)
        return tss


def station_extractor(station_file, working_dir, time_basis):
    """ Create a staout, SCHISM standard output file, extractor

        Parameters
        ----------
        station_file:
            A staout file path to read
        working_dir:
            A directory where staout file resides
        time_basis:
            A time basis of the staout file

        Returns
        -------
        An instance of the station extractor
    """
    sr = StationReader(working_dir, time_basis)
    sr.read_station_in(station_file)
    return sr


class FlowReader(object):
    """ SCHISM flux.dat reader
    """

    # class Station(object):
    #     def __init__(self, name, coord):
    #         self._name = name
    #         self._coord = coord

    #     def __str__(self):
    #         return "%s, (%f, %f ,%f, %f)" % (self._name,
    #             self._coord[0], self._coord[1],
    #             self._coord[2], self._coord[3])

    #     @property
    #     def name(self):
    #         return self._name
    #     @name.setter
    #     def name(self, value):
    #         self._name = value

    #     @property
    #     def coord(self):
    #         return self._coord

    #     @coord.setter
    #     def coord(self, value):
    #         self._coord = value

    def __init__(self, working_dir, time_basis):
        """ Constructor

            Parameters
            ----------
            working_dir: A full path of flux.dat
            time_basis: A time basis of the flux.dat
        """
        self._working_dir = working_dir
        self._time_basis = time_basis
        self._items = None
        self.data = None
        
        self._flow_fname = 'flux.out' if os.path.exists(os.path.join(working_dir,'flux.out')) else 'flux.dat'
        self._stations = None
        self._station_id_to_index = None

    @property
    def flow_fname(self):
        return self._flow_fname

    @flow_fname.setter
    def flow_fname(self, value):
        self._flow_fname = value

    @property
    def stations(self):
        return self._stations

    def read_flow_input(self, fpath):
        """ Read in 'flowlines.yaml'

            Parameters
            ----------
            fpath: a file path of the input
        """
        # yaml.add_representer(collections.OrderedDict, dict_representer)
        # yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        #                      dict_constructor)
        with open(fpath, 'r') as f:
            flowlines = load_raw(f)['linestrings']
            self._stations = flowlines
            self._map_station_ids()

    def retrieve_ts(self, name=None):
        """ Retrieve a time series of an output constituent for a station

            Parameters
            ----------
            name: str
                station ID in flowlines.yaml

            return
            ------
            vtools.data.timeseries.TimeSeries
                a flow time series
        """
        if name not in list(self._station_id_to_index.keys()):
            print(name, self._station_id_to_index)
            # raise ValueError("No matching station for %s" % name)
            print("Warning: No matching station for %s in station.in" % name)
            return None
        indices = self._station_id_to_index[name]

        if len(indices) < 1:
            print("More than two outputs with the same name.")
            print("Use the first one.")

        if self.data is None:
            print("Reading flow...: {}".format(self.flow_fname))
            fname = os.path.join(self._working_dir, self.flow_fname)
            self.data = self.read_all(fname)
        return self.data[indices[0]]

    def read_all(self, fname):
        try:
            raw = np.loadtxt(fname)
        except:
            print("Failure reading file with loadtxt: %s" % fname)
            raise
        # Get the first time stamp
        ts_begin = datetime.timedelta(seconds=np.around(raw[0, 0]*86400))
        # Get dt
        for i in range(raw.shape[0]):
            dt = np.around((raw[i+1, 0] - raw[i, 0])*86400.)
            if dt > 0.:
                if i > 0:
                    raw = raw[::i+1]
                dt = datetime.timedelta(seconds=dt)
                break
        # Convert into Vtools time series
        tss = list()
        for i in range(1, raw.shape[1]):
            ts = rts(raw[:, i], self._time_basis + ts_begin, dt)
            ts.props['aggregation'] = 'INST-VAL'
            ts.props['timestamp'] = 'INST-VAL'
            ts.props['unit'] = 'cms'
            tss.append(ts)
        return tss

    def _map_station_ids(self):
        station_ids = dict()
        for index, station in enumerate(self._stations):
            station_id = station.get("name")
            if station_id is not None:
                if station_id in station_ids:
                    station_ids[station_id].append(index)
                else:
                    station_ids[station_id] = [index]
        self._station_id_to_index = station_ids


def flow_extractor(flow_input_file, working_dir, time_basis):
    """ Create a flow extractor

        Return
        ------
        FlowReader object
    """
    fr = FlowReader(working_dir, time_basis)
    fr.read_flow_input(flow_input_file)
    return fr


# def create_arg_paresr():
#     """ Create a argparse parser and return it """
#     description = "Manage standard outputs from SCHISM"
#     parser = argparse.ArgumentParser(description=description)
#     parser.add_argument('--station_file', dest="statino_file",
#                         help = "file name to write the list of station_list.")
#     return parser


# if __name__ == "__main__":
#     arg_parser = create_arg_parsen()
#     args = arg_parser.parse()

