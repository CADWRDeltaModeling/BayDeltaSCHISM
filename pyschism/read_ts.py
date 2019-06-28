# -*- coding: utf-8 -*-
""" Routines to read field data files
"""

from vtools.data.vtime import infer_interval
import vtools.data.vtime as vtt
import vtools.data.timeseries as vts
import numpy
import abc
import datetime
import re
import sys

__all__ = ['read_ts', 'read_noaa', 'read_wdl', 'read_cdec',
           'read_usgs', 'read_usgs_rdb','read_vtide']

class TextTimeSeriesReader(object):
    """ Base class to read in time series of field data in various text
        formats.
        This class is designed to be inherited. A user needs to implement
        key abstract methods to read different formats:
        'parse_datetime' and 'parse_value' are function to parse date & time
        and value from a line.
        'set_ts_props' is called at the end of reading routines to set
        properties of vtools.data.timeseries.TimeSeries.
        To use 'is_reabable' function for automatic file format detection,
        class attribute '_record_regex,' which is a regular expression to
        tell a format, must be set before calling
        'is_readable.' '__init__' function would be a good place to do so.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self._record_regex = None
        self._header_approval_regexes = None
        self._header_regexs = [r'"?(?P<key>\w*)"?\s?=\s?"?(?P<value>\w*)"?',]
        self._prop_key_table = dict()
        self._prop_value_table = {"m": "meter"}
        self.n_lines_to_check = 300
        # Default timezone table
        self._timezone_table = {
            'PST': vtt.hours(0),
            'PDT': vtt.hours(-1),
            'LST': vtt.hours(0)
            }
        self._comment_indicators = '#'

    @property
    def record_regex(self):
        """ record pattern getter
        """
        return self._record_regex

    @record_regex.setter
    def record_regex(self, value):
        """ record pattern setter
        """
        self._record_regex = value

    @property
    def header_regexs(self):
        return self._header_regexs
    @header_regexs.setter
    def header_regexs(self, value):
        self._header_regexs = value

    @property
    def prop_key_table(self):
        return self._prop_key_table
    @prop_key_table.setter
    def prop_key_table(self, value):
        self._prop_key_table = value

    def is_comment(self, line):
        return line[0] in self._comment_indicators

    def is_record(self,line):
        return True if re.match(self._record_regex, line) else False

    def cull_using_selector(self,arr):
        pass

    def is_readable(self, fpath, nlines_check=None):
        """ Check if the file fits to the record pattern in the reader.
            '_record_regex' must be set before calling this
            function.

            Parameters
            ----------
            fpath: str
                file name to test

            Returns
            -------
            boolean
                True if the reader believes it is appropriate
                False otherwise.
        """
        if nlines_check:
            n_lines_to_check = nlines_check
        else:
            n_lines_to_check = self.n_lines_to_check

        if self._record_regex is None:
            raise ValueError("The record pattern in the reader" \
                             "must be set first.")
        with open(fpath, 'r') as f_in:
            line_i = 0
            for line in f_in:
                line = line.strip()
                # print line_i, line
                if len(line) == 0:
                    continue
                # Look through the top n lines only
                if line_i > n_lines_to_check:
                    return False
                # attempt to approve the file using the header if appropriate
                if self._header_approval_regexes:
                    for regex in self._header_approval_regexes:
                        match = re.search(regex, line)
                        if match:
                            return True
                match = re.match(self._record_regex, line)
                if match is not None:
                    return True
                line_i += 1
        return False


    def process_header(self, fpath,selector=None):
        """Process the header, producing the number of header lines, the list of variables in the file, the units of those variables and a list of
           station metadata. Note that for many formats some or all of these are scant, missing or inapplicable and will be returned as None.

           Parameters
           ----------

            fpath: str
                filepath to read

           Returns
           -------
            n_headerlines: int The number of the lines in the header, allowing unchecked fast forward

            last_n_lines: str
            The last n lines of the header

            metadata: Dictionary
            Dictionary of name-value pairs of attributes for the station or sensor

        """
        n_headerlines = self.count_headers(fpath)
        metadata = self.read_metadata_from_header(fpath)
        if selector:
            raise ValueError("selector not implemented")
        return n_headerlines, metadata

    def read_metadata_from_header(self, fpath):
        """ Read useful information from a file header

            Parameters
            ----------
            fpath: str
                filepath to read
            n_headerlines: int, optional
                Number of header lines other than comments
            comments: str, optional
                Characters indicating comments

            Returns
            -------
            dict
                metadata in a hash table
        """
        with open(fpath, 'r') as f_in:
            metadata = dict()
            for line in f_in:
                line = line.strip()
                if len(line) < 1 or not self.is_comment(line):
                    break
                for pattern in self._header_regexs:
                    m = re.search(pattern, line)
                    if m is not None:
                        k = m.groupdict()["key"]
                        v = m.groupdict()["value"]
                        if k in self._prop_key_table.keys():
                            k = self._prop_key_table[k]
                        if v in self._prop_value_table.keys():
                            v = self._prop_value_table[v]
                        metadata[k] = v
            return metadata


    def count_headers(self, fpath):
        """ Count the number of lines in the header of the file.
        """
        if self._record_regex is None:
            raise ValueError("The pattern of a record must be set before use.")
        hcount = -1
        with open(fpath, 'r') as f_in:
            for line_i, line in enumerate(f_in):
                if not self.is_comment(line):
                    if self.is_record(line):
                        hcount = line_i
                        return hcount
        raise ValueError("Could not find any records")
        if hcount < 0:
            raise ValueError("Could not find a data record in file %s while counting header lines" % fpath)
    @abc.abstractmethod
    def parse_datetime(self, line):
        """ A function to parse out date & time from a line.
            This is an empty abstract and needs to be defined in a child class.

            Parameters
            ----------
            line: str
                a line to parse

            Returns
            -------
            datetime.datetime
                parsed datetime.datetime
        """
        return

    @abc.abstractmethod
    def parse_value(self, line):
        """ A function to parse out a value & time from a line.
            This is an empty abstract and needs to be defined in a child class.

            Parameters
            ----------
            line: str
                a line to parse

            Returns
            -------
            datetime.datetime
                parsed value
        """
        return

    def parse_record(self,line):
        """ This is a first cut that should be backward compatible"""
        return self.parse_datetime(line), self.parse_value(line)

    def read(self, fpath, start=None, end=None, force_regular=True, selector=None):
        """ Read a text file with the given pattern and parsers.
            Parsers and a pattern must be defined and set in the child class.

            Parameters
            ----------
            fpath: str
                file to read
            start: datetime.datetime, optional
                datetime to start reading in.
                If None, read from the start of the file
            end: datetime.datetime, optional
                datetime to finish reading in.
                If None, read till the end of the file
            force_regular: boolean, optional
                If it is true, it returns a regular time series

            Returns
            -------
            vtools.data.timeseries.TimeSeries
                time series from the file
        """
        # The selector (if it exists) can probably be precalculated or at least recorded.
        # Almost always this amounts to picking variables out of a list of column names
        # and recording indexes, but here we don't ask any questions about what "selector" is.
        n_headerlines, metadata = self.process_header(fpath,selector)
        if n_headerlines is None: raise ValueError("Problem counting header lines (check format?)")
        metadata = dict()
        if not self._header_regexs is None:
            metadata = self.read_metadata_from_header(fpath)
        if not start is None and not end is None:
            if start >= end:
                raise ValueError("The end time must be later than the start")


        with open(fpath, 'r') as f_in:
            times = list()
            values = list()
            # fast forward past header
            if n_headerlines > 0:
                for _ in range(n_headerlines):
                    f_in.readline()
            # process lines starting from current file pointer
            for i, line in enumerate(f_in):
                if self.is_comment(line):
                    continue

                timestamp, vals = self.parse_record(line)
                if start and timestamp < start:
                    continue
                if end and timestamp > end:
                    break
                times.append(timestamp)
                values.append(vals)

        if len(times) < 1:
            return None

        arr = numpy.array(values)

        # Here I assumed that it is more effective to retrieve too much
        # in the reading stage and then do this with numpy fancy indexing.
        # I But you can override this function
        # todo: never seemed complete selector handled elsewhere
        #arr = self.cull_using_selector(arr)
        ts = vts.its(times, arr)


        if force_regular:
            interval = infer_interval(times[:11],
                                      fraction=0.5,
                                      standard=[vtt.minutes(6),
                                                vtt.minutes(10),
                                                vtt.minutes(15),
                                                vtt.hours(1),
                                                vtt.days(1)])
            if not interval:
                # for t in times[:10]:
                #     print t.strftime("%Y-%m-%d %H:%M:%S")
                raise ValueError("Interval could not be inferred from first time steps in %s" % fpath)
            import warnings
            # todo: this really should be an option
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ts = vts.its2rts(ts, interval)
            # if start is not None:
            #     if start < ts.start:
            #         print "extending front..."
            #         ts = vts.extrapolate_ts(ts, start=start)
            #         print ts.times, ts.data
            #     else:
            #         ts = ts.window(start=start)
            # if end is not None:
            #     if end > ts.end:
            #         print "extending back..."
            #         ts = vts.extrapolate_ts(ts, end=end)
            #     else:
            #         ts = ts.window(end=end)
        for k, v in metadata.iteritems():
            ts.props[k] = v

        return ts



class VTideReader(TextTimeSeriesReader):
    """ Reader for VTide text file.
        The format has no header, date time in format 2009-12-24 00:25 and space-delimited fields
    """
    def __init__(self):
        super(VTideReader, self).__init__()
        self._record_regex = r"(?P<datetime>\d{4}\-\d{2}\-\d{2}\s\d{2}:\d{2})\s(?P<value>[-\d\.\s]*$)"
        self._header_approval_regexes = [r""]

    def parse_datetime(self, line):
        pass

    def parse_value(self, line):
        pass

    def parse_record(self, line):
        parts = line.strip().split(' ')
        timestamp = datetime.datetime.strptime(parts[0] + parts[1],
                                               "%Y-%m-%d%H:%M")

        # Please do not revert this code. It used to put a nan in for anything that fails to parse
        # If this doesn't cover nan, we need to learn about the other codes in the data dictionary
        value = [float(x) for x in parts[2:] if x != ""]
        return timestamp, value


def read_vtide(fpath, start=None, end=None, force_regular=True):
    reader = VTideReader()
    return reader.read(fpath, start, end, force_regular)



class CDECReader(TextTimeSeriesReader):
    """ CDEC Reader class to read in CDEC style text file.
        The fields of the CDEF format are delineated with ',' e.g.
        20140101,0110,1000 (Day, hour, value)
    """
    def __init__(self):
        super(CDECReader, self).__init__()
        self._record_regex = r"(?P<datetime>\d{8},\d{4}),(?P<value>[-\d.]*)"
        self._header_approval_regexes = [r"Title:\s\"[A-Z0-9\_\-]*\.csv\""]

    def parse_datetime(self, line):
        pass

    def parse_value(self, line):
        pass

    def parse_record(self, line):
        parts = line.strip().split(',')
        timestamp = datetime.datetime.strptime(parts[0] + parts[1],
                                               "%Y%m%d%H%M")

        # Please do not revert this code. It used to put a nan in for anything that fails to parse
        # If this doesn't cover nan, we need to learn about the other codes in the data dictionary
        value = float(parts[2].replace("m","nan"))
        return timestamp, value


    
class CDECReader2(TextTimeSeriesReader):
    """ CDEC Reader class revised 2018 to read in CDEC style text file.
        The fields of the CDEF format are delineated with ',' e.g.
        20140101,0110,1000 (Day, hour, value)
    """
    def __init__(self):
        super(CDECReader2, self).__init__()
        #STATION_ID,DURATION,SENSOR_NUMBER,SENSOR_TYPE,DATE TIME,OBS DATE,VALUE,DATA_FLAG,UNITS
        # FPT,H,1,RIV STG,20181123 1000,,103.27, ,FEET
        # DSJ,E,20,FLOW,20071001 0100,,7283, ,CFS
        self._record_regex = r"(?P<id>[\w]{3}),.*?,.*?,.*?,(?P<datetime>\d{8} \d{4}),.*?,(?P<value>[-\d.]*),.*?"
        #self._record_regex = r"(?P<datetime>\d{8},\d{4}),.*?,(?P<value>[-\d.]*),.*?,.*?"        
        self._header_approval_regexes = [r"STATION_ID,DURATION,SENSOR_NUMBER.*"]

    def parse_datetime(self, line):
        pass

    def parse_value(self, line):
        pass

    def parse_record(self, line):
        parts = line.strip().split(',')
        timestamp = datetime.datetime.strptime(parts[4],
                                               "%Y%m%d %H%M")

        # Please do not revert this code. It used to put a nan in for anything that fails to parse
        # If this doesn't cover nan, we need to learn about the other codes in the data dictionary
        value = float(parts[6].replace("m","nan").replace("---","nan"))
        return timestamp, value
           
        
def read_cdec(fpath, start=None, end=None, force_regular=True):
    reader = CDECReader()
    return reader.read(fpath, start, end, force_regular)


class NOAAReader(TextTimeSeriesReader):
    """ NOAA Reader class to read in NOAA style text file.
        The format of NOAA file has a fixed field lengths.
        e.g.
        1234567 19920307 00:00 0.32758 0.32758
        It is assumed that the first two records are healthy, and
        delta t is assumed by the first two when a regular time series is
        requested.
    """
    def __init__(self):
        super(NOAAReader, self).__init__()
        self._record_regex = r"\d+\s(?P<datetime>\d+\s+\d{2}:\d{2})" \
                               r"\s+[-\d.]*\s+(?P<value>[-\d.]*)"

    def parse_datetime(self, line):
        timestamp = datetime.datetime.strptime(line[8:22],
                                               "%Y%m%d %H:%M")
        return timestamp

    def parse_value(self, line):
        try:
            value = float(line[31:])
        except ValueError, IndexError:
            value = numpy.nan
        return value

    def set_ts_props(self, ts):
        ts._props['agency'] = 'noaa'



def read_noaa(fpath, start=None, end=None, force_regular=True):
    reader = NOAAReader()
    return reader.read(fpath, start, end, force_regular)


class WDLReader(TextTimeSeriesReader):
    """ CSV Reader class to read in data from WDL style CSV files.
        The format of WDL file is delimited with commas, e.g.
            10/01/2008 00:00:13,3.16,1
    """
    def __init__(self):
        super(WDLReader, self).__init__()
        self._record_regex = r"(?P<datetime>\d{1,2}\/\d{1,2}\/\d{4}" \
                               r"\s+\d{1,2}:\d{2}:\d{2}),\s*(?P<value>[-\w.]*)"

    def parse_datetime(self, line):
        parts = line.split(',')
        timestamp = datetime.datetime.strptime(parts[0],
                                               "%m/%d/%Y %H:%M:%S")
        return timestamp

    def parse_value(self, line):
        parts = line.split(',')
        try:
            text = parts[1].strip()
            value = float(text) if len(text) > 0 else numpy.nan
        except ValueError, IndexError:
            value = numpy.nan
        return value

    def set_ts_props(self, ts):
        ts._props['agency'] = 'wdl'



def read_wdl(fpath, start=None, end=None, force_regular=True):
    reader = WDLReader()
    return reader.read(fpath, start, end, force_regular)


class DESReader(TextTimeSeriesReader):
    """ CSV Reader class to read in data from DES style CSV files.
        The format of WDL file is delimited with commas, e.g.
            2009-03-01 00:00,371.0,G
    """
    def __init__(self):
        super(DESReader, self).__init__()
        self._record_regex = r"(?P<datetime>\d{4}-\d{2}-\d{2}\s+" \
                               r"\d{2}:\d{2}(:\d{2})?)\s*(?P<value>([-\w.]+)?)"

    def parse_datetime(self, line):
        parts = line.split(',')
        time_string = parts[0]
        if time_string.count(':') == 1:
            timestamp = datetime.datetime.strptime(time_string,
                                                   "%Y-%m-%d %H:%M")
        else:
            timestamp = datetime.datetime.strptime(time_string,
                                                   "%Y-%m-%d %H:%M:%S")
        return timestamp

    def parse_value(self, line):
        parts = line.split(',')
        try:
            text = parts[1].strip()
            if text == 'None':
                value = numpy.nan
            else:
                value = float(text) if len(text) > 0 else numpy.nan
        except IndexError:
            print 'missing field??', line
            value = numpy.nan
        return value



def read_des(fpath, start=None, end=None, force_regular=True):
    reader = DESReader()
    return reader.read(fpath, startrt, end, force_regular)


class USGSReader(TextTimeSeriesReader):
    """ Reader class to read in data from USGS file.
        Fields are delimited by tabs. The format is as follows:
        03/07/1992  00:00:00    PST 0.327579    6           A
    """
    def __init__(self):
        super(USGSReader, self).__init__()
        self.record_regex = \
            r"(?P<datetime>\d{2}\/\d{2}\/\d+\s\d{2}:\d{2}:\d{2})" \
            r"\s(?P<timezone>\w{3})\s(?P<value>(\s|[-\d.]+))"

    def parse_datetime(self, line):
        parts = line.split('\t')
        # timestamp = datetime.datetime.strptime(parts[0] + parts[1],
        #                                        "%m/%d/%Y%H:%M:%S")
        timestamp_parts = re.split(r'[^\d]', parts[0] + ' ' + parts[1])
        timestamp_parts = [timestamp_parts[i] for i in [2, 0, 1, 3, 4, 5]]
        timestamp = datetime.datetime(*map(int, timestamp_parts))
        timezone = parts[2]
        timestamp += self._timezone_table[timezone]
        return timestamp

    def parse_value(self, line):
        parts = line.split('\t')
        text = parts[3].strip()
        value = float(text) if len(text) > 0 else numpy.nan
        return value


def read_usgs(fpath, start=None, end=None, force_regular=True):
    reader = USGSReader()
    return reader.read(fpath, start, end, force_regular)


class USGS2Reader(TextTimeSeriesReader):
    """ Reader class to read in data from one of USGS file formats.
        The fields are delimited by tabs.
        USGS    11458000    2013-08-01 00:00    PDT 0.00    A
    """
    def __init__(self):
        super(USGS2Reader, self).__init__()
        self.n_lines_to_check = 30
        self.record_regex = \
            r"\w*\s\d*\s(?P<datetime>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})" \
            r"\s(?P<timezone>\w*)\s(?P<value>[-\d\.]*)\s\w"

    def parse_datetime(self, line):
        parts = line.split('\t')
        timestamp = datetime.datetime.strptime(parts[2],
                                               "%Y-%m-%d %H:%M")
        timezone = parts[3]
        timestamp += self._timezone_table[timezone]
        return timestamp

    def parse_value(self, line):
        parts = line.split('\t')
        text = parts[4].strip()
        value = float(text) if len(text) > 0 else numpy.nan
        return value

    def set_ts_props(self, ts):
        ts._props['agency'] = 'usgs'



class USGSRdbReader(TextTimeSeriesReader):
    """ Reader class to read in data from one of USGS rdb file formats.
        The fields are delimited by tabs, and the selector can be used to pick a name
        from the column header using "sensor=..."
    """
    def __init__(self):
        super(USGSRdbReader, self).__init__()
        self.n_lines_to_check = 150
        self.record_regex = \
            r"\w*\s\d*\s(?P<datetime>\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})" \
            r"\s(?P<timezone>\w*)\s(?P<value>[-\d\.]*)\s\w"
        self._header_approval_regexes = [r"DD parameter", r"TZCD"]

    def count_headers(self, fpath):
        """ Count the number of lines in the header of the file.
        """
        with open(fpath, 'r') as f_in:
            for line_i, line in enumerate(f_in):
                if not self.is_comment(line):
                    nheader = line_i+2
                    break
        return nheader


    def parse_value(self, line):
        pass

    def parse_datetime(self, line):
        pass

    def parse_record(self, line):
        parts = line.split("\t")  #very important not to strip()

        d = parts[self.time_ndx]
        if self.year_first_dash:
            if self.column_is_datetime:
                timestamp = datetime.datetime(*map(int,[d[0:4],d[5:7],d[8:10],d[11:13],d[14:16]]))
            else:
                t = parts[self.time_ndx+1]
                timestamp = datetime.datetime(*map(int,[d[0:4],d[5:7],d[8:10],t[0:2],t[3:5]]))
        elif self.month_first_dash:
            if self.column_is_datetime:
                timestamp = datetime.datetime(*map(int,[d[6:10],d[0:2],d[3:5],d[10:12],d[12:14]]))
            else:
                t = parts[self.time_ndx+1]
                timestamp = datetime.datetime(*map(int,[d[6:10],d[0:2],d[3:5],t[0:2],t[3:5]]))
        else:
            if self.column_is_datetime:
                timestamp = datetime.datetime(*map(int,[d[0:4],d[4:6],d[6:8],d[10:12],d[12:14]]))
            else:
                t = parts[self.time_ndx+1]
                timestamp = datetime.datetime(*map(int,[d[0:4],d[4:6],d[6:8],t[0:2],t[2:4]]))

        if self.zone_ndx > -1:
            timezone = parts[self.zone_ndx]
            timestamp += self._timezone_table[timezone]

        vstr = parts[self.data_ndx]
        if vstr == '': return timestamp,numpy.nan
        try:
            value=float(vstr)
        except:
            if vstr == "Rat": value = numpy.nan
        return timestamp,value

    def set_ts_props(self, ts):
        ts._props['agency'] = 'usgs'

    def process_header(self, fpath,selector=None):
        """Process the header, producing the number of header lines, the list of variables in the file, the units of those variables and a list of
           station metadata. Note that for many formats some or all of these are scant, missing or inapplicable and will be returned as None.

           Parameters
           ----------

            fpath: str
                filepath to read

            selector: str
                string indicating the selection. Limited at the moment to strings of the form "sensor=##_######"

           Returns
           -------
            n_headerlines: int The number of the lines in the header, allowing unchecked fast forward

            metadata: Dictionary
            Dictionary of name-value pairs of attributes for the station or sensor

        """
        n_headerlines = self.count_headers(fpath)
        metadata = self.read_metadata_from_header(fpath)
        has_tz = True
        with open(fpath,"r") as f:
            for i  in range(n_headerlines - 2):
                f.readline()
            nextline = f.readline().strip().split()
            columns = [x.lower() for x in nextline]
            nextline = f.readline() # data type definition line
            nextline = f.readline() # first line
        try:
            time_col = columns.index("datetime")
            iextra = 0  # because space between date and time will not be a tab
        except:
            time_col = columns.index("date")
            iextra = 0
        print columns
        try:
            zone_col = columns.index("tz_cd")
        except:
            try:
                zone_col = columns.index("tzcd")
            except:
                has_tz = False
                zone_col = time_col
        if has_tz: assert zone_col > time_col     # Needed for accounting because datetime column has a space
        #data_col_re = re.compile(r"(\d{2}_\d{5}\b)|value$")
        data_col_re = re.compile(r"(\d{5,6}_\d{5}\b)|value$|_cd")
        data_names = []
        data_ndxs = []
        for icol in range(zone_col+1,len(columns)):
            if data_col_re.match(columns[icol]):
                data_names.append(columns[icol])
                data_ndxs.append(icol)
        if selector is None:
            if len(data_ndxs) > 1:
                raise ValueError("Multiple data columns found but no selector provided for path %s" %fpath)
            else:
                data_name = data_names[0]
                data_ndx = data_ndxs[0]
        else:
            lselector = selector.lower()
            if lselector.startswith("sensor="):
                lselector = lselector.split("=")[1]
            else:
                raise ValueError("Only selections beginning with sensor= are currently supported")
            try:
                ndx = data_names.index(lselector)
                data_ndx = data_ndxs[ndx]
            except:
                print data_names
                raise ValueError("Sensor not found %s " % lselector)

        self.time_ndx = time_col
        self.zone_ndx = (zone_col + iextra) if has_tz else -1
        self.data_ndx = data_ndx + iextra

        # sniff some details concerning the structure of the data lines too and cache
        parts = nextline.split("\t")  #very important not to strip()
        if len(parts) < 1:
            return None
        d = parts[self.time_ndx]
        self.year_first_dash = self.month_first_dash = self.column_is_datetime = False
        try:
            if d[4] in ["-","/"]:
                self.year_first_dash = True
            elif d[2] in ["-","/"]:
                self.month_first_dash = True
            if self.year_first_dash or self.month_first_dash:
                self.column_is_datetime = len(d) > 10
            else:
                self.column_is_datetime = len(d) > 8
        except IndexError:
            return n_headerlines, None

        return n_headerlines, metadata  #, col_ndx


def read_usgs2(fpath, start=None, end=None, force_regular=True, selector = None):
    reader = USGS2Reader()
    return reader.read(fpath, start, end, force_regular)

def read_usgs_rdb(fpath,start=None, end=None, force_regular=True, selector=None):
    reader = USGSRdbReader()
    return reader.read(fpath, start, end, force_regular,selector)

def read_ts(fpath, start=None, end=None, force_regular=True, selector = None):
    """ Read a time series from a text file in various formats.
        This function asks readers for different file formats to attempt to read the file.
        The first reader that confirms its appropriateness will be attempted. The order of this
        is not guaranteed..

        Parameters
        ----------
        fpath: str
            a file path to read in
        start: datetime.datetime, optional
            time to start reading
        end: datetime.datetime, optional
            time to end reading

        Returns
        -------
        vtools.data.timeseries.TimeSeries
            the time series from the file
        dict
            metadata of the time series
    """
    readers = [CDECReader(), CDECReader2(), NOAAReader(), WDLReader(), DESReader(),
               USGSReader(), USGS2Reader(), USGSRdbReader()]
    for reader in readers:
        if reader.is_readable(fpath):
            if selector is None:
                return reader.read(fpath, start, end, force_regular)
            else:
                return reader.read(fpath, start, end, force_regular, selector)
    raise ValueError("File format not identified or supported: %s\n" % fpath)









if __name__ == "__main__":
    c = CDECReader()
    print c.is_readable("Z:/schism/Data_2013/cdec/flow/FAL_flow_E.csv")
    print c.is_readable("Z:/schism/Data_2013/usgs/11162765_sanmateo_ec_2013_2014.rdb")
    d = USGSRdbReader()
    ts = d.read("W:/usgs_scalar_to_oct_2013/x.UV.USGS.11303500.5.C.00000000.rdb")
    print ts.start


    print d.is_readable("Z:/schism/Data_2013/usgs/11162765_sanmateo_ec_2013_2014.rdb")
    #n,x,y = d.process_header("Z:/schism/Data_2013/usgs/11162765_sanmateo_ec_2013_2014.rdb",selector="sensor=02_00095")

    ts = d.read("Z:/schism/Data_2013/usgs/11162765_sanmateo_ec_2013_2014.rdb",force_regular=True,selector="sensor=04_00095")
    print ts.start
    print ts.end
    print ts.interval
    print ts[3].time
    print ts[3].value
    print ts[46536].time
    print ts[46536].value
    import datetime as dtm
    t = dtm.datetime(2014,8,12,1,45)
    print ts[t].time
    print ts[t].value
    t = dtm.datetime(2014,8,12,10,30)
    print ts[t].time
    print ts[t].value
    t = dtm.datetime(2014,8,12,10,45)
    print ts[t].time
    print ts[t].value


