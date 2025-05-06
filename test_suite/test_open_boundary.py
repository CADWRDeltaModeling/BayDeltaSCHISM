import pytest
import numpy as np
import os

elev_lines = {0:"0", 1:"0", 2:"1", 3:"nbfr*(1+nodes)", 4:"0", \
              5:"nbfr*(1+nodes)"}

vel_lines = {0:"0", 1:"0", 2:"1", 3:"nbfr*(1+nodes)", 4:"0", \
              5:"nbfr*(1+nodes)",-4:"1",-1:"2+2*nodes" }

temp_lines = {0:"0", 1:"1", 2:"2", 3:"1", 4:"1"}
## salt, tracer module and temp are the same
skip_lines ={1:elev_lines, 2:vel_lines, 3:temp_lines}


def read_hgrid_gr3(file_path):
    """Read hgrid.gr3 and extract number of nodes in each open boundary."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Skip header (first 2 lines)
    parts = lines[1].split()
    num_eles = int(parts[0])
    num_nodes = int(parts[1])
    # Read open boundaries
    open_boundaries = []
    num_openboundary = int(lines[2+num_eles+num_nodes].split()[0])
    num_boundarynode = int(lines[3+num_eles+num_nodes].split()[0])
    i_num_node = 0
    pos = 3 + num_eles + num_nodes + 1
    for i in range(num_openboundary):
        i_num_node = int(lines[pos].split()[0])
        open_boundaries.append(i_num_node)
        pos += 1+i_num_node
    return open_boundaries

def read_bctides_in(file_path):
    """Read bctides.in and extract open boundary nodes."""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('!')]
    ntip = int(lines[1].split()[0])
    line_ptr = 1+ntip*2+1
    nbfr = int(lines[line_ptr].split()[0])
    line_ptr += ntip*2+1
    num_open_boundaries = int(lines[line_ptr].split()[0])
    open_boundaries = []
    line_ptr += 1

    for _ in range(num_open_boundaries):
        # Each boundary has: boundary_type, num_nodes, [node_list]
        line = lines[line_ptr]
        if "!" in line:
            line = line.split("!")[0]
        parts = line.split()
        nodes = int(parts[0])
        open_boundaries.append(nodes)

        for itype in range(1,len(parts)):
            btype = int(parts[itype])
            i = min(3,itype)
            skip_line = eval(skip_lines[i][btype])
            line_ptr += skip_line
        line_ptr += 1
    return open_boundaries

@pytest.mark.prerun
def test_boundary_consistency(sim_dir):
    """Test if open boundaries in bctides.in match hgrid.gr3."""
    hgrid_file = os.path.join(sim_dir,"hgrid.gr3")
    bctides_file = os.path.join(sim_dir,"bctides.in")
    assert os.path.exists(hgrid_file), \
            f" hgrid.gr3 doesn't exist"
    assert os.path.exists(bctides_file), \
            f" bctides.in doesn't exist"
    

    # Read boundary nodes from both files
    hgrid_boundaries = read_hgrid_gr3(hgrid_file)
    bctides_boundaries = read_bctides_in(bctides_file)
    
    # Check if the number of boundaries matches
    assert len(hgrid_boundaries) == len(bctides_boundaries), \
        f"Mismatch in number of open boundaries: hgrid.gr3 has {len(hgrid_boundaries)}, bctides.in has {len(bctides_boundaries)}"
    
    # Check each boundary's nodes
    for i, (hgrid_nodes, bctides_nodes) in enumerate(zip(hgrid_boundaries, bctides_boundaries)):
        assert hgrid_nodes == bctides_nodes, \
            f"Boundary {i+1} mismatch: hgrid.gr3 has {hgrid_nodes}, bctides.in has {bctides_nodes}"


