# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 15:50:34 2019

@author: zzhang
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import logging
from shapely.geometry import Polygon, MultiPolygon

def shapely_to_geopandas(features,Proj4=None,shp_fn=None):
    """
    convert shapely features to geopandas and generate shapefiles as needed
    """
    df = pd.DataFrame()
    df['geometry'] = features
    gdf = gpd.GeoDataFrame(df,geometry='geometry')
    if Proj4:
        gdf.crs = Proj4
    else:
        gdf.crs = "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_def"
    if shp_fn:  
        gdf.to_file(shp_fn)
        print("%s generated"%shp_fn)        
    return gdf

def Contiguity_Check(mesh,poly_fn,centering='nodes'):
    """
    Check if the mesh division by polygons in poly_fn is contiguous. 
    The contiguity check is based on nodes or elems
    1) if there are any orphand nodes, and 
    2) if any nodes were assigned to multiple polygons. 
    """
    poly_gpd = gpd.read_file(poly_fn)        
    if centering == 'elems':
        mesh_gpd = mesh.to_geopandas(feature_type = 'polygon')
        # if the centroid falls in a polygon, the mesh grid is in the polygon
        mesh_gpd['geometry'] = mesh_gpd['geometry'].centroid
    else:
        mesh_gpd = mesh.to_geopandas(feature_type = 'point')   
    
    poly_gpd.set_index('id',inplace=True)
    poly_gpd.sort_index(inplace=True)
    for id_n, poly in zip(poly_gpd.index,poly_gpd['geometry']):
        id_name = "id_%s"%str(id_n) # make it one-based. 
        mesh_gpd[id_name] = mesh_gpd.within(poly)
    
    ID_keys = mesh_gpd.keys()[ ['id_' in k for k in mesh_gpd.keys()] ]
    ID_df = mesh_gpd[ID_keys]
    # check if there is at least one id that each cell belongs to
    orphaned_cells = np.where(~np.any(ID_df,axis=1))[0]
    if len(orphaned_cells) >=1:
        string = ",".join(orph_cells.astype(str))
        raise Exception("Orphaned cells found at %s"%string)
    # check if there are cells that belong to multiple polygons
    multi_labeled_cells = np.where(np.count_nonzero(ID_df,axis=1)>1)[0]
    if len(multi_labeled_cells) >=1:
        string = ",".join(multi_labeled_cells.astype(str))
        raise Exception("These cells belong to mulitple polygons %s"%string) 
    # otherwise the domain is contiguous. 
    logging.info("The domain divisino is contiguous!")
    mapping = np.where(ID_df.values)[1]+1 # change to one-based indices
    return mapping

def Polylen(poly):
    # find the number of polygons in a polygon feature
    if isinstance(poly,Polygon):
        poly_len = 1
    elif isinstance(poly, MultiPolygon):
        poly_len = len(poly)  
    return poly_len

def FindMultiPoly(poly_array):
    # find the indices for multipolygons in a list or array of polygons
    plens =[]
    for poly in poly_array:
        poly_len = Polylen(poly)
        plens.append(poly_len)
        
    ind = np.where(np.array(plens)>1)[0]
    return ind


            
        


    
        
    
    
