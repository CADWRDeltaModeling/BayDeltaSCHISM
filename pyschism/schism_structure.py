## This module contains a structure related data container and I/O
## routines.
##
## Author: Kijin Nam, knam@water.ca.gov
##

from .base_io import *

# Some constants
ELEVATION = 0
FLOW = 0
WIDTH = 1
RADIUS = 1
COEFF = 2
OP_DOWN = 3
OP_UP = 4
HEIGHT = 5

class SchismStructure(object):
    """ A class to hold structure information
    """
    def __init__(self):
        self._name = None
        self._reference = None
        self._ref_pair = (None, None)
        self._pairs = []
        self._type = None             # Just lower case name
        self._n_duplicate = 0
        self._properties = None
        self._timeseries = None
        self._coords = None           # Pair of physical coords

#     def __str__(self):
#         return "%s %s %s" % (self._name, self._type,
#                              " ".join(map(str,self._properties)))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def reference(self):
        return self._reference

    @reference.setter
    def reference(self, value):
        self._reference = value

    @property
    def reference_pair(self):
        return self._ref_pairs

    @reference_pair.setter
    def reference_pair(self, value):
        self._ref_pairs = value

    @property
    def node_pairs(self):
        return self._pairs

    @node_pairs.setter
    def node_pairs(self, value):
        self._pairs = value

    def n_node_pairs(self):
        return len(self._pairs)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def n_duplicate(self):
        return self._n_duplicate

    @n_duplicate.setter
    def n_duplicate(self, value):
        self._n_duplicate = value

    @property
    def properties(self):
        return self._properties

    @properties.setter
    def properties(self, value):
        self._properties = value

    @property
    def use_timeseries(self):
        return self._timeseries

    @use_timeseries.setter
    def use_timeseries(self, value):
        self._timeseries = value

    @property
    def coords(self):
        return self._coords

    @coords.setter
    def coords(self, value):
        self._coords = value


