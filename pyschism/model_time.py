#!/usr/bin/env python
""" Script to make model date conversion convenient, converting elapsed model seconds to/from dates"""
import argparse
import datetime
import re
import textwrap
import sys
import os.path


def create_arg_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog="model_time.py",
        description=textwrap.dedent(
            """
      Interpret model times in elapsed seconds and translate 
      between calendar time and elapsed. The script requires
      a subcommand like: $ model_time.py to_elapsed. You can also 
      get subject-specific help on a subcommand by typing
      $ model_time.py subcommand --help
      """))

    subparsers = parser.add_subparsers(
        title='subcommands', help='sub-commands indicating the particular action required. ', dest='subcommand')

    parser_elapsed = subparsers.add_parser(
        'to_elapsed', help='Convert input datetime string or *.th file with datetime column to equivalent output in elapsed seconds.')
    parser_elapsed.add_argument('dated_input', default=None, nargs='+',
                                help='One or more dates to be converted in ISO-like format 2009-03-12T00:00:00 (time can be ommitted) or the name of a *.th file with the time column in this format.')

    parser_elapsed.add_argument('--start', required=False, type=str,
                                help='Starting date and time basis for output if the input is a file. Allows a larger database with readable times to be clipped')
    parser_elapsed.add_argument(
        '--annotate', default=False, action='store_true')
    parser_elapsed.set_defaults(func=to_elapsed)
    parser_elapsed.add_argument('--step', default=None, nargs='?', type=float,
                                help='Model time step. If given, answer will be the integer time step.')
    parser_elapsed.add_argument('--out', default=None, type=str,
                                help='Name of output file. If input is a *.th file the file will be converted and output to this file, otherwise printed to screen')
    parser_elapsed.add_argument('--skip_nan', default=False, type=bool,
                                help='Skip a record with nan if True')

    parser_date = subparsers.add_parser(
        'to_date', help='Convert input elapsed seconds or *.th file with elapsed seconds as the time column to equivalent output with a datetime or annotated with datetimes.')
    parser_date.add_argument('--start', required=True, type=str,
                             help='Start time in ISO-like format 2009-03-12T00:00:00. Time part is optional.')
    parser_date.add_argument('--step', default=None, nargs='?', type=float,
                             help='Model time step in seconds. If given, answer will be the integer time step.')
    parser_date.add_argument('elapsed_input', default=None, nargs='+',
                             help='One or more numbers representing elapsed seconds since the start argument or the name of a *.th file with the time column in elapsed seconds.')
    default_date = "Time format for output, e.g. the default is %%Y-%%m-%%dT%%H:%%M:%%S for 2009-03-14T22:40:00. Only used when converting fields."
    parser_date.add_argument('--elapsed_unit', default='s',
                             help="Time unit of input file. Must be either 's' for seconds or 'd' for days. Only used for files")
    parser_date.add_argument(
        '--time_format', default="%Y-%m-%dT%H:%M", help=default_date)
    parser_date.add_argument('--annotate', default=False, action='store_true')
    parser_date.add_argument('--out', default=None, type=str,
                             help='Name of output file. If input is a *.th file the file will be converted and output to this file, otherwise printed to screen')
    parser_date.set_defaults(func=to_datetime)

    parser_clip = subparsers.add_parser(
        'clip', help='Clip (subset) an input file in elapsed time to a new, later, start date')

    parser_clip.add_argument(
        '--start', required=True, help='Start time in ISO-like format 2009-03-12T00:00:00. Time part is optional.')
    parser_clip.add_argument(
        '--clip_start', required=True, help='Starting date for output.')
    parser_clip.add_argument('--out', default=None, type=str,
                             help='Name of output file. If input is a *.th file the file will be converted and output to this file, otherwise printed to screen')
    parser_clip.add_argument('elapsed_input', default=None, nargs='+',
                             help='One or more numbers representing elapsed seconds since the start argument or the name of a *.th file with the time column in elapsed seconds.')
    parser_clip.set_defaults(func=clip)
    return parser


def to_elapsed(args):
    s = args.start
    inputfile = args.dated_input
    dt = args.step
    # convert start time string input to datetime
    try:
        sdtime = datetime.datetime(*list(map(int, re.split(r'[^\d]', args.start))))
    except:
        raise ValueError("Could not convert start time to datetime: {}".format(args.start))
    print("Model start time given: %s" % sdtime)
    # Some correctness checking
    if len(inputfile) > 1 and inputfile[0].endswith(".th"):
        raise ValueError("Only one file argument allowed at a time")

    th = len(inputfile) == 1 and inputfile[0].endswith(".th")
    th = len(inputfile) == 1 and os.path.exists(inputfile[0])
    # NOTE: the second th above overrides the first one.
    outpath = args.out
    if outpath and not th:
        raise ValueError(
            "Outfile option only allowed if the input is a *.th file")

    # Delegate chore based on the input (file, timestamp string or elapsed
    # time)
    annotate = args.annotate
    skip_nan = args.skip_nan
    if th:
        infile = inputfile[0]
        if to_elapsed:
            file_to_elapsed(infile, s, outpath, annotate, skip_nan)
    else:
        describe_timestamps(inputfile, s, dt)


