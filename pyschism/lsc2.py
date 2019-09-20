#!/usr/bin/env python
""" Methods for generating local sigma coordinates
    These routines are meant to be called a pair. First,
    default_num_layers is called to obtain the recommended number of layers for
    each node based on depth. Then, gen_sigma is called to generate
    the actual local sigma values at each level (nlevels = nlayers+1).

    Note that in this script eta is the "reference" free surface at which the mesh
    is conditioned, which can be a global scalar or array of local nodal values.
    Using a medium-higher value (2-4 depending on typical flood levels) usually
    does't hurt the final product in low water. The example() shows how to visualize a mesh
    generated on one ref water surface on another surface.

    The major user parameters are already set at their defaults. It is mildly
    important to realize that the S coordinate parameters have the same qualitative
    interpretation, but that the S system is really just used as a heuristic and
    everything is manipulated locally.

    Besides theta (refinement to the surface) the mostly likely item to manipulate
    will be minlayer and maxlayer. These can be supplied locally (if these are
    given as arrays) or globally (if provided as scalars).


"""

import numpy as np
from laplace_smooth_data import *

def szcoord(s, h, eta, theta, b, hc):
    thetaterm = np.tanh(0.5 * theta)
    thetavec = theta
    c = (1 - b) * np.sinh(thetavec * s) / np.sinh(thetavec)\
        + 0.5 * b * (np.tanh(thetavec * (s + 0.5)) - thetaterm) / thetaterm
    z = eta * (1 + s) + hc * s + (h - hc) * c
    return z


def default_num_layers0(total_ref_depth, minlayer, maxlayer):
    return np.minimum(np.maximum(minlayer, total_ref_depth.astype('i')), maxlayer).astype('f')


def default_num_layers(eta, h0, minlayer, maxlayer,dz_target):
    total_ref_depth = eta + h0
    effdepth = total_ref_depth
    NCUTOFF = 18
    layerds=np.ones(NCUTOFF+1,dtype="d")/float(NCUTOFF)
    layerds[0]=0.
    ss = np.cumsum(layerds)
    zz = szcoord(ss, NCUTOFF-eta, eta, 2., 0., 1.) - 1.
    print("zz in default_num_layers")
    print(zz)
 
    nlayer0 = np.maximum(np.searchsorted(zz,effdepth),1)
    HCUT = 5.6
    nlayercutoff =  np.searchsorted(zz,HCUT)
    print("default num layer")
    print(NCUTOFF/2)
    print(nlayercutoff)
    print(zz[nlayercutoff])
    print(zz[nlayercutoff-1])
    nlayer1 = (effdepth - HCUT) + 1 + nlayercutoff
    
    nlayer_trial = np.where(effdepth<HCUT,nlayer0,nlayer1.astype("i"))
    
    nlayer = np.minimum(np.maximum(
        minlayer, (nlayer_trial).astype('i')), maxlayer) #.astype('f')

    print("Small minlayer %s = " % np.any(minlayer<=1.))
    print("Any small number layers: %s %s" % (np.amin(nlayer), np.argmin(nlayer)))   
    return nlayer