class SchismStructureIO(BaseIO):
    """ A class to manage hydraulic structure I/O files
    """
    def __init__(self, input):
        """
            input = a SCHISM input instance
        """
        super(SchismStructureIO, self).__init__()
        self._input = input

    def read(self, fname):
        """ Read in 'hydraulics.in' file.
        """
        print("Reading in" + fname + "...")
        f = open(fname, 'r')
        # # of blocks
        tokens, ok = self._read_and_parse_line(f, 1)
        n_structures = int(tokens[0])
        # Nudging
        tokens, ok = self._read_and_parse_line(f, 1)
        nudging = float(tokens[0])
        # Loof for structure
        for struct_i in range(n_structures):
            struct = SchismStructure()
            # index and name
            tokens, ok = self._read_and_parse_line(f, 2)
            i_struct = int(tokens[0])
            struct_name = tokens[1]
            struct.name = struct_name
            # # of pairs and reference pairs
            tokens, ok = self._read_and_parse_line(f, 3)
            n_pairs = int(tokens[0])
            ref_pair = (int(tokens[1]) - 1 , int(tokens[2]) - 1)
            struct.reference_pair = ref_pair
            pairs = []
            # Pairs
            for pair_i in range(n_pairs):
                tokens, ok = self._read_and_parse_line(f, 2)
                pairs.append((int(tokens[0]) - 1, int(tokens[1]) - 1))
            struct.node_pairs = pairs
            # Structure type
            tokens, ok = self._read_and_parse_line(f, 1)
            struct_type = tokens[0]
            struct.type = struct_type.lower()
            # n_duplicates
            tokens, ok = self._read_and_parse_line(f, 1)
            n_duplicate = int(tokens[0])
            struct.n_duplicate = n_duplicate
            # parameters
            if struct_type == "weir" or struct_type == "culvert":
                tokens, ok = self._read_and_parse_line(f, 2)
                elevation = float(tokens[0])
                width = float(tokens[1])
                tokens, ok = self._read_and_parse_line(f, 3)
                coeff = float(tokens[0])
                op_down = float(tokens[1])
                op_up = float(tokens[2])
                struct.properties = [elevation, width, coeff, op_down, op_up]
            elif struct_type == "radial" or struct_type == "orifice":
                tokens, ok = self._read_and_parse_line(f, 3)
                elevation = float(tokens[0])
                width = float(tokens[1])
                height = float(tokens[2])
                tokens, ok = self._read_and_parse_line(f, 3)
                coeff = float(tokens[0])
                op_down = float(tokens[1])
                op_up = float(tokens[2])
                struct.properties = [elevation, width, height,
                                     coeff, op_down, op_up]
            elif struct_type == "transfer":
                tokens, ok = self._read_and_parse_line(f, 1)
                flow = float(tokens[0])
                struct.properties = [flow]
            else:
                raise Exception("Not supported structure type")

            # Time series
            tokens, ok = self._read_and_parse_line(f, 1)
            timeseries = int(tokens[0])
            struct.use_timeseries = timeseries
            # Add the structure
            self._input.add_structure(struct)

        f.close()
        print("Done reading a structure file.")

    def write(self, fname='hydraulics.in'):
        """ Write out 'hydraulics.in' file.
        """
        f = open(fname, 'w')
        buf = "%d !# of structures\n" % self._input.n_structures()
        f.write(buf)
        buf = "%f  !Nudging factor\n" % self._input.nudging
        f.write(buf)
        i = 0
        for struct in self._input.structures:
            i += 1
            # index and name
            buf = "%d %s\n" % (i, struct.name)
            f.write(buf)
            # # of node pairs and reference nodes
            buf = "%d %d %d !  # of node-pairs, 2 ref." \
                  "nodes (global indices) for 2 faces\n" \
                  % (struct.n_node_pairs(),
                     struct.reference_pair[0] + 1,
                     struct.reference_pair[1] + 1)
            f.write(buf)
            # node pairs
            for pair in struct.node_pairs:
                buf = "%d %d\n" % (pair[0] + 1, pair[1] + 1)
                f.write(buf)
            # type
            buf = "%s ! struct type\n" % struct.type
            f.write(buf)
            # nduplicate
            k = 'n_duplicates'
            n_duplicates = struct.properties[k] if k in struct.properties else 0.
            buf = "%d ! n_duplicates\n" % n_duplicates
            f.write(buf)
            # parameters
            if struct.type == "weir" or struct.type == "culvert":
                val = struct.properties['width'] if struct.type == "weir" else struct.properties['radius']
                buf = "%f %f ! elevation, width or radius\n" % \
                      (struct.properties['elevation'],
                       val)
                f.write(buf)
                buf = "%f %f %f ! coef, op_downstream, op_upstream\n" % \
                      (struct.properties['coefficient'],
                       struct.properties['op_downstream'],
                       struct.properties['op_upstream'])
                f.write(buf)
            elif struct.type == "radial" or struct.type == "orifice":
                buf = "%f %f %f ! elevation, width, height or radius\n" % \
                      (struct.properties['elevation'],
                       struct.properties['width'],
                       struct.properties['height'])
                f.write(buf)
                buf = "%f %f %f ! coef, op_downstream, op_upstream\n" % \
                      (struct.properties['coefficient'],
                       struct.properties['op_downstream'],
                       struct.properties['op_upstream'])
                f.write(buf)
            elif struct.type == "radial_relheight":
                buf = "%f %f %f ! elevation, width, height\n" % \
                      (struct.properties['elevation'],
                       struct.properties['width'],
                       struct.properties['height'])
                f.write(buf)
                buf = "%f %f ! coef, coef_height\n" % \
                      (struct.properties['coefficient'],
                       struct.properties['coefficient_height'])
                f.write(buf)
                buf = "%f %f ! op_downstream, op_upstream\n" % \
                      (struct.properties['op_downstream'],
                       struct.properties['op_upstream'])
                f.write(buf)
            elif struct.type == "weir_culvert":
                buf = "%f %f ! elevation and width for weir\n" % \
                       (struct.properties['elevation'],
                        struct.properties['width'])
                f.write(buf)
                buf = "%f %f %f ! coef, op_downstream, op_upstream for weirs\n" % \
                      (struct.properties['coefficient'],
                       struct.properties['op_downstream'],
                       struct.properties['op_upstream'])
                f.write(buf)
                buf = "%d ! n_duplicates for culverts\n" % (
                    struct.properties['culvert_n_duplicates'])
                f.write(buf)
                buf = "%f %f\n" % (struct.properties['culvert_elevation'],
                                   struct.properties['culvert_radius'])
                f.write(buf)
                buf = "%f %f %f ! coef, op_downstream, op_upstream for culverts\n" % \
                      (struct.properties['culvert_coefficient'],
                       struct.properties['culvert_op_downstream'],
                       struct.properties['culvert_op_upstream'])
                f.write(buf)
            elif struct.type == "transfer":
                buf = "%f ! flow\n" % struct.properties['flow']
                f.write(buf)
            else:
                raise Exception("Not supported structure type")

            buf = "%d ! time series enabled\n" % struct.properties['use_time_series']
            f.write(buf)

        f.flush()
        f.close()

    def _read_line_and_split(self, f, lc, expected_count=0):
        """
           returns: (tokens, lc), tokens are parsed items and lc is
           the line counter after reading a line.
        """
        tokens = f.readline().split()
        lc += 1
        if expected_count > 0 and len(tokens) < expected_count:
            print("Line #: {}".format(lc))
            raise Exception("Line is corrupted.")
        return tokens, lc