def to_datetime(args):
    print(args.subcommand)
    s = args.start
    input = args.elapsed_input
    dt = args.step
    annotate = args.annotate

    # convert start time string input to datetime
    sdtime = datetime.datetime(*list(map(int, re.split('[^\d]', args.start))))
    "Model start time given: %s" % sdtime
    # Some correctness checking
    if len(input) > 1 and input[0].endswith(".th"):
        raise ValueError("Only one file argument allowed at a time")

    th = len(input) == 1 and input[0].endswith(".th")
    th = len(input) == 1 and os.path.exists(input[0])
    mt = re.match("\\d{4}\-", input[0])
    outpath = args.out
    if outpath and not th:
        raise ValueError(
            "Outfile option only allowed if the input is a *.th file")

    if annotate and not th:
        raise ValueError(
            "Annotate option only allowed if the input is a *.th file")

    # Delegate chore based on the input (file, timestamp string or elapsed
    # time)
    if th:
        infile = input[0]
        elapsed_unit = args.elapsed_unit
        time_format = args.time_format
        file_to_timestamp(infile, s, outpath,
                          elapsed_unit=elapsed_unit, time_format=time_format)
    else:
        # inputs (hopefully) were elapsed time
        describe_elapsed(input, s, dt)


def clip(args):
    infile = args.elapsed_input
    input = args.elapsed_input

    # convert start time string input to datetime
    start = datetime.datetime(*list(map(int, re.split('[^\d]', args.start))))
    scliptime = datetime.datetime(
        *list(map(int, re.split('[^\d]', args.clip_start))))

    th = len(input) == 1 and input[0].endswith(".th")
    th = len(input) == 1 and os.path.exists(input[0])
    if not th:
        raise ValueError("Clipping command requires file (.th) input")
    infile = input[0]
    outpath = args.out

    if not outpath:
        outfile = sys.stdout
    else:
        outfile = open(outpath, "w")
    with open(infile, "r") as thfile:
        prev_use = False
        prev_outline = None
        for line in thfile:
            if line and len(line) > 1 and not line.startswith("#"):
                splitline = line.split()
                timestr = splitline[0]
                msec_orig = float(timestr)
                mdtm = start + datetime.timedelta(seconds=msec_orig)
                mdelta = (mdtm - scliptime)
                msec = mdelta.total_seconds()
                exact = msec == 0.0
                outline = line.replace(timestr, "%-10.1f " % msec)
                use = (msec >= 0.0)
                if use and not prev_use:
                    if prev_outline and not exact:
                        outfile.write(prev_outline)
                    outfile.write(outline)
                elif use and prev_use:
                    outfile.write(outline)
                prev_outline = outline
                prev_use = use
    if outfile != sys.stdout:
        outfile.close()

def multi_file_to_elapsed(input,output,start):
    import os
    import glob
    if isinstance(input,list):
        inputs = input
        if isinstance(output,list):
            if not len(input) == len(output): 
                raise ValueError("If inputs and outputs are both lists, they should be the same size")
            outputs = output
        elif not os.path.isdir(output):
            raise ValueError("output was a scalar, but not a valid directory name: {}".format(output))
        else:
             outputs = [os.path.join(output,y) for y in [os.path.split(x)[1] for x in input]]
    else:
        is_glob = True
        is_dir = os.path.isdir(output)
        if isinstance(output,list) or not is_dir:
            raise ValueError("If using blob search, output must be a directory not a list: {}".format(output))
        inputs = glob.glob(input)
        if len(inputs) == 0: raise ValueError("No files matched pattern: {}".format(input))
        outputs = [os.path.join(output,y) for y in [os.path.split(x)[1] for x in inputs]]
    for ifn,ofn in zip(inputs,outputs):
        print(ifn)
        file_to_elapsed(ifn,start,ofn)
        
            
