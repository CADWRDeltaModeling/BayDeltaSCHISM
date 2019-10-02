"""
This is a class to hold an unstructured triangular mesh.

Lots of the codes are copied from Rusty Chris Collerman's trigrid program
and modified a bit to meet our needs.

Prerequisite: Numpy, rtree package, and libspatialindex for rtree
"""
##
## Author: Kijin Nam, knam@water.ca.gov
##

import priority_queue as pq
import rtree
import numpy as np
import types
import copy

def enum(**enums):
    """ A enum type definition.
        Copied from http://stackoverflow.com/questions/36932/how-can-i-represent-an-enum-in-python
    """
    return type('Enum', (), enums)


# Edge trait (or marker)
INTERNAL_EDGE = 0
BOUNDARY_EDGE = 1
OPEN_EDGE = 2
LAND_EDGE = 3
ISLAND_EDGE = 4
CUT_EDGE = 99

EdgeTypes = enum(INTERNAL_EDGE = 0,
    BOUNDARY_EDGE = 1,
    OPEN_EDGE = 2,
    LAND_EDGE = 3,
    ISLAND_EDGE = 4,
    CUT_EDGE = 99
    )

# Boundary type
INVALID_BOUNDARY = -1
OPEN_BOUNDARY = 1
LAND_BOUNDARY = 2
ISLAND_BOUNDARY = 3

BoundaryTypes = enum(INVALID_BOUNDARY = -1,
    OPEN_BOUNDARY = 1,
    LAND_BOUNDARY = 2,
    ISLAND_BOUNDARY = 3
    )

BOUNDARY = -1

_XXYY = [0, 0, 1, 1]