def gen_sigma(nlayer, depth_smooth, eta, h, theta, b=0., hc=0.,mesh=None):
    """" Generate local sigma coordinates based on # layers, reference surface and depth

        Parameters
        ----------
        nlayer: ndarray
            Veector of size np (number of nodes) giving desired # layers for each node
            in the mesh

        eta: ndarray or float
            reference water level heights at each node at which generation is to occur.

        h: ndarray
            unperturbed depth for each node in the mesh

        theta: float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        b: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth = h + eta
    npoint = len(nlayer)
    theta = np.maximum(1e-4, theta * depth / 100)
    ds = 1. / nlayer
    maxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    maxlevel = np.max(nlevel)
    midlevel = (maxlevel-1)/3
    
    zcor = np.empty((npoint, maxlevel), 'd')
    print("max level %s mid level %s" % (maxlevel,midlevel))
    print("sizes")
    print(h.shape)
    print(npoint)
    print() 
    
    zcor[:,maxlevel - 1]=-h
    old_layer = -h
    speed = np.maximum(0.5,depth_smooth)*0.55 + np.minimum(40.,np.maximum(0.0,depth-40.))/8.
    if True:
        for i in range(maxlevel+1):
            print("layer iteration: %s" % i)
            new_layer = laplace_smooth_with_vel(mesh,old_layer,vel=speed,kappa=2.4,dt=0.05,iter_total=20)
            latest_layer = np.where(new_layer>old_layer, new_layer, old_layer)
            zcor[:,maxlevel-2-i] = latest_layer
            old_layer = latest_layer
        np.savetxt("zcorsave.txt",zcor)
    else:
        zcor = np.loadtxt("zcorsave.txt")
    
    NCUTOFF = 18
    tlayerds=np.ones(NCUTOFF+1,dtype="d")/float(NCUTOFF)
    tlayerds[0]=0.
    tss = -np.cumsum(tlayerds)
    tzz_base = szcoord(tss, NCUTOFF-eta, eta, 2., 0., 1.0)
    print("tzz")
    print(tzz_base)

    
    
    if True:
        zcortwo=zcor[:,0:2].copy()
        zcortwo[:,0] = zcor[:,midlevel]
        zcortwo[:,1] = -h       
        bndthick = zcortwo[:,0] - zcortwo[:,1]
        bndfrac = bndthick/depth
        
        snaptol=np.maximum(0.15,depth*0.01)
        lastsim01=np.absolute(zcortwo[:,0]-zcortwo[:,1])<snaptol
        
        print("@#%#$@^")
        print("zcortwo")
        print(zcortwo[lastsim01,:][10000:10004,:])
        print("depth")
        print(depth[lastsim01][10000:10004])
        zcortwo[lastsim01,0] = zcortwo[lastsim01,1] + snaptol[lastsim01]
        print(zcortwo[lastsim01,:][10000:10004,:])
        notused = np.sum(np.isnan(zcortwo),axis=1)
        nbnd = 2-notused
        bndlevel = nlevel - 2
        nlevel -= notused
        nlevel = np.maximum(2,nlevel)
        zcor[:,:] = np.nan        
        ds = 1./(bndlevel)
        maxnonbndlayer = np.max(bndlevel) +1

        layerds = np.tile(ds, (maxnonbndlayer, 1)).transpose()
        layerds[:, 0] = 0.
        ss = np.cumsum(layerds, axis=1)
    
        np.set_printoptions(threshold=np.inf)
        ss[ss > 1.0001] = np.nan 
        ss[ss > 0.999] = 1.0
        ss = -ss
        for i in range(maxnonbndlayer):
            zcor[:, i] = szcoord(ss[:, i], -zcortwo[:,0] , eta, theta, b, 1.0)
        
        for i in range(npoint):
            if nlevel[i] == 2:
                zcor[i,0] = eta
                zcor[i,1] = -h[i]
                zcor[i,2:-1] = np.nan
                bndlevel[i] = 0
                continue
            try:
                zcor[i,bndlevel[i]:(bndlevel[i]+2)] = zcortwo[i,:]
            except:
                print("Bad 1")
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcortwo.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah")
            try:
                
                #zcor[i,0:(bndlevel[i]+1)] = np.linspace(eta,zcor[i,bndlevel[i]],bndlevel[i]+1)
                if (bndlevel[i] > 0) and (nbnd[i] > 1):
                    zcor[i,bndlevel[i]] = 0.4*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1] + 0.3*zcor[i,bndlevel[i]+1]
                elif (bndlevel[i] > 0) and (nbnd[i] == 0):
                    zcor[i,bndlevel[i]] = 0.7*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1]               
            except:
                print("Bad 2")
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcortwo.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah blah")
            zcor[i,nlevel[i]:-1] = np.nan

    flatten = True
    if flatten:
        for i in range(npoint):
            zb = 0
            stretch = max(0.8, min((depth[i]-4)/36.,1.25))   # was 0.8
            tzz = (tzz_base-eta)*stretch + eta
            for k in range(min(bndlevel[i]-2,NCUTOFF-1),-1,-1):
                if k < 0: break
                tdepth = eta-tzz[k]
                real_depth=depth[i]
                dzlow = (real_depth-tdepth)/(nlevel[i] - 1 - k)
                dzend = tzz[k-1]-tzz[k] if k > 0 else np.nan # todo: is this right?  
                ratio = dzlow/dzend
                distbnd = tzz[k] - zcor[i,bndlevel[i]]
                levsbnd=bndlevel[i] - k
                dzlow = distbnd/levsbnd
                ratio = dzlow/dzend                
                if ratio > 0.7 and ratio < 3.0 and distbnd > 0.01 :
                    zb = k
                    if depth[i]>=7.:
                        zb = min(int(nlevel[i]/2),max(3,k))
                    break
                #print "k=%s tdepth=%s real_depth=%s dzlow=%s dzend=%s nlayer=%s" % (k,tdepth,real_depth,dzlow,dzend,nlayer[i])
            zsigma=None
            if (depth[i] < 35. and depth[i] > 0 and nlayer[i] >=3 and zb >= 0 and zb < nlevel[i]):      
                blend = max(0.,min((35. - depth[i])/10.,1.0)) 
                replace = zcor[i,:].copy()     
                replace[0:(zb+1)]=tzz[0:(zb+1)]
                try:
                    zsigma = np.linspace(tzz[zb],zcor[i,bndlevel[i]],(bndlevel[i]-zb+1))
                    replace[zb:(bndlevel[i]+1)]=zsigma
                except:
                    print("issue: %s %s %s %s " % (depth[i],zb,nlevel[i],tzz[zb]))
                    print(zsigma)
                    print(len (zsigma))
                    print(tzz)  
                if zb>0: replace[zb] = 0.2*replace[zb]+0.4*replace[zb-1]+0.4*replace[zb+1]
                zcor[i,:] = zcor[i,:]*(1.-blend) + replace*blend
            
        #zcor[i,bndlevel[i]] = 0.2*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i+1]] + 0.5*zcor[i,bndlevel[i-1]]
    sigma = ((np.zeros_like(h) + eta).reshape(npoint, 1) - zcor) / \
        depth.reshape(npoint, 1)
    sigma = np.minimum(sigma, 1)

    shallow = 0.2
    for i in range(npoint):
        if depth[i] < shallow or bndfrac[i] > 0.8:
            sigma[i, 0:(nlevel[i])] = np.linspace(0., 1., nlevel[i])
    sigma = -sigma
    print("sigma")
    print(sigma[0,:])
    print(sigma.shape)
    # zcor[depth<0.,:]=np.nan
    nlayer_revised = nlevel - 1
    return sigma,nlayer_revised    
    

def gen_sigma4(nlayer, depth_smooth, eta, h, theta, b=0., hc=0.,mesh=None):
    """" Generate local sigma coordinates based on # layers, reference surface and depth

        Parameters
        ----------
        nlayer: ndarray
            Veector of size np (number of nodes) giving desired # layers for each node
            in the mesh

        eta: ndarray or float
            reference water level heights at each node at which generation is to occur.

        h: ndarray
            unperturbed depth for each node in the mesh

        theta: float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        b: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth = h + eta
    npoint = len(nlayer)
    theta = np.maximum(1e-4, theta * depth / 100)
    ds = 1. / nlayer
    maxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    maxlevel = np.max(nlevel)
    midlevel = (maxlevel-1)/3
    
    zcor = np.empty((npoint, maxlevel), 'd')
    print("max level %s mid level %s" % (maxlevel,midlevel))
    zcor[:,maxlevel - 1]=-h
    old_layer = -h
    speed = np.maximum(0.5,depth_smooth)*0.55 + np.minimum(40.,np.maximum(0.0,depth-40.))/8.
    if False:
        for i in range(maxlevel+1):
            print("layer iteration: %s" % i)
            new_layer = laplace_smooth_with_vel(mesh,old_layer,vel=speed,kappa=2.4,dt=0.05,iter_total=20)
            latest_layer = np.where(new_layer>old_layer, new_layer, old_layer)
            zcor[:,maxlevel-2-i] = latest_layer
            old_layer = latest_layer
        np.savetxt("zcorsave.txt",zcor)
    else:
        zcor = np.loadtxt("zcorsave.txt")
    

    if True:
        zcortwo=zcor[:,0:2].copy()
        zcortwo[:,0] = zcor[:,midlevel]
        zcortwo[:,1] = -h       
        bndthick = zcortwo[:,0] - zcortwo[:,1]
        bndfrac = bndthick/depth
        
        snaptol=np.maximum(0.15,depth*0.01)
        lastsim01=np.absolute(zcortwo[:,0]-zcortwo[:,1])<snaptol
        
        print("@#%#$@^")
        print("zcortwo")
        print(zcortwo[lastsim01,:][10000:10004,:])
        print("depth")
        print(depth[lastsim01][10000:10004])
        zcortwo[lastsim01,0] = zcortwo[lastsim01,1] + snaptol[lastsim01]
        print(zcortwo[lastsim01,:][10000:10004,:])
        notused = np.sum(np.isnan(zcortwo),axis=1)
        nbnd = 2-notused
        bndlevel = nlevel - 2
        nlevel -= notused
        nlevel = np.maximum(2,nlevel)
        zcor[:,:] = np.nan        
        ds = 1./(bndlevel)
        maxnonbndlayer = np.max(bndlevel) +1

        layerds = np.tile(ds, (maxnonbndlayer, 1)).transpose()
        layerds[:, 0] = 0.
        ss = np.cumsum(layerds, axis=1)
    
        np.set_printoptions(threshold=np.inf)
        ss[ss > 1.0001] = np.nan 
        ss[ss > 0.999] = 1.0
        ss = -ss
        for i in range(maxnonbndlayer):
            zcor[:, i] = szcoord(ss[:, i], -zcortwo[:,0] , eta, theta, b, 1.0)
        
        for i in range(npoint):
            if nlevel[i] == 2:
                zcor[i,0] = eta
                zcor[i,1] = -h[i]
                zcor[i,2:-1] = np.nan
                bndlevel[i] = 0
                continue
            try:
                zcor[i,bndlevel[i]:(bndlevel[i]+2)] = zcortwo[i,:]
            except:
                print("Bad 1")
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcortwo.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah")
            try:
                
                #zcor[i,0:(bndlevel[i]+1)] = np.linspace(eta,zcor[i,bndlevel[i]],bndlevel[i]+1)
                if (bndlevel[i] > 0) and (nbnd[i] > 1):
                    zcor[i,bndlevel[i]] = 0.4*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1] + 0.3*zcor[i,bndlevel[i]+1]
                elif (bndlevel[i] > 0) and (nbnd[i] == 0):
                    zcor[i,bndlevel[i]] = 0.7*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1]               
            except:
                print("Bad 2")
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcortwo.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah blah")
            zcor[i,nlevel[i]:-1] = np.nan
        #zcor[i,bndlevel[i]] = 0.2*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i+1]] + 0.5*zcor[i,bndlevel[i-1]]
    sigma = ((np.zeros_like(h) + eta).reshape(npoint, 1) - zcor) / \
        depth.reshape(npoint, 1)
    sigma = np.minimum(sigma, 1)

    shallow = 0.2
    for i in range(npoint):
        if depth[i] < shallow or bndfrac[i] > 0.8:
            sigma[i, 0:(nlevel[i])] = np.linspace(0., 1., nlevel[i])
    sigma = -sigma
    print("sigma")
    print(sigma[0,:])
    print(sigma.shape)
    # zcor[depth<0.,:]=np.nan
    nlayer_revised = nlevel - 1
    return sigma,nlayer_revised

    

