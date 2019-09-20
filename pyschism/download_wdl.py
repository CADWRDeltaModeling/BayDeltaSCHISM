""" Download robot for water data library
    The main function in this file is wdl_download. Currently takes a list of stations, downloads data.
 
"""

import urllib2
import re
import zipfile
import os
import string
import datetime as dt
import numpy as np


def wdl_download(stations,years,dest_dir,overwrite=False):
    """ Download robot for Water Data Library
    First loads the stations page to see which variables are available 
    from a hardwired list (conductance, gage elevation, flow, etc). 
    Then it downloads all the years from years that are available for 
    those variables and adds the data to txt files one per station-variable. 
    """
    base_url = "http://wdl.water.ca.gov/waterdatalibrary/docs/Hydstra/docs"
    work_dir = "zipfiles"
    retain_zip = False
    dtime  = dt.datetime(1990,1,1)
    
    items = {"FLOW":"discharge",
             "STAGE":"gageheight",
             "CONDUCTIVITY":"conductance",
             "VELOCITY":"velocity",
             "ADCP_WATER_TEMPERATURE":"temperature",
             "WATER_TEMPERATURE":"temperature",
             "TURBIDITY":"turbidity"}

    if not os.path.exists(work_dir):
        os.mkdir(work_dir)

    for station in stations:
        station_query = "http://wdl.water.ca.gov/waterdatalibrary/docs/Hydstra/index.cfm?site=%s" % station
        response = urllib2.urlopen(station_query)
        station_html = response.read()
        params = [x for x in items if  "%s_"%x in station_html]
        for param in items.keys():
            station_param = "%s_%s" % (station,items[param])
            newname = "%s.csv" % station_param
            dest_path = os.path.join(dest_dir,newname)
            print(dest_path)
            if (os.path.exists(dest_path)):
                if overwrite:
                    os.remove(dest_path)
                else:
                    print("Skipping station/param/year because file exists: %s" % newname) 
                    continue
            
            file_created = False
            ndata = 0
            data_years = []
            for year in years:
                station_param_yr = "%s_%s_%s" % (station,items[param],year)
                searchzipstr = """%s/%s/%s/(%s.*.ZIP)""" % (base_url,station,year,param)
                yrzipfile = re.search(searchzipstr,station_html)
                searchcsvstr = """%s/%s/%s/(%s.*.CSV)""" % (base_url,station,year,param)
                yrcsvfile = re.search(searchcsvstr,station_html)
                if yrzipfile:
                    url = yrzipfile.group(0)                
                    response = urllib2.urlopen(url)
                    f = station_param_yr+".zip"
                    f = f.lower()
                    localname = os.path.join(".",work_dir,f)
                    with open(localname, "wb") as local_file:
                        local_file.write(response.read())
                    zf = zipfile.ZipFile(localname)
                    filenames = zf.namelist()
                    assert len(filenames) == 1
                    workfile = filenames[0]
                    workpath = os.path.join(work_dir,workfile)
                    zf.extractall(work_dir)
                    zf.close()
                    if not retain_zip:
                        os.remove(localname)                        
                    f = open(workpath,"r")
                    mode = "a" if file_created else "w"
                    destfile = open(dest_path,mode)
                    file_created = True
                    print("Working on %s" % workpath)
                    for line in f.readlines()[3:]:
                        if line and len(line) > 5:
                            ndata=ndata+1
                            dtm,val,flag = line.strip().split(",")
                            dtm = dtime.strptime(dtm,"%m/%d/%Y %H:%M:%S")
                            if val and not "\"" in val:
                                val = float(val)
                            else:
                                val = np.nan
                            if flag and not "\"" in flag:
                                flag = int(flag)
                            else:
                                flag = "no_flag"
                            destfile.write("%s,%s,%s\n" % (dtm.strftime("%m/%d/%Y %H:%M:%S"),val,flag))
                    f.close()
                    destfile.close()
                    os.remove(os.path.join(work_dir,workfile))
                    data_years.append(str(year))
                elif yrcsvfile:
                    url = yrcsvfile.group(0)                
                    response = urllib2.urlopen(url)
                    workfile = station_param_yr+".csv"
                    workfile = workfile.lower()
                    localname = os.path.join(".",work_dir,workfile)
                    with open(localname, "wb") as local_file:
                        local_file.write(response.read())
                    f = open(localname,"r")
                    mode = "a" if file_created else "w"
                    destfile = open(dest_path,mode)
                    file_created = True
                    print("Working on %s" % workfile)
                    for line in f.readlines()[3:]:
                        if line and len(line) > 5:
                            ndata=ndata+1
                            dtm,val,flag = line.strip().split(",")[:3]
                            dtm = dtime.strptime(dtm,"%m/%d/%Y %H:%M:%S")
                            if val and not "\"" in val:
                                val = float(val)
                            else:
                                val = np.nan
                            if flag and not "\"" in flag:
                                flag = int(flag)
                            else:
                                flag = "no_flag"
                            destfile.write("%s,%s,%s\n" % (dtm.strftime("%m/%d/%Y %H:%M:%S"),val,flag))
                    f.close()
                    destfile.close()
                    os.remove(os.path.join(work_dir,workfile))
                    data_years.append(str(year))
                    
            print("Data for station %s param %s in years: %s" % (station, param, string.join(data_years,",")))
            print("Total # data for %s: %s" % (station_param,ndata))
            #if ndata > 0: convert2netcdf(dest_path,ndata)
            
                    
if __name__ == '__main__':
    import sys
    stationlist = sys.argv[1]
    firstyr = int(sys.argv[2])
    stopyr = int(sys.argv[3]) + 1
    f = open(stationlist,"r")
    stations = [x.strip().split(",")[2] for x in f.readlines() if x and len(x) > 2]
    years = range(firstyr,stopyr)
    destdir = 'wdl_data'
    overwrite = False    
    wdl_download(stations,years,destdir,overwrite)

