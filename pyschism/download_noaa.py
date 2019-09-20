""" Script to download NOAA water level data
"""
import urllib2
import bs4
import calendar
import datetime as dtm
import re


stationlist = {"9414290":"San Francisco",
               "9414750":"Alameda",
               "9414523":"Redwood City",
               "9414575":"Coyote Creek",
               "9414863":"Richmond",
               "9415144":"Port Chicago",
               "9413450":"Monterey",
               "9415020":"Point Reyes",
               "9415102":"Martinez-Amorco Pier"}


name_to_id = dict((v,k) for k, v in stationlist.iteritems())


def retrieve_csv(url):
    response = urllib2.urlopen(url)
    return response.read()


def retrieve_table(url):
    done = False
    while not done:
        try:
            soup = bs4.BeautifulSoup(urllib2.urlopen(url))
            done = True
        except urllib2.URLError:
            print("Failed to retrieve %s" % url)
            print("Try again...")

    table = soup.table.pre.pre.string
    return table


def write_table(table, fname, first):
    f = open(fname, 'a')
    # Remove the Error line
    table = table[:table.find("Error")]
    if table[-1] != '\n':
        table += '\n'
    if first:
        f.write(table)
    else:
        pos = table.find('\n')
        f.write(table[pos+1:])
    f.flush()
    f.close()


def write_header(fname, headers):
    f = open(fname, 'w')
    for key, value in headers.iteritems():
        buf = "# \"%s\"=\"%s\"\n" % (key, value)
        f.write(buf)
    f.flush()
    f.close()


def retrieve_data(station_id, start, end, product=None):
    """ Download stage data from NOAA tidesandcurrents, and save it to
        NOAA CSV format.

        Parameters
        ----------
        station_id : int or str
            station id

        start : datetime.datetime
            first date to download

        end : datetime.datetime
            last date to download, inclusive of the date

        product : str
            production, it is either water_level or predictions.

    """
    if station_id in stationlist.keys():
        strstation = stationlist[station_id]
    else:
        strstation = station_id
        if station_id in name_to_id.keys():
            station_id = name_to_id[station_id]
    print("Station: %s"  % strstation)

    product_info = {"water_level" :      { "agency": "noaa",
                                           "unit": "meters",
                                           "datum": "NAVD",
                                           "station_id": "{}".format(station_id),
                                           "item": "elev",
                                           "timezone": "LST",
                                           "source": "http://tidesandcurrents.noaa.gov/"},
                    "predictions" :      { "agency": "noaa",
                                            "unit": "meters",
                                            "datum": "NAVD",
                                            "station_id": "{}".format(station_id),
                                            "item": "predicted_elev",
                                            "timezone": "LST",
                                            "source": "http://tidesandcurrents.noaa.gov/"},
                    "water_temperature" : { "agency": "noaa",
                                            "unit": "Celcius",
                                            "station_id": "{}".format(station_id),
                                            "item": "temperature",
                                            "timezone": "LST",
                                            "source": "http://tidesandcurrents.noaa.gov/"},
                    "conductivity"      : { "agency": "noaa",
                                            "unit": "microS/cm",
                                            "station_id": "{}".format(station_id),
                                            "item": "conductivity",
                                            "timezone": "LST",
                                            "source": "http://tidesandcurrents.noaa.gov/"}
                    }                                                      

    if product is None:
        product = 'water_level'
    fname = "{}_{}.txt".format(station_id,product)    
    if not product in product_info.keys():
        raise ValueError("Product not supported: {}".format(product))
    first = True
    headers = product_info[product]
    for year in range(start.year, end.year + 1):
        month_start = start.month if year == start.year else 1
        month_end = end.month if year == end.year else 12
        for month in range(month_start, month_end + 1):
            day_start = start.day if year == start.year and month == start.month else 1
            day_end = end.day if year == end.year and month == end.month else calendar.monthrange(year, month)[1]
            date_start = "%4d%02d%02d" % (year, month, day_start)
            date_end = "%4d%02d%02d" % (year, month, day_end)
            #https://tidesandcurrents.noaa.gov/api/datagetter?product=water_temperature&application=NOS.COOPS.TAC.PHYSOCEAN&begin_date=20120101&end_date=20120905&station=9414290&time_zone=lst&units=metric&interval=6&format=csv

            datum = "NAVD"
            url = "http://tidesandcurrents.noaa.gov/api/datagetter?product=%s&application=NOS.COOPS.TAC.PHYSOCEANL&station=%s&begin_date=%s&end_date=%s&datum=%s&units=metric&time_zone=LST&format=csv" % (product, station_id, date_start, date_end, datum)
            print("Retrieving %s, %s, %s..." % (station_id, date_start, date_end))
            print("URL: {}".format(url))
            # raw_table = retrieve_table(url)
            raw_table = retrieve_csv(url)
            if raw_table[0] == '\n':
                datum = "STND"
                url = "http://tidesandcurrents.noaa.gov/api/datagetter?product=%s&application=NOS.COOPS.TAC.PHYSOCEANL&station=%s&begin_date=%s&end_date=%s&datum=%s&units=metric&time_zone=LST&format=csv" % (product, station_id, date_start, date_end, datum)
                print("Retrieving Station %s, from %s to %s..." % (station_id, date_start, date_end))
                print("URL: {}".format(url))
                # raw_table = retrieve_table(url)
                raw_table = retrieve_csv(url)
            print("Done retrieving.")

            if first:
                headers["datum"] = datum
                write_header(fname, headers)
            write_table(raw_table, fname, first)
            first = False

