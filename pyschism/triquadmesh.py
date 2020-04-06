# -*- coding: utf-8 -*-
"""
This is a class to hold an unstructured triangular and quad mesh
for SCHISM.

Lots of the codes are copied and modified
from Rusty Chris Collerman's trigrid.

Prerequisite: Numpy, rtree package, and libspatialindex for rtree
"""

from .priority_queue import priorityDictionary
import rtree
import numpy as np
import types


def enum(**enums):
    """ A enum type definition

        Copied from http://stackoverflow.com/questions/36932/how-can-i-represent-an-enum-in-python
    """
    return type('Enum', (), enums)


# Edge trait (or marker)
# INTERNAL_EDGE = 0
# BOUNDARY_EDGE = 1
# OPEN_EDGE = 2
# LAND_EDGE = 3
# ISLAND_EDGE = 4
# CUT_EDGE = 99

EdgeType = enum(INTERNAL=0,
                BOUNDARY=1,
                OPEN=2,
                LAND=3,
                CUT=-1)

# Boundary type
# INVALID_BOUNDARY = -1
# OPEN_BOUNDARY = 1
# LAND_BOUNDARY = 2
# ISLAND_BOUNDARY = 3

BoundaryType = enum(INVALID=-1,
                    NO_TYPE=0,
                    OPEN=1,
                    LAND=2)

NodeType = enum(INVALID=-1,)

_XXYY = [0, 0, 1, 1]
_X1X2Y1Y2 = [0, 2, 1, 3]

MAX_NODES = 4


