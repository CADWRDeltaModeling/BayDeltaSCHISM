#!/usr/bin/env python
# -*- coding: utf-8 -*-import pandas as pd
import sys

def diff_congruent_gr3(fname0,fname1,fout):
    print(f"Differenceing {fname0} and {fname1}")
    with open(fout,'w') as out:
        with open(fname0,'r') as first:
            with open(fname1,'r') as second:
                first_lines = list(first.readlines())
                nelem,nnode = map(int,first_lines[1].strip().split()[0:2])
                for i,(line0,line1) in enumerate(zip(first_lines,second.readlines())):
                    if i>1 and i<nnode+2:
                        try:
                            n,x,y,z = line0.strip().split()
                        except:
                            print(line1)
                            raise
                        n1,x1,y1,z1 = line1.strip().split()
                        diff = float(z1)-float(z)
                        outline = f"{n} {x} {y} {diff}\n"

                        out.write(outline)
                    else:
                        out.write(line0)
                    
                    
if __name__ == "__main__":
    fname0,fname1,out = sys.argv[1:4]
    diff_congruent_gr3(fname0,fname1,out)