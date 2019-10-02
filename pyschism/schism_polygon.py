# -*- coding: utf-8 -*-
"""
This module contains polygon data holders and related operations.
"""
import schism_yaml
from shapely.geometry.polygon import orient
from shapely.geometry import Polygon, Point
from osgeo.osr import SpatialReference
from osgeo.ogr import Open, CreateGeometryFromWkb, OFTString, GetDriverByName, wkbPolygon, FieldDefn, Feature
import numpy as np
import os


class SchismPolygon(Polygon):
    """
    A polygon class based on shapely.geometry.Polygon.
    This class has extra information
    """

    def __init__(self, shell=None, holes=None, prop=None):
        """
        Constructor

        Parameters
        ----------
        shell : sequence
            A sequence of (x, y [,z]) numeric coordinate pairs or triples
        holes : sequence
            A sequence of objects which satisfy the same requirements as the
            shell parameters above
        props: dict
            property dict. Keys as properties are name, type and attribute.
        """
        super(SchismPolygon, self).__init__(shell, holes)
        self._prop = {} if prop is None else prop

    @property
    def attribute(self):
        return self.prop.get('attribute')

    @attribute.setter
    def attribute(self, val):
        self.prop['attribute'] = val

    @property
    def type(self):
        return self.prop.get('type')

    @type.setter
    def type(self, val):
        self._type = val

    @property
    def name(self):
        return self.prop.get('name')

    @name.setter
    def name(self, val):
        self.prop['name'] = val

    @property
    def prop(self):
        return self._prop

    @prop.setter
    def prop(self, val):
        self._prop = val

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return (self._prop == other._prop and
                super(self.__class__, self).__eq__(other))

    def __repr__(self):
        return "{}".format(self._prop)

    def contains(self, point):
        """ Check the polygon contains the point

            Parameters
            ----------
            point: np.ndarray or shapely.geometry.polygon.Polygon

            Returns
            -------
            bool
        """
        if isinstance(point, np.ndarray):
            point = Point(*point)
        return super(SchismPolygon, self).contains(point)

    def intersects(self, val):
        """ Check the polygon intersects with the point

            Parameters
            ----------
            point: np.ndarray or shapely.geometry.polygon.Polygon

            Returns
            -------
            bool
        """
        if isinstance(val, np.ndarray):
            val = Point(*val)
        return super(SchismPolygon, self).intersects(val)


class SchismPolygonIo(object):
    """ SchismPolygon I/O abstract class
    """

    def read(self, stream):
        raise NotImplementedError()


class SchismPolygonDictConverter(SchismPolygonIo):
    """ Convert a tree to a list of polygons
    """

    def read(self, data):
        polygons = []
        data = data.get('polygons')
        if data is not None:
            for item in data:
                prop = {}
                for k in item:
                    if k == 'vertices':
                        vertices = [[float(e) for e in row]
                                    for row in item['vertices']]
                    else:
                        prop[k] = item[k]
                polygons.append(SchismPolygon(orient(
                    Polygon(vertices)), prop=prop))
        return polygons


class SchismPolygonYamlReader(SchismPolygonIo):
    """ Read polygons from a SCHSIM YAML polygon file
    """

    def read(self, fpath):
        if os.path.exists(fpath):
            with open(fpath, 'r') as f_in:
                raw = schism_yaml.load_raw(f_in)
                return SchismPolygonDictConverter().read(raw)
        else:
            raise ValueError('File not found')


class SchismPolygonShapefileReader(SchismPolygonIo):
    """ Read polygons from a shape file
    """

    def read(self, fpath):
        """ Read polygons from a Shapefile and return a list of
            SchismPolygons.

            Parameters
            ----------
            fpath: str
                Filename of a Shapefile containing Polygons with
                data columns such as name, type, and attribute.

            Returns
            -------
            list
                list of SchismPolygons
        """
        if os.path.exists(fpath):
            datasource = Open(fpath)
            layer = datasource.GetLayer(0)
            feat = layer.GetFeature(0)
            field_names = [feat.GetFieldDefnRef(i).GetName()
                           for i in range(feat.GetFieldCount())]
            # fld_idx = [field_names.index(x)
            #            for x in ('name', 'type', 'attribute')]
            polygons = []
            for feature in layer:
                geom = feature.GetGeometryRef()
                name_geom = geom.GetGeometryName()
                if name_geom in ('POLYGON', 'MULTIPOLYGON'):
                    if name_geom == 'MULTIPOLYGON':
                        geoms = [g for g in geom]
                    else:
                        geoms = [geom, ]
                    for g in geoms:
                        shell = [
                            point for point in g.GetGeometryRef(0).GetPoints()]
                        prop = {}
                        for i, field_name in enumerate(field_names):
                            prop[field_name] = feature.GetFieldAsString(i)
                        polygons.append(SchismPolygon(
                            orient(Polygon(shell=shell)), prop=prop))
            return polygons
            # return SchismPolygonDictConverter().read({'polygons': polygons})
        else:
            raise ValueError('File not found: {}'.format(fpath))


