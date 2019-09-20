
import matplotlib.pyplot as plt
import numpy as np

def schism_timing(workdir,start=1, end=None, block_days = 1.0):
    import glob,os
    sample="elev.61"
    files = [os.path.split(x)[1] for x in glob.glob(os.path.join(workdir,"*_0000_%s" % sample))]
    files.sort(key = lambda x: int(x[0:x.index("_")]))
    blocks = [int(x[0:x.index("_")]) for x in files]
    if end:
        endndx = blocks.index(end)
        print(endndx)
        print(blocks)
    else:
        endndx = len(blocks)-1
    startndx = blocks.index(start)
    files = files[startndx:endndx]    
    blocks = blocks[startndx:endndx]

    paths = [os.path.join(workdir,x) for x in files]
    times = np.array([os.path.getmtime(x) for x in paths])
    diffs = np.diff(times)/(block_days*3600.*24.)

    if np.any(diffs < 0.0):
        raise ValueError("Negative timing between files, which is impossible Old and new run mixed in one directory? Change analysis bracket?")
    
    speed = 1./diffs
    speedmean = np.mean(speed)
    speedmed = np.median(speed)
    print("Mean speed: %5.1f" % speedmean)


    f, ax = plt.subplots()
    
    ax.plot(blocks[:-1],speed)
    ax.set_xlabel("Output block")
    ax.set_ylabel("Speed (days/day)")
    ax.axhline(y=speedmean)
    ax.text(blocks[4],speed.min(),"Mean speed %5.1f (days/d)" % speedmean)
    #ax2=ax.twinx()
    plt.show()
    
def create_arg_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir',default=".",type = str,help = 'Name of working directory')
    parser.add_argument('--start', default = None, type=int,help = 'Start block (integer) of analysis.')
    parser.add_argument('--end', default = None, type=int,help = 'End day (integer) of analysis.')
    parser.add_argument('--blocklen', default = 1., type = float,help = "Number of simulated days in one output block")
    return parser    

if __name__=="__main__":
    import sys
    parser = create_arg_parser()
    args = parser.parse_args()
    workdir = args.dir
    start = args.start
    end = args.end
    blocklen = args.blocklen
    print(start)
    print(end)
    print(workdir)
    print(blocklen)
    schism_timing(workdir,start,end,blocklen)
