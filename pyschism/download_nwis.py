""" Download robot for Nationla Water Informaton System (NWIS)
    The main function in this file is nwis_download. 
    
    For help/usage:
    python nwis_download.py --help
"""
import argparse

import urllib2
import re
import zipfile
import os
import string
import datetime as dt
import numpy as np

def create_arg_parser():
    parser = argparse.ArgumentParser()
   
    parser.add_argument('--dest', dest = "dest_dir", default="nwis_download", help = 'Destination directory for downloaded files.')
    parser.add_argument('--start',required=True,help = 'Start time, format 2009-03-31 14:00')    
    parser.add_argument('--end',default = None,help = 'End time, format 2009-03-31 14:00')
    parser.add_argument('--param',default = None, help = 'Parameter(s) to be downloaded, e.g. \
    00065 = gage height (ft.), 00060 = streamflow (cu ft/sec) and 00010 = water temperature in degrees Celsius. \
    See "http://help.waterdata.usgs.gov/codes-and-parameters/parameters" for complete listing. \
    (if not specified, all the available parameters will be downloaded)')
    parser.add_argument('stationfile', help = 'CSV-format station file.')
    parser.add_argument('--overwrite', type = bool, default = False, help =  
    'Overwrite existing files (if False they will be skipped, presumably for speed)')
    return parser


def nwis_download(stations,dest_dir,start,end=None,param=None,overwrite=False):
    """ Download robot for NWIS
    Requires a list of stations, destination directory and start/end date
    These dates are passed on to CDEC ... actual return dates can be
    slightly different
    """
    if end == None: end = dt.datetime.now()
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir) 
        
    failures = []
    skips = []
    for station in stations:
        print("Downloading station: %s" % (station))
        path = os.path.join(dest_dir,"%s.rdb"% (station))
        if os.path.exists(path) and not overwrite:
            print("Skipping existing station because file exists: %s" % station)
            skips.append(path)
            continue
        stime=start.strftime("%Y-%m-%d")
        etime=end.strftime("%Y-%m-%d")
        found = False
        station_query_base = "http://nwis.waterservices.usgs.gov/nwis/iv/?sites=%s&startDT=%s&endDT=%s&format=rdb"
        if param:
            station_query_base = station_query_base + '&variable=%s'
            station_query = station_query_base % (station,stime,etime,param)
        else:
            station_query = station_query_base % (station,stime,etime)
        print(station_query)
        try: 
            response = urllib2.urlopen(station_query)
        except:
            failures.append(station)
        else:    
            station_html = response.read().replace("\r","")
            if len(station_html) > 30 and not "No sites found matching" in station_html:
                found = True
                with open(path,"w") as f:
                    f.write(station_html)
            if not found: 
                print("Station %s query failed or produced no data" % station)
                failures.append(station)
    
    if len(failures) == 0:
        print("No failed stations")
    else:
        print("Failed query stations: ")
        for failure in failures:
            print(failure)

def process_station_list(file):
    stations = []
    f = open(file,'r')
    all_lines = f.readlines()
    f.close()
    stations = [x.strip().split(',')[0] for x in all_lines if not x.startswith("#")]
    return stations
                
if __name__ == '__main__':
    parser = create_arg_parser()
    args = parser.parse_args()
    destdir = args.dest_dir
    stationfile = args.stationfile
    overwrite = args.overwrite
    start = args.start
    end = args.end
    param = args.param
    stime = dt.datetime(*map(int, re.split('[^\d]', start))) 
    if end:
        etime = dt.datetime(*map(int, re.split('[^\d]', end))) 
    else:
        etime = dt.datetime.now()
    
    if os.path.exists(stationfile):
        stations = process_station_list(stationfile)
        nwis_download(stations,destdir,stime,etime, param)  
    else:
        print("Station list does not exist")
        


