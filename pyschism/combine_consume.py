#!/usr/bin/env python
import subprocess
from itertools import product
import os.path
import os
import sys
import glob
import time
from shutil import copyfile
import datetime as dtm

FBASE_5_6 = ["schout.nc"]
#FBASE_SALT = ["zcor.63","salt.63"]
#FBASE_PTM = ["elev.61","hvel.64","vert.63","zcor.63"]
#FBASE_BINARY= ["elev.61","hvel.64","zcor.63","salt.63"]


SCHISM_INCOMPLETE_COMBINE = 36   # error code for incomplete file

#combine_exe = "D:/Delta/BayDeltaSCHISM/bin/combine_output11.exe"
#combine_hotstart_exe = "D:/Delta/BayDeltaSCHISM/bin/combine_hotstart7.exe"
combine_exe = "combine_output11"
combine_hotstart_exe = "combine_hotstart7"


def do_combine(wdir,begin,end,filebase):
    for iblock in range(begin,end+1):
        finfile = "{}+{}".format(iblock,filebase)
        combinefile = os.path.join(wdir,finfile)
        touch(combinefile)

def do_combine_hotstart(wdir,step):
    finfile = "{}_hotstart".format(step)
    combinefile = os.path.join(wdir,finfile)
    touch(combinefile)

def split(alist, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in xrange(n))    
        
def appears_done(wdir,fb,exten,firstblock,lastblock):
    """ Decide if entire file block already appears to have been combined based on existence of combined file. Date not checked"""
    appears_done = True
    for i in range(firstblock, lastblock+1):
        #fname = "{}_{}".format(i,fb)
        fname = "{}_{}".format(fb,i)
        if exten == ".nc": fname = fname + exten
        combined_filepath = os.path.join(wdir,fname)
        print("checking {}".format(combined_filepath))
        if not os.path.exists(combined_filepath):
            appears_done=False
            break
    print(appears_done)
    return appears_done


def failed_incomplete(e):
    output = e.output
    print(output)
    with open("combine_output.txt","w") as coo:
        print("writing output")
        coo.write(output)
    return e.returncode == SCHISM_INCOMPLETE_COMBINE


def combine(wdir,blocks,fbase,combine_exe,consume=True,assume_done=True):
    print("Called combine with {} in directory {}".format(fbase,wdir))
    pesky_fn = os.path.join(wdir,"combine_files_pesky.txt")
    if os.path.exists(pesky_fn): os.remove(pesky_fn)
    deletable_fn = os.path.join(wdir,"combine_files_deletable.txt")
    if os.path.exists(deletable_fn): os. remove(deletable_fn)
    workdir = wdir
    lastblockonlist = blocks[-1]
    pesky_files = []
    for block in blocks:
        firstblock,lastblock = block
        all_delete_files = []
        for fb in fbase:
            if fb.endswith(".nc"):
                fb =fb[:-3]
                exten = ".nc"
            else:
                exten = ""
            print("Working on file type %s from stack %s to %s" % (fb, firstblock,lastblock))
            print(" In directory %s" % workdir)
            if appears_done(wdir,fb,exten,firstblock,lastblock):
                print("Skipping combine for block because it appears fully combined")
                block_delete = True
            else:
                try:
                    subprocess.check_output([combine_exe, "-b", str(firstblock),"-e", str(lastblock), "-f", fb], cwd = workdir, shell=False)
                    block_delete = True    # If we got here, combine for this block was full success. 
                                           # Files marked eligible to delete (if --consume not chosen)
                except subprocess.CalledProcessError as e:
                    # failed because last file was incomplete
                    if failed_incomplete(e) and (block == lastblockonlist):
                        print("fail")
                        # Appears that combine failed because file was not complete. What to do next depends on whether run is assumed complete. 
                        if assume_done:
                            if lastblock > firstblock:
                                # Since we are done, assume we want to do as much as we can, despite last of block not being there
                                # try again with last index ommitted, delete all including the one that failed
                                subprocess.check_output([combine_exe, "-b", str(firstblock),"-e", str(lastblock-1), "-f", fb], cwd = workdir, shell=False)
                            # move on and delete
                            block_delete = True
                        else:
                            # since not assuming done, we might have better luck later. Don't try again or delete right now. 
                           block_delete = False
                    else:
                        print("not ")
                        print(e.returncode)
       
            #do_combine(wdir,firstblock,lastblock,fb)
            for block in range(firstblock,lastblock+1):
                #pat = "%s_????_" % block
                pat = "{}_????_{}".format(fb,block)
                if exten == ".nc": 
                    pat = pat+exten
                pat = os.path.join(workdir,pat)
                to_delete_files = glob.glob(pat)
                if block_delete:
                    all_delete_files.extend(to_delete_files)
                else:
                    pesky_files.extend(to_delete_files)
        if consume:
            for fname in all_delete_files:
                os.remove(fname)
        else:
            if len(to_delete_files) > 0:
                with open(deletable_fn,'a') as dd:
                    dd.write("\n".join(to_delete_files))

    if len(pesky_files) > 0:
        with open(pesky_fn,'a') as pp:
            pp.write("\n".join(pesky_files))

