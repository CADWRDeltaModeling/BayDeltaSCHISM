#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" A class to read and use stations_utm database in CSV
"""
__all__ = ["StationDB",]



class StationDB(object):
    """ Read a station DB in csv format, and provide station information
    """
    def __init__(self, fname):
        """ Constructor

            fname:
                csv station file
        """
        import csv
        self.data={}
        self.header = None
        with open(fname,"r") as f:
            dialect = csv.Sniffer().sniff(f.read(2048),delimiters=",")
            f.seek(0)
            r = csv.reader(f)

            for line in r:
                if not self.header:
                    columns = [item.lower() for item in line]
                    self.header = columns
                    self.ndx_station_id = columns.index("id")
                    self.ndx_name = columns.index("name")
                    self.ndx_alias = columns.index("alias_id2")
                    self.x_name=columns.index("point_x")
                    self.y_name=columns.index("point_y")
                else:
                    data = line
                    id = str(data[self.ndx_station_id])
                    if len(data) == len(self.header):
                        self.data[id] = data
                    else:
                        raise ValueError("Station with id %s has incorrect number of columns compared to header (%s vs %s)" % (id,len(data),len(self.header)))

    def ids(self):
        return list(self.data.keys())
                        
                        
    def alias(self, station_id):
        """ Get an alias of a station with ID
            station_id:
                station name
        """
        alias = None
        if station_id in self.data:
            alias = self.data[station_id][self.ndx_alias]
        return alias

    def name(self, station_id):
        """ Get a long name of a station with an ID

            Parameters
            ----------
            station_id:
                station name

            Returns
            -------
            str
                a long name of a station
        """
        long_name = None
        if station_id in self.data:
            long_name = self.data[station_id][self.ndx_name]
        return long_name

    def xy(self, station_id):
            """ Get coordinates of station with station_id

                Parameters
                ----------
                station_id:
                    station name

                Returns
                -------
                loc : array
                    a tuple length 2 with x and y coordinate
            """
            
            if station_id in self.data:
                x = float(self.data[station_id][self.x_name])
                y = float(self.data[station_id][self.y_name])
                return (x,y)        
            else:
                return None
        
    def station_ids_from_alias(self, alias):
        ids = [x for x in self.data if self.data[x][self.ndx_alias] == alias]
        return ids

    def station_attribute(self, station_id, attrname):
        if not station_id in self.data:
            raise ValueError("Station ID not on station list")
        try:
            ndx = self.header.index(attrname)
            return self.data[station_id][ndx]
        except:
            print("Dumping column headers: ")
            # import string
            print(self.header) #string.join(self.header,",")
            raise ValueError("Unable to retrieve attribute %s for station_id %s" % (attrname,station_id))

    def exists(self, station_id):
        """ Check if the station_id is in the database
        """
        return True if station_id in self.data else False

