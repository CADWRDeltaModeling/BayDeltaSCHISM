""" Read outputs from read_output*_xyt and create a neat list of
    Vtools time series
"""
# Kijin Nam, knam@water.ca.gov

from vtools.data.timeseries import its
from vtools.data.vtime import time_interval
import matplotlib.pyplot as plt
import numpy
import scipy.integrate
import datetime
import os

__all__ = ['read_depth_avg_from_output7b_xyt']

class Output7bXYTReader(object):
    """ Reader class to read in output from read_output7b_xyt
    """
    _MAP_I23D = {'elev.61': False, 'hvel.64': True, }

    def __init__(self):
        self._fname_station = None
        self._fname_output = None
        self._val_junk = None
        self._val_start = None
        self._val_window = None
        self._val_stride = None
        self._prefix = None
        self._coords = None
        self._nxy = None
        self._nvrt = None
        self._outputs = None
        self._n_casts = None

    def _read_input_file(self, fname):
        """ Read the input files of read_output7b_xyt

            Parameters
            ----------
            fname: str
                file name of the mater input of read_output7b_xyt
        """
        with open(fname, 'r') as fin:
            self._fname_station = fin.readline().split()[0]
            self._fname_output = fin.readline().split()[0]
            self._val_junk = float(fin.readline().split()[0])
            self._val_start = float(fin.readline().split()[0])
            l = fin.readline().split()
            self._val_window = float(l[0])
            self._val_stride = float(l[1])
            self._prefix = fin.readline().split()[0]
        self._n_casts = int(2 * self._val_window / self._val_stride) + 1

    def _read_station(self, fpath=None):
        """ Read station list from station.bp
        """
        if fpath is None:
            fpath = self._fname_station
        fname, ext = os.path.splitext(fpath)
        if ext == '.bp':
            coords = list()
            with open(fpath, 'r') as fin:
                fin.readline()   # First line: comment
                nxy = int(fin.readline().split()[0])  # 2nd: nxy
                self._nxy = nxy
                for xy_i in range(nxy):
                    coord = list(map(float, fin.readline().split()[1:4]))
                    coords.append(coord)
            self._coords = coords

    def _read_vgrid(self, fpath='vgrid.in'):
        """ Read in information from 'vgrid.in'
        """
        with open(fpath, 'r') as fin:
            fin.readline()
            self._nvrt = int(fin.readline().split()[0])

    def _read_output(self):
        """ Read an output file of read_output7b_xyt and store in a raw
            numpy array. The columns are time in days, value, and depth.

            Returns
            -------
            list of numpy array
                data read in from outputs of read_output7b_xyt
        """
        is3d = self._MAP_I23D[self._fname_output]
        if is3d is True:
            fpaths = (self._prefix + mid + '.out' for mid in ('_a', '_b'))
        else:
            fpaths = (self._prefix + '.out',)
        outputs = list()
        for fpath in fpaths:
            data = list()
            with open(fpath, 'r') as fin:
                for xy_i in range(self._nxy):
                    # Ignore the first block because it is repeated later
                    for nvrt_i in range(self._nvrt):
                        fin.readline()
                    for line_i in range(self._n_casts * self._nvrt):
                        line = fin.readline().strip()
                        # time, value, depth
                        tokens = (line.split()[i] for i in [3, 1, 2])
                        records = list(map(float, tokens))
                        data.append(records)
            outputs.append(numpy.array(data))
        self._outputs = outputs

    def read(self, fpath):
        """ Read outputs of read_output7b_xyt with information from input
            files.

            Parameters
            ----------
            fpath: str
                master input file of read_output7b_xyt
        """
        self._read_input_file(fpath)
        self._read_station()
        self._read_vgrid()
        self._read_output()

    def make_depth_average(self, time_basis):
        """ Make depth averaged values from numpy array of outputs

            Parameters
            ----------
            time_basis: datetime.datetime
                time base of the outputs

            Returns
            -------
            lists of a set vtools.data.timeseries of depth and depth-averaged values
                For scalars, the list has only one set of time series.
                For vectors, the list has two sets of time series.
                Each time series has multiple columns of data, and each column
                is for stations.
        """
        nvrt = self._nvrt
        n_casts = self._n_casts
        # collect time stamp first
        times = list()
        output = self._outputs[0]
        for cast_i in range(n_casts):
            i_begin = cast_i * nvrt
            time = time_basis + time_interval(days=output[i_begin, 0])
            times.append(time)
        # collect data
        values = list()
        for output in self._outputs:
            values_at_point = list()
            depths_at_point = list()
            for xy_i in range(self._nxy):
                depths_at_cast = list()
                values_at_cast = list()
                for cast_i in range(n_casts):
                    i_begin = cast_i * nvrt + xy_i * (n_casts * nvrt)
                    depth = -output[i_begin + nvrt - 1, 2]
                    x = -output[i_begin:i_begin + nvrt, 2]
                    y = output[i_begin:i_begin + nvrt, 1]
                    avg = scipy.integrate.simps(y, x) / depth
                    depths_at_cast.append(depth)
                    values_at_cast.append(avg)
                depths_at_point.append(depths_at_cast)
                values_at_point.append(values_at_cast)
            ts_depths = its(times, numpy.array(depths_at_point).transpose())
            ts_values = its(times, numpy.array(values_at_point).transpose())
            values.append((ts_depths, ts_values))
        return values

