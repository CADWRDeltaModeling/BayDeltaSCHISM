from three_point_linear_norm import *


location_labels = {54: "Martinez",
                   82:"Collinsville",
                   92:"Emmaton",
                   75:"Mallard",
                   101:"Rio Vista"}

MAX_STATION = 0
MIN_STATION = 0
MAX_DEPTH = 0
                   
def set_index_bounds(min_station,max_station,max_depth):
    global MAX_STATION
    global MIN_STATION
    global MAX_DEPTH
    MIN_STATION = min_station
    MAX_STATION = max_station
    MAX_DEPTH = max_depth

def get_index_bounds():
    return (MIN_STATION,MAX_STATION,MAX_DEPTH)
                   
def nearest_neighbor_fill(arr):
    from scipy.spatial import KDTree
    a = arr.copy()    
    x,y=np.mgrid[0:a.shape[0],0:a.shape[1]]  
    xygood = np.array((x[~a.mask],y[~a.mask])).T
    xybad = np.array((x[a.mask],y[a.mask])).T
    a[a.mask] = a[~a.mask][KDTree(xygood).query(xybad)[1]] 
    return a

def vertical_fill(arr):
    out = arr.copy()
    column_max = np.tile(np.amax(out, axis = 0),(out.shape[0],1))
    a_shifted=np.roll(out,shift= 1,axis=0)
    a_shifted2=np.roll(out,shift=2,axis=0)
    a_shifted3=np.roll(out,shift=3,axis=0)   
    idx= out.mask.copy() #* ~a_shifted.mask
    out[idx]=column_max[idx]
    return out

