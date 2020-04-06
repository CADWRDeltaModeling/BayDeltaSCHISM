#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Command line tool to convert SCHISM line strings in YAML
    to Shapefile and vice versa
"""
from schism_linestring import read_linestrings, write_linestrings
import argparse

def create_arg_parser():
    """ Create an argument parser
    """
    parser = argparse.ArgumentParser(description="Convert line string information from one file format to another")
    parser.add_argument('--input',
                        help="input file")
    parser.add_argument('--output',
                        help="output file")
    return parser


def main():
    """ A main function to convert polygon files
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    if args.input.endswith('.yaml'):
        linestrings = read_linestrings(args.input)
        if args.output.endswith('.shp'):
            write_linestrings(args.output, linestrings)
        else:
            raise ValueError("Not supported output file type")
    elif args.input.endswith('.shp'):
        linestrings = read_linestrings(args.input)
        write_linestrings(args.output, linestrings)
    else:
        raise ValueError("Not supported input file type")


if __name__ == '__main__':
    main()