def combine_hotstart(wdir,combine_hotstart_exe,minstep=0,maxstep=99999999,consume=True):
    workdir = wdir
    print("Called combine_hotstart")
    pat = "hotstart_0000_*.nc"
    proc0files = glob.glob(os.path.join(wdir,pat))
    proc0files = [os.path.splitext(os.path.split(p0)[1])[0] for p0 in proc0files]
    exten = ".nc"
    allindex = [int(p0.split("_")[2]) for p0 in proc0files]
    print(allindex)
    if maxstep:
        allindex = [x for x in allindex if x > minstep and x<maxstep]
    else: 
        allindex = [x for x in allindex if x > minstep]    
    allindex.sort()
    all_delete_files = []
    for step in allindex:
        #do_combine_hotstart(wdir,step)
        #subprocess.check_call([combine_hotstart_exe, "-i", str(step),"-p", str(128), "-t", str(2)], cwd = workdir, shell=False)
        subprocess.check_call([combine_hotstart_exe, "-i", str(step)], cwd = workdir, shell=False)
        #hotstartdest = os.path.join(workdir,"hotstart_{}.in".format(step))
        #hotstartsrc = os.path.join(workdir,"hotstart.in")
        #print("renaming {} as {} ".format(hotstartsrc,hotstartdest))
        #os.rename(hotstartsrc,hotstartdest)
        #pat = "%s_????_hotstart" % step
        pat = "hotstart_????_{}".format(step)
        if  exten == ".nc": pat = pat + exten
        to_delete_files = glob.glob(os.path.join(wdir,pat))
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
            last_block = (last_block[0],b[1])
        else: 
            cblock.append(last_block)
            last_block = b
    if cblock[-1] != last_block: cblock.append(last_block)
    # impose min and max block
    cblock = [x for x in cblock if x[1] >= ndxmin and x[0] <= ndxmax]
    cblock[0]=(max(cblock[0][0],ndxmin),cblock[0][1])
    cblock[-1]=(cblock[-1][0],min(cblock[-1][1],ndxmax))
    print("cblock"    )
    print(cblock)
    return cblock
            
def gather_ppf_names(wdir,blocks):
    max_block = 200

def prune_ppf_files(wdir,blocks,fbase,list_only=False):
    flist = []
    print("pruning")
    print(fbase)
    for fb in fbase:
        if fb.endswith(".nc"):
            fb = fb[:-3]
            exten = ".nc"
        else:
            exten = ""
        for b in blocks:
            #globpath = os.path.join(wdir,"%s_????_%s" % (int(b),fb))
            gpath = "{}_????_{}{}".format(fb,int(b),exten)
            globpath = os.path.join(wdir,gpath)
            globlist = glob.glob(globpath)            
            for g in globlist:
                os.remove(g)



def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)
    
# 1 gather ppf search 
# filter wanted/unwanted

def setup(wdir,filebase):
    for fb in filebase:
        for iday in range(5,180):
            for icore in range(0,4): 
                fname = "%s_%04d_%s" % (iday,icore,fb)
                fpath = os.path.join(wdir,fname)
                touch( fpath)
    for istep in range(1,60000,1440):
        for icore in range(0,4):
            fname = "%s_%04d_hotstart" % (istep,icore)
            fpath = os.path.join(wdir,fname)
            touch (fpath)