def gen_sigma3(nlayer, depth_smooth, eta, h, theta, b=0., hc=0.,mesh=None):
    """" Generate local sigma coordinates based on # layers, reference surface and depth

        Parameters
        ----------
        nlayer: ndarray
            Veector of size np (number of nodes) giving desired # layers for each node
            in the mesh

        eta: ndarray or float
            reference water level heights at each node at which generation is to occur.

        h: ndarray
            unperturbed depth for each node in the mesh

        theta: float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        b: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth = h + eta
    npoint = len(nlayer)
    theta = np.maximum(1e-4, theta * depth / 100)
    ds = 1. / nlayer
    maxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    maxlevel = np.max(nlevel)

    zcor = np.empty((npoint, maxlevel), 'd')
    print("max level %s" % maxlevel)
    zcor[:,maxlevel - 1]=-h
    old_layer = -h
    speed = np.maximum(0.5,depth_smooth)*0.55 + np.minimum(40.,np.maximum(0.0,depth-40.))/8.
    if True:
        for i in range(maxlevel-1):
            print("layer iteration: %s" % i)
            new_layer = laplace_smooth_with_vel(mesh,old_layer,vel=speed,kappa=2.4,dt=0.05,iter_total=20)
            latest_layer = np.where(new_layer>old_layer, new_layer, old_layer)
            zcor[:,maxlevel-2-i] = latest_layer
            old_layer = latest_layer
        np.savetxt("zcorsave.txt",zcor)
    else:
        zcor = np.loadtxt("zcorsave.txt")
    
    midlevel = (maxlevel-1)/2
    if True:
        zcorthree=zcor[:,0:3].copy()
        zcorthree[:,1] = zcor[:,midlevel]
        print("max level %s" % maxlevel)    
        zcorthree[:,2] = zcor[:,(maxlevel-1)]
        bndthick = zcorthree[:,0] - zcorthree[:,2]
        bndfrac = bndthick/depth
        
        snaptol=0.1
        lastsim12=np.absolute(zcorthree[:,1]-zcorthree[:,2])<snaptol
        save=zcorthree[lastsim12,2]
        zcorthree[lastsim12,2] = np.nan
        zcorthree[lastsim12,1] = save
        lastsim01=np.absolute(zcorthree[:,0]-zcorthree[:,1])<snaptol
        save=zcorthree[lastsim01,1]
        zcorthree[lastsim01,1] = np.nan
        zcorthree[lastsim01,0] = save
        notused = np.sum(np.isnan(zcorthree),axis=1)
        nbnd = 3-notused
        bndlevel = nlevel - 3
        nlevel -= notused
        nlevel = np.maximum(2,nlevel)
        zcor[:,:] = np.nan
        
        ds = 1./(bndlevel)
        maxnonbndlayer = np.max(bndlevel) +1

        layerds = np.tile(ds, (maxnonbndlayer, 1)).transpose()
        layerds[:, 0] = 0.
        ss = np.cumsum(layerds, axis=1)
    
        np.set_printoptions(threshold=np.inf)
        ss[ss > 1.0001] = np.nan 
        ss[ss > 0.999] = 1.0
        ss = -ss
        for i in range(maxnonbndlayer):
            zcor[:, i] = szcoord(ss[:, i], -zcorthree[:,0] , eta, theta, b, 1.0)
        
        for i in range(npoint):
            if nlevel[i] == 2:
                zcor[i,0] = eta
                zcor[i,1] = -h[i]
                zcor[i,2:-1] = np.nan
                bndlevel[i] = 0
                continue
            try:
                zcor[i,bndlevel[i]:(bndlevel[i]+3)] = zcorthree[i,:]
            except:
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcorthree.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah")
            try:
                
                #zcor[i,0:(bndlevel[i]+1)] = np.linspace(eta,zcor[i,bndlevel[i]],bndlevel[i]+1)
                if (bndlevel[i] > 0) and (nbnd[i] > 1):
                    zcor[i,bndlevel[i]] = 0.4*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1] + 0.3*zcor[i,bndlevel[i]+1]
                elif (bndlevel[i] > 0) and (nbnd[i] == 0):
                    zcor[i,bndlevel[i]] = 0.7*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i]-1]               
            except:
                print("bndlevel[%s] = %s " % (i,bndlevel[i]))
                print(zcorthree.shape)
                print("nlevel[%s] = %s" % (i,nlevel[i]))
                print("nbnd[%s] = %s" % (i,nbnd[i]))
                print(maxlevel)
                raise ValueError("blah blah")
            zcor[i,nlevel[i]:-1] = np.nan
        #zcor[i,bndlevel[i]] = 0.2*zcor[i,bndlevel[i]] + 0.3*zcor[i,bndlevel[i+1]] + 0.5*zcor[i,bndlevel[i-1]]
    sigma = ((np.zeros_like(h) + eta).reshape(npoint, 1) - zcor) / \
        depth.reshape(npoint, 1)
    sigma = np.minimum(sigma, 1)

    shallow = 1e-3
    for i in range(npoint):
        if depth[i] < shallow or (1.-bndfrac[i])/(nlevel[i]-1) < 0.05:
            sigma[i, 0:(nlevel[i])] = np.linspace(0., 1., nlevel[i])
    sigma = -sigma
    print("sigma")
    print(sigma[0,:])
    print(sigma.shape)
    # zcor[depth<0.,:]=np.nan
    nlayer_revised = nlevel - 1
    return sigma,nlayer_revised    
    
    
    
def gen_sigma2(nlayer, depth_smooth, eta, h, theta, b=0., hc=0.):
    """" Generate local sigma coordinates based on # layers, reference surface and depth

        Parameters
        ----------
        nlayer: ndarray
            Veector of size np (number of nodes) giving desired # layers for each node
            in the mesh

        eta: ndarray or float
            reference water level heights at each node at which generation is to occur.

        h: ndarray
            unperturbed depth for each node in the mesh

        theta: float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        b: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth = h + eta
    npoint = len(nlayer)
    theta = np.maximum(1e-4, theta * depth / 100)
    ds = 1. / nlayer
    maxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    maxlevel = np.max(nlevel)

    zcor = np.empty((npoint, maxlayer + 1), 'd')
    layerds = np.tile(ds, (maxlevel, 1)).transpose()
    layerds[:, 0] = 0.
    ss = np.cumsum(layerds, axis=1)
    
    np.set_printoptions(threshold=np.inf)
    ss[ss > 1.0001] = np.nan
    ss[ss > 0.999] = 1.0
    ss = -ss
    for i in range(maxlevel):
        zcor[:, i] = szcoord(ss[:, i], h, eta, theta, b, 1.0)

        
    NCUTOFF = 18
    tlayerds=np.ones(NCUTOFF+1,dtype="d")/float(NCUTOFF)
    tlayerds[0]=0.
    tss = np.cumsum(tlayerds)
    tzz = (szcoord(tss, NCUTOFF-eta, eta, 2., 0., 1.0) - 1.)*0.8

    #todo: hardwire
    #todo: could cause dz to be too large on bottom?
    #zbreak = np.minimum(12,0.6*nlayer).astype(int)
    #zbreak = np.maximum(zbreak0,6)
    #f = 0.65 # layers below the regular ones must be this fraction of the regular ones in size
    #import pdb
    flatten = True
    if flatten:
        for i in range(npoint):
            zb = 0
            for k in range(min(nlevel[i]-2,NCUTOFF-1),-1,-1):
                tdepth = tzz[k]
                real_depth=depth[i]
                dzlow = (real_depth-tdepth)/(nlevel[i] - 1 - k)
                dzend = tzz[k]-tzz[k-1] if k > 0 else 100000. # todo: is this right?  
                ratio = dzlow/dzend                
                if ratio > 0.6 and ratio < 3.:
                    zb = k
                    break
                #print "k=%s tdepth=%s real_depth=%s dzlow=%s dzend=%s nlayer=%s" % (k,tdepth,real_depth,dzlow,dzend,nlayer[i])
            zsigma=None
            if (depth[i] < 30. and depth[i] > 0 and nlayer[i] >=3 and zb >= 0 and zb < nlevel[i]):      
                blend = max(0.,min((30. - depth[i])/5.,1.0)) 
                replace = zcor[i,:].copy()     
                replace[0:(zb+1)]=eta-tzz[0:(zb+1)] 
                try:
                    zsigma = eta - np.linspace(tzz[zb],depth[i],(nlevel[i]-zb))
                    replace[zb:(nlevel[i])]=zsigma
                except:
                    pass
                    print("issue: %s %s %s %s " % (depth[i],zb,nlevel[i],tzz[zb]))
                    print(zsigma)
                    print(len (zsigma))
                    print(tzz)                    
                if zb>0: replace[zb] = 0.2*replace[zb]+0.4*replace[zb-1]+0.4*replace[zb+1]
                zcor[i,:] = zcor[i,:]*(1.-blend) + replace*blend

                
    sigma = ((np.zeros_like(h) + eta).reshape(npoint, 1) - zcor) / \
        depth.reshape(npoint, 1)
    sigma = np.minimum(sigma, 1)

    for i in range(npoint):
        if depth[i] < 1e-3:
            sigma[i, 0:(nlevel[i])] = np.linspace(0., 1., nlevel[i])
    sigma = -sigma
    print("sigma")
    print(sigma[0,:])
    print(sigma.shape)
    # zcor[depth<0.,:]=np.nan
    return sigma


