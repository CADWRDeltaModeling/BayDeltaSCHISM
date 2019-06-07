#!/usr/bin/env python2
import os
__author__ = "Kijin Nam <knam@water.ca.gov"


def create_arg_parse():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file_base", help="VisIt file for a base case. The values in this file(s) will be subtracted from the alternative case.")
    parser.add_argument(
        "file_alternative", help="VisIt file for an alternative case. From the values in this file(s), the values in a base case will be subtracted")
    parser.add_argument("--convert_to_ec", default=False,
                        help="Convert PSU into EC before taking a difference.")
    parser.add_argument("--output_prefix", default='diff_salt',
                        help="A prefix for a final output file.")
    parser.add_argument("--visit_dir", default=None,
                        help="The VisIt installation directory. If this option is provided, it will be included in PYTHONPATH by the script. This works only for Linux 64bit now.")
    return parser


def main():
    """ Main function to process files on the command line with arguments.
        There is no safety check at the moment.
    """
    parser = create_arg_parse()
    args = parser.parse_args()
    if args.visit_dir is not None:
        import sys
        sys.path.insert(0, os.path.join(os.path.normpath(args.visit_dir),
                                        'current/linux-x86_64/lib/site-packages'))

    from tidal_averaged_salinity_w_visit import calculate_difference_of_tidal_average_salinity

    calculate_difference_of_tidal_average_salinity(
        args.file_base, args.file_alternative, args.output_prefix,
        convert_to_ec=args.convert_to_ec)


if __name__ == "__main__":
    main()
