# -*- coding: utf-8 -*-
""" Routine to create hotstart
"""

from shapely.geometry import Point
from scipy.spatial import cKDTree
import numpy as np
from bisect import bisect_left
import csv
import re
import datetime
import struct
import logging

__all__ = ['HotstartGenerator',
           'RegionalInitializer',
           'NearestNeighborInitializer',
           'init_logger',
           'read_stations']

def parse_date_time(date_str, time_str):
    """ Pares date and time string
    """
    date = re.split(r'[^\d]+', date_str)
    hr = time_str
    dtm = list(map(int, [date[i] for i in (2, 0, 1)]))
    dtm.extend((int(hr[:2]), int(hr[2:])))
    tm = datetime.datetime(*dtm)
    return tm


def init_logger(name='hotstart_gen'):
    """ Initialize Python logging
    """
    logging.basicConfig(level=logging.INFO,
                        filename="%s.log" % name,
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger(name).addHandler(console)
    return logging.getLogger(name)


class HotstartGenerator(object):
    """
    Hotstart generator with node value functors.
    Element and side values are averaged from node values.
    No tracer is implemented.
    """
    def __init__(self,
                 elev=None, vel=None, temp=None, salt=None,
                 logger=None):
        """
        Parameters
        ----------
        elev, hvel, temp, salt: functor
            functors to generate those variables
        """
        self.gen_elev = elev
        self.gen_vel = vel
        self.gen_temp = temp
        self.gen_salt = salt
        self.logger = logger
        self.mesh = None
        self.vert_grid = None
        self.depths = None
        self.vel = None

    def reset(self):
        pass

    def create_hotstart(self, mesh, fpath_hotstart=None):
        if fpath_hotstart is None:
            fpath_hotstart = 'hotstart.in'
        self.mesh = mesh
        self.nvrt = mesh.vmesh.param['nvrt']
        self.compute_variables()
        self.write_hotstart(fpath_hotstart)

    def compute_depth(self):
        """ Calculate points in 3-D grid
        """
        mesh = self.mesh
        vert_grid = self.mesh.vmesh
        nvrt = vert_grid.param['nvrt']
        depths = np.full([mesh.n_nodes(), nvrt], np.finfo(np.float32).min)
        if vert_grid.ivcor == 1:
            if nvrt < 3:
                raise ValueError()

            for i, node in enumerate(mesh.nodes):
                hmod2 = max(0.1, node[2])
                kbps = vert_grid.kbps[i]
                depths[i, kbps-1:] = hmod2 * vert_grid.sigma[i, :nvrt-kbps+1]
                depths[i, :kbps-1] = depths[i, kbps-1]
            self.depths = depths
        elif vert_grid.ivcor == 2:
            h_s = vert_grid.param['h_s']
            h_c = vert_grid.param['h_c']
            kz = vert_grid.param['kz']
            c_s = vert_grid.c_s
            for i, node in enumerate(mesh.nodes):
                # TODO: Maybe add surface elevation?
                depth = node[2]
                # S-level
                hmod2 = max(0.1, min(depth, h_s))
                for k, s in enumerate(vert_grid.sigma):
                    k_a = kz + k - 1
                    if hmod2 <= h_c:
                        depths[i, k_a] = s * hmod2
                    else:
                        depths[i, k_a] = h_c * s + (hmod2 - h_c) * c_s[k]
                # Z-level
                for k, d in enumerate(vert_grid.ztot[:-1]):
                    depths[i, k] = d
            self.depths = depths
        else:
            raise("Not supported ivcor")

    def compute_variables(self):
        """ Compute variables
        """
        # TODO: Maybe I can replace the whole thing with fortran function
        if self.logger is not None:
            self.logger.info("Start calculating levels ...")
        self.compute_depth()
        if self.logger is not None:
            self.logger.info("Done calculating levels...")

        # 2D
        # Elevation
        nodes = self.mesh.nodes[:, :2]
        if self.logger is not None:
            self.logger.info("Start calculating elev...")
        if not self.gen_elev is None:
            self.elev = np.empty(nodes.shape[0])
            for i in range(self.mesh.n_nodes()):
                self.elev[i] = self.gen_elev(node_idx=i)
        else:
            self.elev = np.zeros(self.mesh.n_nodes())
        if self.logger is not None:
            self.logger.info("Done calculating elev...")
        # 3D
        # temperature
        nvrt = self.nvrt
        n_nodes = self.mesh.n_nodes()
        points = np.empty((nodes.shape[0] * nvrt, 3))
        for i in range(nvrt):
            points[i*n_nodes:(i+1)*n_nodes] = np.hstack((nodes,
                                    self.depths[:, i].reshape(-1, 1)))

        if not self.vel is None:
            self.vel = self.gen_vel(*nodes[:, 0:2])
        else:
            self.vel = np.zeros_like(nodes[:, 0:2])
        if self.logger is not None:
            self.logger.info("Start calculating temperature..")
        self.temp = np.empty((nodes.shape[0], nvrt))
        if not self.gen_temp is None:
            for i in range(self.mesh.n_nodes()):
                self.temp[i, :] = self.gen_temp(node_idx=i, depths=self.depths[i])
        if self.logger is not None:
            self.logger.info("Start calculating salt..")
        self.salt = np.empty((nodes.shape[0], nvrt))
        if not self.gen_salt is None:
            for i in range(self.mesh.n_nodes()):
                self.salt[i, :] = self.gen_salt(node_idx=i, depths=self.depths[i])
        if self.logger is not None:
            self.logger.info("Done calculating salt..")

        n_vars = 2
        shape = list(self.depths.shape)
        shape.append(n_vars)
        self.var_nodes = np.full(shape, np.finfo(np.float32).min)
        for node_i, node in enumerate(self.mesh.nodes):
            self.var_nodes[node_i, :, 0] = self.temp[node_i]
            self.var_nodes[node_i, :, 1] = self.salt[node_i]

    def write_hotstart(self, fpath=None):
        """
        Write 'hotstart.in'
        """
        # Maybe I can switch all these to FORTRAN function to speed things up
        if fpath is None:
            fpath = 'hotstart.in'
        if self.logger is not None:
            self.logger.info('Taking averages for sides and elements...')
        mesh = self.mesh
        nvrt = self.nvrt
        # Elements
        out_elem = np.empty((self.mesh.n_elems(), nvrt, 2))
        for elem_i in range(mesh.n_elems()):
            elem = mesh.elem(elem_i)
            avg = np.average(self.var_nodes[elem, :, :], axis=0)
            out = np.average(np.dstack((avg[1:], avg[:-1])), axis=2)
            out_elem[elem_i] = np.vstack((out[0], out))
        # Sides
        out_side = np.empty((self.mesh.n_edges(), nvrt, 2))
        for i, edge in enumerate(mesh.edges):
            node_i = edge[:2]
            out_side[i] = np.average(self.var_nodes[node_i], axis=0)
        if self.logger is not None:
            self.logger.info("Finished averaging.")

        # Write
        if self.logger is not None:
            self.logger.info("Start writing a hotstart.in...")
        with open(fpath, 'wb') as fout:
            fmt = 'dii'  # Time, iths, ifile
            pad = struct.calcsize(fmt)
            fmt = '=i' + fmt + 'i' # Padding
            buf = struct.pack(fmt, pad, 0., 0, 1, pad)
            fout.write(buf)
            # element
            for i, vals in enumerate(out_elem):
                fmt = '=ii' # Elem_i, idry
                buf = struct.pack(fmt, i + 1, 0)
                for row in vals:
                    buf += struct.pack('=d', 0.)  # w_e (vertical vel at elem)
                    buf += struct.pack('=%dd' % len(row), *row) # Temp, Salt
                pad = len(buf)
                buf = struct.pack('=i', pad) + buf + struct.pack('=i', pad)
                fout.write(buf)
            # side
            for i, vals in enumerate(out_side):
                fmt = 'ii'
                buf = struct.pack(fmt, i + 1, 0)
                for row in vals:
                    buf += struct.pack('=dd', 0., 0.)
                    buf += struct.pack('=%dd' % len(row), *row)
                pad = len(buf)
                buf = struct.pack('i', pad) + buf + struct.pack('i', pad)
                fout.write(buf)
            # node
            for i, vals in enumerate(self.var_nodes):
                fmt = '=idi'
                buf = struct.pack(fmt, i + 1, self.elev[i], 0)
                for row in vals:
                    buf += struct.pack('=%dd' % len(row), *row)
                    buf += struct.pack('=%dd' % len(row), *row)
                    buf += struct.pack('=7d', 0., 0., 0., 0., 0., 0., 0.)
                pad = len(buf)
                buf = struct.pack('=i', pad) + buf + struct.pack('=i', pad)
                fout.write(buf)
        if self.logger is not None:
            self.logger.info("Finished writing a hotstart file.")


class RegionalInitializer(object):
    """
    IC implementation that delegates
    to other IC implementations according to region.
    NOTE: If a node or position does not belong to any of the polygons,
    region with zero will be used for now. This is not desirable, and
    it will be updated later.
    """
    def __init__(self, mesh, polygons, mapped_initializers):
        self.mesh = mesh
        self.mapped_initializers = mapped_initializers
        self.polygons = polygons

    def __call__(self, **kwargs):
        node_idx = kwargs.get('node_idx')
        p = self.mesh.nodes[node_idx]
        region = 'default'
        for polygon in self.polygons:
            if polygon.contains(Point(p)):
                region = polygon.name
                break
        initializer = self.mapped_initializers.get(region)
        if initializer is None:
            raise ValueError('No corresponding initializer')
        val = initializer(**kwargs) if callable(initializer) else initializer
        return val


class NearestNeighborInitializerBase(object):
    def __init__(self, stations, casts, item):
        self.item = item
        self.stations = stations
        self.rearrange_casts(casts)

    def rearrange_casts(self, casts):
        new_casts = {}
        for cast in casts:
            name = cast['id']
            val = [-cast['depth'] if 'depth' in cast else 0., cast[self.item]]
            new_cast = new_casts.get(name)
            if new_cast is None:
                new_casts[name] = [val]
            else:
                new_casts[name].append(val)
        new_casts = dict([(k, np.array(sorted(v))) for (k, v) in new_casts.items()])
        self.casts = new_casts

    # def find_nearest_station(self, x, y):
    #     """ Find nearest cast and return station id

    #         Parameters
    #         ----------
    #         x: float
    #         y: float

    #         Returns
    #         -------
    #         str
    #             ID of the nearest station
    #     """
    #     dist_min = 1.e23
    #     nearest_station = None
    #     for station_id in self.casts:
    #         station_pos = Point([self.stations[station_id][field]
    #                              for field in ('x', 'y')])
    #         dist = station_pos.distance(Point(x, y))
    #         if dist < dist_min:
    #             dist_min = dist
    #             nearest_station = station_id
    #     if nearest_station is None:
    #         raise RuntimeError("Fail to find a cast")
    #     return nearest_station

    def __call__(self):
        """ Abstract __call__
        """
        raise NotImplementedError()


class NearestNeighborInitializer(NearestNeighborInitializerBase):
    """ Fast nearest neighbor initializer
    """
    def __init__(self, mesh, stations, casts, item):
        """
        Parameters
        ----------
        mesh: target mesh to interpolate
        vmesh: target vertical mesh to interpolate
        stations:
        casts:
        """
        super(NearestNeighborInitializer, self).__init__(stations, casts, item)
        self.mesh = mesh
        self.find_nearest_stations()

    def find_nearest_stations(self):
        pt_avail_stations = [[(s['x'], s['y'])
                              for s in self.stations
                              if s['id'] == x][0]
                             for x in self.casts]
        # Voronoi tessellation
        kdtree = cKDTree(pt_avail_stations)
        _, self.nearest_station_idx = kdtree.query(self.mesh.nodes[:, :2])

    def __call__(self, **kwargs):
        node_idx = kwargs['node_idx']
        depth = kwargs['depths']
        nearest_station = list(self.casts.keys())[self.nearest_station_idx[node_idx]]
        casts = self.casts[nearest_station]
        cast_depths = casts[:, 0]
        values = []
        for z in depth:
            try:
                if z <= cast_depths[0]:
                    val = casts[0, 1]
                elif z >= cast_depths[-1]:
                    val = casts[-1, 1]
                else:
                    idx = bisect_left(cast_depths, z)
                    ratio = (z - cast_depths[idx-1]) / (cast_depths[idx] - cast_depths[idx-1])
                    # assert ratio >= 0. and ratio <= 1.
                    val = ratio * casts[idx, 1] + (1. - ratio) * casts[idx-1, 1]
                values.append(val)
            except Exception as e:
                print(node_idx, z, casts)
                raise e
        return np.array(values)


def read_stations(fpath):
    """
    Returns
    -------
    list
        list of dictionary like JSON
    """
    with open(fpath, 'r') as f:
        fields = [x.strip().lower() for x in f.next().split(',')]
        reader = csv.DictReader(f, fields)
        stations = []
        try:
            for row in reader:
                stations.append(dict([(k.lower(), float(v)) if k in ('x', 'y', 'depth') else (k.lower(), v.strip()) for k, v in row.items()]))
        except AttributeError:
            raise ValueError("Format of the station file may be wrong")
        return stations


def read_station_data(fpath):
    """
    items_to_list: list
        item (column) names to read
    Returns
    -------
    list
        list of dictionary like JSON
    """
    with open(fpath, 'r') as f:
        fields = [x.strip().lower() for x in f.next().split(',')]
        fmt = f.next().split(',')
        data = []
        for l in f:
            l = l.strip()
            if len(l) < 1:
                continue
            data.append(dict([(k.lower(), v) for k, v in zip(fields, l.split(','))]))
        for row in data:
            for k in row:
                if k in ('depth', 'salinity', 'temperature'):
                    row[k] = float(row[k])
        return data
