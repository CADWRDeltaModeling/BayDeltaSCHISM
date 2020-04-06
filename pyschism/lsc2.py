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

showlist = [0,1,2] #,419,28778,28923,237892,237893,232311]
showlist = [7942, 7967, 7968, 7969, 7972]
showlist = [67, 71, 72, 73, 76]
showlist = [29914, 29915,30094,30774]
showlist = [16948,16949,207525,207526]
showlist = [245201]

def szcoord(s, h, eta, theta, b, hc):
    thetaterm = np.tanh(0.5 * theta)
    thetavec = theta
    c = (1 - b) * np.sinh(thetavec * s) / np.sinh(thetavec)\
        + 0.5 * b * (np.tanh(thetavec * (s + 0.5)) - thetaterm) / thetaterm
    z = eta * (1 + s) + hc * s + (h - hc) * c
    return z




def default_num_layers0(total_ref_depth, minlayer, maxlayer):
    return np.minimum(np.maximum(minlayer, total_ref_depth.astype('i')), maxlayer).astype('f')



class CubicLSC2MeshFunction(object):

    def __init__(self):
        #self.params = np.array([0.6,0.066,0.002,1e-5])
        self.params = np.array([0.5,0.055,0.002,1e-5])

    def density(self,x,tlev):
        p = self.params
        return p[3]*tlev**3.+ p[2]*tlev**2. + p[1]*tlev + p[0]

    def depth(self,x,tlev):
        p = self.params
        d = p[3]*tlev**4./4.+ p[2]*tlev**3./3. + p[1]*tlev**2./2. + p[0]*tlev
        return d



class BilinearMeshDensity(object):

    def __init__(self):
        #self.params = np.array([0.6,0.066,0.002,1e-5])
        self.params = np.array([0.5,0.012,0.1,1e-5])
        self.params = np.array([0.5,0.005,0.09,-8.5e-5])
        self.params = np.array([0.5,0.005,0.07,-3.e-5])


    def density(self,z,h,x):
        (a,b,c,d) = self.params
        return a + b*h + c*z + d*z*h

    def depth(self,t,h,x):
        (a,b,c,d) = self.params
        m = (a + b*h)
        n = (c+d*h)
        opnd = np.outer(t,n) 
        retval = ((np.exp(opnd)-1)*m/n).T
        return retval




def default_num_layers(x,eta, h0, minlayer, maxlayer,dz_target,meshfun,maxlev=100):
    """ Returns the number of layers that, according to meshfun, gives a depth matching eta + h0
        In the (likely) case of inexact fit) the lower bound n- of the number of layers
        not yet outfitted for variation in x"""
    totaldepth = eta + h0
    levs = np.arange(0.,float(maxlev))
    levdepths = meshfun.depth(levs,totaldepth,x)
    # todo: redo with ndindex
    nlayer = np.zeros_like(totaldepth)
    npoint = len(nlayer)
    for inode in range(npoint):
        #hi_ndx is the index that is equal or greater
        nlayer[inode] = np.maximum(1,np.searchsorted(levdepths[inode,:],totaldepth[inode]))
    print("Maximum reference depth: {} Unrestricted max layer: {}".format (np.max(totaldepth),np.max(nlayer)))
    nlayer = np.minimum(np.maximum(
        minlayer, (nlayer).astype('i')), maxlayer) #.astype('f')    
    print("# small minlayer = %s " % np.count_nonzero(minlayer<=1.))
    print("Any small number layers: %s at index %s" % (np.amin(nlayer), np.argmin(nlayer)))   
    return nlayer.astype("i")


def example3():
    eta = 1.5
    h0 = np.array([2.,-1.,-1.8,0.,2.,5.,20.,28.])
    minlayer = np.array([3,1,2,5,2,2,2,2])
    maxlayer = np.array([5,5,5,5,5,8,32,32])
    meshfun = BilinearMeshDensity()
    nlayer = default_num_layers(0.,eta,h0,minlayer,maxlayer,0.,meshfun)
    print(nlayer)


def example2():
    eta = 1.5
    h0 = np.array([3.58,1.,0.25,0.,4.5,107.0,120.])
    minlayer = np.array([3,4,4,5,8,12,12])
    maxlayer = np.array([8,8,8,10,8,38,38])
    meshfun = BilinearMeshDensity()
    nlayer = default_num_layers(0.,eta,h0,minlayer,maxlayer,0.,meshfun)
    sigma = gen_sigma(nlayer,eta,h0,None,meshfun)


