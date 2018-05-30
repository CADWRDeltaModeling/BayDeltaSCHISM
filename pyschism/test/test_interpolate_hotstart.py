#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" Unit test of interpolate_hotstart
"""
from interpolate_hotstart import interpolate_hotstart
from schism_mesh import read_mesh
from schism_hotstart import read_hotstart
import numpy as np
import unittest
import os


class TestInterpolateHotstart(unittest.TestCase):
    """ Class to test 'interpolate_hotstart.py'
    """

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__),
                                     'testdata/schism_hotstart')

    # def tearDown(self):
        # os.chdir(self.test_dir)

    def test_interpolate_hotstart_simple_triquad_self(self):
        """ Interpolating to the same grid should yield the same hotstart
        """
        mesh_in = read_mesh(
            os.path.join(self.test_dir, 'simple_triquad/hgrid1.gr3'),
            os.path.join(self.test_dir, 'simple_triquad/vgrid1.in'))
        hotstart_base = read_hotstart(
            mesh_in,
            os.path.join(self.test_dir, 'simple_triquad/hotstart1_elev0.in'))
        hotstart_new = interpolate_hotstart(mesh_in, hotstart_base, mesh_in)
        # np.testing.assert_allclose(hotstart_base.nodes, hotstart_new.nodes)
        # np.testing.assert_allclose(hotstart_base.elems, hotstart_new.elems, atol=1e-100)
        # np.testing.assert_allclose(hotstart_base.sides, hotstart_new.sides, atol=1e-100)
        # np.testing.assert_allclose(hotstart_base.nodes_elev, hotstart_new.nodes_elev, atol=1e-100)
        # np.testing.assert_allclose(hotstart_base.nodes_dry, hotstart_new.nodes_dry)
        # np.testing.assert_allclose(hotstart_base.elems_dry, hotstart_new.elems_dry)
        # np.testing.assert_allclose(hotstart_base.sides_dry, hotstart_new.sides_dry)
        self.assertEqual(hotstart_base, hotstart_new)


if __name__ == '__main__':
    unittest.main()
