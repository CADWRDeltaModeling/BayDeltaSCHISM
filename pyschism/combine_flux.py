#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Command line tool to merge possibly overlapping flux.dat files from hotstart runs
"""
import argparse
import numpy as np


def combine_flux(infiles,outfile,prefer_last=False):
    """ Merge possibly overlapping flux.dat files from hostart runs
    """
    
    filedata = [np.loadtxt(f) for f in infiles]
    nfile = len(filedata)
    starts = np.array([fd[ 0,0] for fd in filedata])
    ends   = np.array([fd[-1,0] for fd in filedata])
    sorder = np.argsort(starts)
    eorder = np.argsort(ends)
    if np.any(np.not_equal(sorder,eorder)):
        raise ValueError("input files are ambiguously ordered (one lies inside another)")
    if np.any(sorder[1:]<sorder[:-1]):
        raise ValueError("Files out of order. This is the apparent order of inputs: {}".format(sorder))
    
    nstation = filedata[0].shape[1] -1
    writeformat = ["%16.6f"] + nstation*["%14.4e"]        

    ndxlast = filedata[-1].shape[0]
    if prefer_last:
        sblock = np.full(len(filedata), 0, dtype=np.int64)
        eblock = [np.searchsorted(filedata[i][:,0],starts[i+1]) for i in range(nfile-1)] + [ndxlast]
    else:
        sblock = [0] + [np.searchsorted(filedata[i][:,0],ends[i-1],side="right") for i in range(1,nfile)]
        eblock = [filedata[i].shape[0] for i in range(len(filedata))]

    blocks2merge = [d[s:e] for d,s,e in zip(filedata,sblock,eblock)]
    for m in blocks2merge: print(m.shape)
    merged = np.vstack(tuple(blocks2merge))
    
    ddt = np.diff(merged[:,0],n=2)
    if np.max(ddt) > 1.e-4:
        raise ValueError("The continuity of time in the files is wrong. Successive time steps should differ by less than 1e-4")

    np.savetxt(outfile,merged,delimiter=" ",fmt=writeformat)




def test_combine_flux():
    full = open("flux_small.dat","r")
    breaks = [60,120,200]
    b = 0
    fnames=[]
    lines = full.readlines()
    for i,e in enumerate(breaks):
        fname = "flux{}.dat.".format(i)
        fnames.append(fname)
        out = open(fname,"w")
        for line in lines[b:(e+10)]:
            out.write(line+"\n")
        b=e
        out.close()
    fout = "flux_comb.dat"
    combine_flux(fnames,fout,prefer_last=False)


def create_arg_parser():
    parser = argparse.ArgumentParser(description="Merge possibly-overlapping flux.dat files from hotstarted runs. ")
    parser.add_argument('--prefer_last', action='store_true')
    parser.add_argument('--output', 
                        help="output file")
    parser.add_argument('files',type=argparse.FileType('r'),nargs="+",
                        help="List of input files in chronological order")
                        
    return parser

    
def main():
    """ Driver to parse arguments
    """
    parser = create_arg_parser()
    args = parser.parse_args()
    filelist = args.files
    inputs = [x.name for x in filelist]
    prefer_last = args.prefer_last
    output = args.output
    if output in inputs:
        raise ValueError("Cannot overwrite input file names")
    combine_flux(filelist,output,prefer_last)



if __name__ == '__main__':
    #test_combine_flux()
    main()