def mesh_function_depths(nlayer, depth, mesh, meshfun):
    
    print("Entering mesh_functino_depths")
    for inode in showlist:
        print("inode={} depth={} nlayer={}".format(inode,depth[inode],nlayer[inode]))
    
    
    
    npoint = len(nlayer)
    globalmaxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    globalmaxlevel = globalmaxlayer + 1

    meshfundepths = np.empty((npoint, globalmaxlevel), 'd')

    # sigmadepths is the uniform mesh implied by applying the layer thickness over the depth
    sigmadepths = np.empty((npoint, globalmaxlevel), 'd')
    hsig = np.empty(npoint,dtype='d')



    levs = np.arange(globalmaxlevel) # The plus two is to protect against situations when all nlayer == 0
    x = np.zeros(npoint,dtype="d")

    x = np.zeros(npoint)
    for inode in range(npoint):
        meshfundepths[inode,:]=meshfun.depth(levs,depth[inode],x)

    dz1 = meshfundepths[:,1].copy()  # height (dz) of top layer



    hnv = np.zeros_like(dz1)         #
    hnv1 = hnv.copy()
    dh_meshfun = np.zeros_like(dz1)
    for inode in range(npoint):
        # hnv is depth given by # vertical layers and mesh function
        # hnv1 is the depth of the level above
        # In this version, the vanilla case is that these straddle depth

        hnv[inode] = meshfundepths[inode,nlevel[inode]-1]
        hnv1[inode] = meshfundepths[inode,nlevel[inode]-2]

        excess_depth = depth[inode] - hnv1[inode]
        dh_meshfun[inode] = hnv[inode] - hnv1[inode]

        # rule out cases where the bed is at above the lowest meshfun (which will become
        # hybrid with sigma or sigma)
        # rule out the exact case where the bed ifind out if lowest level falls below bottom (eliminating exact fit case)
        # and if it does check if it is a sliver
        sliver = 0.025

        if excess_depth > 0.:
            if (excess_depth < sliver*dh_meshfun[inode]) and (nlayer[inode]>1):    # todo is this the right plae for nlayer check?

                # sliver below bed that needs to be absorbed into layer above
                # reduce nlevel and nlayer, readjust hnv. Mesh will be stretched later. hnv1[inode] is now invalidv
                if inode in showlist: print("WATCH inode={}".format(inode))
                nlayer[inode] -= 1
                nlevel[inode] -= 1
                meshfundepths[inode,nlevel[inode]-1] = depth[inode]
                hnv[inode] = depth[inode]

            elif excess_depth < dh_meshfun[inode]:
                # it is sufficiently big, set it to bed height
                #todo: could these be asserts?
                meshfundepths[inode,nlevel[inode]-1] = depth[inode]
                hnv[inode] = depth[inode]

                if excess_depth < 0.3*dh_meshfun[inode]:
                    meshfundepths[inode,nlevel[inode]-2] -= 0.25*dh_meshfun[inode]
            #else:
            #    #print "excess at {}".format(inode)

        sigmadepths[inode,0:nlevel[inode]] = np.arange(nlevel[inode],dtype='d')*dz1[inode]
        hsig[inode]=sigmadepths[inode,nlevel[inode]-1]
        sigmadepths[inode,nlevel[inode]:] = hsig[inode]

        if inode in showlist:
            print("SHOWLIST")
            print("inode={} depth={} nlevel={} nlayer={}".format(inode,depth[inode],nlevel[inode],nlayer[inode]))
            print(meshfundepths[inode,:])
    


    # hsig is the depth of a uniform sigma grid
    # given the specificed num layers and layer thickness of the top layer
    # from the mesh function. If the depth is less this, a pure sigma grid will be used
    # todo: single layer is a special case that I thought would be taken care of by using <= not =
    # but the special case seems to require spelling out
    is_sigma = (depth <= hsig)  | (nlayer==1)


    # is_expand means that the depth is greater than the depth of the mesh function evaluated at the bottom level.
    # This will often be true ... it implies some stretching, which may be a lot or a little
    # For now (pre-stretch) use the coordinates as given by mesh function (min/max doesn't affect)
    is_expand = depth > hnv
        
    # for hsig <= h < htrans the levels given by meshfun don't quite fit in the (shallower) water column, 
    # so transition to sigma coordinates with weight gamma
    print("gamma stuff")
    #for inode in showlist:
    #    print(depth[inode])
    #    print(hsig[inode])
    #    print(hnv[inode])
    #    print(meshfundepths[inode,:])
    
    safe_divisor = hnv - hsig
    safe_divisor[hnv == hsig] = 1.
    # todo is this really safe?
    gamma = np.minimum(1.,np.maximum(0.,(depth - hsig)/safe_divisor ) )  # One value per node
    htrans  = (meshfundepths.T*gamma + sigmadepths.T*(1.-gamma)).T

    dh_meshfun = dh_meshfun*gamma + dz1*(1.-gamma)


    # now evaluate any stretching to be done
    # the stretching factor starts out at zero at the surface and linearly increases to the full amount
    # at the lowest level. In other words, the stretching gets stretched
    stretch = depth/hnv
    expandfac = np.ones(globalmaxlevel,dtype="d")
    for i in range(npoint):
        if is_expand[i]:
            expandfac[0:nlevel[i]] = 1. + np.power(np.linspace(0.,1.,nlevel[i]),4.)*(stretch[i]-1.)
            expandfac[nlevel[i]:] = expandfac[nlevel[i]-1]
            htrans[i,:] = expandfac[0:]*htrans[i,:]
            dh_meshfun[i] *= stretch[i]
        # todo: this is new because it gives some behavior for sigma. This is reasonable for positive depth but
        # a bit funny for negative. The real issue of course is that the bed is above the reference
        if is_sigma[i]:
            htrans[i,0:nlevel[i]] = np.linspace(0,depth[i],nlevel[i])
        htrans[i,nlevel[i]:] = depth[i]
    if False:
        print("{{{{{{{}}}}}}}")
        for i in showlist:
            print("\ni={} depth ={} gamma={} nlayer={} hvn={}".format(i,depth[i],gamma[i],nlayer[i],hnv[i]))
            print(htrans[i,0:nlevel[i]])
            print("meshfundepths:")
            print(meshfundepths[i,0:nlevel[i]])
            print("sigmadepths")
            print(sigmadepths[i,0:nlevel[i]])
    return htrans,is_sigma,nlayer,dh_meshfun


