#!/usr/bin/python 
import numpy as np
import os.path


def analyze(hgrid,dir,ncore,dtb,start,end):
    
    hgrid = open(hgrid,"r")
    header0 = hgrid.readline()
    parts = hgrid.readline().strip().split()
    num_ele=parts[0]
    num_node=parts[1]
    hgrid.close()
    num_ele = int(num_ele)
    num_node = int(num_node)
    flag = np.zeros(num_ele, int)
    proc = np.zeros(num_ele, int)
    for i in range(ncore):
        filename = os.path.join(dir,"nonfatal_%04d"%i)
        with open(filename,"r") as f:
            for line in f:
                if line.startswith("TVD-upwind dtb info"):
                    parts = line.strip().split()
                    subtd = float(parts[8])
                    elapsed = float(parts[9])/86400.
                    element = int(parts[5])
                    if (elapsed >= start) and (elapsed <= end) and (subtd<dtb):
                        flag[element-1] += 1
                        proc[element-1] = i
    
    with open("subcycling.prop","w") as out:
        for j in range(num_ele):
            out.write("%s %s %s\n" % ((j+1), flag[j],proc[j]))
    

            
def create_arg_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start',default = 0, required=True,type = int,help = 'Start day (integer) of subcycling analysis. Avoid the beginning where feasible')
    parser.add_argument('--end', default = None, type=int,help = 'End day (integer) of analysis.')
    parser.add_argument('--dtb', default = 1e6, type = float,help = "Time step threshold above which subcycling is ignored")
    parser.add_argument('--ncore',default = None, type=int, help = "Number of cores in simulation")
    parser.add_argument('--hgrid',default = 'hgrid.gr3', type=str, help = "absolute or relative path of hgrid.gr3") 
    parser.add_argument('--dir',default = 'outputs',type=str,help='directory where nonfatal* are located')    
    return parser
    
    
def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    
    s=args.start
    e=args.end
    dtb = args.dtb
    ncore = args.ncore
    hgrid = args.hgrid
    if not os.path.exists(hgrid):
        raise ValueError("hgrid.gr3 does not exist at: %s" % hgrid)
    dir = args.dir        
    if not os.path.exists(dir):
        raise ValueError("The argument dir does not exist: %s" % dir)
    analyze(hgrid,dir,ncore,dtb,s,e)
    
    
if __name__ == '__main__':
   main()