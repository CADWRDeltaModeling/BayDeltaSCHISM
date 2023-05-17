#!/usr/bin/env python
""" Process and generate flux, gate th files. """
from pathlib import Path
import click
import schimpy.model_time


@click.command()
@click.option('--dir_th', required=True, type=str,
              help="directory with timestamped th files")
@click.option('--list_of_th', required=True, type=str,
              help="file containing list of th files.")
@click.option('--start', required=True, type=str,
              help="start time of the run in string, e.g. '2009-11-18'")
def main(dir_th, list_of_th, start):
    """
    Process time-stamped th files and generate SCHISM th files

    Read time-stamped th files and generate SCHISM th files for the run.
    """
    path_baydelta = Path(dir_th)
    path_th_list = Path(list_of_th)
    files = []
    with open(path_th_list, "r") as f:
        for ln in f.readlines():
            ln = ln.strip()
            if len(ln) < 1 or ln[0] == '#':
                continue
            files.append(ln.split()[:2])

    input = [str(path_baydelta / i[0]) for i in files]
    output = [i[1] for i in files]
    schimpy.model_time.multi_file_to_elapsed(input, output, start)


if __name__ == "__main__":
    main()