def lowest_layer_height(htrans,nlevel,klev=0):
    npoint = htrans.shape[0]
    print("npoint: %s" % npoint)
    print(htrans.shape[1])
    llh = np.zeros(npoint,dtype=float)
    for ipoint in range(npoint):
        bigindex = np.maximum(nlevel[ipoint]-klev - 1, 1)
        llh[ipoint] = htrans[ipoint,bigindex] - htrans[ipoint,bigindex - 1]
    #todo: experieent necessitated because htrans can go negative when bed is above reference
    return np.absolute(llh)




def label_components(mesh,nlayer,thresh,exclude):

    labels = -np.ones(len(nlayer))

    labels[exclude]=0
    current_label = 0
    cc = [exclude]
    qualified = (nlayer > thresh) & (labels < 0)
    while np.any(qualified):
        current_label +=1
        cc.append([])
        # pick first seed that qualifies and that isn't labeled yet

        v = np.nonzero(qualified)[0][0]
        stack = [v] 
        while len(stack) > 0:
            v = stack.pop()
            if labels[v] > 0:
                continue
            if nlayer[v] > thresh:
                labels[v] = current_label
                cc[current_label].append(v)
                for v0 in mesh.get_neighbor_nodes(v):
                    if not labels[v0]>0:
                        stack.append(v0)
        qualified = (nlayer > thresh) & (labels < 0)
    print("Number of components: {}".format(len(cc)))
    return cc



def process_orphans2(mesh,nlayer,depth,hcor):
    norphan = 0
    maxlayer = np.max(nlayer)-1
    smallest_nlayer = 3   # don't check for orphans smaller than this # layers
    smallest_component_size = 16   # size of component considered orphan

    for ilay in range(maxlayer,smallest_nlayer,-1):
        exclude, = np.where(nlayer<=ilay)
        print("orphans {}".format(ilay))
        # find connected components that have this many or fewer layers
        cc = label_components(mesh,nlayer,ilay,exclude)
        sizes = np.array([len(c) for c in cc],dtype="i")
        #print sizes
        use_labels, = np.where(sizes < smallest_component_size)
        for iuse in use_labels:
            cuse = cc[iuse]
            norphan += len(cuse)
            #print "cuse"
            #print cuse
            for inode in cuse:
                #print "inode"
                #print inode
                nlayer[inode] -= 1
                hcor[inode,nlayer[inode]:]=depth[inode]
        print("ilay={} norphan = {}".format(ilay,norphan))
    return nlayer,hcor