def profile_plot(x,z,data,ax,context_label = None,add_labels = False,xlabel = None,xmin = None, xmax=None, max_depth=None):
    """
    UnTRIM-like profile plot of salinity
    xmin,xmax are the bounds (in km) of the profile
    max_depth is the maximum depth, data assumed to be 
    """

    import matplotlib
    import numpy as np
    import matplotlib.cm as cm
    import matplotlib.mlab as mlab
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import matplotlib.colors as colors
    global x_part
    global z_part


    
    matplotlib.rcParams['xtick.direction'] = 'out'
    matplotlib.rcParams['ytick.direction'] = 'out'

         
    if (not max_depth):
        max_depth = data.shape[0]
        
    if (xmin):
        min_station = x[0,:].searchsorted(xmin)
    else:
         min_station = 0
    
    if (xmax):
        max_station = x[0,:].searchsorted(xmax)
    else:
        max_station = x.shape[1]
        
    set_index_bounds(min_station,max_station,max_depth)
    
    print("context label: %s" % context_label)
    print("add label: %s" % add_labels)

    print("min x dist %s max x dist %s" %(xmin,xmax))
    print("min x station %s max x station %s max_depth %s" %(min_station,max_station,max_depth))
    
    x_part = x[0:max_depth,min_station:max_station]
    z_part = z[0:max_depth,min_station:max_station]
    
    data_part = data[0:max_depth,min_station:max_station]
    data_part = np.ma.masked_where(np.isnan(data_part),data_part)


    norml = ThreePointLinearNorm(2,0,20) 

    cmap=cm.get_cmap("RdBu_r").copy() 
    cmap.set_bad("white",0.0)

    
    do_image=False
    if do_image:
        lev = [0.0,0.1,0.2,0.5,1.0,2.0,4.0,8.0,16.0,24.0,32.0] 
        #lev = [0,0.25,0.5,1.0,2.0,4.0,8.0,16.0,32.0]            
        norml = colors.BoundaryNorm(lev, 256)
        im = ax.imshow(vertical_fill(data_part), interpolation='bilinear', origin='upper', 
                    aspect = 'auto', vmin = 0.0, vmax = 32.0,
                    norm=norml, cmap=cmap,
                    extent=(x[0,min_station],x[0,max_station-1],max_depth,0))    
        bad_data = np.ma.masked_where(~data_part.mask, data_part.mask) 
        ax.imshow(bad_data, interpolation='nearest', aspect = 0.75, cmap=cm.gray,extent=(x[0,min_station],x[0,max_station-1],max_depth,0)) 
        # Colorbar for the image.
        cbi = ax.colorbar(im, orientation='vertical', shrink=0.6,ticks = lev)
        cbi.set_label("Salinity (psu)", size = 14)
    else:
        im = None
   
    do_line_contour = True
    if do_line_contour:
        lev = np.array([2.0, 4.0, 8.0, 16.0])
        greys = 1.0-lev/32.
        cs = ax.contour(x_part,z_part,data_part,levels = lev,colors=['black','black','black','black'],linewidths=2)
        greylev = 1.0
        for c in cs.collections:
            c.set_linestyle('solid')
        #Thicken the zero contour.
        zc = cs.collections[0]
        #ax.setp(zc, linewidth=3)
        #ax.setp(zc, linestyle = 'dotted')
        ax.clabel(cs, lev,  # label every second level
               inline=1,
               inline_spacing = 3,
               fmt='%1.1f',
               fontsize=12)
    else:
        cs = None

    do_filled_contour = True
    if do_filled_contour:
        #lev = [0.0,0.1,0.2,0.5,1.0,2.0,4.0,8.0,16.0,32.0]  
        lev = [0,0.25,0.5,1.0,2.0,4.0,8.0,16.0,32.0]           
        norml = colors.BoundaryNorm(lev, 256)
        filled_data_part = vertical_fill(data_part)
        bad_data = np.ma.masked_where(~data_part.mask, data_part.mask, copy=True) 
        maxz = np.argmax(bad_data,axis=0)
        
        maxz[maxz == 0] = max_depth
        maxz = np.concatenate(([max_depth],maxz,[max_depth]))
        xstat = np.concatenate(([x_part[0,0]],x_part[0,:],[x_part[0,-1]]))
        
        ax.set_ylim([max_depth,0])
        cs = ax.contourf(x_part,z_part,filled_data_part,levels = lev, cmap = cm.RdBu_r, 
                          norm = norml,extent=(x[0,min_station],x[0,max_station-1],max_depth,0))                          
        ax.fill(xstat,maxz,"darkgray")
        #cb = ax.colorbar(cs, orientation='vertical', shrink=0.8,ticks = [32,16,8,4,2,1,0.5,0.2,0.1,0])
        #cb.set_label("Salinity (psu)", size = 14)    

    add_cruise_loc = False
    if add_cruise_loc:
        xloc = x_part[0]
        zloc = np.ones_like(xloc)*19
        stops, = ax.plot(xloc,zloc,'o',label="USGS cast")
        xloc = np.array([84.86])
        yloc = np.ones_like(xloc)*19
        dayflow, = ax.plot(xloc,yloc,"*",label="Dayflow X2",markersize=14)
    add_labels = True
    if (add_labels):
        inbound_label_dists = [x for x in location_labels.keys() if (x>xmin and x<xmax)]
        bbox_props = dict(boxstyle="rarrow,pad=0.3", fc="white", lw=2)
        for dist in inbound_label_dists:
            t = ax.text(dist, max_depth-2, location_labels[dist], ha="center", va="bottom", rotation=270,
                size=12,
                bbox=bbox_props)
        
    if (add_cruise_loc and add_labels):
        font= FontProperties(color="white");
        leg = ax.legend(("USGS cast","Dayflow X2"),"center left",numpoints=1,frameon=False)
        leg_texts = leg.get_texts()
        if len(leg_texts) > 0:
            leg_texts[0].set_color("white")
            leg_texts[1].set_color("white")

    if context_label:
        ttxt = ax.text(x_part[0,0]+2,5,context_label,size = 18, color = 'white')

    #ax.title('Vertical Salinity Profile', size = 14)
    if xlabel:
        ax.set_xlabel(xlabel, size = 14)
    ax.set_ylabel('Depth (m)', size = 14)


    return im, cs, ttxt



