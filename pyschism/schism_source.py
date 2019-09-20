## Module to process source/sink information
##
## Author: Kijin Nam, knam@water.ca.gov
##

## Some constants
SOURCE = 0
SINK = 1

class SchismSource(object):
    """ A class to hold structure information
    """  
    def __init__(self):
        self._element_id = None
        self._type = None
        self._coord = None
        self._note = None

    @property
    def element_id(self):
        return self._element_id

    @element_id.setter
    def element_id(self, value):
        self._element_id = value

    @property
    def coord(self):
        return self._coord

    @coord.setter
    def coord(self, value):
        self._coord = value

    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, value):
        self._note = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value


class SchismSourceIO(object):
    """ A class to manage source/sink I/O
    """
    def __init__(self, input):
        self._input = input

    def read(self, fname):
        f = open(fname, 'r')
        linecount = 0
        (tokens, linecount, note) = self._read_line_and_split(f, linecount, 1)
        n_sources = int(tokens[0])
        for i in range(n_sources):
            (tokens, linecount, note) = self._read_line_and_split(f, linecount, 1)
            source = SchismSource()
            source.type = SOURCE
            source.element_id = int(tokens[0]) - 1
            self._input.sources.append(source)

        (tokens, linecount, note) = self._read_line_and_split(f, linecount, 1)
        n_sinks = int(tokens[0])
        f.readline()                    # Blank line
        for i in range(n_sinks):
            (tokens, linecount, note) = self._read_line_and_split(f, linecount, 1)
            source = SchismSource()
            source.type = SINK
            source.element_id = int(tokens[0]) - 1
            self._input.sources.append(source)
            
        f.close()

    def write(self, fname = 'source_sink.in'):
        f = open(fname, 'w')
        buf = "%d ! total # of elements with sources\n" % self._input.n_sources()
        f.write(buf)
        for source in self._input.sources:
            if source.type == SOURCE:
                buf = "%d\n" % (source.element_id + 1)
                f.write(buf)
        f.write('\n')                   # Blank line
        buf = "%d ! total # of elements with sinks\n" % self._input.n_sinks()
        f.write(buf)
        for source in self._input.sources:
            if source.type == SINK:
                buf = "%d\n" % (source.element_id + 1)
                f.write(buf)
                    
        f.flush()
        f.close()

    def _read_line_and_split(self, f, lc, expected_count = 0):
        """
           returns: (tokens, lc), tokens are parsed items and lc is
           the line counter after reading a line.
        """
        splits = f.readline().split()
        comment = False
        tokens = []
        note = ""
        for item in splits:
            if comment:
                note += " " + item
            else:
                if item[0] is '!':
                    comment = True
                else:
                    tokens.append(item)
                
        lc += 1
        if expected_count > 0 and len(tokens) < expected_count:
            print("Line #: {}".format(lc))
            raise Exception("Line is corrupted.")
        return tokens, lc, note
