# -*- coding: utf-8 -*-
"""

"""

from schismviz.suxarray import *
import xarray as xr
from shapely import distance
import numpy as np

###############################################################################################
#
# Read coarse grid
coarse_path = ".//hsi//bay_delta_coarse_v4.gr3"
coarse_mesh=read_hgrid_gr3(coarse_path)


# Read fine grid
fine_path = ".//hgrid.gr3"

fine_mesh=read_hgrid_gr3(fine_path)

# Build map and weights

map_f = open(".//mapped_dwr_new.txt",'w')


fine_nodes=fine_mesh.node_points

coarse_face_id_from_fine_node=coarse_mesh.elem_strtree.query(fine_nodes)
coarse_face_nodes=coarse_mesh.Mesh2_face_nodes.values
# Create an empty array to store the node mapping. `-1` is the fill value.
map_to_coarse_nodes=np.full((fine_mesh.nMesh2_node,3),-1,dtype=int)

map_to_coarse_nodes[coarse_face_id_from_fine_node[0],:]=coarse_face_nodes[coarse_face_id_from_fine_node[1]][:,:3]-1
fine_nodes_not_found=list(set(range(fine_mesh.nMesh2_node))-set(coarse_face_id_from_fine_node[0]))
fine_nodes_not_found.sort()

coarse_nodes_nearest=xr.apply_ufunc(lambda p: coarse_mesh.node_strtree.nearest(p),
                                    fine_nodes.isel(nSCHISM_hgrid_node=fine_nodes_not_found),
                                    vectorize=True,dask="parallelized")
map_to_coarse_nodes[fine_nodes_not_found,0]=coarse_nodes_nearest

da_map_to_coarse_nodes = xr.DataArray(map_to_coarse_nodes,
                                      dims=('nSCHISM_hgrid_node', 'three'),
                                      coords={'nSCHISM_hgrid_node': fine_mesh.ds.nSCHISM_hgrid_node},
                                      attrs={'_FillValue': -1, 'start_index': 0},
                                      name='map_to_coarse_nodes')

def _calculate_weight(conn, points):
    """ Calculate distance between a point and a set of points.
    """
    x = coarse_mesh.Mesh2_node_x.values[conn]
    y = coarse_mesh.Mesh2_node_y.values[conn]
    xy = np.array([p.xy for p in points])
    dist = np.apply_along_axis(np.linalg.norm, 1, np.stack((x, y), axis=1) - xy)
    weight = np.reciprocal(dist)
    # Find where we see the infinite values
    mask = np.where(np.isinf(weight))
    # Adjust the weights for the node
    weight[mask[0], :] = 0.
    weight[mask] = 1.
    return weight

chunk_size = None
da_weight = xr.apply_ufunc(_calculate_weight,
               da_map_to_coarse_nodes.chunk({'nSCHISM_hgrid_node': chunk_size}),
               fine_nodes.chunk({'nSCHISM_hgrid_node': chunk_size}),
               input_core_dims=[['three'], []],
               output_core_dims=[['three']],
               dask='parallelized',
               output_dtypes=float).persist()

# Create a dataset and save it
ds_map_and_weight = da_map_to_coarse_nodes.to_dataset(name=da_map_to_coarse_nodes.name)
ds_map_and_weight['weight'] = da_weight
path_map_and_weight = 'map_and_weight.nc'
ds_map_and_weight.to_netcdf(path_map_and_weight)