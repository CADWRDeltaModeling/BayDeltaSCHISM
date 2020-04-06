#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Gaussian quadrature in 2D space
"""
import numpy as np


class GaussianQuadrature(object):
    """ Base class of GaussianQuadrature
    """

    def __init__(self, order):
        self.order = order
        self.quad_pts_1d, self.quad_wts_1d = list(map(
            np.array, np.polynomial.legendre.leggauss(order)))
        self.quad_pts, self.quad_wts = self.calculate_quadrature_points_and_weights()
        self.shape_at_quads = self.shape(self.quad_pts)
        self.shape_derivative_at_quads = self.shape_derivative(self.quad_pts)

    def shape(self, pts):
        """ Abstract shape function
        """
        raise NotImplementedError()

    def shape_derivative(self, pts):
        """ Abstract shape derivative function
        """
        raise NotImplementedError()

    def calculate_quadrature_points_and_weights(self):
        """ Abstract method
        """
        raise NotImplementedError()

    def number_of_quadrature_points(self):
        """ Get the number of quadrature points

            Returns
            -------
            int
                Number of quadrature points
        """
        return len(self.quad_pts)

    def values_at_quadrature_points(self, values):
        """ Get quadrature points

            Parameters
            ----------
            values: numpy.array
                values at quadrature points

            Returns
            -------
            numpy.array
                values of Gaussian quadrature points
        """
        return self.shape_at_quads.dot(values)

    def integrate(self, vertices, values=None):
        """ Integrate values over a quad element

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes) with values.
                The shape needs to be (:, 2)

            values: numpy.array, optional
                A value vector at vertices
                If it is not provided, the thrid column will be used
                as values

            Returns
            -------
            float
                result of integration
        """
        if values is None:
            values = vertices[:, 2]
        return self.quadrature_vector(vertices).dot(values)

    def quadrature_vector(self, vertices):
        """ Create a quadrature matrix for quadrature integration
            Taking a dot product this quadrature matrix and the values
            at the quadrature points will result in quadrature

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes) with values.
                The shape needs to be (:, 2)

            Returns
            -------
            numpy.array
                two-dimensional matrix of quadrature matrix
        """
        jacobian = self.jacobian_det(vertices)
        return (self.quad_wts * jacobian).dot(self.shape_at_quads)

    def jacobian_det(self, vertices):
        """ Determinant of Jacobian at quadrature points

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (:, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            numpy.array
                array of determinant ant quadrature points
        """
        jacobian = self.shape_derivative_at_quads.dot(vertices[:, :2])
        return np.array([np.linalg.det(j) for j in jacobian])

    def domain_size(self, vertices):
        """ Abstract method to calculate the size of the domain
        """
        raise NotImplementedError()

    def average(self, vertices, values):
        """ Calculate the average of the value over the domain.

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (:, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            float
                the length of the line
        """
        return (self.integrate(vertices, values)
                / self.domain_size(vertices))


class GaussianQuadratureLine2(GaussianQuadrature):
    """ Gaussian quadrature on line with two end points in 2-D space
    """

    def __init__(self, order):
        """ Constructor

            Parameters
            ----------
            order: int
                Order of Gaussian quadrature
        """
        self.n_vertices = 2
        super(GaussianQuadratureLine2, self).__init__(order)

    def calculate_quadrature_points_and_weights(self):
        return self.quad_pts_1d, self.quad_wts_1d

    def shape(self, pts):
        """ Shape functions
            Ordering is counter-clockwise direction

            Parameters
            ----------
            pts: numpy.array
                Local coordinates.

            Returns
            -------
            numpy.array
                matrix of shape function value at the given points
        """
        return np.array([0.5 * (1.0 - pts), 0.5 * (1.0 + pts)]).transpose()

    def shape_derivative(self, pts):
        """ Derivatives of shape functions

            Parameters
            ----------
            pts: numpy.array
                Local coordinates. The dimension is (-1, 2)

            Returns
            -------
            numpy.array
                matrix of shape function derivative wrt xi value at (*, eta)
        """
        return np.array([[-0.5, 0.5] for _ in range(len(pts))])

    def jacobian_det(self, vertices):
        """ Determinant of Jacobian at quadrature points, 1-D version

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (-1, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            numpy.array
                array of determinant ant quadrature points
        """
        l = self.domain_size(vertices)
        n_quad_pts = len(self.quad_pts)
        return np.ones((n_quad_pts)) * (l * 0.5)

    def domain_size(self, vertices):
        """ Size of domian, which is the length of the line in this case

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (2, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            float
                the length of the line
        """
        return np.linalg.norm(vertices[1, :2] - vertices[0, :2])

    def average(self, vertices, values):
        """ Integrate values over a quad element

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes) with values.
                The shape needs to be (-1, 2)

            values: numpy.array
                The values at vertices

            Returns
            -------
            float
                result of integration
        """
        wts = self.quad_wts
        val_at_pts = self.shape_at_quads.dot(values)
        return np.sum(wts * val_at_pts) * 0.5


class GaussianQuadratureQuad4(GaussianQuadrature):
    """ Gaussian Quadrature for a quadrilateral with four nodes
    """

    def __init__(self, order):
        """ Constructor

            Parameters
            ----------
            order: int
                order of Gaussian quadrature between 2 and 5
        """
        self.n_vertices = 4
        super(GaussianQuadratureQuad4, self).__init__(order)

    def calculate_quadrature_points_and_weights(self):
        """ Calculate quadrature points and weights
        """
        quad_pts = np.array([(self.quad_pts_1d[i], self.quad_pts_1d[j])
                             for i in range(self.order) for j in range(self.order)])
        wts = self.quad_wts_1d.reshape(self.order, -1)
        quad_wts = wts.dot(wts.transpose()).flatten()
        return quad_pts, quad_wts

    def domain_size(self, vertices):
        """ Size of domain, which is the area of the quadrilateral
            in this case.
            The area is calculated with shoelace equation.

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (4, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            float
                the length of the line
        """
        return 0.5 * np.abs(np.dot(vertices[:, 0], np.roll(vertices[:, 1], 1))
                            - np.dot(np.roll(vertices[:, 0], 1), vertices[:, 1]))

    def shape(self, pts):
        """ Shape functions
            Ordering is counter-clockwise direction

            Parameters
            ----------
            pts: numpy.array
                Local coordinates. The dimension is (-1, 2)

            Returns
            -------
            numpy.array
                matrix of shape function value at (xi, eta)
        """
        return np.array([0.25 * (1.0 - pts[:, 0]) * (1.0 - pts[:, 1]),
                         0.25 * (1.0 + pts[:, 0]) * (1.0 - pts[:, 1]),
                         0.25 * (1.0 + pts[:, 0]) * (1.0 + pts[:, 1]),
                         0.25 * (1.0 - pts[:, 0]) * (1.0 + pts[:, 1])]).transpose()

    def shape_derivative(self, pts):
        """ Derivatives of shape functions

            Parameters
            ----------
            pts: numpy.array
                Local coordinates. The dimension is (-1, 2)

            Returns
            -------
            numpy.array
                matrix of shape function derivative wrt xi value at (*, eta)
        """
        derivative = np.stack((np.array([-0.25 * (1.0 - pts[:, 1]),
                                         0.25 * (1.0 - pts[:, 1]),
                                         0.25 * (1.0 + pts[:, 1]),
                                         -0.25 * (1.0 + pts[:, 1])]).transpose(),
                               np.array([-0.25 * (1.0 - pts[:, 0]),
                                         -0.25 * (1.0 + pts[:, 0]),
                                         0.25 * (1.0 + pts[:, 0]),
                                         0.25 * (1.0 - pts[:, 0])]).transpose()))
        return np.swapaxes(derivative, 0, 1)

    def jacobian(self, vertices, local_coord=None):
        """ Create a Jacobian matrix or matrixes at the given local
            coordinates

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (4, 2) or more columns.
                The values in the first two columns will be used.

            local_coord: numpy.array
                local coordinates where a Jacobian is calculated

            Returns
            -------
            numpy.array
                Jacobian matrix
        """
        if local_coord is None:
            return self.shape_derivative_at_quads.dot(vertices[:, :2])
        else:
            return self.shape_derivative(local_coord).dot(vertices[:, :2])


class GaussianQuadratureTri3(GaussianQuadrature):
    """ Gaussian Quadrature for triangles with three nodes
    """

    def __init__(self, order):
        """ Constructor

            Parameters
            ----------
            order: int
                order of Gaussian quadrature between 2 and 5
        """
        super(GaussianQuadratureTri3, self).__init__(order)

    def calculate_quadrature_points_and_weights(self):
        """ Calculate quadrature points and weights
        """
        if self.order == 2:
            quad_pts = np.array([[1. / 6., 1. / 6., 2. / 3.],
                                 [1. / 6., 2. / 3., 1. / 6.],
                                 [2. / 3., 1. / 6., 1. / 6.]])
            quad_wts = np.array([1. / 3., 1. / 3., 1. / 3.])
        elif self.order == 4:
            quad_pts = np.array([[1. / 3., 1. / 3., 1. / 3.],
                                 [0.797426985353087, 0.101286507323456, 0.101286507323456],
                                 [0.101286507323456, 0.797426985353087, 0.101286507323456],
                                 [0.101286507323456, 0.101286507323456, 0.797426985353087],
                                 [0.059715871789770, 0.470142064105115, 0.470142064105115],
                                 [0.470142064105115, 0.059715871789770, 0.470142064105115],
                                 [0.470142064105115, 0.470142064105115, 0.059715871789770]])
            quad_wts = np.array([0.225, 0.125939180544827, 0.125939180544827, 0.125939180544827, 0.132394152788506,
                                 0.132394152788506, 0.132394152788506])
        else:
            raise NotImplementedError()
        return quad_pts, quad_wts

    def domain_size(self, vertices):
        """ Size of domian, which is the area of the quadrilateral
            in this case.
            The area is calculated with shoelace equation.

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (3, 2) or more columns.
                The values in the first two columns will be used.

            Returns
            -------
            float
                the length of the line
        """
        return 0.5 * np.abs(np.dot(vertices[:3, 0], np.roll(vertices[:3, 1], 1))
                            - np.dot(np.roll(vertices[:3, 0], 1), vertices[:3, 1]))

    def shape(self, pts):
        """ Shape functions
            Ordering is counter-clockwise direction

            Parameters
            ----------
            pts: numpy.array
                Local coordinates. Not used

            Returns
            -------
            numpy.array
                matrix of shape function value at (xi, eta)
        """
        return pts

    def shape_derivative(self, pts):
        """ Derivatives of shape functions

            Parameters
            ----------
            pts: numpy.array
                Local coordinates. Not used

            Returns
            -------
            numpy.array
                matrix of shape function derivative wrt xi value at (*, eta)
        """
        return np.array([[[-1., 1., 0.],
                          [-1., 0., 1.]] for _ in range(pts.shape[0])])

    def jacobian_det(self, vertices):
        """ Determinant of Jacobian at quadrature points

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes) but it is not used

            Returns
            -------
            numpy.array
                array of determinant ant quadrature points
        """
        l = self.domain_size(vertices)
        return np.full((len(self.quad_pts)), l)

    def jacobian(self, vertices, local_coord=None):
        """ Create a Jacobian matrix or matrixes at the given local
            coordinates

            Parameters
            ----------
            vertices: numpy.array
                coordinates of vertices (or nodes)
                The shape needs to be (4, 2) or more columns.
                The values in the first two columns will be used.

            local_coord: numpy.array
                local coordinates where a Jacobian is calculated

            Returns
            -------
            numpy.array
                Jacobian matrix
        """
        raise NotImplementedError()
