#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TriQuadMesh unit test
"""

import schism_mesh as schism_mesh
import triquadmesh as triquadmesh
import numpy as np
import unittest
import os


class TestTriQuadMesh(unittest.TestCase):
    """ Unit test class for TriQuadMesh
    """

    def setUp(self):
        self.cur_dir = os.path.dirname(__file__)
        reader = schism_mesh.SchismMeshIoFactory().get_reader('gr3')
        fpath_mesh = os.path.join(self.cur_dir, "testdata/testmesh.gr3")
        self.mesh = reader.read(fpath_mesh)

    def test_init(self):
        """ Test __init__. Does nothing. Always pass.
        """
        pass

    def test_nodes(self):
        nodes = self.mesh.nodes
        self.assertEqual(nodes.shape[0], 112)
        np.testing.assert_almost_equal(nodes[0], np.array([0.0, 100.0, 0.0]))

    def test_elems(self):
        elems = self.mesh.elems
        self.assertEqual(len(elems), 135)
        np.testing.assert_equal(elems[0], np.array([2, 0, 4]))
        np.testing.assert_equal(elems[47], np.array([70, 63, 55, 62]))

    def test_edges(self):
        edges = self.mesh.edges
        np.testing.assert_equal(edges[0], np.array([0, 4, 0, 0, 84]))
        np.testing.assert_equal(edges[2], np.array([2, 0, 3, 0, -1]))

    def test_allocate(self):
        mesh = triquadmesh.TriQuadMesh()
        n_nodes = 20
        n_elems = 40
        mesh.allocate(n_elems, n_nodes)
        self.assertEqual(mesh._elems.shape[0], n_elems,
                         'Incorrect memory allocated for cells.')
        self.assertEqual(mesh._nodes.shape[0], n_nodes,
                         'Incorrect memory allocated for nodes.')

    def test_set_node(self):
        mesh = triquadmesh.TriQuadMesh()
        n_nodes = 20
        n_elems = 40
        mesh.allocate(n_elems, n_nodes)
        index = 10
        coords = np.array([1., 2., 3.])
        mesh.set_node(index, coords)
        self.assertTrue((mesh._nodes[index] == coords).all(),
                        'Stored node coord differs from the input.')

    def test_set_elem(self):
        mesh = triquadmesh.TriQuadMesh()
        n_nodes = 20
        n_elems = 40
        mesh.allocate(n_elems, n_nodes)
        elem_i = 10
        connectivity = [1, 2, 3]
        mesh.set_elem(elem_i, connectivity)
        self.assertListEqual(list(mesh.elem(elem_i)), connectivity,
                             "Stored element connectivity differs from the input.")
        elem_i = 11
        connectivity = [1, 2, 3, 4]
        mesh.set_elem(elem_i, connectivity)
        self.assertListEqual(list(mesh.elem(elem_i)), connectivity,
                             "Stored element connectivity differs from the input.")

    def test_basic_attributes(self):
        mesh = self.mesh
        self.assertEqual(mesh.n_nodes(), 112)
        self.assertEqual(mesh.n_elems(), 135)
        self.assertEqual(mesh.n_edges(), 247)

    def test_find_edge(self):
        mesh = self.mesh
        # Internal tri
        edge = mesh.find_edge((4, 8))
        self.assertListEqual(list(mesh._edges[edge]), [8,  4,  0,  4, 86])
        # Internal quad
        edge = mesh.find_edge((73, 82))
        self.assertListEqual(list(mesh._edges[edge]), [73, 82,  0, 55, 61])
        # Boundary tri
        edge = mesh.find_edge((51, 59))
        self.assertListEqual(list(mesh._edges[edge]),
                             [59,  51, triquadmesh.EdgeType.LAND, 128, -1])
        # Boundary quad
        edge = mesh.find_edge((109, 111))
        self.assertListEqual(list(mesh._edges[edge]),
                             [109, 111, triquadmesh.EdgeType.LAND, 83, -1])

    def test_get_elems_i_from_node(self):
        mesh = self.mesh
        node_i = 54
        elems_i = list(mesh.get_elems_i_from_node(node_i))
        self.assertListEqual(elems_i, [40, 41, 46, 118, 124, 125])

    def test_find_nodes_in_box(self):
        mesh = self.mesh
        # Quad #1
        box = [89., -1., 101., 10.1]
        nodes_i = mesh.find_nodes_in_box([box[i]
                                          for i in triquadmesh._X1X2Y1Y2])
        self.assertSetEqual(set(nodes_i), set([109, 111, 107, 110]))
        # Quad #2
        box = [91., -1., 101., 10.1]
        nodes_i = mesh.find_nodes_in_box([box[i]
                                          for i in triquadmesh._X1X2Y1Y2])
        self.assertSetEqual(set(nodes_i), set([111, 110]))
        # Tri
        box = [-1., -1., 10.1, 10.1]
        nodes_i = mesh.find_nodes_in_box([box[i]
                                          for i in triquadmesh._X1X2Y1Y2])
        self.assertSetEqual(set(nodes_i), set([44, 52, 53, 60]))

    def test_get_neighor_nodes(self):
        mesh = self.mesh
        # Triangular
        node_i = 12
        nodes = mesh.get_neighbor_nodes(node_i)
        self.assertListEqual(nodes, [4, 8, 17, 7, 24, 18])
        # Quadrilateral
        node_i = 73
        nodes = mesh.get_neighbor_nodes(node_i)
        self.assertListEqual(nodes, [64, 65, 81, 82])

    def test_add_boundary(self):
        mesh = self.mesh
        # Land
        nodes_i = [0, 2, 5]
        mesh.add_boundary(nodes_i, triquadmesh.BoundaryType.LAND)
        edge_i = mesh.find_edge([0, 2])
        edge_type = mesh._edges[edge_i][2]
        self.assertEqual(edge_type, triquadmesh.EdgeType.LAND)
        edge_i = mesh.find_edge([2, 5])
        edge_type = mesh._edges[edge_i][2]
        self.assertEqual(edge_type, triquadmesh.EdgeType.LAND)

    def test_find_closest_nodes(self):
        mesh = self.mesh
        # One node
        pos = [1., 1.]
        node_i = mesh.find_closest_nodes(pos)
        self.assertEqual(node_i, 52)
        # Two nodes
        pos = [1., 2.]
        node_i = mesh.find_closest_nodes(pos, count=2)
        self.assertSetEqual(set(node_i), set([44, 52]))
        # Boundary only
        pos = [9., 8.]
        node_i = mesh.find_closest_nodes(pos, count=2, boundary=True)
        self.assertSetEqual(set(node_i), set([44, 60]))

    def test_shortest_path(self):
        mesh = self.mesh
        # Easy straight line
        path = mesh.shortest_path(73, 57)
        self.assertListEqual(list(path), [73, 65, 57])
        # Hard non-straight line, #1 from quad to tri
        path = mesh.shortest_path(73, 49)
        # This is one of the non-unique solution for this grid.
        self.assertListEqual(list(path), [73, 65, 57, 49])
        # Hard non-straight line, #2 tri
        path = mesh.shortest_path(54, 29)
        self.assertListEqual(list(path), [54, 46, 29])
        # Boundary only
        path = mesh.shortest_path(67, 51, True)
        self.assertListEqual(list(path), [67, 59, 51])

    def test_find_elem(self):
        mesh = self.mesh
        # tri #1
        pos = [5., 2.]
        elem_i = mesh.find_elem(pos)
        self.assertEqual(elem_i, 123)
        # tri #2
        pos = [5., 8.]
        elem_i = mesh.find_elem(pos)
        self.assertEqual(elem_i, 39)
        # quad
        pos = [95., 2.]
        elem_i = mesh.find_elem(pos)
        self.assertEqual(elem_i, 83)
        # Outside
        pos = [5., -2.]
        elem_i = mesh.find_elem(pos)
        self.assertEqual(elem_i, None)

    def test_find_closest_elems(self):
        mesh = self.mesh
        # Outside, tri
        pos = [1., -1.]
        elem_i = mesh.find_closest_elems(pos)
        self.assertEqual(elem_i, 123)
        # Outside, quad
        pos = [99., -1.]
        elem_i = mesh.find_closest_elems(pos)
        self.assertEqual(elem_i, 83)
        # Inside, tri
        pos = [2., 1.]
        elem_i = mesh.find_closest_elems(pos)
        self.assertEqual(elem_i, 123)
        # Inside, quad
        pos = [99., 11.]
        elem_i = mesh.find_closest_elems(pos)
        self.assertEqual(elem_i, 82)
        # Inside, multiple #1
        pos = [2., 1.]
        elem_i = mesh.find_closest_elems(pos, count=2)
        self.assertSetEqual(set(elem_i), set([39, 123]))
        # Inside, multiple #2
        pos = [31., 29.]
        elem_i = mesh.find_closest_elems(pos, count=2)
        self.assertSetEqual(set(elem_i), set([35, 47]))

    def test_trim_elems(self):
        mesh = self.mesh
        paths = [[35, 42, 49, 56, 64, 73, 82, 90], ]
        mesh.trim_elems(paths)
        self.assertEqual(mesh.n_nodes(), 112 - 12)
        self.assertEqual(mesh.n_elems(), 135 - 21)

    def test_is_elem_on_boundary(self):
        mesh = self.mesh
        # Tri on boundary
        elem_i = 0
        self.assertTrue(mesh.is_elem_on_boundary(elem_i))
        # Tri not on boundary
        elem_i = 1
        self.assertFalse(mesh.is_elem_on_boundary(elem_i))
        # Quad no boundary
        elem_i = 82
        self.assertTrue(mesh.is_elem_on_boundary(elem_i))
        # Quad not on boundary
        elem_i = 79
        self.assertFalse(mesh.is_elem_on_boundary(elem_i))

    def test_get_edges_from_node(self):
        mesh = self.mesh
        edges = mesh.get_elems_i_from_node(0)
        self.assertEqual(edges, set([0, 84]))

    def test_element2edges(self):
        mesh = self.mesh
        elem_i = 0
        edges = mesh.element2edges(elem_i)
        self.assertEqual(edges, [2, 0, 1])


if __name__ == '__main__':
    # unittest.main(testRunner=xmlrunner.XMLTestRunner(output='test-reports'))
    unittest.main()
