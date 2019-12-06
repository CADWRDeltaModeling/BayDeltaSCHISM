#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" unit tests of schism_vertical_mesh
"""
from schism_vertical_mesh import SchismLocalVerticalMesh, read_vmesh, write_vmesh
from schism_mesh import read_mesh
import numpy as np
import unittest
import os


class TestSchismVerticalMesh(unittest.TestCase):

    def setUp(self):
        self.dir_cur = os.path.dirname(__file__)

    def check_vmesh_lsc2_1(self, vmesh):
        self.assertEqual(vmesh.ivcor, 1)
        self.assertEqual(vmesh.n_vert_levels(), 48)
        self.assertEqual(len(vmesh.sigma), 6)
        self.assertEqual(vmesh.kbps[0], 42)
        self.assertEqual(vmesh.kbps[5], 0)
        actual = vmesh.sigma[0]
        desired = np.full((vmesh.n_vert_levels(),), np.nan)
        desired[:6] = np.array([-1.00000, -0.757479, -0.562685, -0.400108,
                                -0.187927,  0.000000])
        np.testing.assert_almost_equal(actual, desired)

    def test_read_vmesh_lsc2(self):
        fpath_vmesh = os.path.join(self.dir_cur,
                                   'testdata/testmesh/vgrid_lsc2_1.in')
        vmesh = read_vmesh(fpath_vmesh)
        self.check_vmesh_lsc2_1(vmesh)

    def test_write_vmesh_lsc2(self):
        fpath_vmesh_in = os.path.join(self.dir_cur,
                                      'testdata/testmesh/vgrid_lsc2_1.in')
        vmesh_in = read_vmesh(fpath_vmesh_in)
        fpath_vmesh_out = os.path.join(self.dir_cur,
                                       'testdata/testmesh/vgrid_lsc2_1_testout.in')
        try:
            write_vmesh(vmesh_in, fpath_vmesh_out)
            vmesh_out = read_vmesh(fpath_vmesh_out)
            self.check_vmesh_lsc2_1(vmesh_out)
        finally:
            pass
            if os.path.exists(fpath_vmesh_out):
                os.remove(fpath_vmesh_out)

    def test_build_vertical_mesh_from_sigma_lsc2(self):
        fpath_vmesh = os.path.join(self.dir_cur,
                                   'testdata/testmesh/vgrid_lsc2_1.in')
        vmesh_in = read_vmesh(fpath_vmesh)
        vmesh_new = SchismLocalVerticalMesh(vmesh_in.sigma)
        self.check_vmesh_lsc2_1(vmesh_new)

    def test_build_z(self):
        fpath_mesh = os.path.join(self.dir_cur,
                                  'testdata/testmesh/testmesh.gr3')
        fpath_vmesh = os.path.join(self.dir_cur,
                                   'testdata/testmesh/vgrid.in')
        mesh = read_mesh(fpath_mesh, fpath_vmesh)
        z = mesh.build_z()
        desired = np.arange(-100.0, 0.1, 10.0)
        np.testing.assert_allclose(z[0], desired)
        node_i = 5
        desired = np.full((mesh.vmesh.n_vert_levels(), ), -80.0)
        desired[2:] = np.arange(-80.0, 0.1, 10.0)
        np.testing.assert_allclose(z[node_i], desired)


if __name__ == '__main__':
    unittest.main()