def read_depth_avg_from_output7b_xyt(fpath, time_basis):
    """ Read output file from read_output7b_xyt and return depth and
        depth-averaged values in vtools.data.timeseries.

        Parameters
        ----------
        fpath: str
            master input file name of read_output7b_xyt
        time_basis: datetime.datetime
            time base of the outputs

        Returns
        -------
        lists of a set vtools.data.timeseries of depth and depth-averaged values
            For scalars, the list has only one set of time series.
            For vectors, the list has two sets of time series.
            Each time series has multiple columns of data, and each column
            is for stations.
    """
    reader = Output7bXYTReader()
    reader.read(fpath)
    return reader.make_depth_average(time_basis)


def calculate_stokes_drift(timeseries):
    """ Calculate scaled stokes drift

        Parameters
        ----------
        timeseries: list of vtools.data.timeseries.TimeSeries
            This is the output from read_depth_avg_from_output7b_xyt, which 
            are Vtools time series of depth and velocity in x and y directions.
        
        Returns
        -------
        list of numpy arrays
            The return value is three numpy arrays: The first is SSD_x,
            the second is SSD_y, and the last SSD.
    """
    ssds = list()
    for h, u in timeseries:
        uh_bar = numpy.mean(numpy.multiply(h.data, u.data), axis=0)
        u_bar = numpy.mean(u.data, axis=0)
        h_bar = numpy.mean(h.data, axis=0)
        uh_perturb_bar = uh_bar - u_bar * h_bar

        u_perturb = numpy.max(numpy.fabs(u.data - u_bar), axis=0)
        h_perturb = numpy.max(numpy.fabs(h.data - h_bar), axis=0)

        ssd = uh_perturb_bar / (u_perturb * h_perturb)
        ssds.append(ssd)

    ssds.append(numpy.linalg.norm(numpy.vstack((ssds[0], ssds[1])), axis=0))
    return ssds


if __name__ == "__main__":
    time_basis = datetime.datetime(2009, 3, 12)
    results = read_depth_avg_from_output7b_xyt('read_output7b_xyt.in',
                                               time_basis)
    ssd = calculate_stokes_drift(results)
    print(ssd)
    for depth, value in results:
        plt.clf()
        ax1 = plt.gca()
        ax2 = ax1.twinx()
        for col_i in range(depth.data.shape[1]):
            ax1.plot(depth.times, depth.data[:, col_i], label=str(col_i + 1))
            ax2.plot(value.times, value.data[:, col_i], '--',
                     label=str(col_i + 1))
        ax1.legend()
        plt.show()