def process_orphans(mesh,nlayer,depth,hcor):
    norphan = 0
    nodes = mesh.nodes
    for ndx in range(nodes.shape[0]):
        nds = mesh.get_neighbor_nodes(ndx)
        nlayer_node = nlayer[ndx]
        max_nlayer_neighbor = np.max(nlayer[nds])

        is_orphan = max_nlayer_neighbor < nlayer_node #No connectivity,
        if is_orphan:
            nlayer[ndx] = max_nlayer_neighbor
            hcor[ndx,nlayer[ndx]:] = depth[ndx]
            norphan+=1
    print("# orphans = {}".format(norphan))
    return nlayer


def smooth_bed(mesh,eta,h,hcor,nlevel,speed):

    nsmoothlev = 1
    i=0
    npoint = len(nlevel)
    nlayer = nlevel - 1
    zsmooth = np.zeros((npoint,nsmoothlev),dtype='d')
    zsmooth[:,nsmoothlev - 1]=-h
    old_layer = -h


    #hlow = lowest_layer_height(hcor,nlevel,0)
    # speed = np.absolute(hlow)
    # with nsmoothlay = 1 used vel=speed*.7,kappa=.75,dt=0.05,iter_total=20
    # this includes experimental smoothing based on neighbors in the base layer and/or current layer depending on whether
    # the number of layers is less in the neighbor. If reverting, eliminate nlayer and use laplace_wismooth_with_vel3
    #new_layer = laplace_smooth_with_vel3(mesh,nlayer,old_layer,vel=speed*.6,kappa=0.75,dt=0.05,iter_total=20)
    new_layer = laplace_smooth_with_vel3(mesh,nlayer,old_layer,vel=speed*.2,kappa=0.7,dt=0.05,iter_total=20)
    #latest_layer = np.where(new_layer>old_layer, new_layer, old_layer)

    # todo: At the moment this script not equipped to change the # of layers.
    # As a result we want to keep the bottom layer off the bed by limiting its shrinkage
    latest_layer = np.maximum(old_layer+0.5*speed, new_layer)
    zsmooth[:,nsmoothlev-2-i] = latest_layer
    old_layer = latest_layer
    np.savetxt("zsmoothsave.txt",zsmooth)
    # Now generate new mesh depths using the smoothed elevations as a pseudo-bed
    # and one fewer layers
    # Mind that the outcome from the previous step is in z coordinates, not depth
    # but the depth function works based on depth from reference eta
    hsmooth = eta - zsmooth
    pseudo_bed_depth = hsmooth[:,0]
    return pseudo_bed_depth



