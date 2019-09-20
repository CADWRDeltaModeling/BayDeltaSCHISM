import subprocess
from itertools import product
import os.path
import os
import sys
import glob
import time
from shutil import copyfile
import datetime as dtm

FBASE_SALT = ["zcor.63","salt.63"]
FBASE_PTM = ["elev.61","hvel.64","vert.63","zcor.63"]

combine_exe = "D:/Delta/BayDeltaSCHISM/bin/combine_output9.exe"
combine_hotstart_exe = "D:/Delta/BayDeltaSCHISM/bin/combine_hotstart6.exe"



def do_combine(dir,begin,end,filebase):
    for iblock in range(begin,end+1):
        combinefile = os.path.join(dir,"%s_%s" % (iblock,filebase))
        touch(combinefile)

def do_combine_hotstart(dir,step):
    combinefile = os.path.join(dir,"%s_hotstart" % (step))
    touch(combinefile)

def split(alist, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in xrange(n))    
        
def combine(dir,blocks,fbase,consume=True):
    print("Called combine with %s" % (fbase))
    workdir = dir
    for block in blocks:
        firstblock,lastblock = block
        all_delete_files = []
        for fb in fbase:
            print("Working on file type %s from stack %s to %s" % (fb, firstblock,lastblock))
            print(" In directory %s" % workdir)
            subprocess.check_call([combine_exe, "-b", str(firstblock),"-e", str(lastblock), "-f", fb], cwd = workdir, shell=True)
            #do_combine(dir,firstblock,lastblock,fb)
            for block in range(firstblock,lastblock+1):
                pat = "%s_????_" % block
                to_delete_files = glob.glob(os.path.join(workdir,pat+fb))
                all_delete_files.extend(to_delete_files)
        if consume:
            for fname in all_delete_files:
                os.remove(fname)

def combine_hotstart(dir,minstep=0,maxstep=99999999,consume=True):
    workdir = dir
    print("Called combine_hotstart")
    proc0files = glob.glob(os.path.join(dir,"*_0000_hotstart"))
    allindex = [int(os.path.split(p0)[1].split("_")[0]) for p0 in proc0files]
    if maxstep:
        allindex = [x for x in allindex if x > minstep and x<maxstep]
    else: 
        allindex = [x for x in allindex if x > minstep]    
    allindex.sort()
    print(allindex)
    all_delete_files = []
    for step in allindex:
        #do_combine_hotstart(dir,step)
        subprocess.check_call([combine_hotstart_exe, "-i", str(step),"-p", str(128), "-t", str(2)], cwd = workdir, shell=True)
        hotstartdest = os.path.join(workdir,"hotstart_{}.in".format(step))
        hotstartsrc = os.path.join(workdir,"hotstart.in")
        print("renaming {} as {} ".format(hotstartsrc,hotstartdest))
        os.rename(hotstartsrc,hotstartdest)
        pat = "%s_????_hotstart" % step
        to_delete_files = glob.glob(os.path.join(dir,pat))
        all_delete_files.extend(to_delete_files)
    if consume:
        for fname in all_delete_files:
            print(fname)
            os.remove(fname)
            
def archive_blocks(ar_file,tbase,blocks_per_day=1,ndxmin=1,ndxmax=None):
    f = open(ar_file,"r")
    blocks = []
    comments = []
    for line in f:
        linecomment = line.strip().split("#")
        if len(linecomment) > 1:
            line = linecomment[0]
            comment = ",".join(linecomment[1:]).strip()
        else:
            comment = None
        if line and len(line) > 10:
            times = line.strip().split(",")
            time0 = times[0]
            time1 = times[1] if len(times)>1 else time0
            t0 = dtm.datetime.strptime(time0,"%Y-%m-%d")
            t1 = dtm.datetime.strptime(time1,"%Y-%m-%d")
            t0 = max(t0,tbase)
            blocks.append( ((t0 - tbase).days*blocks_per_day + 1,(t1 - tbase).days*blocks_per_day + blocks_per_day))
            comments.append(comment)
    # consolidate blocks
    blocks.sort()
    cblock = []
    last_block = blocks[0]
    for b in blocks[1:]:
        if b[0] <= last_block[1]:
            # overlap, so merge but don't add last_block yet
            last_block[1] = b[1]
        else: 
            cblock.append(last_block)
            last_block = b
    if cblock[-1] != last_block: cblock.append(last_block)
    # impose min and max block
    cblock = [x for x in cblock if x[1] >= ndxmin and x[0] <= ndxmax]
    cblock[0]=(max(cblock[0][0],ndxmin),cblock[0][1])
    cblock[-1]=(cblock[-1][0],min(cblock[-1][1],ndxmax))
    print("cblock")
    print(cblock)
    return cblock
            
def gather_ppf_names(dir,blocks):
    max_block = 200

