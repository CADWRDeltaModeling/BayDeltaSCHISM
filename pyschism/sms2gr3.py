# -*- coding: utf-8 -*-
'''
Manage conversion from SMS 2dm format to gr3.
Some material borrowed @author: snegusse
'''
import numpy as np
import string
import re
import math
import os
import argparse
import logging

class Boundary(object):
    def __init__(self,name,btype,nodestring):
        self.name = name
        self.btype = btype
        self.nodestring = nodestring


def addnode(list):
    sum = 0
    for item in list:
        sum += len(item.nodestring)
    return sum

def convert_2dm(file, outfile=None, elev2depth=False, logger=None):
    if logger is None:
        logging_level = logging.INFO
        logging_fname = 'sms2gr3.log'
        logging.basicConfig(level=logging_level, filename=logging_fname,
                            filemode='w')
        logger = logging.getLogger('sms2gr3')
    if not outfile:
        outfile = os.path.splitext(file)[0] + ".gr3"
    logger.info("Converting %s to %s" %(file, outfile))

    f = open(file, 'r')
    all_lines = f.readlines()
    f.close()

    logger.info("  Total lines in input file: %s" % len(all_lines))

    elementlines = [line.strip().split()
                    for line in all_lines
                    if line.startswith("E3T") or line.startswith("E4Q")]
    nelement = len(elementlines)

    nodelines = [line.strip().split()[1:5]
                 for line in all_lines[nelement:]
                 if line.startswith("ND")]
    nnode = len(nodelines)
    last_possible_node = nnode + nelement

    nodestrlines = [line.strip()
                    for line in all_lines[last_possible_node:]
                    if line.startswith("NS")]
    nnodestrlines = len(nodestrlines)

    boundlines = [line.strip()
                  for line in all_lines[last_possible_node+nnodestrlines:]
                  if line.startswith("BC")]

    logger.info("  N nodes: %s" % nnode)
    logger.info("  N element: %s" % nelement)
    nodes = np.zeros((nnode, 3), dtype=np.float)
    elements = np.zeros((nelement, 5), dtype=np.int32)
    for i, nodeinfo in enumerate(nodelines):
        nodes[i, :] = [float(x) for x in nodeinfo[1:]]
        node_id = int(nodeinfo[0])
        assert node_id == (i+1)
    if (elev2depth):
        nodes[:, 2] = -nodes[:, 2]
    else:
        # TODO: there is no function with this name.
        pass
        # adjust_height(nodes)

    for i, eleminfo in enumerate(elementlines):
        if eleminfo[0] == 'E3T':
            _, n0, n1, n2 = [int(x) for x in eleminfo[1:5]]
            elements[i] = 3, n0, n1, n2, -1
        elif eleminfo[0] == 'E4Q':
            _, n0, n1, n2, n3 = [int(x) for x in eleminfo[1:6]]
            elements[i] = 4, n0, n1, n2, n3
        else:
            raise ValueError("Unsupported element type.")

    boundnodestrings = []
    boundid = []
    startnew = True
    for line in nodestrlines:
        if startnew:
            latest = []
            boundnodestrings.append(latest)
            startnew = False
        items = [int(x) for x in line.split()[1:]]
        if items[-2] < 0:
            startnew = True
            items[-2] *= -1
            latest += items[0:-1]
            boundid.append(items[-1])
        else:
            latest += items
    nboundsegs = len(boundnodestrings)

    bc_regex = re.compile(r"""BC\s+\d+\s+\"(land|open|island)\"\s+(\d+).*\nBC_DEF\s+\d+\s+\d+\s+\"(.*)\"\s+\d+\s+\"(.*)\".*""")

    boundary_defs = {}
    for m in bc_regex.finditer(string.join(boundlines, "\n")):
        btype = m.group(1)
        bdef_id = int(m.group(2))
        assert m.group(3) == "name"
        name = m.group(4)
        boundary_defs[bdef_id] = (bdef_id, btype, name)

    boundaries = []
    for line in boundlines:
        if line.startswith("BC_VAL"):
            items = string.split(line)[1:]
            entity_id, def_id, param_id = [int(x)
                                           for x in items[1:-1]]
            name = items[-1]
            boundary_def = boundary_defs[def_id]
            bc = Boundary(name, boundary_def[1],
                          np.array(boundnodestrings[entity_id-1],
                          dtype=np.int32))
            boundaries.append(bc)

    fout = open(outfile, "w")
    fout.write("hgrid.gr3\n")
    fout.write("%s %s    ! number of elements, nodes\n" % (nelement, nnode))
    padding = 2
    maxnum = int(math.log10(max(nelement, nnode))) + padding
    ifmt = "%" + ("%ii" % maxnum)
    ifmtj = "%-" + ("%ii" % maxnum)
    ffmt = "%18.8f"
    nfmt = ifmtj + ffmt * 3 + "\n"

    for i in range(nnode):
        fout.write(nfmt % (i+1, nodes[i, 0], nodes[i, 1], nodes[i, 2]))

    for i in range(nelement):
        n = elements[i, 0]
        efmt = ifmtj + "%2i"+ ifmt * n + "\n"
        elem = (i+1, n) + tuple(elements[i, 1:n+1])
        fout.write(efmt % elem)

    openbound = [bc for bc in boundaries if bc.btype == "open"]
    landbound = [bc for bc in boundaries if bc.btype == "land"]
    islebound = [bc for bc in boundaries if bc.btype == "island"]

    fout.write("%s !Number of open boundaries\n" % len(openbound))
    fout.write("%s !Number of open boundary nodes\n" % addnode(openbound))
    for i, bound in enumerate(openbound):
        fout.write("%s !Number of nodes for open boundary (%s) %s\n"
                   % (len(bound.nodestring), i + 1, bound.name))
        np.savetxt(fout, bound.nodestring, fmt="%i")

    nlandbound = len(landbound) + len(islebound)
    nlandboundnode = addnode(landbound)

    nisleboundnode = addnode(islebound)
    nlandboundnode += nisleboundnode
    fout.write("%s !Number of land boundaries\n" % nlandbound)
    fout.write("%s !Number of land boundary nodes (including islands)\n" % nlandboundnode)
    for i, bound in enumerate(landbound):
        fout.write("%s !Number of nodes for land boundary %s (\'0\' means exterior land boundary)\n" % (len(bound.nodestring),i+1))
        np.savetxt(fout, bound.nodestring, fmt="%i")

    for i, bound in enumerate(islebound):
        fout.write("%s !Number of nodes for island boundary %s (\'1\' means island)\n" % (len(bound.nodestring),i+1))
        np.savetxt(fout, bound.nodestring, fmt="%i")
    fout.close()
    logger.info("Finished converting a 2dm file.")

def create_arg_parser():
    parser = argparse.ArgumentParser(description='Convert a *.2dm SMS mesh to a *.gr3 SCHISM mesh.')
    parser.add_argument('--elev2depth', action='store_true', default=False,help='SMS geometry is in terms of elevation and should be flipped in sign.')
    parser.add_argument('--outfile', default=None, help='name of output file')
    parser.add_argument(dest='infile',default=None, help='name of input file')
    return parser


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    parser = create_arg_parser()
    args = parser.parse_args()
    elev2depth = args.elev2depth
    infile = args.infile
    outfile = args.outfile
    convert_2dm(infile, outfile, elev2depth)
