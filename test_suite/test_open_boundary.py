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
    names = []
    num_openboundary = int(lines[2+num_eles+num_nodes].split()[0])
    num_boundarynode = int(lines[3+num_eles+num_nodes].split()[0])
    i_num_node = 0
    pos = 3 + num_eles + num_nodes + 1
    for i in range(num_openboundary):
        i_num_node = int(lines[pos].split()[0])
        open_boundaries.append(i_num_node)
        names.append(lines[pos].split()[-1])
        pos += 1+i_num_node
    dict_hgrid = {"open_boundaries": open_boundaries, "names": names}
    return dict_hgrid

def read_bctides_in(file_path):
    """Read bctides.in and extract number of open boundary nodes."""
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('!')]
    ntip = int(lines[1].split()[0])
    line_ptr = 1+ntip*2+1
    nbfr = int(lines[line_ptr].split()[0])
    line_ptr += ntip*2+1
    num_open_boundaries = int(lines[line_ptr].split()[0])
    open_boundaries = []
    ettype = []
    fltype = []
    tetype = []
    satype = []
    line_ptr += 1

    for _ in range(num_open_boundaries):
        # Each boundary has: boundary_type, num_nodes, [node_list]
        line = lines[line_ptr]
        if "!" in line:
            line = line.split("!")[0]
        parts = line.split()
        nodes = int(parts[0])
        ettype.append(int(parts[1])) # elevation type
        fltype.append(int(parts[2])) # velocity type
        tetype.append(int(parts[3])) # temperature type
        satype.append(int(parts[4])) # salinity type
        open_boundaries.append(nodes)

        for itype in range(1,len(parts)):
            btype = int(parts[itype])
            i = min(3,itype)
            skip_line = eval(skip_lines[i][btype])
            line_ptr += skip_line
        line_ptr += 1
    dict_bctides = {"open_boundaries": open_boundaries,
                    "boundary_types": {"elevation": ettype, "velocity": fltype,
                                       "temperature": tetype, "salinity": satype}
                    }
    return dict_bctides

def compare_open_boundaries(hgrid_boundaries, bctides_boundaries):
    # Check if the number of boundaries matches
    assert len(hgrid_boundaries) == len(bctides_boundaries), \
        f"Mismatch in number of open boundaries: hgrid.gr3 has {len(hgrid_boundaries)}, bctides.in has {len(bctides_boundaries)}"

    # Check each boundary's nodes
    for i, (hgrid_nodes, bctides_nodes) in enumerate(zip(hgrid_boundaries, bctides_boundaries)):
        assert hgrid_nodes == bctides_nodes, \
            f"Boundary {i+1} mismatch: hgrid.gr3 has {hgrid_nodes}, bctides.in has {bctides_nodes}"


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
    hgrid_boundaries = read_hgrid_gr3(hgrid_file)["open_boundaries"]
    bctides_boundaries = read_bctides_in(bctides_file)["open_boundaries"]

    # Compare the open boundaries
    compare_open_boundaries(hgrid_boundaries, bctides_boundaries)


def bctides_in_summary(bctides_path="bctides.in", hgrid_path="hgrid.gr3"):
    """Summarize bctides.in file into human-readable form."""

    bc_description = {"elevation": {0: "not specified",
                                    1: "time history of elevation (elev.th)",
                                    2: "constant elevation",
                                    3: "tides",
                                    4: "read from elev2D.th.nc",
                                    5: "combination of elev2D.th.nc and tides"},
                    "velocity": {0: "not specified",
                            1: "time history of discharge (flux.th)",
                            2: "constant discharge",
                            3: "velocity (NOT discharge) forced in frequency domain",
                            4: "velocity (NOT discharge) read from uv3D.th.nc",
                            5: "combination of uv3D.th.nc and tides",
                            -4: "3D input with relaxation constants for inflow/outflow",
                            -1: "Flather type radiation b.c."},
                    "temperature": {0: "not specified",
                                    1: "time history of temperature (TEM_1.th)",
                                    2: "constant temperature",
                                    3: "initial temperature profile for inflow",
                                    4: "read from TEM_3D.th.nc"},
                    "salinity": {0: "not specified",
                                1: "time history of salinity (SAL_1.th)",
                                2: "constant salinity",
                                3: "initial salinity profile for inflow",
                                4: "read from SAL_3D.th.nc"},
                    "tracers": {0: "not specified",
                    1: "time history of tracer ('tracer'_*.th)",
                    2: "constant tracer value",
                    3: "initial tracer profile for inflow",
                    4: "read from 'tracer'_3D.th.nc"}
    }

    hgrid = read_hgrid_gr3(hgrid_path)
    bctides = read_bctides_in(bctides_path)

    compare_open_boundaries(hgrid["open_boundaries"], bctides["open_boundaries"])

    num_boundaries = len(hgrid["open_boundaries"])
    for i, boundary in enumerate(hgrid["names"]):
        print(f"Boundary {i+1} of {num_boundaries}: {boundary}")

        for variable in bctides["boundary_types"]:
            btype = bctides["boundary_types"][variable][i]
            description = bc_description[variable][btype]
            print(f"  {variable}:\t[{btype}] {description}")