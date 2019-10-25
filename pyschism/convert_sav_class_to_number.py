#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import argparse
import numpy as np
import matplotlib.pyplot as plt
import gdal
import ogr
from schism_mesh import read_mesh, write_mesh
from schism_polygon import read_polygons, Polygon, Point
from scipy.ndimage import gaussian_filter as gfilt

def create_arg_parse():
    """ Create argument parser
    Parameters
    ----------
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=str, default="hgrid.gr3",
                        help="mesh file for the horizontal mesh")
    parser.add_argument("--density", required=True,
                        help="tiff file for density")
    parser.add_argument("--target", type=str,
                        help="Target polygons to calculate density")
    parser.add_argument("--output", type=str, default="sav_D.gr3",
                        help="output file name")
    return parser


def read_density_tiff(fpath_densitiy_tiff):
    """ Read geotiff values for density
    It is assumed that the projected regular coordinates.

    Parameters
    ----------
    fpath_densitiy_tiff: str
        filename for SAV desity diff

    Returns
    -------
    numpy.ndarray
        3D array containing x's, y's, and density. The shape is (n_x, n_y, 3)
    """
    ds = gdal.Open(fpath_densitiy_tiff)
    (upper_left_x, x_size, x_rotation, upper_left_y,
     y_rotation, y_size) = ds.GetGeoTransform()
    band = ds.GetRasterBand(1)
    array = band.ReadAsArray()
    # xv, yv = np.meshgrid(xrange(array.shape[1]), xrange(array.shape[0]))
    # x = xv * x_size + upper_left_x + x_size / 2.
    # y = yv * y_size + upper_left_y + y_size / 2.
    return (upper_left_x, x_size, x_rotation, upper_left_y,
            y_rotation, y_size), array


def main():
    parser = create_arg_parse()
    args = parser.parse_args()

    tiff = gdal.Open(args.density)
    (upper_left_x, x_size, x_rotation, upper_left_y,
     y_rotation, y_size) = tiff.GetGeoTransform()
    proj = tiff.GetProjection()
    red = tiff.GetRasterBand(1).ReadAsArray()
    green = tiff.GetRasterBand(2).ReadAsArray()
    blue = tiff.GetRasterBand(3).ReadAsArray()
    allband = np.dstack((red, green, blue))
    ndvi = np.zeros_like(red)

    classes = [{'color': (0, 0, 0), 'class': 0.},
               {'color': (0, 80, 255), 'class': 1.},
               {'color': (0, 150, 255), 'class': 2.},
               {'color': (0, 255, 255), 'class': 3.},
               {'color': (0, 255, 150), 'class': 4.},
               {'color': (0, 255, 80), 'class': 5.},
               {'color': (0, 200, 0), 'class': 6.},
               {'color': (150, 255, 0), 'class': 7.},
               {'color': (255, 255, 0), 'class': 8.},
               {'color': (255, 150, 0), 'class': 9.},
               {'color': (255, 0, 0), 'class': 10.},
               ]
    colors = np.array([c['color'] for c in classes],dtype=[('R','<i4'),('G','<i4'),('B','<i4')])
    colarr = colors.view(np.int).reshape(colors.shape + (-1,))
    classval = np.array([c['class'] for c in classes],dtype='d')
    order = np.argsort(colors,axis=0,order = ('R','G','B'))    
    refsort = colarr[order,:]
    valorder = classval[order]

    vals = allband.reshape(-1,3)
    ndvi = -np.empty(vals.shape[0],dtype="d") 
    nclass = len(refsort)
    for iref in range(nclass):
        print("Class: %s/%s" % (iref,nclass-1))
        vo = valorder[iref]
        imatch = np.where((vals == refsort[iref,:]).all(axis=1))
        ndvi[imatch] = vo
    assert np.all(ndvi>-1.)
    ndvi=ndvi.reshape(red.shape)
    ndvi = gfilt(ndvi, sigma=3, order=0)
        

    gtiff_driver = gdal.GetDriverByName('GTiff')
    if gtiff_driver is None:
        raise ValueError
    fpath_out = 'ndvi_adj2.tif'
    ds = gtiff_driver.Create(fpath_out,
                             ndvi.shape[1],
                             ndvi.shape[0],
                             1,
                             gdal.GDT_Float32,)
    ds.SetGeoTransform([upper_left_x, x_size, x_rotation, upper_left_y,
                        y_rotation, y_size])
    ds.SetProjection(proj)
    ds.GetRasterBand(1).WriteArray(ndvi)
    ds.FlushCache()

    # mesh = read_mesh(args.mesh)
    # polygons = read_polygons(args.target)


if __name__ == '__main__':
    import sys
    sys.argv.extend(
        ["--density", "delta_2016_20_28_mosaic_NDVI_tif.tif"])
    sys.argv.extend(["--mesh", "hgrid.gr3"])
    sys.argv.extend(["--target", "test/testdata/sav/frankstract.yaml"])
    main()
