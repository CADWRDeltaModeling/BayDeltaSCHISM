# -*- coding: utf-8 -*-
"""
Created on Fri May  5 09:45:12 2023

@author: qshu
"""

import numpy as np

def gen_node_neibor_ele(mesh_node,max_node_in_a_cell,num_ele,num_node):
    num_ele_at_node=(np.zeros((num_node))).astype(int)
    for i in range(num_ele):
        for j in range(max_node_in_a_cell):
            if(mesh_node[i][j]>0):
                nodeid=mesh_node[i][j]-1
                num_ele_at_node[nodeid]=num_ele_at_node[nodeid]+1

    max_ele_at_node=int(np.max(num_ele_at_node))
    num_ele_at_node[:]=np.zeros((num_node)).astype(int)
    out_neibor_ele=np.empty((num_node,max_ele_at_node))
    out_neibor_ele[:,:]=np.nan
    for i in range(num_ele):
        for j in range(max_node_in_a_cell):
            if(mesh_node[i][j]>0):
                nodeid=mesh_node[i][j]-1
                loc=num_ele_at_node[nodeid]
                out_neibor_ele[nodeid,loc]=i
                num_ele_at_node[nodeid]=loc+1
    return out_neibor_ele,max_ele_at_node


def gen_node_wet_dry(node_wet_dry,ele_wet_dry,num_step,num_node,max_ele_at_node,el):
    
    for t in range(num_step):
        for i in range(num_node):
            all_dry=True
            for j in range(max_ele_at_node):

                if(not(np.isnan(el[i,j]))):
                    dry=ele_wet_dry[t,int(el[i,j])]
                    if(dry==0):
                        all_dry=False
                        break
            if(all_dry):
                node_wet_dry[t,i]=1
            else:
                node_wet_dry[t,i]=0
   

def face_aver(node_depth_average,node_num,face_num,ele_table):
    a1=np.zeros((face_num))
    a2=np.zeros((face_num))
    a3=np.zeros((face_num))
    a4=np.zeros((face_num))
    id1=ele_table[:,0]-1
    id2=ele_table[:,1]-1
    id3=ele_table[:,2]-1
    id4=ele_table[:,3]-1
    a1=node_depth_average[id1]
    a2=node_depth_average[id2]
    a3=node_depth_average[id3]
    node_num=np.where(id4<0,3.0,4.0)
    a4=np.select([id4<0,id4>=0],[0.0,node_depth_average[id4]])
    face_val=(a1+a2+a3+a4)/node_num
    return face_val

def face_aver_inst(inst_node_depth_average,node_num,face_num,ele_table):
    a1=np.zeros((face_num))
    a2=np.zeros((face_num))
    a3=np.zeros((face_num))
    a4=np.zeros((face_num))
    id1=ele_table[:,0]-1
    id2=ele_table[:,1]-1
    id3=ele_table[:,2]-1
    id4=ele_table[:,3]-1
    a1=inst_node_depth_average[:,id1]
    a2=inst_node_depth_average[:,id2]
    a3=inst_node_depth_average[:,id3]
    node_num=np.where(id4<0,3.0,4.0)
    a4=np.zeros(a3.shape)
    at=np.zeros((a3.shape[0]))
    for i in range(a3.shape[0]):
        at=inst_node_depth_average[i,:]
        a4[i,:]=np.select([id4<0,id4>=0],[0.0,at[id4]])
    face_val=(a1+a2+a3+a4)/node_num
    return face_val

def triangle_area(x1, y1, x2, y2, x3, y3):
    return abs(0.5*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2)))

def quad_area(x1, y1, x2, y2, x3, y3,x4,y4):
    a1=triangle_area(x1,y1,x2,y2,x4,y4)
    a2=triangle_area(x2,y2,x3,y3,x4,y4)
    return a1+a2

def fill_ele_area(face_num,ele_table,node_x,node_y,ele_area):
    for k in range(face_num):
        node_id_lst=ele_table[k,:]
        
        i=node_id_lst[0]-1
        x1=node_x[i]
        y1=node_y[i]
        i=node_id_lst[1]-1
        x2=node_x[i]
        y2=node_y[i]
        i=node_id_lst[2]-1
        x3=node_x[i]
        y3=node_y[i]
        i=node_id_lst[3]-1
        if not(np.isfinite(i)): ## schout use garbage
            a=triangle_area(x1,y1,x2,y2,x3,y3)
            ele_area[k]=a
        else:
            
            x4=node_x[i]
            y4=node_y[i]
            a=quad_area(x1,y1,x2,y2,x3,y3,x4,y4)
            ele_area[k]=a
            
def fill_ele_area510(face_num,ele_table,node_x,node_y,ele_area):
    for k in range(face_num):
        node_id_lst=ele_table[k,:]
        
        i=node_id_lst[0]-1
        x1=node_x[i]
        y1=node_y[i]
        i=node_id_lst[1]-1
        x2=node_x[i]
        y2=node_y[i]
        i=node_id_lst[2]-1
        x3=node_x[i]
        y3=node_y[i]
        i=node_id_lst[3]-1
        if (i==-2): ## out2d use -1
            a=triangle_area(x1,y1,x2,y2,x3,y3)
            ele_area[k]=a
        else:
            
            x4=node_x[i]
            y4=node_y[i]
            a=quad_area(x1,y1,x2,y2,x3,y3,x4,y4)
            ele_area[k]=a