def create_arg_parser():
    """ Create an ArgumentParser
    """
    import argparse
    parser = argparse.ArgumentParser(
        description="""Script to download NOAA 6 minute water level data """)
    parser.add_argument('--start', default=None, required=False, type=str,
                        help="First date to download")
    parser.add_argument('--end', default=None, required=False, type=str,
                        help='Last date to download, inclusive')
    parser.add_argument('--syear', default=None, required=False, type=int,
                        help="First year to download")
    parser.add_argument('--eyear', default=None, required=False, type=int,
                        help='Last year to download, inclusive to end'
                             ' of the year.')
    parser.add_argument('--product', default='water_level', required=False,
                        type=str,
                        help='Product to download: water_level, predictions, water_temperature, conductivity.')

    parser.add_argument('--stations', default=None, nargs="*", required=False,
                        help='Id or name of one or more stations.')
    parser.add_argument('--stationfile', default=None, required=False,
                        type=argparse.FileType('r'),
                        help='File listing stations in which the first column'
                             ' is ID number. Must be followed by space')
    parser.add_argument('--list', default=False, action='store_true',
                        help='List known station ids.')
    return parser


def list_stations():
    """ Show NOAA station ID's in our study area.
    """
    print("Available stations:")
    for key in stationlist.keys():
        print("%s: %s" % (key, stationlist[key]))


def assure_datetime(dtime, isend = False):
    if isinstance(dtime,dtm.datetime): 
        return dtime
    elif isinstance(dtime,unicode) or isinstance(dtime,str):
        if len(dtime) > 4:
            return dtm.datetime(*map(int, re.split(r'[^\d]', dtime)))
        elif len(dtime) == 4:
            return dtm.datetime(int(dtime),12,31,23,59) if isend else dtm.datetime(int(dtime),1,1)
        else:
            raise ValueError("Could not coerce string to date: {}".format(dtime))
    elif isinstance(dtime,int):
        return dtm.datetime(dtime,12,31,23,59) if isend else dtm.datetime(dtime,1,1)
        
 
        
def download_noaa(stations,product,start,end):
    start = assure_datetime(start)
    end = assure_datetime(end,isend=True)
        
    for id_ in stations:
        retrieve_data(id_, start, end, product=product)
        
def main():
    """ Main function
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    if args.list:
        list_stations()
        return
    else:
        if args.stations and args.stationfile:
            raise ValueError("Station and stationfile inputs are mutually exclusive")

        if not (args.stations or args.stationfile):
            raise ValueError("Either station or stationfile required")

        if args.start:
            start = dtm.datetime(*map(int, re.split(r'[^\d]', args.start)))
        else:
            start = None
        if args.end:
            end = dtm.datetime(*map(int, re.split(r'[^\d]', args.end)))
        else:
            end = None

        syear = args.syear
        eyear = args.eyear
        if syear or eyear:
            #from numpy import VisibleDeprecationWarning
            #raise VisibleDeprecationWarning("The syear and eyear arguments are deprecated. Please use start and end.")
            if syear and start:
                raise ValueError("syear and start are mutually exclusive")
            if eyear and end:
                raise ValueError("eyear and end are mutually exclusive")
            if syear:
                start = dtm.datetime(syear, 1, 1)
            if eyear:
                end = dtm.datetime(eyear + 1, 1, 1)

        if not start is None and not end is None:
            if start > end:
                raise ValueError("start %s is after end %s" %(start.strftime("%Y-%m-%d"),end.strftime("%Y-%m-%d")))

        if args.stations:
            # stations explicitly input
            stage_stations = args.stations
        else:
            # stations in file
            stage_stations = []
            for line in args.stationfile:
                if not line.startswith("#") and len(line) > 1:
                    sid = line.strip().split()[0]
                    print("station id=%s" % sid)
                    stage_stations.append(sid)

        return download_noaa(stage_stations,args.product,start,end)


if __name__ == "__main__":
    main()
