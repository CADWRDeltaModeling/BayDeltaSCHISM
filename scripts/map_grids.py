# -*- coding: utf-8 -*-
"""

"""

from schismviz.suxarray import *
from shapely import distance

###############################################################################################
#
# Read coarse grid
coarse_path = ".//hsi//bay_delta_coarse_v4.gr3"
coarse_mesh=read_hgrid_gr3(coarse_path)


# Read fine grid
fine_path = ".//hgrid.gr3"

fine_mesh=read_hgrid_gr3(fine_path)

# Build map and weights
f_c_ele_map = []
f_c_ele_wghts = []
map_f = open(".//mapped_dwr_new.txt",'w')
out_str=""

ii=0
for node in fine_mesh.node_points:
    #find encompassing element
    containingCoarseEle=coarse_mesh.find_element_at(node.x,node.y)
   
    #for jj in range(nCoarseEle):
    if(containingCoarseEle):
        #get point list

        jj=containingCoarseEle[0]
        print(ii)
        coarse_element_nodes=coarse_mesh.Mesh2_face_nodes.isel(nSCHISM_hgrid_face=jj)
        valid_coarse_nodes=coarse_element_nodes[coarse_element_nodes>0]
        f_c_ele_map.append(valid_coarse_nodes) ## suxarray default index startint from 1

            #compute and save weighting factors
        weights = []
        loc=0
        
        for pid in valid_coarse_nodes:
            dist=distance(Point(coarse_mesh.Mesh2_node_x[pid-1],coarse_mesh.Mesh2_node_y[pid-1]),node)
            dist2 = dist*dist
                
            if(dist2 > 0):
                weights.append(1.0/dist2)
            else:
                weights.clear()
                weights=[0.0]*len(coarse_element_nodes)
                weights[loc]=1.0
                break
            loc=loc+1
             
        f_c_ele_wghts.append(weights)                   
    else :
        #find closest element 
        closest=coarse_mesh.node_spatial_tree.nearest(node) 
        f_c_ele_map.append([closest]) 
        f_c_ele_wghts.append([1])
   
    

        
    numElNodes=len(f_c_ele_map[ii])
    
    numElNodes=len(valid_coarse_nodes)
    out_str=out_str+("{0} {1}".format(ii+1, numElNodes))
    #pdb.set_trace()
    for jj in range(numElNodes): #1-based index

          out_str=out_str+(" {0}".format(f_c_ele_map[ii][jj]))
    for jj in range(numElNodes):    

          out_str=out_str+(" {0}".format(f_c_ele_wghts[ii][jj]))
        
    out_str=out_str+"\n"

    ii=ii+1
map.write(out_str)
map_f.close()