def gen_sigma(nlayer, minlayer, maxlayer, eta, h, mesh, meshfun, nsmoothlay=0):
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

        mesh : float
            maximum theta to use in S calculations. This is interpreted the same
            as a standard S grid theta although it will be varied according to depth

        meshfun: float
            S coordinate parameter b

        hc: float
            S coordinate parameter hc (do not alter)
    """
    depth=eta+h
    # Have to do this first because nlayer may be modified
    hcor,is_sigma,nlayer,dh_meshfun = mesh_function_depths(nlayer,depth,mesh,meshfun)
    
    print("first hcor")
    for inode in showlist:
        print(hcor[inode,:])
    
    
    #def layer_depths(nlayer, depth, mesh, meshfun):

    do_smooth = nsmoothlay > 0
    SIGMA_NEG = -9999.

    # This is the first pass at generating the zcor using the mesh function
    # If we aren't smoothing this is the z part of the final mesh

    smooth_to_archive = True
    npoint = len(nlayer)
    globalmaxlayer = np.max(nlayer)
    nlevel = nlayer + 1
    globalmaxlevel = np.max(nlevel)
    print("Global maxlevel before smooth: {}".format(globalmaxlevel))
    


    nsmoothlev = nsmoothlay + 1

    #do_smooth = True
    if do_smooth:
        print("******\n\n\nSmoothing")
        print("hcor dims")
        print(hcor.shape)
        print(nlevel.shape)
        print(nlayer.shape)
   
        
        for i in showlist:
            print("i={} nlevel = {}, depth={}".format(i,nlevel[i],depth[i]))
            print("firlst")
            print(hcor[i,:])
        
        
        zsmooth = np.zeros((npoint,nsmoothlev),dtype='d')
        zsmooth[:,nsmoothlev - 1]=-h
        old_layer = -h

        if smooth_to_archive:
            for i in range(nsmoothlay):
                print("layer iteration: %s" % i)
                hlow = lowest_layer_height(hcor,nlevel,i) 
                speed = np.absolute(hlow)
                # with nsmoothlay = 1 used vel=speed*.7,kappa=.75,dt=0.05,iter_total=20
                # this includes experimental smoothing based on neighbors in the base layer and/or current layer depending on whether
                # the number of layers is less in the neighbor. If reverting, eliminate nlayer and use laplace_wismooth_with_vel3
                #new_layer = laplace_smooth_with_vel3(mesh,nlayer,old_layer,vel=speed*.6,kappa=0.75,dt=0.05,iter_total=20)
                new_layer = laplace_smooth_with_vel3(mesh,nlayer,old_layer,vel=speed*.6,kappa=0.7,dt=0.05,iter_total=20)
                #latest_layer = np.where(new_layer>old_layer, new_layer, old_layer)

                # todo: At the moment this script not equipped to change the # of layers.
                # As a result we want to keep the bottom layer off the bed by limiting its shrinkage
                latest_layer = np.maximum(old_layer+0.5*speed, new_layer)
                zsmooth[:,nsmoothlev-2-i] = latest_layer
                old_layer = latest_layer
            np.savetxt("zsmoothsave.txt",zsmooth)
        else:
            zsmooth = np.loadtxt("zsmoothsave.txt")
            
        print("Linking")
        # Now generate new mesh depths using the smoothed elevations as a pseudo-bed
        # and one fewer layers
        # Mind that the outcome from the previous step is in z coordinates, not depth
        # but the depth function works based on depth from reference eta
        hsmooth = eta - zsmooth
        pseudo_bed_depth = hsmooth[:,0]



        # todo from here down is experimental. The next couple lines setup computation of # levels revised
        # after that, nlevel was replaced by nlevel2.
        dztarget = np.zeros_like(nlayer, dtype="d")
        xdummy = 0.
        eta_dummy = 0. # todo: is this good enough? Did it because we already have the eta part of the depth in pseudo_bed_depth

        nlayer2 = default_num_layers(xdummy,eta_dummy, pseudo_bed_depth, np.maximum(1,minlayer-nsmoothlay),
                                     np.maximum(1,maxlayer-nsmoothlay), dztarget,meshfun)

        # the code later recognizes the minimum of 1 enforced above and below is artificial the globalmaxlayer stuff prevents
        # going past bound ... something that came up in a small test problem
        nlayer2 = np.maximum(1,np.minimum(nlayer2, globalmaxlayer-nsmoothlay))
        print("yo")
        print(nlayer2)
         
        # this is a flag needed used later to signal to indicate not enough layers to absorb nsmoothlay into the total
        # this is the last opportunity to calculate it based on the original number of layers
        # this is an all-or-nothing approach that does not try to eek out every opportunity to use the smoothed layers.
        # for instance, if nsmoothlay = 2 and there are 2 original layers we could conceivably use the lowest smoothed layer
        # and then ignore the upper one in order to match the reference
        few4smooth=(nlayer <= nsmoothlay)

        #nlayer2 = np.where(nlayer > nsmoothlay,nlayer2,nlayer)  # right generalization ? will need to test
        #nlayer2 = nlayer_default
        #nlayer = tabu_numlayer(depth,mesh.edges,nlayer_default,minlayer,maxlayer)



        #
        # nlayer-nsmoothlay

        hcor2,is_sigma2,nlayer2 = mesh_function_depths(nlayer2,pseudo_bed_depth,mesh,meshfun)

        nlevel2 = nlayer2+1
        nlevel3 = nlevel2+nsmoothlay
        nlayer3 = nlayer2+nsmoothlay


        # This is simplified from before when it was possible for the smoothing process
        # to reduce the # levels. At the moment the interface is assumed to be the top
        # smoothed level
        #bndlevel = np.maximum(0,nlevel2 - nsmoothlay - 1).astype('i')
        bndlevel = np.maximum(0,nlevel2-1)
        nbnd = (bndlevel*0 + nsmoothlay).astype('i')


        # Blend the region around the interface between the upper part done with the mesh
        # function and the lower part done with the smoothing
        for inode in range(npoint):
            hcor[inode,nlevel2[i]:] = np.nan
            if nlevel2[inode] == 2:
                continue
            blev = bndlevel[inode]
            print("xxxxxxxxxxx\ni={} nlevels = {} nlevel2 = {} nlevel3 = {}\n blev = {} depth = {} pseudo_be_depth={} is_sigma={}".format(
                        inode,nlevel[inode],nlevel2[inode],nlevel3[inode],blev,depth[inode],pseudo_bed_depth[inode],is_sigma[inode]))            
            if blev == 0: 
                continue
            if inode in showlist:
                print("to be joined")                    
                print("\ni={} nlevels = {} nlevel2 = {} nlevel3 = {}\n blev = {} depth = {} pseudo_be_depth={} is_sigma={}".format(
                        inode,nlevel[inode],nlevel2[inode],nlevel3[inode],blev,depth[inode],pseudo_bed_depth[inode],is_sigma[inode]))

                print(hcor[inode,:])
                print(hcor2[inode,:])
                print(hsmooth[inode,:])
            hcor[inode,0:blev] = hcor2[inode,0:blev]
            hcor[inode,blev:nlevel3[inode]] = hsmooth[inode,:]   # nlevel3 is the adjusted number
            hcor[inode,nlevel3[inode]:] = hcor[inode,nlevel3[inode]-1] # copy to lower levels
            
            if inode in showlist: 
                print("** hcor after merge before bound inode = {}** ".format(inode))
                print(hcor[inode,:])
                print(" &*&*")
            #zcor[inode,0:(bndlevel[inode]+1)] = np.linspace(eta,zcor[inode,bndlevel[inode]],bndlevel[inode]+1)
            if (blev > 0) and (nbnd[inode] > 1):
               hcor[inode,blev] = 0.4*hcor[inode,blev] + 0.3*hcor[inode,blev-1] + 0.3*hcor[inode,blev+1]
            elif (blev > 0) and (nbnd[inode] == 1):
                hcor[inode,blev] = 0.7*hcor[inode,blev] + 0.3*hcor[inode,blev-1]              
            
            if inode in showlist: 
                print("final hcor inode={}".format(inode))
                print(hcor[inode,:])
    else:
        # seems like if # smoothing is zero these are not provided?
        nlevel2=nlevel
        nlevel3=nlevel

    smooth_bed_clip = True
    if smooth_bed_clip:
        smoothed_bed = smooth_bed(mesh,eta,h,hcor,nlevel,dh_meshfun)

        for inode in range(npoint):
            if hcor[inode,(nlevel[inode]-2)] > smoothed_bed[inode]:
                if nlevel[inode] == 2:
                    continue
                if (inode > 111900) and (inode < 112000):
                    print("inode = {}, nlevel={} smoothed = {}  hcor={}".format(inode,nlevel[inode],smoothed_bed[inode],hcor[inode,nlevel[inode]-2]))
                nlayer[inode] -= 1
                nlevel2[inode] -= 1
                nlevel[inode] -= 1
                hcor[inode,nlayer[inode]:] = depth[inode]  # todo: should this be nan?


    print("Procesing orphans")
    #nlayer = process_orphans(mesh,nlayer,depth,hcor)
    oldnlayer = nlayer.copy()
    nlayer,hcor = process_orphans2(mesh,nlayer,depth,hcor)
    #plt.hist(oldnlayer-nlayer)
    #plt.show()


    nlevel3 = nlayer + 1
    nlevel = nlayer + 1

    print("Convert to sigma")


    # Convert to sigma and replace
    sigma = (hcor / depth.reshape(npoint, 1))
    sigma = np.minimum(sigma, 1)
    sigma[sigma==-0.0] = 0.0

    print(" (*(*(*())))")
    for inode in showlist:
        print("inode={} depth={} nlayer={} nlevel={} nlevel3={}".format(inode,depth[inode],nlayer[inode],nlevel[inode],nlevel3[inode]))
        print(hcor[inode,:])
        print(sigma[inode,:])

    if nsmoothlay > 0:
        for inode in range(npoint):
            # when is_sigma changes this is conservative for monotonicity
            # first, assume that the smoothed layers are OK and just do sigma down to the top of the smoothing
            if inode in showlist or inode==2:
                print("deciding if sigma for i={} is_sigma= {} is_sigma2={}".format(inode,is_sigma[inode],is_sigma2[inode]))
            
            if is_sigma2[inode] or is_sigma[inode]:
                nnonbndlev = nlevel2[inode]
                if inode in showlist:
                    print("Experimental stuff inode={} nonbndlev={} nlevel={} nlevel2={} nlevel3={}".format(
                            inode,nnonbndlev,nlevel[inode],nlevel2[inode],nlevel3[inode]))
                    print("sigma")
                    print(sigma[inode,:])
                sigma[inode,0:nnonbndlev] = np.linspace(0.,sigma[inode,nnonbndlev-1],nnonbndlev) 
                
                
                # the above step may have left some very thin sigma layers above some very wide smoothing layers
                # sigmartio is the ratio of the sigma layer width to the top smoothed layer, unless the smoothing went above the
                # reference ratio (which is indirectly indicated by sigmas<0) and in this case it is just 0. as a signal
                sigmaratio =  sigma[inode,1]/ (sigma[inode,nnonbndlev] - sigma[inode,nnonbndlev-1])

                # another flagged issue is the possibility that sigma values are negative, which wouldd have happened because
                # hsmooth was negative
                if np.any(sigma[inode,0:nnonbndlev] < 0.):
                    sigmaratio = SIGMA_NEG


                # abandon the shole matching/merge idea and do sigma from scratch
                # hardwired threshold
                ACCEPT_RATIO=0.2
                nlev = nlevel[inode] if few4smooth[inode] else nlevel3[inode]
                nlevel3[inode] = nlev
                if (sigmaratio < ACCEPT_RATIO) or np.isnan(sigmaratio) or few4smooth[inode]:
                    if inode == 2: print("\n**\nsigma not accepted i={} sigmaratio={} nlev={} few4smooth={}".format(inode,sigmaratio,nlev,few4smooth[inode]))                  
                    sigma[inode,0:nlev] = np.linspace(0.,1.,nlev)
                else:
                    pass
                    #print "\n**\nsigma IS accepted i={} sigmaratio={} nlev={} few4smooth={}".format(inode,sigmaratio,nlev,few4smooth[inode])

                if inode in showlist:
                    print("\msigmaratio stuff: inode={} sigmaratio={} nlevel={} nlevel2={} nlevel3={} few4smooth={} nnonbndlev={}".format(
                            inode,sigmaratio,nlevel[inode],nlevel2[inode],nlevel3[inode],few4smooth[inode],nnonbndlev))
                    print(sigma[inode,:])
                    print("***\n")
                    
                sigma[inode,nlev:] = np.nan
    else:
        for inode in range(npoint):
            nlev = nlevel3[inode]
            if is_sigma[inode]:
                sigma[inode,0:nlev] = np.linspace(0.,1.,nlev)
            sigma[inode,nlev:] = np.nan

    # todo: these are rules to abandon smoothing altogether and go with even sigma everywhere
    # the first one says to do it if the number of layers does not exceed the number of smoothing layers
    # the second says do it if depth of the upper levels isn't too fine compared to the  enough and that rule is very
    # ad hoc and hardwired


    #for inode in range(npoint):
    #    # when is_sigma changes this is conservative for monotonicity
    #    if is_sigma[inode] or is_sigma2[inode] or nlevel2[inode] == 2:
    #        #print nlevel2[inode]
    #        sigma[inode, 0:nlevel[inode]] = np.linspace(0., 1., nlevel[inode])
    #    sigma[inode,nlevel[inode]:maxlevel] = np.nan
 
    print("Testing monotonicity")
    nonmon=[]
    for inode in range(npoint):
        if np.any(sigma[inode,:-1] > sigma[inode,1:]):
            nonmon.append(inode)
    if len(nonmon)>1:
        for inode in range(min(3,len(nonmon))):
            ii = nonmon[inode]
            print("\nNode {} is not monotonic in sigma".format(ii))
            print("depth={} nlevel0={} nlevel={} nlevel2={} nlevel3={} is_sigma={} is_sigma2={}".format(depth[ii],nlevel0[ii],
                         nlevel[ii],nlevel2[ii],nlevel3[ii],is_sigma[ii], is_sigma2[ii]))
            print(sigma[ii,:])
            print(hcor[ii,:])


    print(sigma[0:5,:])
    #print sigma[0:7,0:9]
    sigma = -sigma
    nlayer3 = nlevel3 - 1

    return sigma,nlayer3






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
    example2()