class SchismPolygonYamlWriter(SchismPolygonIo):
    """ Write polygons into a YAML file
    """

    def write(self, fpath, polygons):
        with open(fpath, 'w') as f:
            data = {}
            data['polygons'] = []
            for p in polygons:
                leaf = {}
                leaf['name'] = p.name
                leaf['vertices'] = list([list(xy) for xy in p.exterior.coords])
                if p.type is not None and p.type.lower() != 'none':
                    leaf['type'] = p.type
                if not p.attribute is None:
                    if p.attribute.lower() != 'none':
                        leaf['attribute'] = p.attribute
                data['polygons'].append(leaf)
            schism_yaml.dump(data, f)


class SchismPolygonShapefileWriter(SchismPolygonIo):

    def write(self, fpath, polygons, spatial_reference=None, driver_name=None):
        """ Convert SCHISM polygon YAML file to a shapefile

        Parameters
        ----------
        fpath: str
            output file name
        polygons: array of schism_polygon.SchismPolygon
            polygons to write
        spatial_reference: osgeo.osr.SpatialReference or proj4 string
            default: NAD83, UTM zone 10N, meter
        driver_name: osgeo.ogr Driver name
            default: ESRI Shapefile
        """
        if spatial_reference is None:
            spatial_reference = '+proj=utm +zone=10N +ellps=NAD83 +datum=NAD83 +units=m'
        if isinstance(spatial_reference, str):
            spatial_reference_obj = SpatialReference()
            spatial_reference_obj.ImportFromProj4(spatial_reference)
        elif isinstance(spatial_reference, SpatialReference):
            spatial_reference_obj = spatial_reference
        else:
            raise ValueError('Not support spatial_reference type')
        if driver_name is None:
            driver_name = 'ESRI Shapefile'
        driver = GetDriverByName(driver_name)
        if driver is None:
            print('%s is not available.' % driver_name)
            raise RuntimeError()
        datasource = driver.CreateDataSource(str(fpath))
        if datasource is None:
            raise RuntimeError("Cannot create a GIS file")
        layer = datasource.CreateLayer('layer',
                                       spatial_reference_obj,
                                       wkbPolygon)
        fields = ('name', 'type', 'attribute')
        map(layer.CreateField, [FieldDefn(field) for field in fields])
        feature_defn = layer.GetLayerDefn()
        feature = Feature(feature_defn)

        for i, polygon in enumerate(polygons):
            feature.SetGeometry(CreateGeometryFromWkb(polygon.wkb))
            feature.SetField(0, polygon.name)
            feature.SetField(1, polygon.type)
            feature.SetField(2, polygon.attribute)
            layer.CreateFeature(feature)
        datasource.Destroy()


class SchismPolygonIoFactory(object):
    """ A factory class for SchismPolygonIo
    """
    registered_readers = {'dict': 'SchismPolygonDictConverter',
                          'yaml': 'SchismPolygonYamlReader',
                          'shp': 'SchismPolygonShapefileReader'}
    registered_writers = {'yaml': 'SchismPolygonYamlWriter',
                          'shp': 'SchismPolygonShapefileWriter'}

    def get_reader(self, name):
        if name in self.registered_readers:
            return globals()[self.registered_readers[name]]()
        else:
            raise ValueError('Not in the SchismPolygonIoFactory')

    def show_registered_readers(self):
        print(self.registered_readers)

    def get_writer(self, name):
        if name in self.registered_writers:
            return globals()[self.registered_writers[name]]()
        else:
            raise ValueError('Not in the SchismPolygonIoFactory')


def read_polygons(fpath):
    """ Read a polygon file
    """
    if fpath.endswith('.yaml'):
        return SchismPolygonIoFactory().get_reader('yaml').read(fpath)
    elif fpath.endswith('.shp'):
        return SchismPolygonIoFactory().get_reader('shp').read(fpath)
    else:
        raise ValueError("Not supported file type")


def write_polygons(fpath, polygons):
    """
    """
    if fpath.endswith('.yaml'):
        return SchismPolygonIoFactory().get_writer('yaml').write(fpath, polygons)
    elif fpath.endswith('.shp'):
        return SchismPolygonIoFactory().get_writer('shp').write(fpath, polygons)
    else:
        raise ValueErroreError("Not supported file type")
