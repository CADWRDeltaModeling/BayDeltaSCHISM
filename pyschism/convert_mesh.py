#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Mesh converter
"""
from schism_mesh import read_mesh, write_mesh
import argparse


def create_arg_parser():
    parser = argparse.ArgumentParser(
        description="Convert a mesh from one format to another. The format is decided by the extensions automatically.")
    parser.add_argument('--input', help="Input mesh file")
    parser.add_argument('--output', help="Output mesh file")
    parser.add_argument('--proj4', help="Proj4 string for the projection")
    return parser


def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    convert_mesh(args)


def convert_mesh(args):
    mesh = read_mesh(args.input)
    write_mesh(mesh, args.output, proj4=args.proj4)


if __name__ == '__main__':
    main()