class TriQuadMesh(object):
    """ Class that holds a triangular and quadrilateral mesh information
    """

    def __init__(self, logger=None):
        """ Constructor of TriQuadMesh
        """
        self._logger = logger
        self._elems = None
        self._nodes = None
        self._edges = None
        self._node2elems = None
        self._node2edges = None
        self._node_index = None  # Rtree index for nodes
        self._elem_index = None  # Rtree index for elements
        self._elemcenter_index = None  # Rtree index for element centers

    @property
    def nodes(self):
        """ Node array consisting of three-dimensional coordinates of each node.
            The shape of the array is (# of nodes, 3)

            :getter: Get the array of the nodes.
            :type: Numpy float array.
        """
        return self._nodes

    @property
    def elems(self):
        """ Array of node indexes of all elements.
            The shape of the array is (# of elems, 5).

            Returns
            -------
            list of Numpy integer array
                list of node indexes for all elements
        """
        return [self.elem(i) for i in range(self._elems.shape[0])]
        # return self._elems

    @property
    def edges(self):
        """ Get the array of edges

            :getter: Get the array of the edges.
            :type: Numpy integer array
        """
        if self._edges is None:
            self.build_edges_from_elems()
        return self._edges

    @property
    def node2elems(self):
        if self._node2elems is None:
            self.build_elem_balls()
        return self._node2elems

    def node(self, node_i):
        return self._nodes[node_i]

    def elem(self, elem_i):
        """ Get connectivity of an element

            Parameters
            ----------
            elem_i: int
                element index


            Returns
            -------
            Numpy int32 array
                connectivity of the element (node indexes of the element)
                None, if the element is marked as deleted
        """
        if self._elems[elem_i, 0] == NodeType.INVALID:
            return None
        else:
            return self._elems[elem_i, self._elems[elem_i] > NodeType.INVALID]

    def mark_elem_deleted(self, elem_i):
        """ Mark an element as deleted or invalid.

            Parameters
            ----------
            elem_i: int
                element index to mark
        """
        self._elems[elem_i, 0] = NodeType.INVALID

    def allocate(self, n_elems, n_nodes):
        """ Allocate memory for nodes and elems

            Parameters
            ----------
            n_elems: int
                Total number of elems
            n_nodes: int
                Total number of nodes
        """
        self._nodes = np.full((n_nodes, 3), np.nan, dtype=np.float64)
        # Elements up to 2,147,483,647 (int32)
        # # of nodes in the element, and connectivities
        self._elems = np.full((n_elems, MAX_NODES),
                              np.iinfo(np.int32).min, dtype=np.int32)

    def set_node(self, index, coords):
        """ Set one node information.
            Memory for nodes must be allocated already.

            Parameters
            ----------
            index: integer
                Zero-based node index
            coords: Numpy array
                a Numpy array of node coordinates
        """
        if not index < self._nodes.shape[0]:
            raise ValueError("Accessing out of bound in node array")
        self._nodes[index, ] = coords

    def set_elem(self, index, connectivity):
        """ Set element connectivity information.
            Memory for elems must be allocated already.

            Parameters
            ----------
            index: integer
                Zero-based element index
            connectivity: Numpy array
                a Numpy array of element connectivity, which means node
                indexes in the element.
        """
        if not index < self._elems.shape[0]:
            raise ValueError("Accessing out of bound in node array")
        n_nodes = len(connectivity)
        if n_nodes < 3:
            raise ValueError("Not enough connectivity information.")
        if n_nodes > MAX_NODES:
            raise ValueError("Too many connectivity information.")
        self._elems[index, :len(connectivity)] = np.array(
            connectivity, dtype=np.int32)

    def n_nodes(self):
        """ Get the total number of nodes.
        """
        return self._nodes.shape[0]

    def n_elems(self):
        """ Get the total number of elements.
        """
        return self._elems.shape[0]

    def n_edges(self):
        """ Get the total number of edges.
        """
        return self.edges.shape[0]

    def compare(self, mesh):
        """ Compare the mesh with another

            Parameters
            ----------
            mesh: triquadmesh.TriQuadMesh
                a mesh to compare

            Returns
            -------
            boolean
                True if they have identical node and element array
        """
        if (self._nodes == mesh._nodes).all() and (self._elems == mesh._elems).all():
            return True
        else:
            return False

    def build_edges_from_elems(self, shift=1):
        """
        Build edge array from the elements.

        Parameters
        ----------
        shift:
            shift of indexing in edged building. It is introduce to keep
            the ordering of edges in line with SCHISM Mesh.
        """
        if self._logger is not None:
            self._logger.info("Building edges from elements")
        # iterate over elements, and for each element, if it's index
        # is smaller than a neighbor or if no neighbor exists,
        # write an edge record
        edges = []

        # this will get built on demand later.
        self._node2edges = None

        for elem_i in range(self.n_elems()):
            # find the neighbors:
            # the first neighbor: need another element that has
            # both self._elems[i,0] and self._elems[i,1] in its
            # list.
            my_set = set([elem_i])
            elem = self.elem(elem_i)
            n_nodes = len(elem)
            for j in range(shift, n_nodes + shift):
                node_a = elem[j % n_nodes]
                node_b = elem[(j + 1) % n_nodes]
                elem_ball_node_a = self.get_elems_i_from_node(node_a)
                elem_ball_node_b = self.get_elems_i_from_node(node_b)

                # the intersection is us and our neighbor
                # so difference out ourselves...
                adj_elem_of_edge = elem_ball_node_a.intersection(
                    elem_ball_node_b).difference(my_set)
                # and maybe we get a neighbor, maybe not (we're a boundary)
                n_neighbors = len(adj_elem_of_edge)
                if n_neighbors == 1:
                    adj_elem_i = adj_elem_of_edge.pop()
                elif n_neighbors == 0:
                    adj_elem_i = -1
                else:
                    raise RuntimeError("Cannot have more than two neighbors "
                                       "of one edge.")
                if adj_elem_i == -1 or elem_i < adj_elem_i:
                    edges.append((node_a,
                                  node_b,
                                  EdgeType.BOUNDARY
                                  if adj_elem_i == -1 else EdgeType.INTERNAL,
                                  elem_i, adj_elem_i))

        self._edges = np.array(edges, dtype=np.int32)

    def _build_node_index(self):
        if self._node_index is None:
            if self._logger is not None:
                self._logger.info("Building node indexes...")
            # assemble points into list of (id, [x x y y], None)
            # but new rtree allows for interleaved coordinates all the time.
            # best solution probably to specify interleaved=False
            tuples = [(i, self._nodes[i, _XXYY], None)
                      for i in range(self.n_nodes())
                      if np.isfinite(self._nodes[i, 0])]
            self._node_index = rtree.Rtree(tuples, interleaved=False)

    def _build_elem_index(self):
        # Build Rtree index for elems
        if self._elem_index is None:
            if self._logger is not None:
                self._logger.info("Building element indexes...")
            tuples = []
            for elem_i in range(self.n_elems()):
                # TODO: This could be better with numpy.
                box = [None, None, None, None]  # [xmin xmax ymin ymax]
                elem = self.elem(elem_i)
                for node_i in elem:
                    node = self._nodes[node_i]
                    if box[0] is None or box[0] > node[0]:
                        box[0] = node[0]
                    if box[1] is None or box[1] < node[0]:
                        box[1] = node[0]
                    if box[2] is None or box[2] > node[1]:
                        box[2] = node[1]
                    if box[3] is None or box[3] < node[1]:
                        box[3] = node[1]

                index = (elem_i, box, None)
                tuples.append(index)
            self._elem_index = rtree.Rtree(tuples, interleaved=False)

    def build_elem_balls(self):
        """ Build balls of elements around each node
        """
        if self._node2elems is not None:
            if self._logger is not None:
                self._logger.info("Remapping nodes to elements...")
            del self._node2elems
        if self._logger is not None:
            self._logger.info("Mapping nodes to elements...")
        # build array for point->element lookup
        # Use set for later convenience
        self._node2elems = [set() for _ in range(self.n_nodes())]
        for elem_i in range(self.n_elems()):
            elem = self.elem(elem_i)
            for node_index in elem:
                self._node2elems[node_index].add(elem_i)

    def get_elems_i_from_node(self, node_i):
        """ Get the ball of elements around a node, node_i

            Parameters
            ----------
            node_i: int
                node index (zero-based)

            Returns
            -------
            set
                set of element indexes
        """
        if self._node2elems is None:
            self.build_elem_balls()
        return self._node2elems[int(node_i)]

    def find_edge(self, nodes, direction=False):
        """ Find an edge index with the two given node indexes.

            Parameters
            ----------
            nodes: array-like
                two node indexes
            direction:
                match the ordering of the nodes when an edge is found.

            Returns
            -------
            int
                an edge index, None if not found
        """
        el0 = self.get_edges_from_node(nodes[0])
        if direction is True:
            for e in el0:
                if self.edges[e][1] == nodes[1]:
                    return e
            return None
        else:
            el1 = self.get_edges_from_node(nodes[1])
            for e in el0:
                if e in el1:
                    return e
            return None

    def find_nodes_in_box(self, box):
        """
        Find nodes in a bounding box. Note that the box is not interleaved.
        The backend is based on R-tree.

        Parameters
        ----------
        box: array-like
            array of bounding box, [x_min, x_max, y_min, y_max]

        Returns
        -------
        set
            node indexes
        """
        if self._node_index is None:
            self._build_node_index()
        nodes = self._node_index.intersection(box)
        return nodes

    def _build_node2edges(self):
        """
        Build a map from nodes to edges
        """
        if self._logger is not None:
            self._logger.info("Building nodes to edges...")
        # Build node2edges map
        n2e = [[] for i in range(self.n_nodes())]
        for edge_i in range(self.n_edges()):
            for n in self.edges[edge_i, :2]:
                n2e[int(n)].append(edge_i)
        self._node2edges = n2e

    def get_edges_from_node(self, node_i):
        """ Get edge indexes related to node_i

            Parameters
            ----------
            node_i: int
                Node index (zero-based)
            Returns
            -------
            list
                a list of edges
        """
        if self._node2edges is None:
            self._build_node2edges()
        if node_i < len(self._node2edges):
            return self._node2edges[node_i]
        else:
            return []

    def get_neighbor_nodes(self, node_i):
        """ Get neighboring node indexes from the given node index.
        """
        if self._node2edges is None:
            self._build_node2edges()
        nodes = []
        edges = self._node2edges[node_i]
        for edge_i in edges:
            edge = self.edges[edge_i]
            if edge[0] == node_i:
                nodes.append(edge[1])
            else:
                nodes.append(edge[0])
        return nodes

    def add_boundary(self, nodes, btype):
        """ Add boundary types to an edge with the given array of node indexes
        """
        node_prev_i = nodes[0]
        for node_i in nodes[1:]:
            edge_i = self.find_edge([node_prev_i, node_i])
            if edge_i is None:
                raise Exception('No edge found with the given nodes')
            if -1 not in self.edges[edge_i, 3:5]:
                raise Exception('Trying to tag a non-boundary edge '
                                'as boundary')
            if btype == BoundaryType.OPEN:
                self.edges[edge_i, 2] = EdgeType.OPEN
            elif btype == BoundaryType.LAND \
                    or btype == BoundaryType.ISLAND:
                self.edges[edge_i, 2] = EdgeType.LAND
            else:
                raise Exception("Unsupported boundary type")
            node_prev_i = node_i

    def find_closest_nodes(self, pos, count=1, boundary=False):
        """
        Returns the count closest nodes to the given node in 2D space.
        Roughly copied from trigrid

        Parameters
        ----------
        pos: array-like
            position
        count: int
            # of nodes to retrieve
        boundary: int 1
            only choose nodes on the boundary.

        Returns
        -------
        int or list
            nearest node indexes
        """
        if boundary:
            # print "Searching for nearby boundary point"
            # Rusty's Note:
            # This is slow,
            # but I'm too lazy to add any sort of index specific to
            # boundary nodes.
            # Note that this will include interprocessor boundary
            # nodes, too.
            boundary_nodes = np.unique(self.edges[self.edges[:, 2] > 0, :2])
            dists = np.sum((pos - self._nodes[boundary_nodes, 0:2]) ** 2,
                           axis=1)
            order = np.argsort(dists)
            closest = boundary_nodes[order[:count]]
            # print "   done with boundary node search"

            if count == 1:
                return closest[0]
            else:
                return closest
        else:
            if self._node_index is None:
                self._build_node_index()

            pos = np.array(pos)

            # returns the index of the grid point closest to the given point:
            hits = self._node_index.nearest(pos[_XXYY], count)

            # newer versions of rtree return a generator:
            if isinstance(hits, types.GeneratorType):
                # so translate that into a list like we used to get.
                hits = [next(hits) for _ in range(count)]

            if count > 1:
                return hits
            else:
                return hits[0]

    def shortest_path(self, n1, n2, boundary_only=False):
        """
        Dijkstra on the edge graph from node n1 to n2.
        copied and modified form Rusty's code.
        Keep in mind that the solution can be non-unique
        because there are multiple paths that have the same distances.

        Parameters
        ----------
        n1: int
            node index for one end of the path
        n2: int
            node_i for the other end
        boundary_only: boolean
            limit search to edges on the boundary

        Returns
        -------
        numpy.ndarray
            shortest node indexes or None if it cannot be found
        """
        queue = priorityDictionary()
        queue[n1] = 0

        done = {}

        while True:
            # find the queue-member with the lowest cost:
            best = queue.smallest()
            best_cost = queue[best]
            del queue[best]
            done[best] = best_cost
            if best == n2:
                # print "Found the ending point"
                break
            # figure out its neighbors
            all_nodes_i = self.get_neighbor_nodes(best)
            for node_i in all_nodes_i:
                if node_i in done:
                    # both for p and for points that we've already done
                    continue
                if boundary_only:
                    e = self.find_edge((best, node_i))
                    if self.edges[e, 2] < EdgeType.BOUNDARY:
                        continue
                dist = np.sqrt(
                    ((self._nodes[node_i] - self._nodes[best])**2).sum())
                new_cost = best_cost + dist
                if node_i not in queue:
                    queue[node_i] = np.inf
                if queue[node_i] > new_cost:
                    queue[node_i] = new_cost
        # reconstruct the path:
        path = [n2]
        while True:
            node_i = path[-1]
            if node_i == n1:
                break
            # figure out its neighbors
            all_nodes_i = self.get_neighbor_nodes(node_i)
            found_prev = False
            for nbr in all_nodes_i:
                if nbr == node_i or nbr not in done:
                    continue
                dist = np.sqrt(
                    ((self._nodes[node_i] - self._nodes[nbr])**2).sum())
                if done[node_i] == done[nbr] + dist:
                    path.append(nbr)
                    found_prev = True
                    break
            if found_prev is False:
                return None
        return np.array(path[::-1])

    @classmethod
    def _box_from_points(cls, points):
        """
        Format of the line segment: start_x, start_y, end_x, end_y
        """
        box = np.array(points)
        for p in points:
            for i in range(2):
                if box[0, i] > p[i]:
                    box[0, i] = p[i]
                if box[1, i] < p[i]:
                    box[1, i] = p[i]
        return np.transpose(box).reshape(4,)

    def find_intersecting_elems_with_line(self, line_segment):
        """ Format of the line segment: start_x, start_y, end_x, end_y
        """
        if self._elem_index is None:
            self._build_elem_index()

        x = np.array(line_segment).reshape(2, 2)
        normal = np.array((x[0, 1] - x[1, 1], x[1, 0] - x[0, 0]))
        box = self._box_from_points(x)
        hits = self._elem_index.intersection(box)
        # Test which one is actually intersect
        real_hits = []
        for hit in hits:
            nodes_hit = np.array(self.elem(hit),dtype = 'i')
            nodes = self._nodes[nodes_hit,0:2]                
            signs = np.sign(np.dot(normal, \
                    np.transpose(np.subtract(nodes, x[0, ]))))
            if not np.all(signs == signs[0]):
                real_hits.append(hit)

        return real_hits

    def find_neighbors_on_segment(self, line_segment):
        """ Find elements on the line_segment and neighbors that are all to the left (downstream)
        Format of the line segment: start_x, start_y, end_x, end_y
        Returns a list of elements on the segment and a list of neighbors. The lists are not guarateed to be ordered spatially
        """
        if self._elem_index is None:
            self._build_elem_index()

        x = np.array(line_segment).reshape(2, 2)
        normal = np.array((x[0, 1] - x[1, 1], x[1, 0] - x[0, 0]))
        box = self._box_from_points(x)
        hits = list(self._elem_index.intersection(box))
        assert len(hits) > 0
        # Test which one is actually intersect
        neighborset = set()
        real_hits = []
        for hit in hits:
            nodes_hit = np.array(self.elem(hit),dtype = 'i')
            
            nodes = self._nodes[nodes_hit,0:2]                
            signs = np.sign(np.dot(normal, \
                                   np.transpose(np.subtract(nodes, x[0, ]))))
            if np.all(signs == signs[0]): 
                # nodes of polygon all on same side of line, no real intersection
                continue
            real_hits.append(hit)
            candidate_edges = self.element2edges(hit)
            for ee in candidate_edges:
                # neighbor elemets accepted if their adjoining edges are all on downstream side of 
                # the segment
                edge_info = self._edges[ee]
                nodes_ee = np.array(edge_info[0:2],dtype = 'i')  
                nodes2 = self._nodes[nodes_ee,0:2]                  
                signs2 = np.sign(np.dot(normal, \
                                   np.transpose(np.subtract(nodes2, x[0, ]))))
                all_left = np.all(signs2 > 0)
                if all_left:
                    els =edge_info[3:5]
                    if not hit in els: 
                        raise Exception("Boundary case not handled")
                    other = els[0] if (els[0] != hit) else els[1]
                    neighborset.add(other)
                    
        return real_hits, list(neighborset)




    def find_elem(self, pos):
        """ Find a element index from a coordinate
            pos = A coordinate (2D)
            return = element index
        """
        if self._elem_index is None:
            self._build_elem_index()

        pos = np.array(pos[:2])
        hits = self._elem_index.intersection(pos[_XXYY])
        # Test which one is actually intersect
        nodes = np.empty((3, 2))
        for hit in hits:
            elem = self.elem(hit)
            n_nodes = len(elem)
            nodes[0] = self._nodes[elem[0]][:2]
            for i in range(n_nodes - 2):
                for j in range(2):
                    nodes[j + 1] = self._nodes[elem[i + j + 1]][:2]

                # Test if this is the element (Barycentric method)
                v0 = nodes[2] - nodes[0]
                v1 = nodes[1] - nodes[0]
                v2 = pos - nodes[0]
                dot00 = np.dot(v0, v0)
                dot01 = np.dot(v0, v1)
                dot02 = np.dot(v0, v2)
                dot11 = np.dot(v1, v1)
                dot12 = np.dot(v1, v2)

                invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
                u = (dot11 * dot02 - dot01 * dot12) * invDenom
                v = (dot00 * dot12 - dot01 * dot02) * invDenom

                # This test returns positive if a dot is on the element border.
                # And it return anything that is tested first.
                if (u >= 0.) and (v >= 0.) and (u + v <= 1.):
                    return hit
        return None

    def _build_boundary_node_string(self, n1, n2, ccw=True):
        """ This function builds a node string of boundary nodes from
            node n1 to n2 in CCW direction.
            CAVEAT: The node order in the mesh file is assumed CCW.
            return = array of node_i
        """
        ns = []
        ns.append(n1)
        done = False
        while not done:
            next_node = self._get_next_node_on_boundary(n1, ccw)
            if next_node is None:
                raise Exception("No next node on the bouandry...")
            else:
                ns.append(next_node)
                if next_node == n2:
                    done = True
                else:
                    n1 = next_node
        return ns

    def _clear_edge_types(self):
        """ Clear edge types
        """
        if self._edges is not None:
            for edge in self._edges:
                if edge[2] > EdgeType.INTERNAL:
                    edge[2] = EdgeType.BOUNDARY

    def _get_next_node_on_boundary(self, node_i, ccw=True):
        """ This function gets a node index next to the given one
            on the boundary.
        """
        edges_i = self.get_edges_from_node(node_i)
        for edge_i in edges_i:
            edge = self._edges[edge_i]
            if ccw:
                if (not edge[2] == EdgeType.INTERNAL) and edge[0] == node_i:
                    return edge[1]
            else:
                if (not edge[2] == EdgeType.INTERNAL) and edge[1] == node_i:
                    return edge[0]
        return None

    def find_closest_elems(self, pos, count=1):
        """ Find indexes of the closet elems with the given position.
            The distance is measured with the element mass center.
            All triangular elems is assumed.

            Parameters
            ----------
            pos: array-like
                2D position

            Returns
            -------
            int or list
                element index or indexes

        """
        if self._elemcenter_index is None:
            tuples = []
            for elem_i in range(self.n_elems()):
                center = np.zeros(2)
                elem = self.elem(elem_i)
                for node_i in elem:
                    np.add(center, self._nodes[node_i][:2], center)
                center /= float(len(elem))
                tuples.append((elem_i, center[_XXYY], None))
            self._elemcenter_index = rtree.Rtree(tuples, interleaved=False)

        pos = np.array(pos)
        # returns the index of the grid point closest to the given point:
        hits = self._elemcenter_index.nearest(pos[_XXYY], count)

        # newer versions of rtree return a generator:
        if isinstance(hits, types.GeneratorType):
            # so translate that into a list like we used to get.
            hits = [next(hits) for _ in range(count)]

        if count > 1:
            return hits
        else:
            return hits[0]

    def trim_elems(self, paths, left=None):
        """
        Given a path, trim all elems to the left of it.
        This function is lifted and modified slightly from Rusty's code.

        Parameters
        ----------
        paths: array of integer array-like
            arrays of cut paths in arrays of node indexes
        """
        # mark the cut edges:
        for path in paths:
            for i in range(len(path) - 1):
                e = self.find_edge(path[i:i + 2])
                if self._edges[e, 2] == EdgeType.INTERNAL:
                    # or self._edges[e, 2] == EdgeType.CUT:
                    # record at least ones that is really cut,
                    # in case some of the cut edges are
                    # actually on the boundary
                    cut_edge = (path[i], path[i + 1], e)
                    self._edges[e, 2] = EdgeType.CUT

        # choose the first element based on the last edge that was touched
        # above
        a = self._nodes[cut_edge[0]]
        b = self._nodes[cut_edge[1]]

        # the edge index
        edge = cut_edge[2]

        # the two elems that form this edge:
        elem1_i, elem2_i = self._edges[edge, 3:]
        other_point1 = np.setdiff1d(self.elem(elem1_i), cut_edge[:2])[0]
        other_point2 = np.setdiff1d(self.elem(elem2_i), cut_edge[:2])[0]

        parallel = (b - a)
        # manually rotate 90deg CCW
        bad = np.array([-parallel[1], parallel[0]])

        left = True if left is None else False

        if np.dot(self._nodes[other_point1, :2], bad) \
                > np.dot(self._nodes[other_point2, :2], bad):
            bad_elem = elem1_i if left is True else elem2_i
        else:
            bad_elem = elem2_i if left is True else elem1_i

        if self._logger is not None:
            self._logger.info("Deleting elems...")
        self._recursive_delete(bad_elem)
        if self._logger is not None:
            self._logger.info("Renumbering nodes and elems...")
        self.renumber()

    def _recursive_delete(self, elem_i_to_delete, renumber=1):
        """
        Delete elements recursively
        This function is modified from Rusty's original function.

        Parameters
        ----------
        elem_i_to_delete: int
            element index
        """

        del_count = 0
        to_delete = [elem_i_to_delete]

        # things the queue have not been processed at all...
        while len(to_delete) > 0:
            # grab somebody:
            elem_i = to_delete.pop()
            conn = self.elem(elem_i)
            if conn is None:
                continue
            n_nodes = len(conn)

            # get their edges
            my_edges = [self.find_edge((conn[i], conn[(i + 1) % n_nodes]))
                        for i in range(n_nodes)]
            # mark it deleted:
            self.mark_elem_deleted(elem_i)
            del_count += 1

            # add their neighbors to the queue to be processed:
            for edge_i in my_edges:
                # only on non-cut, internal edges:
                if self._edges[edge_i, 2] == EdgeType.INTERNAL:
                    c1, c2 = self._edges[edge_i, 3:]
                    if c1 == elem_i:
                        nbr = c2
                    else:
                        nbr = c1

                    if nbr >= 0:
                        to_delete.append(nbr)
        if self._logger is not None:
            self._logger.info("Deleted %i elems." % del_count)

    def renumber(self):
        """
        removes duplicate elems and nodes that are not referenced
        by any element, as well as elems that have been deleted (==-1)
        This function is lifted and modified slightly from Rusty's code.

        Returns
        -------
        dict
            {'valid_elems':new_elems, 'pointmap':old_indexes,
             'valid_nodes':active_nodes}
        """
        element_hash = {}  # sorted tuples of vertices
        new_elems = []  # list of indexes into the old ones
        for i in range(self.n_elems()):
            my_key = tuple(self._elems[i])
            if my_key not in element_hash and self.elem(i) is not None:
                # we're original and not deleted
                element_hash[my_key] = i  # value is ignored...
                new_elems.append(i)

        self._elems = self._elems[new_elems]  # Survived elems

        # remove lonesome nodes
        active_nodes = np.unique(np.ravel(self._elems[:, :MAX_NODES]))[1:]
        if np.any(active_nodes) <= 0:
            raise Exception(
                "renumber: Active nodes includes some negative indexes.")

        old_indexes = -np.ones(self.n_nodes(), np.int32)

        self._nodes = self._nodes[active_nodes]
        if np.any(np.isnan(self._nodes)):
            raise Exception("renumber: some points have NaNs!")

        # need a mapping from active node to its index -
        # explicitly ask for int32 for consistency
        new_indexes = np.arange(active_nodes.shape[0], dtype=np.int32)
        old_indexes[active_nodes] = new_indexes
        # map onto the new indexes
        flag_active_nodes = np.greater_equal(self._elems[:, :MAX_NODES], 0)
        self._elems[flag_active_nodes] = old_indexes[
            self._elems[flag_active_nodes]]

        if np.any(self._elems) < 0:
            raise Exception(
                "renumber: after remapping indexes, have negative node index in elems")

        # clear out stale data
        self._clear_stale_data()

        # rebuild the edges
        self.build_edges_from_elems()

        # return the mappings so that subclasses can catch up
        return {'valid_elems': new_elems, 'pointmap': old_indexes,
                'valid_nodes': active_nodes}

    def _clear(self):
        """ Clear up the data
        """
        self._nodes = None
        self._elems = None
        self._edges = None
        self._clear_stale_data()

    def _clear_stale_data(self):
        """ Clear up the memory
        """
        self._node2elems = None
        self._node_index = None
        self._elem_index = None
        self._node2edges = None

    def is_elem_on_boundary(self, elem_i):
        """ Check if the given element with index elem_i is on the boundary
                elem_i = element index
            return = True if the element is on the boundary, otherwise False
        """
        is_on_boundary = False
        for edge_i in self.element2edges(elem_i):
            if self._edges[edge_i][2] != EdgeType.INTERNAL:
                is_on_boundary = True
        return is_on_boundary

    def element2edges(self, elem_i):
        """
        Get edge indexes of the give element index

        Parameters
        ----------
        elem_i: int
            the element index
        Returns
        -------
        array of int
            edge indexes of the element
        """
        elem = self.elem(elem_i)
        n_nodes = len(elem)
        edges = [self.find_edge((elem[i], elem[(i + 1) % n_nodes]))
                 for i in range(n_nodes)]
        return edges

    def build_edgecenters(self):
        """ Build centers of sides

            Returns
            -------
            numpy.array
                list of side centers
        """
        edges = np.array([edge[:2] for edge in self._edges])
        nodes = self._nodes[edges]
        return nodes.mean(axis=1)