def file_to_elapsed(infile, start, outpath=None, annotate=False, skip_nan=False):

    if not isinstance(start,datetime.datetime):
        start = datetime.datetime(*list(map(int, re.split(r'[^\d]', start))))

    if not outpath:
        outfile = sys.stdout
    else:
        outfile = open(outpath, "w")
    with open(infile, "r") as thfile:
        prev_use = False
        prev_outline = None
        no_record = True
        for iline,line in enumerate(thfile):
            if line and len(line) > 4 and not line.startswith("#"):
                splitline = line.split()
                if skip_nan and splitline[-1] == 'nan':
                    continue
                if len(splitline) <  2: continue
                timestr = splitline[0]
                if len(timestr) == 10:
                    # Only got the date,not the time
                    timestr += " %s" % splitline[1]
                use = True
                try:
                    mdtm = datetime.datetime(*list(map(int, re.split('[^\d]', timestr))))
                except:
                    raise ValueError("Could not parse time {} in line {}".format(timestr,iline))
                mdelta = (mdtm - start)
                mdtime = start + mdelta
                msec = mdelta.total_seconds()
                exact = msec == 0.0
                if annotate:
                    outline = "%s (%s,  %s)\n" % (line, mdtime, mdelta)
                    use = True
                else:
                    outline = line.replace(timestr, "%-10.1f " % msec)
                    use = (msec >= 0.0)
                if use and not prev_use:
                    if prev_outline and not exact:
                        outfile.write(prev_outline)
                    outfile.write(outline)
                    no_record = False
                elif use and prev_use:
                    outfile.write(outline)
                    no_record = False
                prev_outline = outline
                prev_use = use
        if no_record:
            outfile.write(prev_outline)
    if outfile != sys.stdout:
        outfile.close()


def file_to_timestamp(infile, start, outpath=None, annotate=False,
                      elapsed_unit="s", time_format="%Y-%m-%dT%H:%M "):
    if elapsed_unit == "s":
        elapsed_fac = 1.
    elif elapsed_unit == "d":
        elapsed_fac = 24 * 3600
    else:
        raise ValueError("elapsed_unit must be 's' or 'd'")

    if type(start) == str:
        start = datetime.datetime(*list(map(int, re.split('[^\d]', start))))
    if not outpath:
        outfile = sys.stdout
    else:
        outfile = open(outpath, "w")
    with open(infile, "r") as thfile:
        for line in thfile:
            if line and len(line) > 4:
                splitline = line.split()
                timestr = splitline[0]
                try:
                    msec = round(float(timestr) * elapsed_fac)
                except:
                    raise ValueError(
                        "elapsed time %s could not be coerced to float. \nDid you mean to convert a date to elapsed (use to_elapsed)?" % timestr)
                mdelta = datetime.timedelta(seconds=msec)
                mdtime = start + mdelta
                if annotate:
                    outline = "%s (%s,  %s)\n" % (line, mdtime, mdelta)
                else:
                    mdtimestr = mdtime.strftime(time_format)
                    outline = line.replace(timestr, mdtimestr, 1)
                outfile.write(outline)
    if outfile != sys.stdout:
        outfile.close()


def describe_elapsed(times, start, dt=None):
    if type(start) == str:
        start = datetime.datetime(*list(map(int, re.split('[^\d]', start))))
    for elapsed in times:
        elapsed = elapsed.lower()
        if elapsed.endswith("d") or elapsed.endswith("days") or elapsed.endswith("day"):
            mday = elapsed.split("d")[0]
            msec = float(mday) * (24. * 3600)  # mtime is in days
        elif elapsed.endswith("s") or elapsed.endswith("sec"):
            msec = elapsed.split("s")[0]
            msec = float(msec)
        else:
            # assuming that the input elapsed time is in seconds
            msec = float(elapsed)
        mdelta = datetime.timedelta(seconds=msec)
        print("Model seconds:  %s" % msec)
        print("Elapsed time:   %s" % mdelta)
        mdtime = start + mdelta
        print("Model datetime: %s" % mdtime)
        if dt:
            remain = abs(msec % dt)
            if abs(msec % dt) > 1.e-6:
                print("Model step:    %s" % (msec / dt))
                print("\n Input time is %s seconds past the last even model time step\n" % remain)
            else:
                print("Model step:    %s\n" % int(msec / dt))
        else:
            print("\n")


def describe_timestamps(timestamps, start, dt=None):
    if type(start) == str:
        start = datetime.datetime(*list(map(int, re.split('[^\d]', start))))
    if not type(timestamps) == list:
        timestampse = [timestamps]
    for stamp in timestamps:
        # assume mtime argument is a date time and try to parse to datetime
        mdtime = datetime.datetime(*list(map(int, re.split('[^\d]', stamp))))
        mdelta = mdtime - start
        msec = mdelta.total_seconds()
        print("Datetime:      %s" % mdtime)
        print("Elapsed time:  %s" % mdelta)
        print("Model seconds: %s" % msec)
        if dt:
            remain = abs(msec % dt)
            if abs(msec % dt) > 1.e-6:
                print("Model step:    %s" % (msec / dt))
                print("\n Input time is %s seconds past the last model time step\n" % remain)
            else:
                print("Model step:    %s\n" % int(msec / dt))
        else:
            print("\n")


# driver for standalone use
def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    func = args.func
    func(args)


if __name__ == "__main__":
    main()
