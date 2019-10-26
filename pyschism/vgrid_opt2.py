# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 16:28:10 2016

@author: eli
"""
from scipy.ndimage.filters import gaussian_filter1d
from lsc2 import *

def incr_grad(grad,i,k,val,ndx):
    n = ndx[i,k]
    if n >=0:
        grad[n] += val
    return grad

def targeth2inv(zbar,eta):
    href = 1. + (eta-zbar)/60.
    href2inv = 1./(href*href)
    #print "zbar= %s  href= %s  href2inv=%s" % (zbar,href,href2inv)
    #href2inv = np.maximum(0.5,np.minimum(1.,href2inv))
    #print href2inv
    href2inv = 1.
    return href2inv

def triweight(n):
    tw=max(3,float(n)/2.)
    return 1.0  # todo



def meshobj(xvar,zcorig,mesh,nlayer,ndx,eta,depth,gradmat,
            sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
            href_hess, grad_hess,laplace_hess):
    import pdb
    obj = 0.

    #print "objective"
    nodes = mesh.nodes
    nx = nodes.shape[0]
    edges = mesh.edges
    nside = edges.shape[0]

    zcor = zcorig.copy()
    zcor[ndx>=0] = xvar

    nlevel = nlayer + 1
    zdiff = np.diff(zcor,axis=1)
    href = -np.diff(zcorig,axis=1)
    href2inv2 = 1./(href*href)
    href2inv2[np.isinf(href2inv2)] = 0.

    # vertical spacing
    zdiff2norm = href2inv2*zdiff**2.
    zdiff2norm[nodemasked,:] = 0.
    obj += np.sum(zdiff2norm)


    # minimum spacing
    lht = -zdiff-(foldfrac*href)
    #lht = np.nan_to_num(lht)
    bad = np.minimum(lht,0.)
    bad[nodemasked,:] = 0.
    obj += np.sum(bad*bad)*foldwgt


    grad = gradmat.dot(zcor)
    obj += np.sum(grad*grad)*dx2fac

    laplace = ata.dot(zcor)
    #laplace[nodemasked,:]= 0.
    laplace[np.isnan(laplace)] = 0.
    #laplace[(ndx<0) | np.isnan(laplace)] = 0.
    laplacesum = np.sum(laplace*laplace*curvewgt)
    obj += laplacesum

    return obj/2.



def meshgrad(xvar,zcorig,mesh,nlayer,ndx,eta,depth,gradmat,
             sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess, grad_hess,laplace_hess):
    grad = np.zeros_like(xvar)

    nodes = mesh.nodes
    nx = nodes.shape[0]
    edges = mesh.edges
    nside = edges.shape[0]

    zcor = zcorig.copy()
    zcor[ndx>=0] = xvar


    zdiff = np.diff(zcor,axis=1)
    href = -np.diff(zcorig,axis=1)
    href2inv2 = 1./(href*href)
    href2inv2[np.isinf(href2inv2)] = 0.
    nlevel = nlayer + 1

    # vertical spacing
    dzdiff2norm = np.zeros_like(zcor)
    dd = zdiff*href2inv2
    #dd = np.nan_to_num(dd)
    dzdiff2norm[:,0] = -dd[:,0]
    dzdiff2norm[:,1:] = dd
    dzdiff2norm[:,1:-1] -= dd[:,1:]
    dzdiff2norm[nodemasked,:] = 0.
    grad += dzdiff2norm[ndx>=0]    # todo: flatten not neededs


    # minimum vertical spacing
    dd = -zdiff-(foldfrac*href)
    #dd = np.nan_to_num(dd)
    dd = np.minimum(dd,0.)
    dzdiff2norm[:] = 0.
    dzdiff2norm[:,0] = -dd[:,0]
    dzdiff2norm[:,1:] = -dd
    dzdiff2norm[:,1:-1] += dd[:,1:]
    dzdiff2norm[nodemasked,:] = 0.
    grad += dzdiff2norm[ndx>=0].flatten()*foldwgt


    gradcost = gradmat.dot(zcor)
    dzdiff3 = gradmat.transpose().dot(gradcost)*dx2fac
    #print "pre dzdiff3"
    #print grad
    #print "dzdiff3"
    #print dzdiff3[ndx>=0]
    grad += dzdiff3[ndx>=0]  # todo: flatten not needed
    #print "now the matrix"
    #print gradmat


    laplace = ata.dot(zcor)
    #print "laplace evaluation"
    #print laplace
    #laplace[nodemasked,:] = 0.
    # todo: does the Hessian agree with this? What limits?
    laplace[np.isnan(laplace)] = 0.
    #laplacegrad = (laplace.transpose().dot(ata.toarray())).transpose()*curvewgt
    laplacegrad = ata.transpose().dot(laplace*curvewgt)
    grad += laplacegrad[ndx>=0]  # todo: flatten not needed
    return grad


def meshessp(xvar,p,zcorig,mesh,nlayer,ndx,eta,depth,gradmat,sidelen2,
             nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess,grad_hess,laplace_hess):
    import pdb
    obj = 0.

    #print "objective"
    nodes = mesh.nodes
    nx = nodes.shape[0]
    edges = mesh.edges
    nside = edges.shape[0]

    zcor = zcorig.copy()
    zcor[ndx>=0] = xvar

    nlevel = nlayer + 1
    zdiff = np.diff(zcor,axis=1)
    href = -np.diff(zcorig,axis=1)

    #print "href hessian dimensions: %s,%s" % href_hess.shape
    #print "grad hessian dimensions: %s,%s" % grad_hess.shape
    #print "laplace hess dimensions: %s,%s" % laplace_hess.shape

    # todo: this is OK for testing, but eventually sum them?
    prod = href_hess.dot(p)

    prod += grad_hess.dot(p)
    prod += (laplace_hess).dot(p)

    # The penalty for folding is still quadratic, but has a min() in it so
    # it is state dependent.
    folded_below = (ndx >= 0) # just a starting point, not the folded computation (see below)
    folded_above = (ndx >= 0)
    folded_below[:,:-1] &= ((-zdiff - foldfrac*href) < 0)
    folded_above[:,1:]  &= ((-zdiff - foldfrac*href) < 0)


    prod[ndx[folded_below].ravel()] += p[ndx[folded_below].ravel()]*foldwgt
    prod[ndx[folded_above].ravel()] += p[ndx[folded_above].ravel()]*foldwgt

    prod[ndx[folded_above].ravel()] -= p[ndx[folded_above].ravel() - 1]*foldwgt
    ndxf = ndx[folded_below].ravel()
    if len(ndxf) > 0 and ndxf[-1] == (len(prod)-1): ndxf = ndxf[:-1]
    prod[ndxf] -= p[ndxf + 1]*foldwgt
    return prod

def hess_base(xvar,zcorig,mesh,nlayer,ndx,eta,depth,gradmat,sidelen2,
              nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac):
    import pdb
    from scipy.sparse import coo_matrix,diags

    obj = 0.

    #print "objective"
    nodes = mesh.nodes
    nx = nodes.shape[0]
    sides = mesh.edges
    nside = sides.shape[0]

    zcor = zcorig.copy()
    zcor[ndx>=0] = xvar
    maxlevel = zcor.shape[1]

#   hessian based on gradients along edges
# todo: forgot the layers so way too small same for laplacian
# dxinv?

    edgesgood = mesh.edges[~sidemasked]
    first = edgesgood[:,0]
    second = edgesgood[:,1]
    # get indices on each side. Some may be <0 (not optimized, top level or below bed)

    edgelen2inv = np.tile(1./sidelen2[~sidemasked],(maxlevel,1)).transpose()
    ix = ndx[first,:].ravel()        # nedge by maxlevel

    jy = ndx[second,:].ravel()
    diag = np.hstack((ix[ix>=0],jy[jy>=0]))

    # Any valid (ndx>=0) index on ix or jy gets a positive diagonal entry
    # regardless of whether it is joined to another. Duplicates are possible at an index
    # depending on the valence of the node.
    icross = ix[(ix>=0) & (jy>=0)]
    jcross = jy[(ix>=0) & (jy>=0)]
    indx = np.hstack((diag,icross))
    jndx = np.hstack((diag,jcross))

    data = np.hstack((edgelen2inv.ravel()[ix >= 0],
                      edgelen2inv.ravel()[jy >= 0],
                     -edgelen2inv.ravel()[(ix>=0) & (jy>=0)]))

    # Negative cross terms occur in places where both indices are optimization variables,
    grad_hess = coo_matrix((data,(indx,jndx))).tocsr()


#   hessian based on interfacial heights

    zdiff = np.diff(zcor,axis=1)
    href = -np.diff(zcorig,axis=1)
    href2inv2 = 1./(href*href)
    href2inv2[np.isinf(href2inv2)] = 0.
    diag1 = np.zeros_like(zcor)
    diag2= np.zeros_like(zcor)
    diag3 = np.zeros_like(zcor)
    diag1[:,:-1] += href2inv2
    diag1[:,1:] += np.where(ndx[:,1:]>=0,href2inv2,0.)
    diag2[:,0:-1] -= np.where((ndx[:,1:] >= 0) & (ndx[:,:-1] >=0), href2inv2,0.)


    href_hess = diags((diag1[ndx>=0].ravel(),
                       diag2[ndx>=0].ravel(),
                       diag2[ndx>=0].ravel()),[0,1,-1]).tocsr()


    ix = ndx[first,:].ravel()        # nedge by maxlevel
    jy = ndx[second,:].ravel()
    diag = np.hstack((ix[ix>=0],jy[jy>=0]))

    # Any valid (ndx>=0) index on ix or jy gets a positive diagonal entry
    # regardless of whether it is joined to another. Duplicates are possible at an index
    # depending on the valence of the node.
    icross = np.hstack((ix[(ix>=0) & (jy>=0)],jy[(ix>=0) & (jy>=0)]))
    jcross = np.hstack((jy[(ix>=0) & (jy>=0)],ix[(ix>=0) & (jy>=0)]))
    indx = np.hstack((diag,icross))
    jndx = np.hstack((diag,jcross))

    # Create weights for (i,i), (j,j),(i,j) and (j,i)
    data = dx2fac*np.hstack((edgelen2inv.ravel()[ix >= 0],
                             edgelen2inv.ravel()[jy >= 0],
                     -edgelen2inv.ravel()[(ix>=0) & (jy>=0)],
                     -edgelen2inv.ravel()[(ix>=0) & (jy>=0)]))

    # Negative cross terms occur in places where both indices are optimization variables,
    grad_hess = coo_matrix((data,(indx,jndx))).tocsr()


    nnode = mesh.n_nodes()
    ii = []
    jj = []
    data = []
    from scipy.spatial.distance import cdist
    #import pdb
    #pdb.set_trace()
    for i in np.arange(nnode):
        edgecon = mesh.get_edges_from_node(i)
        # Get connected edges
        e = [xedge for xedge in edgecon if not sidemasked[xedge]]
        if len(e) == 0: continue
        # and the corresponding "other" node on each edge
        other = [(sides[nn][0] if sides[nn][0] != i else sides[nn][1]) for nn in e]

        dists = cdist(nodes[i,0:2].reshape(1,2),nodes[other,0:2])
        scaledist = np.max(dists)
        wgt = (np.ones_like(dists)).ravel()/scaledist
        sumwgt = np.sum(wgt)
        curvewgtcol = curvewgt[i,:].ravel()

        ix = ndx[i,:].ravel()
        o1 = sumwgt*wgt
        o2 = curvewgtcol*sumwgt*sumwgt
        nother2 = o2[ix>=0]   # np.repeat(o2,ix[ix>=0].shape[0])


        ii.append(ix[ix>=0])
        jj.append(ix[ix>=0])
        data.append(nother2)


        for jcount,j in enumerate(other):
            jy = ndx[j,:].ravel()
            diag = jy[jy>=0]
            ii.append(diag)
            jj.append(diag)
            jdat = curvewgtcol[jy>=0]*wgt[jcount]*wgt[jcount]
            data.append(jdat)

            icross0 = ix[(ix>=0) & (jy>=0)]
            jcross0 = jy[(ix>=0) & (jy>=0)]
            icross1 = jy[(ix>=0) & (jy>=0)]
            jcross1 = ix[(ix>=0) & (jy>=0)]

            ii.append(icross0)
            jj.append(jcross0)
            data.append(-o1[jcount]*curvewgtcol[(ix>=0) & (jy>=0)])
            ii.append(icross1)
            jj.append(jcross1)
            data.append(-o1[jcount]*curvewgtcol[(ix>=0) & (jy>=0)])
            for jothcount,joth in enumerate(other):
                if joth == j: continue
                jjy = ndx[joth,:].ravel()
                jjvalid =  (jy >= 0) & (jjy >= -0)
                nothercross = np.count_nonzero(jjvalid)
                ii.append( jy[jjvalid] )
                jj.append( jjy[jjvalid] )
                data.append(wgt[jothcount]*wgt[jcount]*curvewgtcol[jjvalid])


    ii = np.concatenate(ii)
    jj = np.concatenate(jj)
    data = np.concatenate(data)
    laplace_hess = coo_matrix((data,(ii,jj))).tocsr()
    #laplace_hess = ata.transpose().dot(ata).transpose()
    return href_hess, grad_hess, laplace_hess


def index_interior(mat,nodemasked,nlevel=None):
    if nlevel is None:
        """ Detect using nans """
        nlevel = np.sum(~np.isnan(mat),axis=1)
    nlayer=nlevel-1
    ndx=np.zeros(mat.shape,'i')-1
    cum = 0
    #todo: changed this from range(1,mat.shape-1)
    for i  in range(mat.shape[0]):
        if nlayer[i] > 1 and not nodemasked[i]:
            ndx[i,1:(nlayer[i])] = np.arange(cum,cum+nlayer[i]-1)
            cum +=(nlayer[i]-1)
    return nlayer,ndx

def test_vgrid_spacing(zcor,zcorig,nodemasked,foldfrac):
    zdiff = -np.diff(zcor,axis=1)
    href = -np.diff(zcorig,axis=1)
    #infeasible = zdiff < 0.
    lht = zdiff-(foldfrac*href)
    bad = np.minimum(lht,0.)
    bad[nodemasked,:] = 0.

    wherebad = np.where((bad<0.) & (href> 1e-14))
    print("Any bad?")
    print(wherebad)
    print(np.count_nonzero(wherebad))

    #print nlayer[7]
    #print nlayer[23]
    #print zdiff[wherebad[0:5,],:]
    #print



def mesh_opt(zcor,mesh,nlayer,ndx,eta,depth,gradmat,sidelen2,
             nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess, grad_hess,laplace_hess,maxiter=8000):
    from scipy.optimize import minimize
    zcorig = zcor.copy()
    xvar = zcorig[ndx>=0].flatten()
    #zmin = np.nanmin(zcorig,axis = 1)
    #deptharr = np.tile(zmin,(zcorig.shape[1],1)).T
    #zcorig = np.where(np.isnan(zcorig),deptharr,zcorig)


    objstart = meshobj(xvar,zcorig,mesh,nlayer,ndx,eta,depth,gradmat,
            sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
            href_hess, grad_hess,laplace_hess)
    print("Starting obj value: %s" % objstart)
    #import pdb
    #pdb.set_trace()


    result = minimize(meshobj,xvar,args=(zcorig,mesh,nlayer,ndx,eta,
                                         depth,gradmat,
                                         sidelen2,nodemasked,sidemasked,ata,
                                         dx2fac,curvewgt,foldwgt,foldfrac,
                                         href_hess, grad_hess,laplace_hess),
                                         options={"maxiter": maxiter,"xtol":1e-8},
                                         tol=0.001,method= "Newton-CG",
                                         jac=meshgrad,hessp=meshessp)



    zcornew=zcorig.copy()
    zcornew[ndx>=0] = result.x
    test_vgrid_spacing(zcornew,zcorig,nodemasked,foldfrac*0.75)


    print("Optimization succeeded: %s with objective value %s" % (result.success,result.fun))
    print("Number iterations: %s Func: %s  Grad: %s" % (result.nit,result.nfev,result.njev))
    print("Gradient had bad values: %s" % np.any(np.isnan(result.jac)))
    print(result.message)
    return zcornew


def fix_depth(zcor,zcornew,x):
    #Adjust for changes in absolute heights.
    newsurf = zcornew[:,0]
    newbed = np.nanmin(zcornew,axis=1)
    newdepth = newsurf-newbed
    surf = zcor[:,0]
    bed = np.nanmin(zcor,axis=1)
    depth = surf-bed
    ratio = (depth/newdepth)
    dhn = np.diff(zcornew,axis=1)*ratio[:,np.newaxis]
    zcornew=zcor.copy()
    zcornew[:,1:]=dhn
    zcornew = np.cumsum(zcornew,axis=1)
    return zcornew

def smooth_heights(zcor,x,wgt=0.2):
    nx = len(x)
    dx = np.diff(x)
    weight_lo = 0.5+0*dx[:-1] # 1/dx[:-1]
    weight_hi = 0.5+0*dx[1:] # 1/dx[1:]

    weight = weight_lo+weight_hi
    weight_lo /= weight
    weight_hi /= weight

    dh = np.diff(zcor,axis=1)
    dh[np.isnan(dh)] = 0. # fill vlues
    ddh = np.diff(dh,axis=0)
    incr = ddh[1:,:]*weight_hi[:,np.newaxis]-ddh[:-1,:]*weight_lo[:,np.newaxis]
    dh2 = dh[1:-1,:]+wgt*incr
    dh2[dh[1:-1,:]==0.]=0.
    zcornew = zcor.copy()
    zcornew[1:-1,1:]=dh2
    zcornew[1:-1,:]=np.cumsum(zcornew[1:-1,:],axis=1)
    zcornew = fix_depth(zcor,zcornew,x)
    return zcornew


def laplace2(mesh,nodemasked,sidemasked):
    """produces a 2d matrix"""
    #import pdb
    from scipy.sparse import coo_matrix
    from scipy.spatial.distance import cdist

    nnode = mesh.n_nodes()
    sides = mesh.edges
    nodes = mesh.nodes
    ii = []
    jj = []
    data = []

    for i in np.arange(nnode):
        #if nodemasked[i]: continue
        edgeall = mesh.get_edges_from_node(i)
        e = [xedge for xedge in edgeall if not sidemasked[xedge]]
        if len(e) == 0: continue
        other = [i]+[(sides[nn][0] if sides[nn][0] != i else sides[nn][1]) for nn in e ]
        ii.append(np.repeat(i,1+len(other)))
        jj.append([i]+other)
        dists = cdist(nodes[i,0:2].reshape(1,2),nodes[other,0:2])
        scaledist = np.max(dists)
        #wgt = (np.ones_like(dists)/maxdist).ravel()
        wgt = np.ones_like(dists).ravel()/scaledist
        sumwgt = np.sum(wgt)
        #data.append(wgt)
        #wgt = np.ones(1+len(other))
        data.append([-sumwgt])
        data.append(wgt)
    ii = np.concatenate((ii))
    jj = np.concatenate((jj))
    data =np.concatenate((data))
    weightcoo = coo_matrix((data.ravel(),(ii.ravel(),jj.ravel())),shape=(nnode,nnode))
    weightcsr = weightcoo.tocsr() # todo: for debug
    #weightcsr2 = weightscsr.transpose().dot(weightscsr)
    return weightcsr

def gradient_matrix(mesh,sidedist2,sidemasked):
    from scipy.sparse import coo_matrix
    edges = mesh.edges[~sidemasked]
    edgesgood = mesh.edges[~sidemasked]
    nedge = edgesgood.shape[0]
    first = edgesgood[:,0]
    second = edgesgood[:,1]
    s2 = 1./np.sqrt(sidedist2[~sidemasked])
    idim = np.concatenate((np.arange(nedge),np.arange(nedge)))
    jdim = np.concatenate((first,second))
    data = np.concatenate((s2,-s2))

    gradmat = coo_matrix((data,(idim,jdim)),shape=(nedge,mesh.nodes.shape[0]))
    return gradmat.tocsr()


def example():
    import schism_mesh
    dx2fac = 10.  #1000.
    curvewgt = 100. #0.01 # 0.05 #0.05 #0.05 #0.03 #800000
    foldwgt = 22. #1.e3
    foldfrac = 0.35
    maxiter = 200
    #gr3name = "gg_cut.gr3"
    gr3name = "victoria.gr3"
    #gr3name= "hgrid.gr3"

    mesh = schism_mesh.read_mesh(gr3name)

    nodes = mesh.nodes
    edges = mesh.edges


    x =nodes[:,0:2]    # x positions for xsect. These have no analog in 3D
    h0=nodes[:,2]     # nominal depth, as in hgrid.gr3
    nx = x.shape[0]
    sidelen2 = np.sum((x[edges[:,1],:] - x[edges[:,0],:])**2.,axis=1)


    eta = 1.0  # Reference height at which assessed. Aim on the high side
    minlayer=4
    maxlayer=8
    maxlayer=np.zeros(nx,'i')+maxlayer
    maxlevel = maxlayer+1
    depth = eta+h0
    theta = 2
    b=0.
    hc = 0

    nlayer_default = default_num_layers(eta,h0,minlayer,maxlayer)
    nlayer = deap_numlayer(depth,mesh.edges,nlayer_default,float(minlayer))

    nodemasked = depth < 1.0
    sidemasked = nodemasked[edges[:,0]] | nodemasked[edges[:,1]]
    gradmat = gradient_matrix(mesh,sidelen2,sidemasked)



    print("Nodes excluded: %s" % np.sum(nodemasked))
    print("Sides excluded: %s" % np.sum(sidemasked))

    sigma = gen_sigma(nlayer,eta,h0,theta,b,hc)
    zcor = sigma_z(sigma,eta,h0)


    nlayer,ndx = index_interior(zcor,nodemasked)
    ata = laplace2(mesh,nodemasked,sidemasked)



    xvar = zcor[ndx>=0].flatten()
    xvarbase=xvar.copy()



    zcorold = zcor.copy()
    zmin = np.nanmin(zcorold,axis = 1)
    deptharr = np.tile(zmin,(zcorold.shape[1],1)).T
    zcorold = np.where(np.isnan(zcorold),deptharr,zcorold)
    href_hess, grad_hess,laplace_hess = hess_base(xvar,zcorold,mesh,nlayer,ndx,
                                                  eta,depth,gradmat,sidelen2,
                                                  nodemasked,sidemasked,ata,
                                                  dx2fac,curvewgt,foldwgt,foldfrac)


    zcor2 = mesh_opt(zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
                     sidelen2,nodemasked,sidemasked,ata,
                     dx2fac,curvewgt,foldwgt,foldfrac,
                     href_hess, grad_hess,laplace_hess)





#todo: still haven't tested min # layers = 1
def test_gradients():
    import schism_mesh

    dx2fac = 0.0  #1000.
    curvewgt = 0.02  #0.01 # 0.05 #0.05 #0.05 #0.03 #800000
    foldwgt = 1.e3
    foldfrac = 0.5
    maxiter = 4000
    gr3name = "test.gr3"
    delta = 1e-6

    mesh = schism_mesh.read_mesh(gr3name)
    nodes = mesh.nodes
    edges = mesh.edges
    x =nodes[:,0:2]    # x positions for xsect. These have no analog in 3D
    h0=nodes[:,2]     # nominal depth, as in hgrid.gr3
    nx = x.shape[0]
    sidelen2 = np.sum((x[edges[:,1],:] - x[edges[:,0],:])**2.,axis=1)

    eta = 1.0  # Reference height at which assessed. Aim on the high side
    minlayer=3
    maxlayer=6
    maxlayer=np.zeros(nx,'i')+maxlayer
    maxlevel = maxlayer+1
    depth = eta+h0
    theta = 2
    b=0.
    hc = 0


    nodemasked = depth < 1.0
    sidemasked = nodemasked[edges[:,0]] & nodemasked[edges[:,1]]
    gradmat = gradient_matrix(mesh,sidelen2,sidemasked)

    print("Nodes excluded: %s" % np.sum(nodemasked))
    print("Sides excluded: %s" % np.sum(sidemasked))

    #sigma = gen_sigma(nlayer,eta,h0,theta,b,hc)
    # todo: this has excluded node, but not side
    zcor = np.array([[1.0,-0.2,np.nan,np.nan,np.nan],
                     [1.0,-0.3,-1.8,np.nan,np.nan],
                     [1.0,-0.1,-1.2,-2.3,np.nan],
                     [1.0,-0.2,-1.4,-2.6,-3.8],
                     [1.0,-0.1,-1.2,-2.3,np.nan],
                     [1.0,0.8,0.6,0.4,np.nan]])

    #todo: nlayer is being calculated several times
    nlayer,ndx = index_interior(zcor,nodemasked)
    assert np.all(nlayer == [1,2,3,4,3,3])

    #this is a 2D quantity
    ata = laplace2(mesh,nodemasked,sidemasked)


    xvar = zcor[ndx>=0].flatten()
    xvarbase=xvar.copy()

    zcorold = zcor.copy()
    zmin = np.nanmin(zcorold,axis = 1)
    deptharr = np.tile(zmin,(zcorold.shape[1],1)).T
    zcorold = np.where(np.isnan(zcorold),deptharr,zcorold)
    curvewgt = np.zeros_like(zcorold)+curvewgt
    curvewgt[2,:]=0.1
    curvewgt[3:,0:2]=0.2
    href_hess, grad_hess,laplace_hess = hess_base(xvar,zcorold,mesh,nlayer,ndx,
                                                  eta,depth,gradmat,sidelen2,
                                                  nodemasked,sidemasked,ata,
                                                  dx2fac,curvewgt,foldwgt,foldfrac)

    xvar[5] = -2.8
    xvar[6] = 0.8
    xvar[7]= 0.5
    obj1 = meshobj(xvar,zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
            sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
            href_hess, grad_hess,laplace_hess)
    grad1 = meshgrad(xvar,zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
             sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess, grad_hess,laplace_hess)
    print("calc hessian")
    big_hess = grad_hess + href_hess + laplace_hess
    print(big_hess)
    xvarbase=xvar.copy()
    numgrad = np.zeros(8)
    for i in range(8):
        xvar = xvarbase.copy()
        xvar[i] += delta
        obj2 = meshobj(xvar,zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
            sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
            href_hess, grad_hess,laplace_hess)
        grad2 = meshgrad(xvar,zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
             sidelen2,nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess, grad_hess,laplace_hess)
        numgrad[i] = (obj2-obj1)/delta

        print("num hessian (%s)" % i)
        print((grad2-grad1)/delta)
    xvar = xvarbase.copy()
    p = np.array([0.,0.,0.,0.,0.,0.,0.,0.])
    jtest = 7
    p[jtest]=1.
    hessp = meshessp(xvar,p,zcorold,mesh,nlayer,ndx,eta,depth,gradmat,sidelen2,
             nodemasked,sidemasked,ata,dx2fac,curvewgt,foldwgt,foldfrac,
             href_hess,grad_hess,laplace_hess)

    print("\n**hessian element [%s]" % jtest)
    print(hessp)
    print("\ngradient")
    print(numgrad)
    print(grad1)



if __name__ == '__main__':
    #example()
    test_gradients()
