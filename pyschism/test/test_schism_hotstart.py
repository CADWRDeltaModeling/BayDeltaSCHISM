#!/usr/bin/env python
# -*- coding: utf-8 -*-

from schism_hotstart import read_hotstart
from schism_mesh import read_mesh
import numpy as np
import unittest
import os


class TestSchismHotstart(unittest.TestCase):

    def test_read_hotstart(self):
        """ Check values from a hotstart
        """
        fpath_mesh = os.path.join(
            os.path.dirname(__file__),
            'testdata/schism_hotstart/simple_triquad/hgrid1.gr3')
        fpath_vmesh = os.path.join(
            os.path.dirname(__file__),
            'testdata/schism_hotstart/simple_triquad/vgrid1.in')
        mesh = read_mesh(fpath_mesh, fpath_vmesh)
        fpath_hotstart = os.path.join(
            os.path.dirname(__file__),
            'testdata/schism_hotstart/simple_triquad/hotstart1_elev0.in')
        hotstart = read_hotstart(mesh, fpath_hotstart)
        desired = np.array([[0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 35.],
                            [0., 10., 32.5]])
        np.testing.assert_allclose(hotstart.elems[0], desired)
        desired = np.array([[0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 35.],
                            [0., 0., 10., 30.]])
        np.testing.assert_allclose(hotstart.sides[0], desired)
        desired = np.array([[10., 35., 10., 35.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 35., 10., 35.,  0.,  0.,
                                0.,  0.,  0.,  0.,  0.],
                            [10., 30., 10., 30.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]])
        np.testing.assert_allclose(hotstart.nodes[0], desired)


if __name__ == '__main__':
    unittest.main()
