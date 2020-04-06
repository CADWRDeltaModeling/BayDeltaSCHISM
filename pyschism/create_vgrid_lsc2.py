#!/usr/bin/env python
# -*- coding: utf-8 -*-

#runfile('D:/Delta/BayDeltaSCHISM/Scripts/create_vgrid_lsc2.py',
#         wdir='D:/temp/gridopt/%s' % (scene),
#        args="--hgrid=%s.gr3 --minmaxregion=../minmaxlayer.shp --dxwgt=1.0 --curvewgt=8. --archive_nlayer=out --nlayer_gr3=%s_nlayer.gr3 --eta=1.0" %(scene,scene) )


""" Create LSC2 vertical grid lsc2.py

    The min and max layers can be specified in polygons in yaml or shp
    with minlayer and maxlayer attributes.
"""
from lsc2 import * #default_num_layers, gen_sigma, flip_sigma
from schism_vertical_mesh import SchismLocalVerticalMesh, write_vmesh
from schism_mesh import read_mesh,write_mesh
from schism_polygon import read_polygons
from vgrid_opt2 import *
import numpy as np
import scipy.spatial
fix_minmax = False
fixed_min = 1
fixed_max = 40


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
                        help='Number of iterations for layer simplification')
    parser.add_argument('--eta', type=float, default=1.5,
                        help='Reference surface elevation')
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
    minmax_region = args.minmaxregion
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
            for fname in transectfiles:
                if not os.path.exists(fname): raise ValueError("Requested output transect file does not exist: {}".format(fname))


    vgrid_gen(hgrid,vgrid_out,eta,minmax_region,archive_nlayer,nlayer_gr3)

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

    vgrid_out = "vgrid.in"
    vgrid0_out = "D:/Delta/BayDeltaSCHISM.bak/BayDeltaSCHISM/calibration_20171101_v87d/run58/vgrid.in.58d"
    vgrid0_out = "vgrid.in"
    plot_vgrid(hgrid,vgrid_out,vgrid0_out,eta,transectfiles)



def vgrid_gen(hgrid,vgrid_out,eta,
              minmaxlayerfile,archive_nlayer=None,nlayer_gr3=None):
    from lsc2 import default_num_layers

    meshfun = BilinearMeshDensity()

    dummydepth = np.linspace(0,14,15)
    dummyk = np.linspace(0,14,15)
    dummyout = meshfun.depth(dummyk,dummydepth,0.)

    print("Reading the mesh " )
    mesh = read_mesh(hgrid)
    h0 = mesh.nodes[:, 2]

    places_on = np.array([[626573.490000,4260349.590000],[626635.000000,4260391.7]],dtype='d')
    dists_on = np.min(scipy.spatial.distance.cdist(mesh.nodes[:,0:2],places_on),axis=1)
    print(np.where(dists_on<100))

    depth = eta+h0

    print("Reading the polygons...")
    polygons = read_polygons(minmaxlayerfile)
    minlayer = np.ones_like(h0, dtype='int')
    #minlayer[:] = 8 # todo need polygons
    maxlayer = np.ones_like(h0, dtype='int')*10000
    dztarget = np.full_like(h0, 100., dtype='d')
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
        print((np.where(np.isnan(minlayer))))
        raise ValueError('Nan value in minlayer')

    if archive_nlayer == 'out':

        dztarget = 0.
        #todo: these will ruin the code
        if fix_minmax:
            minlayer = minlayer*0+fixed_min
            maxlayer = maxlayer*0+fixed_max  #np.max(maxlayer)

        xdummy = 0.
        nlayer_default = default_num_layers(xdummy,eta, h0, minlayer, maxlayer, dztarget,meshfun)
        nlayer = nlayer_default
 
        if archive_nlayer=="out":
            print("writing out number of layers")
            write_mesh(mesh,nlayer_gr3.replace(".gr3","_default.gr3"),node_attr=nlayer_default)
            write_mesh(mesh,nlayer_gr3,node_attr=nlayer)
            #write_mesh(mesh,nlayer_gr3.replace(".gr3","_dztarget.gr3"),node_attr=dztarget)
    elif archive_nlayer == "in":
        nlayer_mesh = read_mesh(nlayer_gr3)
        #dztarget=read_mesh(nlayer_gr3.replace(".gr3","_dztarget.gr3")).nodes[:,2]
        nlayer = nlayer_mesh.nodes[:,2].astype('i')
        if int(nlayer_mesh.n_nodes()) != int(mesh.n_nodes()):
            raise ValueError("NLayer gr3 file (%s)\nhas %s nodes, hgrid file (%s) has %s" 
                  %(nlayer_gr3, nlayer_mesh.n_nodes(),hgrid,mesh.n_nodes()) )
    else:
        raise ValueError("archive_nlayer must be one of 'out', 'in' or None")


    # inclusion of minlayer and maxlayer has to do with experiment regenerating # layers after smoothing
    # this will ruin code generally, and if the experiment goes well we need to make sure this is available when archive_nlayer="in"
    if fix_minmax:
        minlayer = nlayer*0+fixed_min
        maxlayer = nlayer*0+fixed_max #np.max(maxlayer)


    sigma2,nlayer_revised = gen_sigma(nlayer, minlayer,maxlayer, eta, h0, mesh, meshfun)
    print("Returned nlayer revised: {}".format(np.max(nlayer_revised)))
    nlayer = nlayer_revised
    nlevel = nlayer+1

    vmesh = SchismLocalVerticalMesh(flip_sigma(sigma2))
    #vgrid0 = vgrid_out.replace(".in", "_int.in")
    #write_vmesh(vmesh, vgrid0)
    #vmesh1 = SchismLocalVerticalMesh(flip_sigma(sigma1))
    print("Writing vgrid.in output file...")
    write_vmesh(vmesh, vgrid_out)
    print("Done")


def plot_vgrid(hgrid_file,vgrid0_file,vgrid_file,eta,transectfiles):
    from lsc2 import default_num_layers,plot_mesh
    from schism_vertical_mesh import read_vmesh
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
        path = []        
        transx = transect[:,1:3] 
        for p in range(transx.shape[0]):
            path.append( mesh.find_closest_nodes(transx[p,:]))        
        #zcorsub = zcor[path,:]
        xx = x[path]
        xpath = np.zeros(xx.shape[0])
        
        for i in range (1,len(path)):
            dist = np.linalg.norm(xx[i,:] - xx[i-1,:])
            xpath[i] = xpath[i-1] + dist
        try:
            fig,(ax0,ax1) = plt.subplots(2,1,figsize=(10,8)) #,sharex=True,sharey=True)
            ax0.set_title(transectfile)
            #plot_mesh(ax0,xpath,zcor0[path,:],0,len(xpath),c="0.5",linewidth=2)
            plot_mesh(ax0,xpath,zcor0[path,:],0,len(xpath),c="red")
            plot_mesh(ax1,xpath,zcor1[path,:],0,len(xpath),c="blue")
            ax0.plot(xpath,-h0[path],linewidth=2,c="black")
            ax1.plot(xpath,-h0[path],linewidth=2,c="black")
            plt.savefig(ospath.join("images",base+".png"))
            plt.show()
        except:
            print("Plotting of grid failed for transectfile: {}".format(transectfile))


if __name__ == '__main__':
    main()
