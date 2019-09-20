""" Download robot for water data library
    The main function in this file is cdec_download. 
    
    For help/usage:
    python cdec_download.py --help
"""
import argparse

import urllib2
import re
import zipfile
import os
import string
import datetime as dt
import numpy as np
params={"ec":[100],"ec_bot":[101,102],
        "flow":[20,21,23,70,75,110],
        "stage":[1],"temp":[4,25,258389,2741],"wind_speed":[9,134],"wind_dir":[10]}

      
def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that some hosts may not respond to a ping request even if the host name is valid.
    """
    from platform import system as system_name # Returns the system/OS name
    import subprocess as sp       # Execute a shell command  
    # Ping parameters as function of OS
    parameters = ["ping","-n","1",host] if system_name().lower()=="windows" else ["ping","-c","1",host]
    # Pinging
    with open(os.devnull, 'w') as devnull:
        return sp.call(parameters,stdout=devnull) == 0        
cdec_base_url = "cdec4gov.water.ca.gov" if ping("cdec4gov.water.ca.gov") else "cdec.water.ca.gov"        
       
        
def create_arg_parser():
    parser = argparse.ArgumentParser()
    paramhelp = 'Variable to download, should be in list:\n%s' % list(params.keys())
    
    parser.add_argument('--dest', dest = "dest_dir", default="cdec_download", help = 'Destination directory for downloaded files.')
    parser.add_argument('--cdec_col', default = 0, type = int, help = 'Column in station file representing CDEC ID. IDs with > 3 characters will be ignored.')
    parser.add_argument('--param_col', type = int, help = 'Column in station file representing the parameter to download.')
    parser.add_argument('--start',required=True,help = 'Start time, format 2009-03-31 14:00')    
    parser.add_argument('--end',default = None,help = 'Start time, format 2009-03-31 14:00')    

    parser.add_argument('--param',help=paramhelp)
    parser.add_argument('stationfile', help = 'CSV-format station file.')
    parser.add_argument('--overwrite',  action="store_true", help = 'Overwrite existing files (if False they will be skipped, presumably for speed')
    return parser


def cdec_download(stations,dest_dir,start,end="Now",param="ec",overwrite=False):
    """ Download robot for CDEC
    Requires a list of stations, destination directory and start/end date
    These dates are passed on to CDEC ... actual return dates can be
    slightly different
    """
    if end == None: end = "Now"
    if not type(param) == list:
        if not param in params.keys():
            raise ValueError("Requested param has no code in script or is incorrect")
        param=[param]*len(stations)
    paramcode=[params[p] for p in param]

    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)       
    failures = []
    skips = []
    for station,p,z in zip(stations,param,paramcode):
        print("Processing station: %s param: %s" % (station,p))
        path = os.path.join(dest_dir,"%s_%s.csv"% (station,p))
        if os.path.exists(path) and not overwrite:
            print("Skipping existing station because file exists: %s" % path)
            skips.append(path)
            continue
        stime=start.strftime("%m-%d-%Y")
        etime=end if end == "Now" else end.strftime("%m-%d-%Y")
        found = False
       
        for code in z:
            station_query_base = "http://%s/dynamicapp/req/CSVDataServlet?Stations=%s&SensorNums=%s&dur_code=%s&Start=%s&End=%s"
            #station_query_base = "http://%s/cgi-progs/queryCSV?station_id=%s&sensor_num=%s&dur_code=%s&start_date=%s&end_date=%s"
            dur_codes = ["E","H","D"]
            for dur in dur_codes:
                station_query = station_query_base % (cdec_base_url,station,code,dur,stime,etime)
                print(station_query)
                response = urllib2.urlopen(station_query)
                station_html = response.read().replace("\r","")
                if station_html.startswith("Title") or station_html.startswith("STATION_ID") and len(station_html) > 16:
                    found = True
                    with open(path,"w") as f:
                        f.write(station_html)
                    print("Found, duration code: %s" % dur)
                    break
            if found: break
        if not found: 
            print("Station %s query failed or produced no data" % station)
            failures.append(station)
    
    if len(failures) == 0:
        print("No failed stations")
    else:
        print("Failed query stations: ")
        for failure in failures:
            print(failure)


def process_station_list(file,cdec_ndx,param_ndx=None):
    stations = []
    variables = [] if param_ndx else None
    for line in open(file,'r'):
        if not line or line.startswith("#") or len(line) < (param_ndx+1): continue
        elements = line.strip().split(",")
        cdec_id = elements[cdec_ndx]
        param = elements[param_ndx] if param_ndx else None
        if len(cdec_id.strip()) == 3:
            stations.append(cdec_id)
            if param_ndx: variables.append(param)            
    return stations,variables
                
if __name__ == '__main__':

    parser = create_arg_parser()
    args = parser.parse_args()
    cdec_column = args.cdec_col
    param_column = args.param_col
    destdir = args.dest_dir
    stationfile = args.stationfile
    overwrite = args.overwrite
    param = args.param
    start = args.start
    end = args.end
    stime = dt.datetime(*map(int, re.split('[^\d]', start))) 
    if end:
        etime = dt.datetime(*map(int, re.split('[^\d]', end))) 
    else:
        etime = "Now"
    if param_column and param:
        raise ValueError("param_col and param cannot both be specified")
    if not (param_column or param):
        raise ValueError("Either param_col or param must be specified")
    
    if os.path.exists(stationfile):
        stations,variables = process_station_list(stationfile,cdec_column,param_column)
        if not variables: variables = [param]*len(stations)
        cdec_download(stations,destdir,
                      stime,
                      etime,
                      variables,overwrite)
    else:
        print("Station list does not exist")

