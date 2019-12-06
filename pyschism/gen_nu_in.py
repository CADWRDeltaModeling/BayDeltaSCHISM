#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Script to create TEM_nu.in and SAL_nu.in
"""

from schism_mesh import SchismMeshIoFactory
from station_db import StationDB
from schism_polygon import Polygon, Point
from unit_conversions import ec_psu_25c
from vtools.functions.api import interpolate_ts_nan
from vtools.data.timeseries import rts
import numpy as np
from datetime import datetime, timedelta
from time import strptime
from copy import deepcopy
import csv
import struct
import os
import matplotlib.pyplot as plt
import logging


def setup_logger():
    """ Set up a logger and return one

        Returns
        -------
        logging.Logger
    """
    logging_level = logging.INFO
    logging_fname = 'gen_nu.log'
    logging.basicConfig(level=logging_level, filename=logging_fname,
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging_level)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return logging.getLogger('gen_nu')


def logger():
    """ get logger

        Returns
        -------
        logging.Logger
    """
    return logging.getLogger('gen_nu')


def generate_ocean_nudging_factors(mesh):
    """ Set ocean nudging factor.
        This function is specific for the current Bay or Bay-Delta grid.
        The method and numbers are borrowed from Joseph's 'gen_nudge.f90'

        Parameters
        ----------
        mesh: SchismMesh

        Return
        ------
        numpy array
            nudging factors
    """
    ocean_polygon = Polygon(np.array([[526062.827808, 4226489.867824],
                                      [566004.141418, 4136786.330387],
                                      [497563.036325, 4137201.624542],
                                      [499019.230051, 4222752.220430]]))

    nodes = mesh.nodes
    center = np.array((542699., 4183642.)).reshape((1, 2))
    r = (32.3e3, 32.3e3)
    r2 = r[0] * r[0]
    rat = 41.e3 / r[0]
    rmax = 1. / 2. / 86400.

    # Square of distance over Square of radius
    rr = np.sum(np.square(np.subtract(nodes[:, :2], center)), axis=1) / r2
    tnu = rmax * (rr - 1.) / (rat * rat - 1)
    cut = np.empty(tnu.shape)
    cut[:] = rmax
    tnu = np.minimum(tnu, rmax)
    cut[:] = 0.
    tnu = np.maximum(tnu, cut)
    for i, node in enumerate(nodes):
        # if ocean_polygon.check_point_inside_polygon(node[:2]):
        if not ocean_polygon.contains(Point(node[:2])):
            tnu[i] = 0.
    return tnu


def add_nudging_stations(mesh, stations, rmax):
    """ Add nudging factors of the given stations with the radii of influence.
        The strength of the nudging decreases linearly from the station.

        Parameters
        ----------

        mesh: :class:`selfe_mesh`
            Mesh to process. The node depths are used as nudging factors.
        stations: tuple of tuples or list of lists
            ((x, y, r), ...)
            x and y are coordinates of each station and r is its radius of
            influence
        rmax: float
            The maximum nudging factor
    """
    # Linear nudging for now
    for station in stations:
        center = station[:2]
        r = station[2]
        box = [center[0] - r, center[0] + r, center[1] - r, center[1] + r]
        candidates = mesh.find_nodes_in_box(box)
        for node_i in candidates:
            node = mesh.nodes[node_i]
            dist = np.linalg.norm(node[:2] - center)
            tnu = rmax * (1 - dist / r)
            tnu = np.maximum(0., tnu)
            node[2] = tnu


def write_fortran_binary(f, val):
    """ Write a binary block in the FORTRAN unformatted style.
        FORTRAN adds paddings with the length of binary block in front and
        at the end of a block.
        If the array has multiple ranks, it is written rank by rank, not 
        all in one chunk.

        f: file handle
        val: Value to write in Numpy array
    """
    # Assuming numpy float
    if len(val.shape) == 1:
        fmt = "f" * val.shape[0]
        size = struct.calcsize(fmt)
        # Padding
        buf = struct.pack('i', size)
        f.write(buf)
        # Value
        buf = struct.pack(fmt, *val)
        f.write(buf)
        # Padding
        buf = struct.pack('i', size)
        f.write(buf)
    else:
        for i in range(val.shape[0]):
            write_fortran_binary(f, val[i])


def add_nudging_step_to_nu_in(fpath, t, data):
    """ Add another nudging step to *_nu.in
    """
    with open(fpath, 'ab') as f:
        write_fortran_binary(f, np.array([t]))
        for i in range(data.shape[0]):
            write_fortran_binary(f, data[i])


def add_salt_station(nodes, salts, stations, data):
    """
        Parameters
        ----------
        nodes: list of shapely.Point
        salts: 2D numpy array
            salt matrix. shape=(n_nodes, nvrt)
        stations: 2D array
            list of station coordinates in 3D
        data: 1D array
            matrix of values to nudge with

        Return
        ------
    """
    for station, val in zip(stations, data):
        center = station[:2]
        r = station[2] * 1.5 # Expand a little
        box = [center[0] - r, center[0] + r, center[1] - r, center[1] + r]
        candidates = mesh.find_nodes_in_box(box)
        for node_i in candidates:
            salts[node_i,:] = val


def convert_string_to_float(string):
    """ Convert a string to float. It return numpy.nan for failure.
    """
    try:
        return float(string)
    except:
        return np.nan


def read_csv_from_dss(fpath):
    """ Read CSV file from dss
        Assume LST (no daylight saving)

        Parameters
        ----------
        fpath: str
            file path

        Returns
        -------
        array of vtools.data.timeseries.TimeSeries
            regular time series.
    """
    with open(fpath, 'rU') as f:
        reader = csv.reader(f)
        data = []
        times = []
        for i, row in enumerate(reader):
            if i == 1:
                stations = row[2:]
            elif i > 6:
                t = datetime(*strptime(row[1], r'%d%b%Y  %H%M')[:5])
                times.append(t)
                row_data = list(map(convert_string_to_float, row[2:]))
                data.append(row_data)
        data = np.array(data)
        return [rts(data[:, i], times[0], times[1] - times[0],
                    props={'unit': 'ec', 'name': stations[i]})
                for i in range(len(stations))]


def select_ec_in_stations_db(tss, stations_db):
    """ Select EC time series in stations db.
        NOTE: Selected EC time series will have props['pos'] for positions of
        the stations.

        Parameters
        ----------
        tss: list of vtools.data.timeseries.TimeSeries
        stations_db: StationDB

        Returns
        -------
        list of vtools.data.timeseries.TimeSeries
    """
    point_idx = [stations_db.header.index(name)
                 for name in ('point_x', 'point_y')]
    ts_selected = []
    for ts in tss:
        cdec_name = ts.props['name']
        ids = stations_db.station_ids_from_alias(cdec_name)
        if len(ids) > 0:
            logger().info("Found matching station: %s", cdec_name)
            station_data = stations_db.data[ids[0]]
            try:
                station_coord = list(map(float, [station_data[idx] for idx in point_idx]))
                ts.props['pos'] = station_coord
                ts_selected.append(ts)
            except:
                logger().warning("This station does not have coordinate: %s",
                                 cdec_name)
        else:
            logger().warning("No matching station: %s", cdec_name)
    return ts_selected


def fill_gaps_and_remove_ts_with_big_gaps(tss, max_gap):
    """ Fill gaps and remove time series that cannot be filled

        Returns
        -------
        list of time series

    """
    ts_processed = []
    for ts in tss:
        # Fill gaps
        ts_filled = interpolate_ts_nan(ts, max_gap=max_gap)
        if np.any(np.isnan(ts_filled.data)):
            # Drop the station
            logger().warning("This station has too big a gap: %s",
                             ts_filled.props['name'])
        else:
            ts_processed.append(ts_filled)
    return ts_processed

def read_rki_to_cdec(fpath):
    """ Read Siqing's table between CDEC names to RKI ones

        Returns
        -------
        dict
            dict from RKI to CDEC
    """
    with open(fpath, 'r') as f:
        reader = csv.reader(f)
        rki_to_cdec = {}
        for i, row in enumerate(reader):
            if i == 0:
                header = [x.upper() for x in row]
                cdec_idx = header.index('CDEC_STA')
                rki_idx = header.index('PARA')
            else:
                rki_to_cdec[row[rki_idx].upper()] = row[cdec_idx].upper()
        return rki_to_cdec


def create_ocean_salt_ts(ts_template, salt=33.5):
    """ Create a time series for the ocean boundary with a constant value.
        All the other properties of the time series will be identical
        to the given template time series except the name in the properties.

        Returns
        -------
        vtools.data.timeseries.TimeSeries
            regular time series for the ocean
    """
    ts = rts(np.full_like(ts_template.data, salt),
             ts_template.start,
             ts_template.interval,
             props=deepcopy(ts_template.props))
    ts.props['name'] = 'ocean'
    return ts


def create_un_in(fpath):
    pass


def main():
    """ Just a main function
    """
    log = setup_logger()
    # Read mesh
    fpath = "hgrid.gr3"
    mesh = SchismMeshIoFactory().get_reader('gr3').read(fpath)
    nodes_as_point = [Point(node) for node in mesh.nodes]

    # Create salts and nudging_factors
    n_nodes = mesh.n_nodes()
    nvrt = 23
    nudging_factors = np.zeros((n_nodes,))

    # Read station db
    fpath = "stations_utm.csv"
    stations_db = StationDB(fpath)

    # Read salt time series
    # obs_dir = "../../selfe/BayDeltaSELFE/Data/CDEC_realtime/salt"
    time_basis = datetime(2015, 8, 26)
    time_start = time_basis
    time_window = (time_start, datetime(2015, 9, 2))
    # padding = timedelta(days=1)
    # time_window_padded = (time_window[0] - padding, time_window[1] + padding)

    fpath_csv_15min = '../Data/ec_15min.csv'
    ec_15min = read_csv_from_dss(fpath_csv_15min)
    fpath_csv_1hr = '../Data/ec_1hour.csv'
    ec_1hr = read_csv_from_dss(fpath_csv_1hr)
    ec_1hr.extend([rts(ts.data[::4], ts.times[0], timedelta(hours=1),
                       props=deepcopy(ts.props))
                   for ts in ec_15min])

    # Read RKI to CDEC mapping
    fpath_rki = '../Data/cdec_stas_nearterm.list'
    rki_to_cdec = read_rki_to_cdec(fpath_rki)
    for ts in ec_1hr:
        if rki_to_cdec.get(ts.props['name']) is not None:
            ts.props['name'] = rki_to_cdec[ts.props['name']]

    ec_for_nudging = select_ec_in_stations_db(ec_1hr, stations_db)
    # Cut out time windows
    ec_for_nudging = [ts.window(*time_window) for ts in ec_for_nudging]
    max_gap = 8  # 8 hours
    ec_for_nudging = [interpolate_ts_nan(ts, max_gap=max_gap) for ts in ec_for_nudging]
    ec_for_nudging = [ts for ts in ec_for_nudging
                      if not np.any(np.isnan(ts.data))]

    log.info("Total %d stations to nudge", len(ec_for_nudging))
    if len(ec_for_nudging) < 1:
        log.warning("No station to nudge...")

    # Convert to PSU
    log.info("Convert EC to PSU...")
    list(map(ec_psu_25c, ec_for_nudging))

    # Filtering, not doing it now
    # ts_filt, filt = med_outliers(ts, level=6., range=[100., None])

    # Collect masks nodes in the mesh for nudging of CDEC stations
    log.info("Creating nudging masks...")
    radius_of_nudging = 500.
    radius_padding = 0.
    nudging_pos = [ts.props['pos'] for ts in ec_for_nudging]
    nudging_areas = [Point(p).buffer(radius_of_nudging + radius_padding)
                     for p in nudging_pos]
    nudging_mask = np.full((n_nodes,), -1., dtype=np.int32)
    for node_idx, node in enumerate(nodes_as_point):
        for nudging_idx, ball in enumerate(nudging_areas):
            if ball.contains(node):
                nudging_mask[node_idx] = nudging_idx

    # Nudging factor
    log.info("Creating nudging factors...")
    station_nudging_factor = 1. / 86400.
    station_nudging = np.zeros((n_nodes,))
    for node_idx, mask in enumerate(nudging_mask):
        if mask >= 0:
            center = Point(ec_for_nudging[mask].props['pos'])
            dist = center.distance(nodes_as_point[node_idx])
            station_nudging[node_idx] = np.max(1. - dist / radius_of_nudging, 0.) * station_nudging_factor
    nudging_factors += station_nudging


    log.info("Add ocean boundary...")
    # Ocean nudging
    # Nudging factor
    ocean_nudging = generate_ocean_nudging_factors(mesh)
    nudging_factors += ocean_nudging

    # Add ocean nudging time series
    ec_for_nudging.append(create_ocean_salt_ts(ec_for_nudging[0]))

    # Add the ocean nudging mask
    for node_idx in range(n_nodes):
        if ocean_nudging[node_idx] > 0.:
            nudging_mask[node_idx] = len(ec_for_nudging) - 1

    # Write SAL_nudge.gr3
    fpath_nudge_out = "SAL_nudge.gr3"
    log.info("Creating %s", fpath_nudge_out)
    SchismMeshIoFactory().get_writer('gr3').write(mesh=mesh,
                                                  fpath=fpath_nudge_out,
                                                  node_attr=nudging_factors)

    # Write nu file
    fpath_salt_nu = 'SAL_nu.in'
    log.info("Creating %s", fpath_salt_nu)
    if os.path.exists(fpath_salt_nu):
        os.remove(fpath_salt_nu)

    times = ec_for_nudging[0].times
    print(times[0], times[-1])
    times = [(t - time_basis).total_seconds() for t in times]
    salt_background = 0.1
    data = np.full((n_nodes, nvrt), salt_background)
    for ts_idx, t in enumerate(times):
        for node_idx, mask in enumerate(nudging_mask):
            if mask >= 0:
                data[node_idx, :] = ec_for_nudging[mask].data[ts_idx]
        with open(fpath_salt_nu, 'ab') as f:
            write_fortran_binary(f, np.array([t]))
            for i in range(data.shape[0]):
                write_fortran_binary(f, data[i])


    # Quick copy and paste: Need to make these a function to reuse
    # Write TEM_nudge.gr3
    fpath_nudge_out = "TEM_nudge.gr3"
    log.info("Creating %s", fpath_nudge_out)
    SchismMeshIoFactory().get_writer('gr3').write(mesh=mesh,
                                                  fpath=fpath_nudge_out,
                                                  node_attr=np.zeros_like(nudging_factors))

    # Write nu file
    fpath_temp_nu = 'TEM_nu.in'
    log.info("Creating %s", fpath_temp_nu)
    if os.path.exists(fpath_temp_nu):
        os.remove(fpath_temp_nu)

    # No temperature nudging here. 20 deg C everywhere
    temp_background = 20.
    data = np.full((n_nodes, nvrt), temp_background)
    for ts_idx, t in enumerate(times):
        # for node_idx, mask in enumerate(nudging_mask):
        #     if mask >= 0:
        #         data[node_idx, :] = ec_for_nudging[mask].data[ts_idx]
        with open(fpath_temp_nu, 'ab') as f:
            write_fortran_binary(f, np.array([t]))
            for i in range(data.shape[0]):
                write_fortran_binary(f, data[i])

if __name__ == "__main__":
    main()
