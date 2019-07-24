import numpy as np

def laplace_smooth_data(mesh,data,rate=0.05,iter_total=150):
    nodes = mesh.nodes
    edges = mesh.edges    
    x =nodes[:,0:2]
    iter = 0
    smooth_data=data.copy()
    while (iter < iter_total):
        zz = smooth_data.copy()
        for ndx in range(nodes.shape[0]):
            nds = mesh.get_neighbor_nodes(ndx)
            vnode = data[ndx]
            vneighbor = [smooth_data[n] for n in nds]
            vave = np.mean(vneighbor)
            zz[ndx] = vnode + rate*(vave-vnode)
            
        iter += 1
        smooth_data = zz
    return smooth_data

def laplace_smooth_data2(mesh,data,kappa=0.05,dt=1.0,iter_total=150):
    nodes = mesh.nodes
    edges = mesh.edges
    rate = dt*kappa    
    x =nodes[:,0:2]
    iter = 0
    smooth_data=data.copy()
    while (iter < iter_total):
        zz = smooth_data.copy()
        for ndx in range(nodes.shape[0]):
            nds = mesh.get_neighbor_nodes(ndx)
            vnode = smooth_data[ndx]
            vneighbor = [smooth_data[n] for n in nds]
            vave = np.mean(vneighbor)
            zz[ndx] = vnode + rate*(vave-vnode)
            
        iter += 1
        smooth_data = zz
    return smooth_data




def laplace_smooth_with_vel(mesh,data,vel,kappa=0.05,dt=1.,iter_total=1):
    nodes = mesh.nodes
    edges = mesh.edges       
    x =nodes[:,0:2]
    iter = 0
    smooth_data=data.copy()
    while (iter < iter_total):
        zz = smooth_data.copy()
        for ndx in range(nodes.shape[0]):
            nds = mesh.get_neighbor_nodes(ndx)
            vnode = data[ndx]
            vneighbor = [smooth_data[n] for n in nds]
            vave = np.mean(vneighbor)
            zz[ndx] = vnode + dt*kappa*(vave-vnode) + dt*vel[ndx]
            
        iter += 1
        smooth_data = zz
    return smooth_data    

def laplace_smooth_with_vel2(mesh,data,vel,kappa=0.05,dt=1.,iter_total=1):
    nodes = mesh.nodes
    #edges = mesh.edges    
    #x =nodes[:,0:2]
    iter = 0
    smooth_data=data.copy()
    while (iter < iter_total):
        zz = smooth_data.copy()
        #print "iter = {} smooth_data = {} ".format(iter,smooth_data[100000:100005])
        for ndx in range(nodes.shape[0]):
            nds = mesh.get_neighbor_nodes(ndx)
            vnode =smooth_data[ndx]
            vneighbor = [smooth_data[n] for n in nds]
            vave = np.mean(vneighbor)
            zz[ndx] = vnode + dt*kappa*(vave-vnode) + dt*vel[ndx]
            
        iter += 1
        smooth_data = zz
    return smooth_data  



def laplace_smooth_with_vel3(mesh,nlayer,data,vel,kappa=0.05,dt=1.,iter_total=1):
    nodes = mesh.nodes
    #edges = mesh.edges    
    #x =nodes[:,0:2]
    iter = 0
    smooth_data=data.copy()
    while (iter < iter_total):
        zz = smooth_data.copy()
        for ndx in range(nodes.shape[0]):
            nds = mesh.get_neighbor_nodes(ndx)
            nlayer_node = nlayer[ndx]
            vnode =smooth_data[ndx]
            vneighbor = smooth_data[nds]
            vbase = data[nds]
            neighbor = np.where(nlayer[nds] >= nlayer_node, vneighbor,vbase)
            vave = np.mean(neighbor)
            zz[ndx] = vnode + dt*kappa*(vave-vnode) + dt*vel[ndx]
            
        iter += 1
        smooth_data = zz
    return smooth_data  












