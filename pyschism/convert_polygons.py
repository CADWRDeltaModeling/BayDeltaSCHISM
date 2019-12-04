#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Command line tool to convert SCHISM polygons in YAML
    to Shapefile and vice versa
"""
from schism_polygon import read_polygons, write_polygons
import argparse

def create_arg_parser():
    """ Create an argument parser
    """
    parser = argparse.ArgumentParser(description="Convert polygon information from one file format to another")
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
        polygons = read_polygons(args.input)
        if args.output.endswith('.shp'):
            write_polygons(args.output, polygons)
        else:
            raise ValueError("Not supported output file type")
    elif args.input.endswith('.shp'):
        polygons = read_polygons(args.input)
        write_polygons(args.output, polygons)
    else:
        raise ValueError("Not supported input file type")


if __name__ == '__main__':
    main()