def prune_ppf_files(dir,blocks,fbase,list_only=False):
    flist = []
    print("pruning")
    for fb in fbase:
        for b in blocks:
            globpath = os.path.join(dir,"%s_????_%s" % (int(b),fb))
            globlist = glob.glob(globpath)            
            for g in globlist:
                os.remove(g)



def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)
    
# 1 gather ppf search 
# filter wanted/unwanted

def setup(dir,filebase):
    for fb in filebase:
        for iday in range(5,180):
            for icore in range(0,4): 
                fname = "%s_%04d_%s" % (iday,icore,fb)
                fpath = os.path.join(dir,fname)
                touch( fpath)
    for istep in range(1,60000,1440):
        for icore in range(0,4):
            fname = "%s_%04d_hotstart" % (istep,icore)
            fpath = os.path.join(dir,fname)
            touch (fpath)

#def detect_nproc(dir,sample_fbase,sample_ndx):
#    os.path.join(dir,"*_0000_%s" % sample_fbase)  
            
def detect_min_max_index(dir,sample_fbase):
    pat = os.path.join(dir,"*_0000_%s" % sample_fbase)
    proc0files = glob.glob(pat)
    if len(proc0files) == 0:
        raise ValueError("No files detecting matching base filename patterns. Wrong directory or pattern?")
    allindex = [int(os.path.split(p0)[1].split("_")[0]) for p0 in proc0files]
    allindex.sort()
    ndxmin,ndxmax = allindex[0],allindex[-1]
    return ndxmin,ndxmax



def create_arg_parser():
    """ Create argument parser for
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, 
                        help='start date of simulation in format like yyyy-mm-dd')
    parser.add_argument('--dir', default='.', type=str,
                        help='directory in which output will be processed')                 
    parser.add_argument('--fbase', type=str,default = "schout.nc",nargs='+',
                        help="File base name. This will either be 'schout.nc' or a list of files like 'elev.61,hvel.64,salt.63'. ")
    parser.add_argument('--hotstart', action = 'store_true', help = "Combine hotstart in addition to fbase")
    parser.add_argument('--consume',  action = 'store_true', help = "Delete combined files or unrequested files")
    parser.add_argument('--combiner',  default="combine_output9", help = "Executable for combine_output.")
    parser.add_argument('--hot_combiner',  default="combine_hotstart6", help = "Executable for combine_output.")
    parser.add_argument('--sndx',  default=None, type=int, help = "First index to consider for processing.")    
    parser.add_argument('--endx',  default=None, type=int, help = "First index to consider for processing.") 
    parser.add_argument('--sndx_hot',  default=None, type=int, help = "First index to consider for processing.")    
    parser.add_argument('--endx_hot',  default=None, type=int, help = "First index to consider for processing.") 
    
    parser.add_argument('--datefile', type=str,help="File containing list of dates. Each line can have a single date or comma-separated pair indicating block start and end. Blank lines are ignored and # is comment character that can comment the entire line or be placed at the side of a line after the date(s). ")
    parser.add_argument('--blocks_per_day', type=int, default=1,help = 'Blocks used to store 1 day worth of output.')
    return parser


    
def combine_consume(is_test=False):
    parser = create_arg_parser()
    args = parser.parse_args()
    dir = args.dir
    fbase = args.fbase
    blocks_per_day = args.blocks_per_day
    start = dtm.datetime.strptime(args.start,"%Y-%m-%d")
    consume = args.consume
    hotstart = args.hotstart
    datefile = args.datefile
    
    if is_test: 
        setup(dir,fbase)
    else:
        if not os.path.exists(combine_exe): 
            raise Exception("combine_output executable not found")
        if hotstart and not os.path.exists(combine_hotstart_exe):
            raise Exception("combine_hotstart executable not found")

    ndxmin,ndxmax = 1,100 # detect_min_max_index(dir,fbase[0])
    print("min/max: %s %s" % (ndxmin,ndxmax ))
    blocks = archive_blocks(datefile,start,blocks_per_day,ndxmin,ndxmax)
    wanted = set()
    for b in blocks: 
        wanted.update(range(b[0],b[1]+1))
    u  = range(ndxmin,ndxmax+1)
    unwanted = [ii for ii in u if not ii in wanted]
    unwanted = [ii for ii in u if not ii in wanted]
    wanted = list(wanted)
    wanted.sort()
    unwanted.sort()
    print("wanted")
    print(wanted)
    if consume: 
        prune_ppf_files(dir,unwanted,fbase,list_only = True)
    #combine(dir,blocks,fbase,consume=consume)
    if hotstart:
        combine_hotstart(dir,consume=consume)
      
          
if __name__ == "__main__":
    dir = "./test_archive"
    fbase = FBASE_SALT
    combine_consume()
