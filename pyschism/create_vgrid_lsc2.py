
#runfile('D:/Delta/BayDeltaSCHISM/Scripts/create_vgrid_lsc2.py',
#         wdir='D:/temp/gridopt/%s' % (scene), 
#        args="--hgrid=%s.gr3 --minmaxregion=../minmaxlayer.shp --dxwgt=1.0 --curvewgt=8. --archive_nlayer=out --nlayer_gr3=%s_nlayer.gr3 --eta=1.0" %(scene,scene) )


""" Create LSC2 vertical grid lsc2.py

    The min and max layers can be specified in polygons in yaml or shp
    with minlayer and maxlayer attributes.
"""
from lsc2 import default_num_layers, gen_sigma, flip_sigma
from schism_vertical_mesh import SchismLocalVerticalMesh, write_vmesh
from schism_mesh import read_mesh,write_mesh
from schism_polygon import read_polygons
import numpy as np


def create_arg_parser():
    """ Create argument parser for
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hgrid', default='hgrid.gr3',
                        help='hgrid file name')
    parser.add_argument('--vgrid', default='vgrid.in',
                        help='vgrid output file name')                        
    help_region = "Polygon file that contains min and max layer information"
    parser.add_argument('--minmaxregion', required=True,
                        help=help_region)
    parser.add_argument('--ngen', type=int, default=60,
                        help='Number of EA iterations for layer simplification')                                                 
    parser.add_argument('--eta', type=float, default=1.,
                        help='Reference surface elevation')
    parser.add_argument('--theta_f', type=float, default=2.,
                        help='theta_f, S coord parameter')
    parser.add_argument('--theta_b', type=float, default=0.,
                        help='theta_b, S coord parameter')
    parser.add_argument('--h_c', type=float, default=0., help='h_c, S coord parameter')
    parser.add_argument('--dxwgt', type=float, default=1.,
                        help='Weight on vertical derivative penalty')
    parser.add_argument('--curvewgt', type=float, default=8.,
                        help='Weight on curvature penalty')
    parser.add_argument('--foldwgt', type=float, default=2.,
                        help='Weight on folding/tangling penalty')
                      
    parser.add_argument('--foldfrac', type=float, default=0.35,
                        help='Fraction of nominal dz at which to impose folding/tangling penalty') 
    parser.add_argument('--plot_transects',default=None,
                        help='Filename or glob prefix of transects to plot (e.g. mallard for files mallard_1.csv, mallard_2.csv, etc')
    parser.add_argument('--archive_nlayer',default='out',
                        help='Filename or glob prefix of transects to plot (e.g. mallard for files mallard_1.csv, mallard_2.csv, etc')
    parser.add_argument('--nlayer_gr3',default='nlayer.gr3',
                        help='Filename or glob prefix of transects to plot (e.g. mallard for files mallard_1.csv, mallard_2.csv, etc')

    return parser




def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    hgrid=args.hgrid
    theta = args.theta_f
    b = args.theta_b
    hc = args.h_c     
    minmax_region = args.minmaxregion
    dxfac = args.dxwgt
    curvewgt = args.curvewgt
    foldwgt = args.foldwgt
    foldfrac = args.foldfrac
    vgrid_out = args.vgrid
    archive_nlayer = args.archive_nlayer
    
    nlayer_gr3 = args.nlayer_gr3
    if nlayer_gr3 == hgrid: raise ValueError ("Nlayer archive gr3 and hgrid.gr3 the same")
    eta = args.eta
    vgrid0 = vgrid_out.replace(".in", "_int.in")
    maxiter=200
    ngen=args.ngen
    transect = args.plot_transects
    from os import getcwd
    import os.path
    import glob
    fulldir = getcwd()
    head,tail=os.path.split(fulldir)
    if not transect: 
        transect = tail
        transectfiles = glob.glob(tail+"_*.csv")
    else:
        with open(transect,"r") as f:
            lines = f.readlines()
            transectfiles = [line.strip() for line in lines if ("csv" in line) and (not line.startswith("#"))]

    
    vgrid_gen(hgrid,vgrid_out,eta,minmax_region,ngen,maxiter,
              theta,b,hc,dxfac,
              curvewgt,foldwgt,foldfrac,
              archive_nlayer,nlayer_gr3)
              
        
          
    transect_mallard = ["mallard_1.csv","mallard_2.csv"]         
    transect_gg = ["transect_gg1.csv","transect_gg2.csv"]
    transect_liberty = ["toe_drain_north_liberty_1.csv","toe_drain_north_liberty_2.csv",
                        "toe_drain_north_liberty_3.csv","toe_drain_north_liberty_4.csv"]
    transect_pinole = ["pinole_shoal_1.csv","pinole_shoal_2.csv",
                       "pinole_shoal_3.csv","pinole_shoal_4.csv"]
    transect_franks = ["frank_tract_sjr_1.csv","frank_tract_sjr_2.csv",
                       "frank_tract_sjr_3.csv","frank_tract_sjr_4.csv",
                       "frank_tract_sjr_5.csv"]

    #transectfiles = transect_franks
    
    plot_vgrid(hgrid,vgrid_out,vgrid0,eta,transectfiles)
          
    

def vgrid_gen(hgrid,vgrid_out,eta,
              minmaxlayerfile,ngen,maxiter,theta,b,hc,
              dx2fac=20.0,curvewgt=100.0,foldwgt=20.,foldfrac=0.35,
              archive_nlayer=None,nlayer_gr3=None):
    from numlayer import tabu_numlayer
    from lsc2 import default_num_layers
    from vgrid_opt2 import *
   
   
   
    print("Reading the mesh " )
    mesh = read_mesh(hgrid)
    h0 = mesh.nodes[:, 2]    
    depth = eta+h0


    if archive_nlayer == 'out':     
        print("Reading the polygons...")
        polygons = read_polygons(minmaxlayerfile)
        minlayer = np.ones_like(h0, dtype='int')
        #minlayer[:] = 8 # todo need polygons
        maxlayer = np.ones_like(h0, dtype='int')*10000
        dztarget = np.full_like(h0, 100., dtype='d')
        #maxlayer[:] = 31
        print("Assign min/max layers to nodes based on polygons...")
        for polygon in polygons:
            box = [polygon.bounds[i] for i in (0, 2, 1, 3)]
            candidates = mesh.find_nodes_in_box(box)
            n_layers_min = int(polygon.prop['minlayer'])
            n_layers_max = int(polygon.prop['maxlayer'])
            dz0 = float(polygon.prop['dz_target'])
            for node_i in candidates:
                if polygon.intersects(mesh.nodes[node_i, :2]):
                    minlayer[node_i] = n_layers_min
                    maxlayer[node_i] = n_layers_max
                    dztarget[node_i] = dz0

        if np.any(np.isnan(minlayer)):
            print(np.where(np.isnan(minlayer)))
            raise ValueError('Nan value in minlayer')
        print("Creating vertical grid...")
        #meshsmooth = read_mesh("hgrid_depth_smooth.gr3")
        hsmooth = mesh.nodes[:,2]
        etazero = 0.
        assert len(hsmooth) == len(h0)
        # todo: was eta and h0
        dztarget = dztarget*0 + 1.
        dztarget = 0.6 + 0.4*(hsmooth-12.)/(22. - 12.)
        dztarget = np.minimum(1.0,dztarget)
        dztarget = np.maximum(0.65,dztarget)
        #dztarget2 = np.minimum(1.3,0.65+0.65*(2.-hsmooth))
        #dztarget[hsmooth<2.] = dztarget2[hsmooth<2.]
        nlayer_default = default_num_layers(eta, hsmooth, minlayer, maxlayer, dztarget)
        #print nlayer_default
        #nlayer = deap_numlayer(depth,mesh.edges,nlayer_default,minlayer,ngen)
        nlayer = tabu_numlayer(depth,mesh.edges,nlayer_default,minlayer,maxlayer,ngen)
        print(depth.shape)
        print(nlayer.shape)

        if archive_nlayer=="out":
            print("writing out number of layers")
            write_mesh(mesh,nlayer_gr3.replace(".gr3","_default.gr3"),node_attr=nlayer_default)
            write_mesh(mesh,nlayer_gr3,node_attr=nlayer)
            write_mesh(mesh,nlayer_gr3.replace(".gr3","_dztarget.gr3"),node_attr=dztarget)
    elif archive_nlayer == "in":
        nlayer_mesh = read_mesh(nlayer_gr3)
        dztarget=read_mesh(nlayer_gr3.replace(".gr3","_dztarget.gr3")).nodes[:,2]
        nlayer = nlayer_mesh.nodes[:,2].astype('i')
        if long(nlayer_mesh.n_nodes()) != long(mesh.n_nodes()):
            raise ValueError("NLayer gr3 file (%s)\nhas %s nodes, hgrid file (%s) has %s" 
                  %(nlayer_gr3, nlayer_mesh.n_nodes(),hgrid,mesh.n_nodes()) )
        #print("Reading the polygons for dz_target...")
        #polygons = read_polygons(minmaxlayerfile)
        #dztarget = np.full_like(h0, np.nan, dtype='d')
        #maxlayer[:] = 31
        #print("Assign dz_target to nodes based on polygons...")
        #for polygon in polygons:
        #    box = [polygon.bounds[i] for i in (0, 2, 1, 3)]
        #    candidates = mesh.find_nodes_in_box(box)
        #    dz0 = float(polygon.prop['dz_target'])
        #    for node_i in candidates:
        #        if polygon.intersects(mesh.nodes[node_i, :2]):
        #            dztarget[node_i] = dz0

    else: 
        raise ValueError("archive_nlayer must be one of 'out', 'in' or None")
        
    #np.savez("savevar.npz",nlayer,nlayer_default,depth,h0)
    sigma,nlayer_revised = gen_sigma(nlayer, dztarget, eta, h0, theta, b, hc,mesh=mesh)
    print("sigma shape")
    print(sigma.shape)
    nlayer = nlayer_revised
    nlevel = nlayer+1
    
    #fsigma = flip_sigma(sigma)
    #print fsigma[0,:]
    vmesh = SchismLocalVerticalMesh(flip_sigma(sigma))
    vgrid0 = vgrid_out.replace(".in", "_int.in")    
    write_vmesh(vmesh, vgrid0)

    
#   Gradient based stuff
    
    nodes = mesh.nodes
    edges = mesh.edges
    x =nodes[:,0:2]    # x positions for xsect. These have no analog in 3D
    sidelen2 = np.sum((x[edges[:,1],:] - x[edges[:,0],:])**2.,axis=1)

    #nodemasked = (depth < 0.75) #| (nlayer <= 2)
    #todo hardwire was 0.75
    nodemasked = (depth < 0.75) #| (nlayer <= 2)
    sidemasked = nodemasked[edges[:,0]] | nodemasked[edges[:,1]]
    gradmat = gradient_matrix(mesh,sidelen2,sidemasked)    
    
    print("Nodes excluded: %s" % np.sum(nodemasked))
    print("Sides excluded: %s" % np.sum(sidemasked))

    zcor = vmesh.build_z(mesh,eta)[:,::-1]
 
    
    # todo: test this
    #zcor[depth < 0., :] = np.nan
   

   
    
    # todo: why is kbps-1 so common? What does it mean and why the funny offset

    nvlevel = (vmesh.n_vert_levels() - vmesh.kbps)
    #nvlevel[depth<0] = 0    
  
    nlayer,ndx = index_interior(zcor,nodemasked,nvlevel)
    xvar = zcor[ndx>=0].flatten()
    xvarbase=xvar.copy()
    zcorold = zcor.copy()
    zmin = np.nanmin(zcorold,axis = 1)
    deptharr = np.tile(zmin,(zcorold.shape[1],1)).T
    zcorold = np.where(np.isnan(zcorold),deptharr,zcorold)

    do_opt = False
    if do_opt:
        curvewgt=np.zeros_like(zcorold)+curvewgt
        #todo: hardwire
        #bigcurvewgt = 4
        #for iii in range(zcor.shape[0]):
        #    nlev = nlayer[iii]+1
        #    curvewgt[iii,0:nlev]+=np.maximum(np.linspace(bigcurvewgt-nlev,bigcurvewgt-nlev,nlev),1)
              

        # todo
        ata = laplace2(mesh,nodemasked,sidemasked)        
        href_hess, grad_hess,laplace_hess = hess_base(xvar,zcorold,mesh,nlayer,ndx,
                                                  eta,depth,gradmat,sidelen2,
                                                  nodemasked,sidemasked,ata,
                                                  dx2fac,curvewgt,foldwgt,foldfrac)
                                                            


        zcor1 = mesh_opt(zcorold,mesh,nlayer,ndx,eta,depth,gradmat,
                     sidelen2,nodemasked,sidemasked,ata,
                     dx2fac,curvewgt,foldwgt,foldfrac,
                     href_hess, grad_hess,laplace_hess)

    else:
            zcor1 = zcorold                                             
    

    sigma1 = z_sigma(zcor1)
    nlevel = nlayer + 1
    for i in range(len(depth)):
        nlev = nlevel[i]
        if depth[i]<=0:  
            sigma1[i,0:nlev] = np.linspace(0,-1.0,nlev)
        sigma1[i,nlev:] = np.nan
    

    
    vmesh1 = SchismLocalVerticalMesh(flip_sigma(sigma1))
    print("Writing vgrid.in output file...")
    write_vmesh(vmesh1, vgrid_out)
    print("Done")
    

def plot_vgrid(hgrid_file,vgrid_file,vgrid0_file,eta,transectfiles):
    from lsc2 import default_num_layers,plot_mesh
    from schism_vertical_mesh import *
    import matplotlib.pylab as plt
    import os.path as ospath

    mesh = read_mesh(hgrid_file)
    x=mesh.nodes[:,0:2] 
    vmesh0 = read_vmesh(vgrid0_file)
    vmesh1 = read_vmesh(vgrid_file)
    h0 = mesh.nodes[:, 2]
    depth = eta+h0         
        
    zcor0 = vmesh0.build_z(mesh,eta)[:,::-1]
    zcor1 = vmesh1.build_z(mesh,eta)[:,::-1]
    for transectfile in transectfiles:
        base = ospath.splitext(ospath.basename(transectfile))[0]
        transect = np.loadtxt(transectfile,skiprows=1,delimiter=",")
        #transx = transect[:,1:3] 
        path = []        
        transx = transect[:,1:3] 
        for p in range(transx.shape[0]):
            path.append( mesh.find_closest_nodes(transx[p,:]))
        
        #ndx1 = mesh.find_closest_nodes(transx[-1,:])     
        #path = mesh.shortest_path(ndx0,ndx1)    
        #zcorsub = zcor[path,:]
        xx = x[path]
        xpath = np.zeros(xx.shape[0])
        for i in range (1,len(path)):
            dist = np.linalg.norm(xx[i,:] - xx[i-1,:])
            xpath[i] = xpath[i-1] + dist        
        
        fig,(ax0,ax1) = plt.subplots(2,1) #,sharex=True,sharey=True)
        plt.title(transectfile)
        #plot_mesh(ax0,xpath,zcor0[path,:],0,len(xpath),c="0.5",linewidth=2)
        plot_mesh(ax0,xpath,zcor0[path,:],0,len(xpath),c="red")
        plot_mesh(ax1,xpath,zcor1[path,:],0,len(xpath),c="blue")
        ax0.plot(xpath,-h0[path],linewidth=2,c="black")
        ax1.plot(xpath,-h0[path],linewidth=2,c="black")
        plt.savefig(ospath.join("images",base+".png"))
        plt.show()
    
    

if __name__ == '__main__':
    main()