class TriMesh(object):
    """ Class that holds a triangular mesh information
    """

    def __init__(self):
        """ Constructor of TriMesh
        """
        self._elems = None
        self._nodes = None
        self._edges = None
        self._node2elems = None
        self._node2edges = None
        self._node_index = None  # Rtree index for nodes
        self._elem_index = None  # Rtree index for elements
        self._elemcenter_index = None # Rtree index for element centers

    def deepcopy(self, mesh):
        """ Deep copy mesh information.
        """
        self._elems = np.copy(mesh.elems)
        self._nodes = np.copy(mesh.nodes)
        self._edges = copy.deepcopy(mesh.edges)

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
        """ Array of node indices of each element.
            The shape of the array is (# of elems, 3).
            It is assumed that all elems are triangular.

            :getter: Get the Numpy array of the node indices.
            :type: Numpy integer array
        """
        return self._elems

    @property
    def edges(self):
        """ Array of edges

            :getter: Get the array of the edges.
            :type: Numpy integer array
        """
        return self._edges

    def allocate(self, n_elems, n_nodes):
        """ Allocate memory for nodes and elems

            Parameters
            ----------
            n_elems: integer
                Total number of elems
            n_nodes: integer
                Total number of nodes
        """
        self._nodes = np.zeros((n_nodes, 3), dtype=np.float)
        # Elements up to 2,147,483,647
        self._elems = np.zeros((n_elems, 3), dtype=np.int32)

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
        self._nodes[index,:len(coords)] = coords

    def set_elem(self, index, connectivities):
        """ Set element connectivity information.
            Memory for elems must be allocated already.

            Parameters
            ----------
            index: integer
                Zero-based element index
            connectivities: Numpy array
                a Numpy array of element connectivity, which means node
                indies in the element.
        """
        if not index < self._elems.shape[0]:
            raise ValueError("Accessing out of bound in node array")
        self._elems[index,] = connectivities

    def n_nodes(self):
        """ Get the total number of nodes.
        """
        return self._nodes.shape[0]

    def n_elems(self):
        """ Get the total nuber of elems.
        """
        return self._elems.shape[0]

    def n_edges(self):
        """ Get the total number of edges.
        """
        if self._edges is None:
            self.build_edges_from_elems()
        return self._edges.shape[0]

    def build_edges_from_elems(self):
        """ This is a function copied and modified from TriGrid
        """
        print("Building edges from elements")
        # iterate over elements, and for each element, if it's index
        # is smaller than a neighbor or if no neighbor exists,
        # write an edge record
        edges = []

        # this will get built on demand later.
        self._node2edges = None

        for elem_i, elem in enumerate(self._elems):
            # find the neighbors:
            # the first neighbor: need another element that has
            # both self._elems[i,0] and self._elems[i,1] in its
            # list.
            my_set = set([elem_i])
            for j in range(3):
                node_a = elem[j]
                node_b = elem[(j + 1) % 3]

                elem_ball_node_a = self.get_elems_i_from_node(node_a)
                elem_ball_node_b = self.get_elems_i_from_node(node_b)

                # the intersection is us and our neighbor
                # so difference out ourselves...
                adj_elem_of_edge = elem_ball_node_a.intersection(elem_ball_node_b).difference(my_set)
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
                                  BOUNDARY_EDGE if adj_elem_i == -1 else INTERNAL_EDGE,
                                  elem_i, adj_elem_i))

        self._edges = np.array(edges, dtype=np.int32)

    def _build_node_index(self):
        if self._node_index is None:
            print("Building node indices...")
            # assemble points into list of (id, [x x y y], None)
            # but new rtree allows for interleaved coordinates all the time.
            # best solution probably to specify interleaved=False
            tuples = [(i, self._nodes[i, _XXYY], None) \
                      for i in range(self.n_nodes()) \
                      if np.isfinite(self._nodes[i, 0])]

            self._node_index = rtree.Rtree(tuples, interleaved=False)

    def _build_elem_index(self):
        # Build Rtree index for elems
        if self._elem_index is None:
            print("Building element indices...")
            elem_i = 0
            tuples = []
            for element in self._elems:
                # TODO: This could be better with numpy.
                box = [None, None, None, None]  # [xmin xmax ymin ymax]
                for node_i in element:
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
                elem_i += 1

            self._elem_index = rtree.Rtree(tuples, interleaved=False)

    def get_elems_i_from_node(self, node_i):
        """ Get neighboring elements indexes of a node, so-called a ball.
        """
        if self._node2elems is None:
            print("Mapping elements to nodes...")
            # build array for point->element lookup
            # Use set for later convenience
            self._node2elems = [set() for i in range(self.n_nodes())]
            for elem_i, elem in enumerate(self._elems):
                for node_index in elem:
                    self._node2elems[node_index].add(elem_i)
        return self._node2elems[int(node_i)]

    def _find_edge(self, nodes, direction=False):
        """ Find an edge index with the two given node indices.

            Parameters
            ----------
            nodes:
                two node indices
            direction:
                match the ordering of the nodes when an edge is found.

            Returns
            -------
            int
                an edge index
        """
        el0 = self.get_edges_from_node(nodes[0])
        if direction is True:
            for e in el0:
                if self._edges[e][1] == nodes[1]:
                    return e
            return None
        else:
            el1 = self.get_edges_from_node(nodes[1])
            for e in el0:
                if e in el1:
                    return e
            return None

    def find_nodes_in_box(self, box):
        """ Find nodse in a bounding box
            box = a numpy array of bounding box, [x_min, x_max, y_min, y_max]
            return = node indices
        """
        if self._node_index is None:
            self._build_node_index()

        nodes = self._node_index.intersection(box)
        return nodes

    def _build_node2edges(self):
        print("Mapping nodes to edges...")
        # Build node2edges map
        n2e = [[] for i in range(self.n_nodes())]
        for edge_i in range(self.n_edges()):
            for n in self._edges[edge_i, :2]:
                n2e[int(n)].append(edge_i)
        self._node2edges = n2e

        n2e = [[] for i in range(self.n_nodes())]
        for edge_i in range(self.n_edges()):
            for n in self._edges[edge_i, :2]:
                n2e[int(n)].append(edge_i)
        self._node2edges = n2e


    def get_edges_from_node(self, node_i):
        """ Get edge indices related to node_i
        """
        if self._node2edges is None:
            self._build_node2edges()
        if node_i < len(self._node2edges):
            return self._node2edges[node_i]
        else:
            return []

    def get_neighbor_nodes(self, node_i):
        """ Get neighboring node indices from the given node index.
        """
        if self._node2edges is None:
            self._build_node2edges()
        nodes = []
        edges = self._node2edges[node_i]
        for edge_i in edges:
            edge = self._edges[edge_i]
            if edge[0] == node_i:
                nodes.append(edge[1])
            else:
                nodes.append(edge[0])
        return nodes

    def add_boundary(self, nodes, btype):
        """ Add boundary types to an edge with the given array of node indices
        """
        node_prev_i = nodes[0]
        for node_i in nodes[1:]:
            edge_i = self._find_edge([node_prev_i, node_i])
            if edge_i is None:
                raise Exception('No edge found with the given nodes')
            if not -1 in self._edges[edge_i, 3:5]:
                raise Exception('Trying to tag a non-boundary edge' \
                                'as boundary')
            if btype == OPEN_BOUNDARY:
                self._edges[edge_i, 2] = OPEN_EDGE
            elif btype == LAND_BOUNDARY or btype == ISLAND_BOUNDARY:
                self._edges[edge_i, 2] = LAND_EDGE
            else:
                raise Exception("Unsupported boundary type")
            node_prev_i = node_i

    def find_closest_nodes(self, pos, count=1, boundary=False):
        """ Returns the count closest nodes to the given node in 2D space.
            pos = position
            count = # of nodes to retrieve
            boundary=1: only choose nodes on the boundary.
            Copied from TriGrid
        """
        if boundary:
            # print "Searching for nearby boundary point"
            # Rusty's Note:
            # This is slow,
            # but I'm too lazy to add any sort of index specific to
            # boundary nodes.
            # Note that this will include interprocessor boundary
            # nodes, too.
            boundary_nodes = np.unique(self._edges[ \
                self._edges[:, 2] > 0, :2])
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
                hits = [next(hits) for i in range(count)]

            if count > 1:
                return hits
            else:
                return hits[0]

    def shortest_path(self, n1, n2, boundary_only=False):
        """ dijkstra on the edge graph from n1 to n2.
            copied and modified form Rusty's code.
            n1 = node_i for one end of the path
            n2 = node_i for the other end
            boundary_only = limit search to edges on the boundary (have
            a -1 for element2)
        """
        queue = pq.priorityDictionary()
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
            elems_i = list(self.get_elems_i_from_node(best))
            all_nodes_i = np.unique(self._elems[elems_i])

            for node_i in all_nodes_i:
                if node_i in done:
                    # both for p and for points that we've already done
                    continue

                if boundary_only:
                    e = self._find_edge((best, node_i))
                    if self._edges[e, 4] != BOUNDARY:
                        continue


                dist = np.sqrt( ((self._nodes[node_i] \
                                  - self._nodes[best])**2).sum() )
                new_cost = best_cost + dist

                if node_i not in queue:
                    queue[node_i] = np.inf

                if queue[node_i] > new_cost:
                    queue[node_i] = new_cost

        # reconstruct the path:
        path = [n2]

        while 1:
            node_i = path[-1]
            if node_i == n1:
                break

            # figure out its neighbors
            elems = list(self.get_elems_i_from_node(node_i))
            all_nodes_i = np.unique(self._elems[elems])

            found_prev = 0
            for nbr in all_nodes_i:
                if nbr == node_i or nbr not in done:
                    continue

                dist = np.sqrt( ((self._nodes[node_i] \
                                  - self._nodes[nbr])**2).sum() )

                if done[node_i] == done[nbr] + dist:
                    path.append(nbr)
                    found_prev = 1
                    break
            if not found_prev:
                return None

        return np.array( path[::-1] )

    def _box_from_points(self, points):
        """ Format of the line segment: start_x, start_y, end_x, end_y
        """
        box = np.array(points)
        for p in points:
            for i in range(2):
                if box[0, i] > p[i]:
                    box[0, i] = p[i]
                if box[1, i] < p[i]:
                    box[1, i] = p[i]
        return np.transpose(box).reshape(4,)

    def _find_intersecting_elems_with_line(self, line_segment):
        """ Format of the line segment: start_x, start_y, end_x, end_y
        """
        if self._elem_index is None:
            self._build_elem_index()

        x = np.array(line_segment).reshape(2, 2)
        normal = np.array((x[0, 1] - x[1, 1], x[1, 0] - x[0, 0]))
        box = self._box_from_points(x)
        hits = self._elem_index.intersection(box)
        # Test which one is actually intersect
        nodes = np.zeros((3, 2))
        real_hits = []
        for hit in hits:
            for i in range(3):
                nodes[i, ] = self._nodes[self._elems[hit][i]][:2]
            signs = np.sign(np.dot(normal, \
                                   np.transpose(np.subtract(nodes, x[0, ]))))
            if signs[0] != signs[1] or signs[0] != signs[2]:
                real_hits.append(hit)

        return real_hits

    def find_elem(self, pos):
        """ Find a element index from a coordinate
            pos = A coordinate (2D)
            return = element index
        """
        if self._elem_index is None:
            self._build_elem_index()

        pos = np.array(pos)
        hits = self._elem_index.intersection(pos[_XXYY])
        # Test which one is actually intersect
        nodes = np.zeros((3, 2))
        for hit in hits:
            for i in range(3):
                nodes[i, ] = self._nodes[self._elems[hit][i]][:2]
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
                return  hit

        return None

    def find_elem_with_tolerance(self, pos, tolerance):
        """ Find a element index from a coordinate with some tolerance
            pos = A coordinate (2D)
            return = element index
        """
        if self._elem_index is None:
            self._build_elem_index()

        pos = np.array(pos)
        hits = self._elem_index.intersection(pos[_XXYY])
        # Test which one is actually intersect
        nodes = np.zeros((3, 2))
        for hit in hits:
            for i in range(3):
                nodes[i, ] = self._nodes[self._elems[hit][i]][:2]
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
            if (u >= -tolerance) and (v >= -tolerance) and \
               (u + v <= (1. + tolerance)):
                return  hit

        return None

    def _build_boundary_node_string(self, n1, n2, ccw = True):
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
        for edge in self._edges:
            if edge[2] > INTERNAL_EDGE:
                edge[2] = BOUNDARY_EDGE

    def _get_next_node_on_boundary(self, node_i, ccw = True):
        """ This function gets a node index next to the given one
            on the boundary.
        """
        edges_i = self.get_edges_from_node(node_i)
        for edge_i in edges_i:
            edge = self._edges[edge_i]
            if ccw:
                if (not edge[2] == INTERNAL_EDGE) and edge[0] == node_i:
                    return edge[1]
            else:
                if (not edge[2] == INTERNAL_EDGE) and edge[1] == node_i:
                    return edge[0]
        return None

    def find_closest_elems(self, pos, count = 1):
        """ Find indices of the closet elems with the given position.
            The distance is measured with the element mass center.
            All triangular elems is assumed.
            pos = position tuple
            return = element indices
        """
        if self._elemcenter_index is None:
            tuples = []
            for i, element in enumerate(self._elems):
                center = np.zeros(2)
                for node_i in element:
                    np.add(center, self._nodes[node_i][:2], center)
                center /= 3.
                tuples.append((i, center[_XXYY], None))
            self._elemcenter_index = rtree.Rtree(tuples, interleaved=False)


        pos = np.array(pos)

        # returns the index of the grid point closest to the given point:
        hits = self._elemcenter_index.nearest(pos[_XXYY], count)

        # newer versions of rtree return a generator:
        if isinstance(hits, types.GeneratorType):
            # so translate that into a list like we used to get.
            hits = [next(hits) for i in range(count)]

        if count > 1:
            return hits
        else:
            return hits[0]


    def trim_to_left(self, paths):
        """ Given a path, trim all elems to the left of it.
            This fuction is lifted and modified slightly from Rusty's code.
        """
        # mark the cut edges:
        for path in paths:
            for i in range(len(path)-1):
                e = self._find_edge(path[i:i+2])

                if self._edges[e,2] == INTERNAL_EDGE \
                       or self._edges[e,2] == CUT_EDGE:
                    # record at least ones that is really cut,
                    # in case some of the cut edges are
                    # actually on the boundary
                    cut_edge = (path[i],path[i+1],e)
                    self.edges[e,2] = CUT_EDGE

        # choose the first element, based on the last edge that was touched above:

        # the actual points:
        a = self._nodes[cut_edge[0]]
        b = self._nodes[cut_edge[1]]

        # the edge index
        edge = cut_edge[2]

        # the two elems that form this edge:
        element1, element2 = self._edges[edge, 3:]
        other_point1 = np.setdiff1d( self._elems[element1], cut_edge[:2] )[0]
        other_point2 = np.setdiff1d( self._elems[element2], cut_edge[:2] )[0]

        parallel = (b - a)
        # manually rotate 90deg CCW
        bad = np.array([ -parallel[1], parallel[0]] )


        if np.dot(self._nodes[other_point1, :2], bad) \
               > np.dot(self._nodes[other_point2, :2], bad):
            bad_elem = element1
        else:
            bad_elem = element2

        print("Deleting elems...")
        self._recursive_delete(bad_elem)
        print("Renumbering nodes and elems...")
        self._renumber()

    def _recursive_delete(self,c,renumber = 1):
        """ This fuction is lifted and modified slightly from Rusty's code.
        """

        del_count = 0
        to_delete = [c]

        # things the queue have not been processed at all...
        while len(to_delete) > 0:
            # grab somebody:
            c = to_delete.pop()
            if self._elems[c,0] == -1:
                continue

            # get their edges
            nodea, nodeb, nodec = self.elems[c]

            my_edges = [self._find_edge( (nodea, nodeb) ),
                        self._find_edge( (nodeb, nodec) ),
                        self._find_edge( (nodec, nodea) ) ]

            # mark it deleted:
            self.elems[c, 0] = -1  # If the first node index is -1, deleted.
            del_count += 1

            # add their neighbors to the queue to be processed:
            for e in my_edges:
                if self._edges[e,2] == 0:# only on non-cut, internal edges:
                    c1, c2 = self._edges[e,3:]
                    if c1 == c:
                        nbr = c2
                    else:
                        nbr = c1

                    if nbr >= 0:
                        to_delete.append(nbr)
        print("Deleted %i elems." % del_count)


    def _renumber(self):
        """ removes duplicate elems and nodes that are not
            referenced by any element,
            as well as elems that have been deleted (==-1)
            This fuction is lifted and modified slightly from Rusty's code.
        """
        element_hash = {} # sorted tuples of vertices
        new_elems = [] # list of indexes into the old ones
        for i in range(self.n_elems()):
            my_key = tuple( np.sort(self._elems[i]) )

            if my_key not in element_hash and self.elems[i,0] >= 0:
                # we're original and not deleted
                element_hash[my_key] = i # value is ignored...
                new_elems.append(i)

        self._elems = self._elems[new_elems] # Survived elems

        # remove lonesome nodes
        active_nodes = np.unique(np.ravel(self._elems))
        if np.any(active_nodes) <= 0:
            raise Exception("renumber: Active nodes includes some negative indices")

        old_indices = -np.ones(self.n_nodes(), np.int32)

        self._nodes = self._nodes[active_nodes]
        if np.any(np.isnan(self._nodes)):
            raise Exception("renumber: some points have NaNs!")

        # need a mapping from active node to its index -
        # explicitly ask for int32 for consistency
        new_indices = np.arange(active_nodes.shape[0],dtype=np.int32)
        old_indices[active_nodes] = new_indices
        # map onto the new indices
        self._elems = old_indices[self._elems]

        if np.any(self._elems) < 0:
            raise Exception("renumber: after remapping indices, have negative node index in elems")

        # clear out stale data
        self._clear_stale_data()

        # rebuild the edges
        self.build_edges_from_elems()

        # return the mappings so that subclasses can catch up
        return {'valid_elems':new_elems, 'pointmap':old_indices,
                'valid_nodes':active_nodes}

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
            if self._edges[edge_i][2] != INTERNAL_EDGE:
                is_on_boundary = True
        return is_on_boundary

    def element2edges(self, elem_i):
        """ Get edge indices from the give element index
            elem_i = the element index
            return = generator of found edge indices
        """
        nodes = self._elems[elem_i]
        edges = [self._find_edge((nodes[i], nodes[(i + 1) % 3]))
                 for i in range(3)]
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
