from netCDF4 import *
import pyproj 
import ogr, osr
import numpy as np
import time
import datetime as dtm


def time_block_report(message,told):
    """ This routine is for reporting incremental timing of parts of the script"""
    tnew=time.time()
    diff = tnew - told
    print("%s : %s" % (message,diff))
    return tnew
    
# For converting the Mercator projection of the data to lat/lon
# Some of the mercator parameters turned out to be a bit 
# inconsistent on the CENCOOS side.
p=pyproj.Proj(r'+proj=merc +lat_ts=30.0 +lon_0=-128.735000610 +ellps=sphere')
cencoos_url = "http://thredds.axiomalaska.com/thredds/dodsC/COAMPS_4KM_10M_WIND.nc"
               #   http://thredds.cencoos.org/thredds/dodsC/COAMPS_4KM_10M_WIND.nc"
def merc_to_latlon(x,y):
    return p(x,y,inverse=True)
    
def cencoos_schism_opendap(lat_lo,lon_lo,lat_hi,lon_hi,
                          file_base,to_cache,from_cache):
    """ Download cencoos opendap data for all time based on a bounding set of lat/lon 
        file_base : str prefix for files
        to_cache :  bool whether to stash data in numpy arrays to make it easier next time
        from_cache : use cache rather than download)
        
        The strategy for this download may change with time. When the script was originally
        written, blocking the query in time was very inefficient
    """
    import time
    t = time.time()
    cencoos_wind_url  = "http://thredds.cencoos.org/thredds/dodsC/COAMPS_4KM_10M_WIND.nc"
    cencoos_pmsl_url  = "http://thredds.cencoos.org/thredds/dodsC/COAMPS_4KM_PRES_MSL.nc"
 
 
 
    if from_cache:
        """ Fetch dimensions that have been stored"""
        x_merc = np.loadtxt("x_merc.txt")
        y_merc = np.loadtxt("y_merc.txt")
        times = np.loadtxt("times.txt")
    else:
        data_wind = Dataset(cencoos_wind_url)      
        t=time_block_report("Wind opened at",t)
   
        x_merc = data_wind.variables['x'][:]*1000.
        y_merc = data_wind.variables['y'][:]*1000.

        timevar=data_wind.variables['time']
        times  = timevar[:]
        tunits = timevar.units
        alldatetimes = num2date(times,tunits)
        print("File time units: %s" % tunits)
        appdt = times[1] - times[0]
        print("Apparent dt in units: %s" % appdt)

        print("First datetime: %s" % alldatetimes[0])
        print("Last datetime: %s" % alldatetimes[-1])
        
        
        t=time_block_report("Full dimensions loaded at",t)    
        data_pmsl= Dataset(cencoos_pmsl_url)
        t=time_block_report("Pressure opened at",t)
    
    # Report any output gaps
    last_time = 0.0
    for tt in times:
        if tt != last_time +1:
            dtt = dtm.datetime(1970,1,1) + dtm.timedelta(hours=tt)
            ldt = dtm.datetime(1970,1,1) + dtm.timedelta(hours=last_time)
            dttxt = dtt.strftime("%Y-%m-%d %H:%M")
            ldtxt = ldt.strftime("%Y-%m-%d %H:%M")
            print("Non-consecutive time %s %s" % (dttxt,ldtxt))
        last_time = tt
    dset_last = dtm.datetime(1970,1,1) + dtm.timedelta(hours=tt)
    print("Last time in cencoos dataset: %s" % dset_last)
    
    # Filter based on bounding box in lat/lon
    lon = np.array([merc_to_latlon(xx,y_merc[0])[0] for xx in x_merc])
    lat = np.array([merc_to_latlon(x_merc[0],yy)[1] for yy in y_merc])
    (latndx,) = np.logical_and(lat >= lat_lo, lat <= lat_hi).nonzero()
    (lonndx,) = np.logical_and(lon >= lon_lo, lon <= lon_hi).nonzero()
    lat_dest = lat[latndx]
    lon_dest = lon[lonndx]
    np.savetxt("latitude.csv",lat_dest,fmt="%.5f")
    np.savetxt("longitude.csv",lon_dest,fmt="%.5f")
    print("# lat: %s" % len(lat_dest))
    print("# lon: %s" % len(lon_dest))
    meshcoord = np.meshgrid(lon_dest,lat_dest)
    meshpoints = np.array(meshcoord).T.reshape(-1,2)
    np.savetxt("meshpoints.csv",meshpoints,delimiter = ",",fmt="%.5f")

    latstart = latndx.min()
    lonstart = lonndx.min()
    latstop = latndx.max() + 1
    lonstop = lonndx.max() + 1

    
    # Now load the major datasets either from cache or query
    if from_cache:
        uwind=np.load("uwind.npy")
        vwind=np.load("vwind.npy")
        pres =np.load("pmsl.npy")
    else:
        subset = "u_component_wind_true_direction_all_geometries"
        uwind = data_wind.variables[subset][:,latstart:latstop,lonstart:lonstop]
        t=time_block_report("Fetched uwind %s", t)
        subset = "v_component_wind_true_direction_all_geometries"                               
        vwind = data_wind.variables[subset][:,latstart:latstop,lonstart:lonstop]
        t=time_block_report("Fetched vwind %s", t)
        data_wind.close()
                
        subset = "pressure_reduce_to_MSL"
        pres = data_pmsl.variables[subset][:,latstart:latstop,lonstart:lonstop]           
        t=time_block_report("Fetched pressure %s", t)
        data_pmsl.close()

    # Save to cache if requested
    if to_cache:
        np.savetxt("times.txt",times)    
        np.savetxt("x_merc.txt",x_merc)
        np.savetxt("y_merc.txt",y_merc)
        
    if to_cache:
        np.save("uwind",uwind)
        np.save("vwind",vwind)
        np.save("pmsl",pres)

    
    nfile = len(times) // 24
    
    hrs = times.astype(int)
    dayint = hrs // 24
    minday = dayint.min()
    maxday = dayint.max()
    dayrange = np.arange(minday,maxday+1)
    
    # This remaining loop processes the big (in time) download and stores it in daily 
    # blocks.
    for d,dy in enumerate(dayrange):
        print("Block: %s" % d)
        timendx, = np.where(dayint == dy)
        if len(timendx) == 24:
            lastgood = timendx
            assert np.all(times[timendx] == np.arange(dy*24,(dy+1)*24))
        elif len(timendx) == 0:
            print("empty index on block %s" % d)
            timendx = lastgood
            desired = np.arange(dy*24,(dy+1)*24)
        else:
            print("incomplete index on block %s" % d)
            desired = np.arange(dy*24,(dy+1)*24)
            timendx = np.searchsorted(times,desired,side="left")

        time_subset = times[timendx]
        
        # times are in hours since 1970-01-01
        base = dtm.datetime(1970,1,1) + dtm.timedelta(hours=dy*24)
        print("Base %s" % base.strftime("%Y-%m-%d %H:%M"))
        time_days = (time_subset - time_subset[0])/24.
        base_date_str = base.strftime("%Y-%m-%d")
        dest_time_unit = "days since %s" % base_date_str
        dest_time_base = base.year,base.month,base.day,base.hour
        dest_time_base = base.year,base.month,base.day,base.hour
        t=time_block_report("Calcs done:",t)
        
        datestr_for_file = base.strftime("%Y%m%d")
        outname = "%s_%s.nc" % (file_base,datestr_for_file)
        out = Dataset(outname,"w",format='NETCDF4')
        print("Created file: %s " % outname)
        

        subset = "u_component_wind_true_direction_all_geometries"
        uwind2 = uwind[timendx,:,:]
        if np.any(np.isnan(uwind2)):
            for i in range(uwinds.shape[0]):
                if np.any(np.isnan(uwind2[i,:,:])):
                    print("uwind[%s] has nan values: %s *************************" % (i,datestr_for_file))
                    
        subset = "v_component_wind_true_direction_all_geometries"                               
        vwind2 = vwind[timendx,:,:]
        if np.any(np.isnan(vwind2)):
            for i in range(vwinds.shape[0]):
                if np.any(np.isnan(vwind2[i,:,:])):
                    print("vwind[%s] has nan values: %s *************************" % (i,datestr_for_file))
            
        pres2 = pres[timendx,:,:]
        if np.any(np.isnan(pres2)):
            for i in range(pres2.shape[0]):
                if np.any(np.isnan(pres2[i,:,:])):
                    pres2[i,:,:] = pres2[i-1,:,:]
                    print("pres[%s] has nan values: %s *************************" % (i,datestr_for_file))
 
        ntime = pres2.shape[0]
        ny = pres2.shape[1]
        nx = pres2.shape[2]

        time=out.createDimension('time',None)
        lat=out.createDimension('ny_grid',ny)
        lon=out.createDimension('nx_grid',nx)
        
        times_dest = out.createVariable('time','f8',('time',))
        times_dest.long_name = "Time"
        times_dest.standard_name = "time"
        times_dest.units = dest_time_unit
        times_dest.base_date = dest_time_base
        times_dest[:] = time_days
        
        
        longitude = out.createVariable('lon','f4',('ny_grid','nx_grid',))
        longitude.long_name = "Longitude"
        longitude.standard_name = "longitude"
        longitude.units = "degrees_east"
        longitude[:,:] = meshcoord[0]
        
        latitude = out.createVariable('lat','f4',('ny_grid','nx_grid',))
        latitude.long_name = "Latitude"
        latitude.standard_name = "latitude"
        latitude.units = "degrees_north"
        latitude[:,:] = meshcoord[1]
        
        uwind_dest = out.createVariable('uwind','f4',('time','ny_grid','nx_grid',))
        uwind_dest.long_name = "Surface Eastward Air Velocity (10m AGL)"
        uwind_dest.standard_name = "eastward_wind"
        uwind_dest.units = "m/s"
        uwind_dest[:,:,:] = uwind2
        
        vwind_dest = out.createVariable('vwind','f4',('time','ny_grid','nx_grid',))
        vwind_dest.long_name = "Surface Northward Air Velocity (10m AGL)"
        vwind_dest.standard_name = "northward_wind"
        vwind_dest.units = "m/s"
        vwind_dest[:,:,:] = vwind2

        
        prmsl = out.createVariable('prmsl','f4',('time','ny_grid','nx_grid',)) 
        prmsl.long_name = "Pressure reduced to MSL"
        prmsl.standard_name = "air_pressure_at_sea_level"
        prmsl.units = "Pa"
        prmsl[:,:,:] = pres2
        
        out.sync()
        print("Creating dummy surface temp and humidity")
        
        stmp = out.createVariable('stmp','f4',('time', 'ny_grid', 'nx_grid',)) 
        stmp.long_name = "Surface Air Temperature (2m AGL)"
        stmp.standard_name = "air_temperature"
        stmp.units = "K"
        
        spfh = out.createVariable('spfh','f4',('time', 'ny_grid', 'nx_grid',))
        spfh.long_name = "Surface Specific Humidity (2m AGL)"
        spfh.standard_name = "specific_humidity"
        spfh.units = "1"
        out.close()
        print("Closed file: %s" % outname)


if __name__ == '__main__':
    lon_lo = -123.15
    lon_hi = -121.1
    lat_lo = 37.30
    #lat_hi = 38.90
    lat_hi = 39.0  # want nx != ny
    file_base = "cencoos_air"
    to_cache = True
    from_cache = False
    cencoos_schism_opendap(lat_lo,lon_lo,lat_hi,lon_hi,file_base,to_cache,from_cache)


