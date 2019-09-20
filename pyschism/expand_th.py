#!/usr/bin/env python


''' Expand a coarse *.th file into a fine one'''


def expand(infile, expandfile, dt, add_line = None):
    ''' Expand a coarse *.th file into a fine one
        infile: input file
        expandfile: fine output file
        dt:      output time step
        add_line value to use for added line (used for temperature)
    '''

    import numpy as np
    import os
    import time

    f1 = open (infile, 'r')
    if os.path.exists(expandfile): 
        os.remove(expandfile)
    f2 = open(expandfile,"a")

    oldtime = 0.
    allvals = f1.readlines()
    oldvals = np.array(allvals[0].strip().split(),dtype = np.float64)
    oldtime = oldvals[0]
    t = 0.
    interp = np.zeros_like(oldvals)
    np.set_printoptions(precision=1,suppress=True)
    if add_line:
        secondval = np.ones_like(oldvals)*add_line
        secondvalstr = " ".join(["%3.1f" % x for x in secondval[1:]])+"\n"
       
    t0 = time.time()
    for line in allvals[1:]:
        newvals = np.array(line.strip().split(),dtype=np.float64)
        newtime = newvals[0]
        while (t < newtime):
            t += dt
            u = (t - oldtime)/(newtime-oldtime)
            v = 1.-u
            interp[0] = t
            interp[1:] =oldvals[1:]*v + newvals[1:]*u          
            if add_line:
                f2.write(str(interp[0])+" ")
                f2.write(secondvalstr)
            f2.write(" ".join([str(interp[0])] + ["%3.1f" % x for x in interp[1:]])+"\n")
            
        if abs(t - newtime) > 1e-10:
            raise ValueError("Requested dt does not evenly divide file dt")
        t = newtime
        del(oldvals)
        oldvals = newvals
        oldtime = newtime

    print("Rough timing of expansion: %s: " % (time.time() - t0))
    f1.close()
    f2.close()    
    
if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description='Expand a coarse (in time) th file to a fine one.')
    parser.add_argument(dest='infile',default = None, help = 'name of input file')
    parser.add_argument('outfile', default = None, help = 'name of output file')
    parser.add_argument(dest='dt',default = None, type=float, help = 'output time step')
    parser.add_argument('--add_val',default = None, type = float, metavar = 'VAL', help = 'If given, used as value for second line for each time step (used for temperature)')
    args = parser.parse_args()
    dt = args.dt
    infile = args.infile
    outfile = args.outfile
    add_line = args.add_val
    expand(infile,outfile,dt,add_line)    

 
