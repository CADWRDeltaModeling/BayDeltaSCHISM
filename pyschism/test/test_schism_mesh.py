#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
""" unit tests of schism_mesh
"""
from schism_mesh import SchismMesh, read_mesh, write_mesh, BoundaryType
import numpy as np
import unittest
import os
import xmlrunner


class TestSchismMesh(unittest.TestCase):
    """ Unit test class for TriSchismMesh
    """

    def setUp(self):
        self.testdata_dir = os.path.join(os.path.dirname(__file__), "testdata")
        self.fpath_mesh = os.path.join(self.testdata_dir, "testmesh.gr3")
        self.fpath_vmesh_sz = os.path.join(self.testdata_dir, "vgrid_sz.in")

    def test_schism_mesh_sms_reader(self):
        fpath_mesh = os.path.join(self.testdata_dir, 'testmesh.2dm')
        mesh = read_mesh(fpath_mesh)
        self.assertEqual(mesh.n_nodes(), 112)
        self.assertEqual(mesh.n_elems(), 135)
        self.assertTrue(np.allclose(mesh.node(0), np.array([0., 100., 0.])))
        self.assertTrue(np.array_equal(mesh.elem(0), np.array([2, 0, 4])))

    def test_find_two_neigboring_node_paths(self):
        path = self.fpath_mesh
        mesh = read_mesh(path)
        # Tri area
        line_segment = (31.0, 69.0, 39.0, 101.0)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path, [32, 25, 19, 14])
        self.assertListEqual(down_path, [24, 18, 13, 9])
        # Quad area
        line_segment = (69.0, 69.0, 101.0, 61.0)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path, [64, 73, 82, 90])
        self.assertListEqual(down_path, [56, 65, 74, 83])
        # Mixed area
        line_segment = (-1.0, 1.0, 101.0, 9.0)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path,
                             [52, 60, 68, 76, 84, 91, 97, 102, 106, 109, 111])
        self.assertListEqual(down_path,
                             [44, 53, 61, 69, 77, 85, 92, 98, 103, 107, 110])
        # Ill-defined, tri
        line_segment = (31.0, 71.0, 39.0, 101.0)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path, [25, 19, 14])
        self.assertListEqual(down_path, [24, 18, 13, 9])
        # Ill-defined, quad
        line_segment = (71.0, 69.0, 101.0, 61.0)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path, [73, 82, 90])
        self.assertListEqual(down_path, [65, 74, 83])
        # Diagonal corner cut
        line_segment = (82., -3, 103., 18.)
        up_path, down_path = mesh.find_two_neighboring_node_paths(line_segment)
        self.assertListEqual(up_path, [109, 111, 110])
        self.assertListEqual(down_path, [106, 103, 107, 104, 108])

    def test_schism_mesh_gr3_reader_wo_vgrid(self):
        path = self.fpath_mesh
        mesh = read_mesh(path)
        self.assertEqual(mesh.n_nodes(), 112)
        self.assertEqual(mesh.n_elems(), 135)
        # Boundaries
        self.assertEqual(mesh.n_boundaries(), 3)
        self.assertEqual(mesh.n_boundaries(btype=BoundaryType.OPEN), 1)
        self.assertEqual(mesh.n_boundaries(btype=BoundaryType.LAND), 2)
        self.assertEqual(mesh.n_total_boundary_nodes(BoundaryType.OPEN), 11)

    def test_schism_mesh_gr3_reader_w_vgrid_sz(self):
        fpath_mesh = self.fpath_mesh
        fpath_vmesh = self.fpath_vmesh_sz
        mesh = read_mesh(fpath_mesh, fpath_vmesh)
        self.assertEqual(mesh.vmesh.param['nvrt'], 12)
        self.assertEqual(mesh.vmesh.param['kz'], 2)
        self.assertEqual(mesh.vmesh.param['h_s'], 80.)
        self.assertEqual(mesh.vmesh.param['h_c'], 5.0)
        self.assertTrue(np.allclose(mesh.vmesh.sigma, np.array(
            [-1.00, -0.9, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0.])))

    def test_schism_mesh_gr3_writer(self):
        fpath_mesh = self.fpath_mesh
        mesh = read_mesh(fpath_mesh)
        fpath_mesh_out = os.path.join(
            os.path.dirname(__file__), "testdata/meshout.gr3")
        write_mesh(mesh, fpath_mesh_out, write_boundary=True)
        meshout = read_mesh(fpath_mesh_out)
        self.assertEqual(meshout.n_nodes(), 112)
        self.assertEqual(meshout.n_elems(), 135)
        self.assertEqual(meshout.n_boundaries(), 3)
        if os.path.exists(fpath_mesh_out):
            os.remove(fpath_mesh_out)

    def test_schism_mesh_areas(self):
        fpath_mesh = self.fpath_mesh
        mesh = read_mesh(fpath_mesh)
        areas = mesh.areas()
        self.assertEqual(areas[0], 50.)
        self.assertEqual(areas[60], 100.)

    def test_schism_mesh_edge_len(self):
        fpath_mesh = self.fpath_mesh
        mesh = read_mesh(fpath_mesh)
        edge_lens = mesh.edge_len()
        self.assertAlmostEqual(edge_lens[0], 14.14213562)
        self.assertAlmostEqual(edge_lens[1], 10.)

    def test_schism_mesh_centroids(self):
        fpath_mesh = self.fpath_mesh
        mesh = read_mesh(fpath_mesh)
        centroids = mesh.centroids()
        np.testing.assert_almost_equal(
            centroids[0, :], np.array([6.66666667, 96.66666667]))
        np.testing.assert_almost_equal(
            centroids[60, :], np.array([75., 45.]))


if __name__ == '__main__':
    # unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    unittest.main()
