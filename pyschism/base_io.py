# -*- coding: utf-8 -*-
"""
This module is a simple common base for text file IO.
@outhor: Kijin Nam, knam@water.ca.gov
"""

class BaseIO(object):
    """ Common IO routines to handle text inputs
    """
    def __init__(self, logger=None):
        """ Constructor
        """
        self._logger = logger
        self._lc = 0

    @property
    def linecounter(self):
        return self._lc

    @linecounter.setter
    def linecounter(self, value):
        self._lc = value

    def _read_and_parse_line(self, f, expected_count):
        """ Read in a line from a file handle and return parse tokens.
            A line will be parsed with whitespaces upto the expected count
            and the rest of the line will be not parsed and returned as
            one token.
            f = file handle
            expected_count = minimum expected count of parse tokens
            return = tokens and flag. If the number of tokens is
            more than the expected count, flag is True. Otherwise, False.
        """
        line = f.readline()
        line = line.strip()
        self._lc += 1
        if len(line) == 0:
            return None, False
        tokens = line.split(None, expected_count)
        if expected_count < 0:
            return tokens, True
        elif len(tokens) < expected_count:
            self._logger.error("Less than the expected count of items are read in.")
            return tokens, False
        else:
            return tokens, True
