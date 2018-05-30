#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import schism_linestring
import unittest
import os
import glob


class TestSchismLineString(unittest.TestCase):
    """ Unit test of SCHISM LineString
    """

    def setUp(self):
        dir_cur = os.path.dirname(__file__)
        self.dir_test = os.path.join(dir_cur, "testdata/schism_linestring")

    def test_read_linestrings_yaml(self):
        fpath = os.path.join(self.dir_test, 'flowlines.yaml')
        lines = schism_linestring.read_linestrings(fpath)
        self.assertEquals([l.prop['name'] for l in lines],
                          ['ocean', 'mixed1', 'middle'])
        self.assertEquals([list(l.coords) for l in lines],
                          [[(41.0, 69.0), (41.0, 101.0)],
                           [(101.0, 75.0), (69.0, 75.0)],
                           [(45.0, 5.0), (45.0, 25.0)]])

    def test_read_linestrings_shapefile(self):
        fpath = os.path.join(self.dir_test, 'test_linestrings.shp')
        lines = schism_linestring.read_linestrings(fpath)
        self.assertEqual([l.prop['name'] for l in lines],
                         ['ocean', 'mixed1', 'middle'])
        self.assertEqual([list(l.coords) for l in lines],
                         [[(41.0, 69.0), (41.0, 101.0)],
                          [(101.0, 75.0), (69.0, 75.0)],
                          [(45.0, 5.0), (45.0, 25.0)]])

    def test_write_linestrings_yaml(self):
        fpath_in = os.path.join(self.dir_test, 'flowlines.yaml')
        lines = schism_linestring.read_linestrings(fpath_in)
        fpath_out = 'test_linestrings.yaml'
        try:
            schism_linestring.write_linestrings(fpath_out, lines)
            lines_readback = schism_linestring.read_linestrings(fpath_out)
            self.assertEqual([l.prop['name'] for l in lines],
                             [l.prop['name'] for l in lines_readback])
            self.assertEqual([list(l.coords) for l in lines],
                             [list(l.coords) for l in lines_readback])
        finally:
            if os.path.exists(fpath_out):
                os.remove(fpath_out)

    def test_write_linestrings_shp(self):
        fpath_in = os.path.join(self.dir_test, 'flowlines.yaml')
        lines = schism_linestring.read_linestrings(fpath_in)
        fpath_out = 'test_linestrings.shp'
        try:
            schism_linestring.write_linestrings(fpath_out, lines)
        finally:
            files_to_remove = glob.glob(os.path.splitext(fpath_out)[0] + '.*')
            for filename in files_to_remove:
                if os.path.exists(filename):
                    os.remove(filename)


if __name__ == '__main__':
    unittest.main()
