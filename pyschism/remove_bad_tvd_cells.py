from schism_setup import *
import numpy as np
import sets
import shutil
import os


def get_number_of_processors_used(global_to_local_fpath):
    """ Infer the number of processors used from 'global_to_local.prop' file
        global_to_local_fpath = path of 'global_to_local.prop'
        return = # of processors used
    """
    data = np.loadtxt(global_to_local_fpath, dtype='i4')
    n_proc = np.amax(data[:,1]) + 1
    return n_proc


def get_bad_elements(output_dir, n_proc):
    """
    """
    bad_elements_dict = {}
    for i_proc in range(n_proc):
	fname = "nonfatal_%04d" % i_proc
	fpath = os.path.join(output_dir, fname)
	print("Processing %s..." % fname)
	f = open(fpath, 'r')
	for l in f:
	    l = l.strip()
	    if len(l) > 0 and l.startswith("TVD"):
		tokens = l.split()
		if len(tokens) < 10:
		    continue
		t = float(tokens[9]) # Timestamp
		element_i = int(tokens[5]) - 1  # element index (zero based)
		dtb = float(tokens[8]) # dtb (subtime step)
		if element_i in bad_elements_dict:
		    old_value = bad_elements_dict[element_i]
		    if dtb < old_value[0]:
			bad_elements_dict[element_i] = (old_value[0] + 1, dtb)
		    else:
			bad_elements_dict[element_i] = (old_value[0] + 1,
					     old_value[1])
		else:
		    bad_elements_dict[element_i] = (1, dtb)
	f.close()
    bad_elements = np.array([(k, ) + v for k, v in bad_elements_dict.items()],
			 dtype = [('element_i', 'i4'), ('count', 'i4'),
				  ('min_dtb', 'f4')])
    return bad_elements

def collect_nodes_to_remove(bad_elements, mesh):
    """
        bad_elements = numpy array of bad elements, which is an output from
	get_bad_elements
	mesh = SCHISM mesh
	from the sorted bad elements.
	return = a set of bad nodes to remove
    """

    # Collecting how many times of nodes are in the 'bad' list
    bad_nodes = {}
    for (element_i, count, dtb) in bad_elements:
	for node_i in mesh.elements[element_i]:
	    if node_i in bad_nodes:
		bad_nodes[node_i] += 1
	    else:
		bad_nodes[node_i] = 1

    # Create a list of nodes to remove
    nodes_to_remove = sets.Set()
    for (element_i, count, dtb) in bad_elements:
	bad_counts = np.array([bad_nodes[node_i]
			       for node_i in mesh.elements[element_i]])
	bad_max = np.amax(bad_counts)
	bad_avg = np.average(bad_counts)
	if bad_max == bad_avg:
	    if mesh.is_element_on_boundary(element_i):
		for edge_i in mesh.element2edges(element_i):
		    edge = mesh.edges[edge_i]
		    if edge[2] != INTERNAL_EDGE:
			nodes_to_remove.add(edge[0])
			nodes_to_remove.add(edge[1])
	    else:
		for node_i in mesh.elements[element_i]:
		    nodes_to_remove.add(node_i)
	else:
	    for node_i in mesh.elements[element_i]:
		if bad_max == bad_nodes[node_i]:
		    nodes_to_remove.add(node_i)

    return nodes_to_remove

def remove_nodes(nodes_to_remove, mesh):
    """ Remove the given nodes from the given tvd mesh
        nodes_to_remove = a set of node indices to remove
        mesh = SCHISM mesh
	no return
    """
    for node_i in nodes_to_remove:
	node = mesh.nodes[node_i]
	if node[2] == 0.:
	    print("This node is not in the TVD zone. Node: {} {}".format(node_i + 1, node))
	else:
	    print("Remove Node: {} {}".format(node_i + 1, node))
	    node[2] = 0.


def main():
    Input_dir = "../Inputs/Baroclinic_44"

    input_dir = Input_dir
    output_dir = os.path.join(input_dir, "outputs")
    global_to_local_fpath = os.path.join(output_dir, "global_to_local.prop")
    n_proc = get_number_of_processors_used(global_to_local_fpath)
    print("# of processors used for the run: {}".format(n_proc))

    # Collect bad elements from all nonfatals
    bad_elements = get_bad_elements(output_dir, n_proc)

    # Sorted up
#     bad_elements_sorted = np.sort(bad_elements, order = 'min_dtb')
    bad_elements_sorted = np.sort(bad_elements, order = 'count')
    bad_elements_sorted = bad_elements_sorted[::-1]  # Flip

    n_elements_to_remove = 20
    # Let's pick up nodes to remove from the TVD list...
    tvd_in_fname = "tvd.gr3"
    tvd_in_fpath = os.path.join(input_dir,tvd_in_fname)
    s = load_hgrid(tvd_in_fpath)
    nodes_to_remove = collect_nodes_to_remove(bad_elements_sorted[:n_elements_to_remove],
					      s.mesh)

    print("Nodes to remove:")
    print(nodes_to_remove)

    # Let's remove selected nodes from tvd.gr3
#     bak_fname = "tvd.gr3.bak"
#     bak_fpath = os.path.join(input_dir, bak_fname)
#     i = 0
#     while os.path.exists(bak_fpath):
# 	bak_fpath = os.path.join(input_dir, bak_fname + "%d" % i)
# 	i += 1
#     shutil.copy(tvd_in_fpath, bak_fpath)

    # Remove the selected nodes and create a new tvd.gr3
    remove_nodes(nodes_to_remove, s.mesh)
    tvd_out_fpath = os.path.join(input_dir, "tvd_new.gr3")
    s.write_gr3(tvd_out_fpath)

if __name__ == "__main__":
    main()
