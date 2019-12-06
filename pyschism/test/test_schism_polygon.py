#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Test Suite for Polygon
"""
from schism_polygon import SchismPolygon, read_polygons, write_polygons
from shapely.geometry import Point
import unittest
import os


class TestSchismPolygon(unittest.TestCase):

    def setUp(self):
        self.cur_dir = os.path.dirname(__file__)
        self.test_dir = os.path.join(self.cur_dir, 'testdata')

    def read_test_polygons(self):
        fpath = os.path.join(self.test_dir, 'polygons.yaml')
        return read_polygons(fpath)

    def check_polygons(self, polygons):
        prop = {'name': 'polygon1', 'attribute': '2.', 'type': 'none'}
        self.assertEqual(polygons[0], SchismPolygon(
            [[-1, -1], [10, 0], [9, 9], [0, 10]], prop=prop))
        prop = {'name': 'polygon2', 'type': 'min', 'attribute': 'x'}
        self.assertEqual(polygons[1], SchismPolygon(
            [[-1, -1], [10, 0], [9, 9]], prop=prop))

    def test_polygon_contain_a_point(self):
        polygons = self.read_test_polygons()
        point = (5, 5)
        self.assertTrue(polygons[0].contains(Point(point)))
        point = (9, 9.1)
        self.assertFalse(polygons[0].contains(Point(point)))

    def test_polygon_reader_yaml(self):
        fpath = os.path.join(self.test_dir, 'polygons.yaml')
        polygons = read_polygons(fpath)
        self.check_polygons(polygons)

    def test_write_polygons_to_shapefile(self):
        polygons = self.read_test_polygons()
        fpath_out_name = 'tempout'
        fpath_out = os.path.join(self.test_dir, fpath_out_name + '.shp')
        try:
            write_polygons(fpath_out, polygons)
            polygons_written = read_polygons(fpath_out)
            self.assertEqual(polygons, polygons_written)
        finally:
            for fpath in [os.path.join(self.test_dir, fpath_out_name + ext)
                          for ext in ('.dbf', '.prj', '.shp', '.shx')]:
                if os.path.exists(fpath):
                    os.remove(fpath)


if __name__ == '__main__':
    # unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    unittest.main()