#def detect_nproc(wdir,sample_fbase,sample_ndx):
#    os.path.join(wdir,"*_0000_%s" % sample_fbase)  
            
def detect_min_max_index(wdir,sample_fbase):
    if sample_fbase.endswith(".nc"):
        bpat = "{}_0000_*{}".format(sample_fbase[:-3],".nc")
    else:
        bpat = "*_0000_{}".format(sample_fbase)
    pat = os.path.join(wdir,bpat)
    proc0files = glob.glob(pat)

    print(pat)
    print(os.path.splitext(os.path.split(proc0files[0])[1]))
    print(os.path.splitext(os.path.split(proc0files[0])[1])[0].split("_"))

    if len(proc0files) == 0:
        raise ValueError("No files detecting matching base filename patterns. Wrong directory or pattern? ({})".format(pat))
    allindex = [int(os.path.splitext( os.path.split(p0)[1])[0].split("_")[2]) for p0 in proc0files]
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
    parser.add_argument('--fbase', type=str,default = ["schout.nc"],nargs='+',
                        help="File base name. This will either be 'schout.nc' or a list of files like 'elev.61,hvel.64,salt.63'. ")
    parser.add_argument('--hotstart', action = 'store_true', help = "Combine hotstart in addition to fbase")
    parser.add_argument('--hotstart_only', action = 'store_true', help = "Only combine hotstart -- avoids file search errors when nothing left to combine")
    parser.add_argument('--consume',  action = 'store_true', help = "Delete combined files or unrequested files")
    parser.add_argument('--assume_done',  action = 'store_true', help = "Assume that the simulation is finished, so incomplete blocks can be deleted")
    parser.add_argument('--combiner',  default="combine_output9", help = "Executable for combine_output.")
    parser.add_argument('--hot_combiner',  default="combine_hotstart6", help = "Executable for combine_output.")
    parser.add_argument('--sndx',  default=None, type=int, help = "First index to consider for processing.")    
    parser.add_argument('--endx',  default=None, type=int, help = "Last index to consider for processing.") 
    parser.add_argument('--sndx_hot',  default=None, type=int, help = "First index to consider for processing.")    
    parser.add_argument('--endx_hot',  default=None, type=int, help = "Last index to consider for processing.") 
    
    parser.add_argument('--datefile', type=str,help="File containing list of dates. Each line can have a single date or comma-separated pair indicating block start and end. Blank lines are ignored and # is comment character that can comment the entire line or be placed at the side of a line after the date(s). ")
    parser.add_argument('--blocks_per_day', type=int, default=1,help = 'Blocks used to store 1 day worth of output.')
    return parser


    
def combine_consume(is_test=False):
    parser = create_arg_parser()
    args = parser.parse_args()
    wdir = args.dir
    fbase = args.fbase
    blocks_per_day = args.blocks_per_day
    start = dtm.datetime.strptime(args.start,"%Y-%m-%d")
    consume = args.consume

    hotstart = args.hotstart or args.hotstart_only
    hotstart_only = args.hotstart_only
    datefile = args.datefile.strip()
    sndx = args.sndx    
    endx = args.endx
    assume_done = args.assume_done
    combine_exe = args.combiner
    combine_hotstart_exe = args.hot_combiner

    if is_test: 
        setup(wdir,fbase)
    else:
        # check soundness of combine utilities before starting
        subprocess.check_call([combine_exe, "-h"], cwd = wdir, shell=False)
        if hotstart:
            subprocess.check_call([combine_hotstart_exe, "-h"], cwd=wdir, shell=False)

    if not hotstart_only:
        ndxmin,ndxmax = detect_min_max_index(wdir,fbase[0])
        if not sndx is None: 
            ndxmin = sndx
        if not endx is None:
            ndxmax = endx
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
        if consume: 
            prune_ppf_files(wdir,unwanted,fbase,list_only = True)
        combine(wdir,blocks,fbase,combine_exe,consume=consume,assume_done=assume_done)
    if hotstart:
        combine_hotstart(wdir,combine_hotstart_exe,consume=consume)
      
          
if __name__ == "__main__":
    wdir = "./test_archive"
    fbase = FBASE_5_6
    combine_consume()
