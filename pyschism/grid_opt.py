#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module contains routines to perform grid optimization with two options:
  1. lsqr without constraint to solve Ax=b (scipy.sparse.linalg.lsqr)
  2.  minimize function 1/2*||Ax-b||^2 using the L-BFGS-B algorithm (scipy.optimize.fmin_l_bfgs_b)

x is depth at nodes with respect to a nominal reference surface (which may be greater than sea level in upstream locations).

Regularization:

  1.  close to the original values for all nodes: damp
  2.  minimize the 1st derivative of node elevation along land boundaries: damp_shoreline

Notes:

 * The function "cal_z_ref" only applies to the Bay Delta grid and need to be modified for other grids.
 * This script create an optimized gr3 file (_opt.gr3) only when one set of optimization parameters is specified.

First version, completed on 9/11/2013
"""
from gaussian_quadrature import GaussianQuadratureQuad4, GaussianQuadratureTri3, GaussianQuadratureLine2
from stacked_dem_fill import stacked_dem_fill
from schism_mesh import read_mesh, write_mesh, BoundaryType, EdgeType
from scipy.sparse.linalg import lsqr
from scipy.optimize import fmin_l_bfgs_b
from scipy.sparse import lil_matrix, eye, vstack
import numpy as np
import schism_yaml
import argparse
import os
import logging


def object_func(x, A, b):
    """ Objective function for the optimization for L-BFGS-B
    """
    y = A * x - b
    return 0.5 * y.dot(y)


def fprime(x, A, b):
    """ The gradient of the objective function with respect to the heights (x).
        This gradient is a vector the same size as x.
        A^T (Ax-b)
    """
    return A.transpose() * (A * x - b)


class GridOptimizer(object):
    """ Grid optimizer class
    """

    def __init__(self, **kwargs):
        """ Constructor

            Parameters
            ----------

            Returns
            -------
        """
        self.mesh = kwargs['mesh']
        self.demfiles = kwargs['demfiles']
        self.na_fill = kwargs['na_fill']
        self.logger = kwargs.get('logger')
        self.order_quadrature_tri_dem = 4
        self.order_quadrature_quad_dem = 5

    def select_solver(self, solver):
        """ Select solver

            Parameters
            ----------
            solver: str
                Name of a solver for the optimization
        """
        if solver != 'L-BFGS-B' and solver != 'lsqr':
            solver = 'L-BFGS-B'
            if self.logger is not None:
                self.logger.info(
                    "invalid solver specified, L-BFGS-B will be used")
        return solver

    def show_parameters(self, solver, param):
        """ Show optimization parameters

            Parameters
            ----------
            solver: str
                solver name
            param: dict
                parameters for the optimization
        """
        if self.logger is not None:
            msg = "%s optimization parameters used: %g, %g, %g, %g" % (solver, param['damp'], param['damp_shoreline'], param['face_coeff'], param['volume_coeff'])
            self.logger.info(msg)

    def collect_element_quadrature_points_for_dem(self):
        """ Collect all quadrature points to calculate volumes of elements
            with DEM

            Returns
            -------
            numpy.array
                Quadrature points of all elements
        """
        quad_tri = GaussianQuadratureTri3(self.order_quadrature_tri_dem)
        quad_quad = GaussianQuadratureQuad4(self.order_quadrature_quad_dem)
        n_quad_points = self.calculate_total_number_of_quadrature_points()
        quad_points = np.empty((n_quad_points, 2))
        row_i = 0
        for node_idx in self.mesh.elems:
            n_nodes = len(node_idx)
            if n_nodes == 3:
                pts = quad_tri.values_at_quadrature_points(
                    self.mesh.nodes[node_idx, :2])
            elif n_nodes == 4:
                pts = quad_quad.values_at_quadrature_points(
                    self.mesh.nodes[node_idx, :2])
            else:
                raise ValueError("Not supported element type")
            n_pts = pts.shape[0]
            quad_points[row_i:row_i + n_pts, :] = pts
            row_i += n_pts
        return quad_points

    def collect_face_quadrature_points_for_dem(self, edges):
        """ Collect all quadrature points to calculate areas of faces
            with DEM

            Parameters
            ----------
            edges: numpy.array
                list of edges containing indices of the two end nodes

            Returns
            -------
            numpy.array
                Quadrature points of faces
        """
        quadrature = GaussianQuadratureLine2(self.order_quadrature_quad_dem)
        n_quad_points = len(quadrature.quad_pts)
        quad_points = np.empty((n_quad_points * edges.shape[0], 2))
        for face_i, node_idx in enumerate(edges):
            pts = quadrature.values_at_quadrature_points(
                self.mesh.nodes[node_idx, :2])
            row_i = face_i * n_quad_points
            quad_points[row_i:row_i + n_quad_points, :] = pts
        return quad_points

    def get_dem_elevation(self, list_of_points):
        """ Get elevations from DEM

            Do this once to save time

            Parameters
            ----------
            list_of_points: list of numpy.array
                array of coordinate matrices of points to get DEM elevations

            Returns
            -------
            list of numpy.array
                list of elevation vectors
        """
        pts = np.vstack(list_of_points)
        elev = stacked_dem_fill(self.demfiles, pts, require_all=False, na_fill=self.na_fill)
        row_i = 0
        list_of_elev = []
        for arr in list_of_points:
            list_of_elev.append(elev[row_i:row_i + arr.shape[0]])
            row_i += arr.shape[0]
        return list_of_elev

    def optimize(self, params, solver='L-BFGS-B'):
        """ Perform a grid optimization

            Two solvers are available:
            (1) L-BFGS-B (default): minimize function 1/2*||Ax-b||^2
            (2) linear least square solver (Ax=b).

            Parameters
            ----------
            params: dict
                Dict of optimization parameters
            solver: str, optional
                solver name

            Returns
            -------
            numpy.array
                optimized elevation
        """
        nodes = self.mesh.nodes
        edges = self.collect_edges()

        quad_points_for_elements = self.collect_element_quadrature_points_for_dem()
        quad_points_for_faces = self.collect_face_quadrature_points_for_dem(
            edges)

        # Fill DEM elevations to node elevations
        elev_dem = self.get_dem_elevation([nodes[:, :2],
                                           quad_points_for_elements,
                                           quad_points_for_faces])
        elev_at_nodes = elev_dem[0]
        nodes[:, 2] = elev_at_nodes
        elev_at_quad_points_of_elements = elev_dem[1]
        elev_at_quad_points_of_faces = elev_dem[2]

        # Element
        ref_surf_at_nodes = self.calculate_reference_surface_maximum()
        depths_at_nodes = ref_surf_at_nodes - elev_at_nodes
        areas_of_elements = self.calculate_element_areas()

        # volumes_of_elements = self.integrate_over_elements(depths_at_nodes)

        depth_at_quad_points_elem = self.calculate_depth_at_element_quad_points(elev_at_quad_points_of_elements, ref_surf_at_nodes)
        volumes_of_elements_dem = self.calculate_element_volumes_w_dem(depth_at_quad_points_elem)
        depth_of_elements_dem = np.divide(volumes_of_elements_dem, areas_of_elements)

        solver = self.select_solver(solver)
        self.show_parameters(solver, params)
        mat_elem = self.assemble_element_matrix(areas_of_elements)

        # Faces
        mat_face = self.assemble_face_matrix(edges)
        lengths_of_faces = self.calculate_edge_lengths(edges)
        depth_at_quad_points_faces = self.calculate_depth_at_face_quad_points(edges, elev_at_quad_points_of_faces, ref_surf_at_nodes)
        areas_of_faces_dem = self.calculate_face_areas_w_dem(edges, depth_at_quad_points_faces)
        depths_of_faces_dem = areas_of_faces_dem / lengths_of_faces

        # Boundaries
        damp_bnd = params.get('damp_shoreline', 0.)
        if damp_bnd > 0.:
            mat_bnd, vec_bnd = self.build_boundary_equations(ref_surf_at_nodes)
        else:
            mat_bnd = None
            vec_bnd = None

        # Build a global matrix and vector for the optimization
        mat, vec = self.build_global_matrix_and_vector(params, mat_elem, mat_face, depth_of_elements_dem, depths_of_faces_dem, mat_bnd, vec_bnd, depths_at_nodes, solver)

        damp = params.get('damp', 0.)
        if self.logger is not None:
            self.logger.info("Run the optimization...")
        if solver == 'lsqr':
            result = lsqr(mat, vec, damp)
        elif solver == 'L-BFGS-B':
            result = fmin_l_bfgs_b(object_func, depths_at_nodes, fprime=fprime, args=(mat, vec),
                                   approx_grad=0, bounds=[(0., None) for _ in range(self.mesh.n_nodes())],
                                   m=10, factr=100.0, pgtol=1e-05, epsilon=1e-08, iprint=-1,
                                   maxfun=15000, maxiter=15000, disp=None, callback=None)
        return ref_surf_at_nodes - result[0]

    def build_global_matrix_and_vector(self, params,
                                       mat_elem, mat_face, vec_elem, vec_face,
                                       mat_bnd, vec_bnd,
                                       depths_at_nodes, solver='L-BFGS-B'):
        """ Build a global matrix and vector for optimization

            Parameters
            ----------
            params: dict
                Dict of optimization parameters
            solver: str, optional
                solver name

            Returns
            -------
            numpy.sparce.lil_matrix
        """
        if self.logger is not None:
            self.logger.info("Assemble a global matrix and vectors...")
        face_coeff = params.get('face_coeff', 1.)
        vol_coeff = params.get('vol_coeff', 1.)
        if (face_coeff == 0. and vol_coeff == 0.) or face_coeff < 0. or vol_coeff < 0.:
            if self.logger is not None:
                self.logger.warning('invalid vol_coeff and face_coeff, default values (1, 1) will be used')
            face_coeff = 1.
            vol_coeff = 1.
        damp_bnd = params['damp_shoreline']
        mat = vstack((vol_coeff * mat_elem, face_coeff * mat_face))
        vec = np.hstack((vol_coeff * vec_elem, face_coeff * vec_face))
        if solver == 'lsqr':
            if damp_bnd > 0.:
                mat = vstack((mat, damp_bnd * mat_bnd))
                vec = np.hstack((vec, damp_bnd * vec_bnd))
        else:
            if damp_bnd > 0.:
                mat = vstack((mat, damp_bnd * mat_bnd))
                vec = np.hstack((vec, damp_bnd * vec_bnd))
            damp = params['damp']
            if damp > 0.:
                mat_node = eye(self.mesh.n_nodes())
                mat = vstack((mat, damp * mat_node))
                vec = np.hstack((vec, damp * depths_at_nodes))
        return mat, vec

    def build_boundary_equations(self, ref_surf_at_nodes):
        """ Build a matrix and vector of land boundary constraints

            Returns
            -------
            numpy.sparse.lil_matrix
                Matrix of land boundary equations
            numpy.array
                Vector of land boundary equations
        """
        n_eqns = self.count_boundary_equations()
        mat = lil_matrix((n_eqns, self.mesh.n_nodes()))
        vec = np.empty((n_eqns))
        eqn_i = 0
        for bound in self.mesh.boundaries:
            if bound.btype == BoundaryType.LAND:
                bound_node_idx = bound.nodes
                for i in range(len(bound_node_idx) - 2):
                    node_idx = bound_node_idx[i:i+3]
                    nodes = self.mesh.nodes[node_idx, :2]
                    length_1 = np.linalg.norm(nodes[1] - nodes[0])
                    length_2 = np.linalg.norm(nodes[1] - nodes[2])
                    coeff = np.array((-length_2, length_1 + length_2, -length_1)) / length_2
                    mat[eqn_i, node_idx] = coeff
                    vec[eqn_i] = coeff.dot(ref_surf_at_nodes[node_idx])
                    eqn_i += 1
        return mat, vec

    def count_boundary_equations(self):
        """ Count how many boundary constraint equations there are
        """
        n_eqns = 0
        for bound in self.mesh.boundaries:
            if bound.btype == BoundaryType.LAND:
                n_nodes = len(bound.nodes)
                n_eqns += n_nodes - 2 if n_nodes > 2 else 0
        return n_eqns

    def collect_edges(self, exclude_land_boundaries=False):
        """ Collect edges for the optimization

            Parameters
            ----------
            exclude_land_boundaries: bool, optional
                Switch to exclude land edges

            Returns
            -------
            numpy.array
                matrix of nodal indices of edges
        """
        edges = []
        for edge in self.mesh.edges:
            edge_type = edge[2]
            if exclude_land_boundaries is True:
                if edge_type <= EdgeType.OPEN:
                    edges.append(edge[:2])
            else:
                edges.append(edge[:2])
        return np.array(edges)

    def calculate_element_areas(self):
        """ Calculate areas of all elements

            Returns
            -------
            numpy.array
                array of the areas of elements
        """
        quad_tri = GaussianQuadratureTri3(2)
        quad_quad = GaussianQuadratureQuad4(2)
        areas = np.empty(self.mesh.n_elems())
        for elem_i, node_idx in enumerate(self.mesh.elems):
            n_nodes = len(node_idx)
            if n_nodes == 3:
                areas[elem_i] = quad_tri.domain_size(self.mesh.nodes[node_idx])
            elif n_nodes == 4:
                areas[elem_i] = quad_quad.domain_size(
                    self.mesh.nodes[node_idx])
            else:
                raise ValueError("Not supported element type")
        return areas

    def calculate_edge_lengths(self, edges):
        """ Calculate areas of all edges

            Returns
            -------
            numpy.array
                array of the areas of edges
        """
        quadrature = GaussianQuadratureLine2(2)
        lengths = np.empty(edges.shape[0])
        for elem_i, node_idx in enumerate(edges):
            lengths[elem_i] = quadrature.domain_size(self.mesh.nodes[node_idx])
        return lengths

    def calculate_total_number_of_quadrature_points(self):
        """ Calculate total number of quadrature points of the mesh
            with the given order

            Returns
            -------
            int
                Total number of quadrature points of the mesh
        """
        quad_tri = GaussianQuadratureTri3(self.order_quadrature_tri_dem)
        quad_quad = GaussianQuadratureQuad4(self.order_quadrature_quad_dem)
        # Collect number of quadrature points
        n_quad_points_tri = quad_tri.number_of_quadrature_points()
        n_quad_points_quad = quad_quad.number_of_quadrature_points()
        n_quad_points = 0
        for node_idx in self.mesh.elems:
            if len(node_idx) == 3:
                n_quad_points += n_quad_points_tri
            elif len(node_idx) == 4:
                n_quad_points += n_quad_points_quad
            else:
                raise ValueError("Not supported element type")
        return n_quad_points

    def calculate_depth_at_element_quad_points(self, elev_at_quads, ref_surf_at_nodes):
        """ Calculate depth at quad points

            This depth is calculated by subtracting bottom elevation
            at quadrature points from the reference surface at quadrature
            points that is calculated by reference elevation at nodes
            with shape functions.

            Parameters
            ----------
            elev_at_quads: numpy.array
                Elevation vector at quadrature points
            ref_surf_at_nodes: numpy.array
                Reference elevation at nodes

            Returns
            -------
            numpy.array
                Vector of depth at quadrature points
        """
        ref_surf_at_quads = self.calculate_values_at_element_quadarture_points(
            ref_surf_at_nodes)
        depth_at_quads = ref_surf_at_quads - elev_at_quads
        depth_at_quads[depth_at_quads < 0.] = 0.
        return depth_at_quads

    def calculate_depth_at_face_quad_points(self, edges, elev_at_quads, ref_surf_at_nodes):
        """ Calculate depth at quad points

            This depth is calculated by subtracting bottom elevation
            at quadrature points from the reference surface at quadrature
            points that is calculated by reference elevation at nodes
            with shape functions.

            Parameters
            ----------
            elev_at_quads: numpy.array
                Elevation vector at quadrature points
            ref_surf_at_nodes: numpy.array
                Reference elevation at nodes

            Returns
            -------
            numpy.array
                Vector of depth at quadrature points
        """
        ref_surf_at_quads = self.calculate_values_at_face_quadarture_points(
            edges, ref_surf_at_nodes)
        depth_at_quads = ref_surf_at_quads - elev_at_quads
        depth_at_quads[depth_at_quads < 0.] = 0.
        return depth_at_quads

    def calculate_element_volumes_w_dem(self, depth_at_quads):
        """ Calculate volumes of elements based on DEM

            Parameters
            ----------
            depth_at_quad: numpy.array
                Vector of depth at the quadrature points

            Returns
            -------
            numpy.array
                Volumes of elements
        """
        if self.logger is not None:
            self.logger.info("Calculating element volumes with DEM elevations...")
        quad_tri = GaussianQuadratureTri3(self.order_quadrature_tri_dem)
        quad_quad = GaussianQuadratureQuad4(self.order_quadrature_quad_dem)
        volumes = np.empty((self.mesh.n_elems()))
        row_i = 0
        for elem_i, node_idx in enumerate(self.mesh.elems):
            n_nodes = len(node_idx)
            nodes = self.mesh.nodes[node_idx]
            if n_nodes == 3:
                n_quad_pts = len(quad_tri.quad_wts)
                volumes[elem_i] = (quad_tri.quad_wts * quad_tri.jacobian_det(nodes)).dot(depth_at_quads[row_i:row_i + n_quad_pts])
            elif n_nodes == 4:
                n_quad_pts = len(quad_quad.quad_wts)
                volumes[elem_i] = (quad_quad.quad_wts * quad_quad.jacobian_det(nodes)).dot(depth_at_quads[row_i:row_i + n_quad_pts])
            else:
                raise ValueError("Not supported element type")
            row_i += n_quad_pts
        return volumes

    def calculate_values_at_element_quadarture_points(self, values):
        """ Calculate values at quadrature points

            Parameters
            ----------
            values: numpy.array
                A vector of nodal values

            Returns
            -------
            numpy.array
                A vector of values at quadrature points
        """
        quad_tri = GaussianQuadratureTri3(self.order_quadrature_tri_dem)
        quad_quad = GaussianQuadratureQuad4(self.order_quadrature_quad_dem)
        values_at_quad_points = []
        for node_idx in self.mesh.elems:
            n_nodes = len(node_idx)
            val_at_nodes = values[node_idx]
            if n_nodes == 3:
                values_at_quad_points.extend(
                    quad_tri.values_at_quadrature_points(val_at_nodes))
            elif n_nodes == 4:
                values_at_quad_points.extend(
                    quad_quad.values_at_quadrature_points(val_at_nodes))
            else:
                raise ValueError("Not supported element type")
        return np.array(values_at_quad_points)

    def calculate_values_at_face_quadarture_points(self, edges, values):
        """ Calculate values at quadrature points

            Parameters
            ----------
            values: numpy.array
                A vector of nodal values

            Returns
            -------
            numpy.array
                A vector of values at quadrature points
        """
        quadrature = GaussianQuadratureLine2(self.order_quadrature_quad_dem)
        values_at_quad_points = []
        for node_idx in edges:
            val_at_nodes = values[node_idx]
            values_at_quad_points.extend(
                quadrature.values_at_quadrature_points(val_at_nodes))
        return np.array(values_at_quad_points)

    def calculate_reference_surface_maximum(self):
        """ Create reference surface elevation at individual nodes

            step 1: derive max elevation within connected elements
            step 2: compare with the reference calculated by
            calculate_reference_surface() and use the higher value
            between the two

            Returns
            -------
            numpy.array
                Vector of reference elevation at nodes
        """
        elev_max = self.calculate_max_elevation_in_balls(self.mesh.nodes[:, 2])
        elev_ref = self.calculate_reference_surface(self.mesh.nodes)
        elev = np.maximum(elev_max, elev_ref)
        return elev

    def calculate_max_elevation_in_balls(self, elev):
        """ Calculate maximum elevation in a ball from a node

            Parameters
            ----------
            elev: numpy.array
                array of elevation at nodes

            Returns
            -------
            numpy.array
                maximum elevation at nodes
        """
        z_max = [np.max([np.max([elev[node_i]
                                 for node_i in self.mesh.elem(elem_i)])
                         for elem_i in elems])
                 for elems in self.mesh.node2elems]
        return z_max

    def calculate_reference_surface(self, coords):
        """ Define reference water surface at locations specified in nodes
            based on the assumptions, which only applicable to Bay Delta grid
            (1) The surface elevation increases linearly from west (ocean) to east
            (2) east of (x_old_river, y_old_river), the elevation increases linearly towards the south

            NOTE: This is Bay-Delta Specific. Coordinates for the calculation are hard-wired.

            Parameters
            ----------
            coords: numpy.array
                Coordinates to calculate reference surface
                The dimension of the array is (-1, 2) or more columns.
                The first two columns are used.

            Returns
            -------
            numpy.array
                Reference water surface for Bay-Delta
        """
        x_east = 653768.1
        x_west = 499546.3
        x_old_river = 647170.0
        y_old_river = 4186000.0
        y_sjr_end = 4171563.0
        eta_ref = np.where(coords[:, 0] > x_old_river,
                           3.0 * (y_old_river - coords[:, 1])
                           / (y_old_river - y_sjr_end), 0.0)
        eta_ref = eta_ref.clip(0.0)
        eta_ref = eta_ref + 0.5 * (coords[:, 0] - x_west) / (x_east - x_west)
        return eta_ref

    def assemble_element_matrix(self, areas):
        """ Build a matrix for element optimization

            Parameters
            ----------
            areas: numpy.array
                areas of the elements
        """
        if self.logger is not None:
            self.logger.info("Assemble a matrix for elements....")
        mesh = self.mesh
        n_elements = mesh.n_elems()
        n_nodes = mesh.n_nodes()
        mat_a = lil_matrix((n_elements, n_nodes))
        order = 2
        quad_quad = GaussianQuadratureQuad4(order)
        quad_tri = GaussianQuadratureTri3(order)
        for elem_i, node_idx in enumerate(mesh.elems):
            if len(node_idx) == 3:
                mat_a_elem = quad_tri.quadrature_vector(
                    mesh.nodes[node_idx]) / areas[elem_i]
            elif len(node_idx) == 4:
                mat_a_elem = quad_quad.quadrature_vector(
                    mesh.nodes[node_idx]) / areas[elem_i]
            else:
                raise ValueError("Not supported element type")
            mat_a[elem_i, node_idx] = mat_a_elem
        return mat_a

    def assemble_face_matrix(self, edges):
        """ Build a matrix for face optimization
            The order of the quadrature is fixed

            Parameters
            ----------
            edges: numpy.array
                list of edges

            Returns
            -------
            lil_matrix
                matrix for face (edge) optimization
        """
        n_edges = len(edges)
        n_nodes = self.mesh.n_nodes()
        mat = lil_matrix((n_edges, n_nodes))
        for edge_i, node_idx in enumerate(edges):
            mat[edge_i, node_idx] = 0.5
        return mat

    def calculate_face_areas_w_dem(self, edges, depth_at_quads):
        """ Calculate area of faces based on DEM

            Parameters
            ----------
            edges: numpy.array

            depth_at_quad: numpy.array
                Vector of depth at the quadrature points

            Returns
            -------
            numpy.array
                Areas of faces
        """
        quadrature = GaussianQuadratureLine2(self.order_quadrature_quad_dem)
        areas = np.empty(edges.shape[0])
        row_i = 0
        n_quad_pts = len(quadrature.quad_wts)
        for edge_i, node_idx in enumerate(edges):
            nodes = self.mesh.nodes[node_idx]
            areas[edge_i] = (quadrature.quad_wts * quadrature.jacobian_det(nodes)).dot(depth_at_quads[row_i:row_i + n_quad_pts])
            row_i += n_quad_pts
        return areas

    def calculate_reference_surface_at_face_quadarture_points(self, ref_surf):
        """ Calculate reference surface at quadrature points
        """
        quad_tri = GaussianQuadratureTri3(self.order_quadrature_tri_dem)
        quad_quad = GaussianQuadratureQuad4(self.order_quadrature_quad_dem)
        ref_surf_at_quads = []
        for node_idx in self.mesh.elems:
            n_nodes = len(node_idx)
            values = ref_surf[node_idx]
            if n_nodes == 3:
                ref_surf_at_quads.extend(
                    quad_tri.values_at_quadrature_points(values))
            elif n_nodes == 4:
                ref_surf_at_quads.extend(
                    quad_quad.values_at_quadrature_points(values))
            else:
                raise ValueError("Not supported element type")
        return np.array(ref_surf_at_quads)

    def integrate_over_elements(self, values):
        """ Integrate over elements with the values at nodes

            Parameters
            ----------
            values: numpy.array
                Values at nodes to integrate

            Returns
            -------
            numpy.array
                Vector of integration over each element
        """
        quad_tri = GaussianQuadratureTri3(2)
        quad_quad = GaussianQuadratureQuad4(2)
        volumes = np.empty((self.mesh.n_elems()))
        for elem_i, node_idx in enumerate(self.mesh.elems):
            n_nodes = len(node_idx)
            if n_nodes == 3:
                volumes[elem_i] = quad_tri.integrate(self.mesh.nodes[node_idx], values[node_idx])
            elif n_nodes == 4:
                volumes[elem_i] = quad_quad.integrate(self.mesh.nodes[node_idx], values[node_idx])
            else:
                raise ValueError("Not supported element type")
        return volumes

    def integrate_over_edges(self, edges, values):
        """ Integrate over edges with the values at nodes

            Parameters
            ----------
            values: numpy.array
                Values at nodes to integrate

            Returns
            -------
            numpy.array
                Vector of integration over each edge
        """
        quadrature = GaussianQuadratureLine2(2)
        volumes = [quadrature.integrate(self.mesh.nodes[node_idx], values[node_idx])
                   for node_idx in edges]
        return volumes


def create_arg_parser():
    """ Create a argparse.ArgumentParser

    """
    parser = argparse.ArgumentParser(
        description='Perform grid optimization with a *.2dm SMS mesh or gr3 file. An optimized gr3 file with extension _opt.gr3 will be created if only one set of optimization parameter specified.')
    parser.add_argument('filename',
                        default=None,
                        help='name of 2dm or gr3 file')
    parser.add_argument('demfile',
                        default=None,
                        help='file containing list of DEMs. These can be in any form that gdal accepts, which includes ESRI ascii format and GeoTiffs')
    parser.add_argument('optparm',
                        default=None,
                        help='file containing optimization parameters: damp, damp_shoreline, face_coeff, volume_coeff')
    parser.add_argument('--optfile',
                        help='name for the gr3 file for the optimized results')
    # parser.add_argument('--detailed_outputs',
    #                     action='store_true',
    #                     default=False,
    #                     help='whether to write detailed optimization results to files, default=False')
    # parser.add_argument('--prefix',
    #                     default='',
    #                     help='prefix used for output files when --detailed_outputs flag is set')
    # parser.add_argument('--boundary_list',
    #                     default='',
    #                     help='boundary node list information (in csv format) when missing from .2dm or .gr3 file, generated from Kijin''s script')
    # parser.add_argument('--remove_boundary_faces',
    #                     action='store_true',
    #                     default=False,
    #                     help='whether to remove faces along the land boundaries, default=False')
    # parser.add_argument('--polygon_file',
    #                     default='None',
    #                     help='polygon definition file used to specify the area for partial grid optimization')
    parser.add_argument('--solver',
                        default='L-BFGS-B',
                        help='solver used for optimization, either L-BFGS-B (default) or lsqr')
    return parser


def init_logger():
    """ Create a logger
    """
    logging_level = logging.INFO
    logging_fname = 'grid_opt.log'
    logging.basicConfig(level=logging_level,
                        filename=logging_fname,
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging_level)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    return logging.getLogger('grid_opt')


def grid_opt_with_args(args):
    """ Optimize grid with arguments parsed by argparse
    """
    with open(args.optparam) as f:
        opt_param = schism_yaml.load(f)
    mesh = read_mesh(args.filename, nodestring_option='land')
    with open(args.demfile, 'r') as f:
        demfiles = schism_yaml.load(f)
        # dir = os.path.dirname(args.demfile)
        # demfiles_full = [os.path.join(dir, fname) for fname in demfiles]
    logger = init_logger()
    kwargs = {'mesh': mesh,
              'demfiles': demfiles, # demfiles_full,
              'na_fill': args.na_fill,
              'logger': logger}
    optimizer = GridOptimizer(**kwargs)
    optimized = optimizer.optimize(opt_param)
    fpath_output = args.optfile
    write_mesh(mesh, fpath_output, node_attr=-optimized)


def main():
    """ A main function to manage command line run
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    grid_opt_with_args(args)


if __name__ == '__main__':
    main()