def gen_sigma_original(nlayer, eta, h, theta, b=0., hc=0.):
    """" Generate local sigma coordinates based on # layers, reference surface and depth

        Parameters
        ----------
        nlayer: ndarray
            Veector of size np (number of nodes) giving desired # layers for each node
            in the mesh

        eta: ndarray or float
            reference water level heights at each node at which generation is to occur.

        h: ndarray
            unperturbed depth for each node in the mesh

        theta: float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        b: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth = h + eta
    npoint = len(nlayer)
    theta = np.maximum(1e-4, theta * depth / 100)
    ds = 1. / nlayer
    maxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    maxlevel = np.max(nlevel)
    zcor = np.empty((npoint, maxlayer + 1), 'd')
    layerds = np.tile(ds, (maxlevel, 1)).transpose()
    layerds[:, 0] = 0.
    ss = np.cumsum(layerds, axis=1)
    np.set_printoptions(threshold=np.inf)
    ss[ss > 1.0001] = np.nan
    ss[ss > 0.999] = 1.0
    ss = -ss
    for i in range(maxlevel):
        zcor[:, i] = szcoord(ss[:, i], h, eta, theta, b, hc)

    sigma = ((np.zeros_like(h) + eta).reshape(npoint, 1) - zcor) / \
        depth.reshape(npoint, 1)
    sigma = np.minimum(sigma, 1)

    for i in range(npoint):
        if depth[i] < 1e-3:
            sigma[i, 0:(nlevel[i])] = np.linspace(0., 1., nlevel[i])
    sigma = -sigma
    # zcor[depth<0.,:]=np.nan
    return sigma



def flip_sigma(sigma):
    """ Flip the ordering of non-nan sigma values.

        The output of get_sigma starts from 0.0, but sigma in vgrid.in from -0.1.
        So it needs to be flipped for further use.

        Parameters
        ----------
        sigma: numpy.ndarray

        Returns
        -------
        numpy.ndarray
            New sigma array that has flipped ordering.
    """
    def flip_no_nan(row):
        length_no_nan = np.argmax(np.isnan(row))
        if not length_no_nan: length_no_nan = len(row)
        row[:length_no_nan] = row[:length_no_nan][::-1]
        return row
    return np.apply_along_axis(flip_no_nan, 1, sigma)

def plot_mesh(ax,x,zcor,startvis,stopvis,c="black",linewidth=1):
    nlevel = np.sum(np.where(np.isnan(zcor),0,1),axis=1)
    nlayer = nlevel - 1
    nquad = np.minimum(nlayer[1:], nlayer[:-1])
    nprism = np.maximum(nlayer[1:], nlayer[:-1])
    ntri = nprism - nquad
    nel = len(nquad)
    maxlevel = zcor.shape[1]
    assert len(x) == len(nlevel)
    for i in range(maxlevel):
        ax.plot(x[startvis:stopvis],zcor[startvis:stopvis,i],c=c,linewidth=linewidth)
    for el in range(startvis,stopvis-1):
        ilo = el
        ihi = el + 1
        nq = nquad[el]
        npris = nprism[el]
        if nq == npris:
            continue

        # print "%s %s" % (nlevel[el],nlevel[el+1])
        for k in range(nq, npris + 1):
            zlo = zcor[ilo, min(k, nlayer[ilo])]
            zhi = zcor[ihi, min(k, nlayer[ihi])]
            # print "%s %s %s"  % (k,nlayer[ilo],nlayer[ihi])
            # print "%s %s %s %s" % (x[ilo],x[ihi],zlo,zhi)
            ax.plot((x[ilo], x[ihi]), (zlo, zhi), c=c)
    ax.set_xlim(x[startvis], x[stopvis - 1])


def sigma_z(sigma, eta, h):
    npoint = sigma.shape[0]
    if not (type(eta) == np.ndarray or type(eta) == float):
        raise ValueError("Eta must be a float or numpy array")
    if type(eta) == float:
        eta = h * 0. + eta
    eta_arr = eta.reshape(npoint, 1)
    depth = eta_arr + h.reshape(npoint, 1)
    zcor = eta_arr + depth * sigma
    zcor[depth[:, 0] < 0., :] = np.nan
    return zcor


def z_sigma(zcor):
    surf = zcor[:,0]
    depth = surf - np.min(zcor,axis=1)
    frac = (zcor - surf[:,np.newaxis])/depth[:,np.newaxis]
    return frac
    


def example():

    # Several example csv files are provided"
    exfile = "test/testdata/transect2a.csv"
    exfile = "test/testdata/ex5.csv"
    transect = np.loadtxt(exfile, delimiter=",", skiprows=1)
    x = transect[:, 0]      # x positions for xsect. These have no analog in 3D
    h0 = -transect[:, 1]     # nominal depth, as in hgrid.gr3
    nx = len(h0)

    eta = 2.0  # Reference height at which assessed. Aim on the high side
    minlayer = 1
    maxlayer = 4
    maxlayer = np.zeros(nx, 'i') + maxlayer
    maxlevel = maxlayer + 1
    depth = eta + h0
    theta = 2
    b = 0.
    hc = 0

    nlayer = default_num_layers(eta, h0, minlayer, maxlayer)
    #nlayer = gaussian_filter1d(nlayer,sigma=3)
    #nlayer = gaussian_filter1d(nlayer,sigma=3)

    sigma = gen_sigma(nlayer, eta, h0, theta, b, hc)
    print(sigma)
    zcor0 = sigma_z(sigma, eta, h0)
    print(x)
    print(zcor0)

    eta1 = 2.5
    zcor1 = sigma_z(sigma, eta1, h0)

    import matplotlib.pyplot as plt
    fig, (ax0, ax1) = plt.subplots(2, 1, sharex=True, sharey=True)
    plot_mesh(ax0, x, zcor0, 0, len(x), c="red")
    plot_mesh(ax1, x, zcor1, 0, len(x), c="blue")
    ax0.plot(x, -h0, linewidth=2, c="black")
    ax1.plot(x, -h0, linewidth=2, c="black")
    plt.show()


if __name__ == '__main__':
    example()
