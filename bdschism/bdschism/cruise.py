import datetime as dtm
from profile_plot import profile_plot
import matplotlib.pyplot as plt
from matplotlib.font_manager import fontManager, FontProperties
from matplotlib import ticker, cm
import sys
import pandas as pd
import numpy as np
import os
import re
from dateutil import parser
import errno
from shutil import copyfile
import subprocess
import argparse
import textwrap
import pdb
RED = (228/256., 26/256., 28/256.)
BLUE = (55/256., 126/256., 184/256.)

plt.style.use(['seaborn-paper','seaborn-colorblind'])

def process_stations(station_file):
    sd=pd.read_csv(station_file,names=["id","x","y","dist_km","elev_navd","name","depth_mllw"],header=0,dtype={"id":pd.StringDtype()})
    
    for i in range(sd.shape[0]):
        station=sd["id"][i]
        if station.endswith(".0"): 
            station = station[:-2]
            sd.at[i,"id"]=station

    sd=sd.set_index('id')
    sd.dist_km=sd.dist_km/1000.0
    return sd
    

def process_cruise(path):
    print ("process_cruise")
    cruisefile = open(path,'r')
    cruisetxt = cruisefile.readlines()[2:]
    cruisefile.close()
    cruiselines = [line.strip().split(",") for line in cruisetxt if (line != "\n")]
    cruise_data = {}
 
    for entry in cruiselines:
        #time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%m/%d/%Y %H:%M")
        time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%Y-%m-%d %H:%M")
        station = entry[2]
        if station.endswith(".0"): 
            station = station[:-2]

        if not station in cruise_data.keys():
            cruise_data[station] = ([],[],time)
        depth = float(entry[3])
        try:
            salinity = float(entry[4])
        except ValueError:
            print(path+" station no."+station+" has invalid salinity observation!")
            cruise_data.pop(station,None)
            continue
        cruise_data[station][0].append(depth)
        cruise_data[station][1].append(salinity)
    for station in cruise_data.keys():
        time = cruise_data[station][2]
        depth = np.array(cruise_data[station][0])
        salinity = np.array(cruise_data[station][1])
        depthorder = np.argsort(depth)
        depth = depth[depthorder]
        salinity = salinity[depthorder]
        cruise_data[station] = (depth,salinity,time)
    return cruise_data


def process_xyt(path,casts,base_time):
    print ("process_xyt")
    cruisefile = open(path,'r')
    cruisetxt = cruisefile.readlines()
    cruisefile.close()
    cruiselines = [line.strip().split() for line in cruisetxt if (line != "\n")]
    cruise_data = {}
  
    for entry in cruiselines:
        castno = int(entry[0])
        salt = float(entry[1])
        depth = -float(entry[2])
        elapsed = 24.*3600.*float(entry[4])
        time = base_time + dtm.timedelta(seconds=elapsed)
        station = casts[castno][4]
      
        if not station in cruise_data.keys():
            cruise_data[station] = ([],[],time)
        cruise_data[station][0].append(depth)
        cruise_data[station][1].append(salt)
    for station in cruise_data.keys():
        time = cruise_data[station][2]
        depth = np.array(cruise_data[station][0])
        salinity = np.array(cruise_data[station][1])
        depthorder = np.argsort(depth)
        depth = depth[depthorder]
        salinity = salinity[depthorder]
        cruise_data[station] = (depth,salinity,time)
    return cruise_data
    
    
def match_cruise(time, station, x, z, times, data):
    times = np.array(times)
    ndxR = np.searchsorted( times, time)
    ndxL = max(ndxR - 1,0)
    if not (time >= times[0] and time <= times[-1]):
        raise ValueError("Time %s (in days) is not in model file spanning from %s to %s" % (time, times[0], times[-1]))
    wl = (times[ndxR] - time)/(times[ndxR] - times[ndxL])
    wr = 1 - wl
    station_ndx = station.data_index
    profile = wl*data[ndxL,:,station_ndx] + wr*data[ndxR,:,station_ndx]

    xx = x[:,station_ndx]
    zz = z[:,station_ndx]
    ndx_farleft = max(ndxL-2, 0)
    ndx_farright = min(ndxR+3, len(times))
    surrounding_profiles = [(time, profile)]
    for n in range(ndx_farleft,ndx_farright):
        t = times[n]
        vals = data[n,:,station_ndx]
        surrounding_profiles.append((t, vals))            
    return zz, surrounding_profiles
    
def do_depth_plot(station,cruise_data,surrounding_profiles,ax,xlabel,ylabel,add_legend = False):

    profiles = []
    all_lines = []
    col = None
    i = 0
    for i,prof in enumerate(surrounding_profiles):
        p = np.array(prof[1])
        zz = np.array(prof[0])
        p = np.ma.masked_where(np.isnan(p),p)
        z_masked = np.ma.masked_where(np.isnan(p),zz)
        linestyle = "solid"
        if (i == 0): 
            col = BLUE
            label = "Model"
            wide = 2
        else:
            col = "0.55"
            wide = 1
            label = "Model +/- 3 hr" if label == "Model" else "_nolegend_"
            linestyle = "--"
        line, = ax.plot(p,z_masked,color = col, linewidth = wide, linestyle = linestyle)
        i += 1
        all_lines.append(line)
    
    depth,salinity,time = cruise_data
    line, = ax.plot(salinity,depth,color = RED, label = "Observed", linewidth = 2)
    all_lines.append(line)
    ax.set_ylim(max(z_masked),0)
    min_data,max_data = ax.get_xlim()
    xcenter =  (min_data+max_data)/2
    xrange = max_data - min_data
    if xrange <8.0:
        print (" > 8")
        #ax.set_xlim(max(0,min_data-3.5), min(35,max_data+3.5))
    if xlabel != None:
        ax.set_xlabel(xlabel, size = 14)
    if ylabel != None:
        ax.set_ylabel('Depth (m)', size = 14)
    if add_legend:
        leg=ax.legend((all_lines[0],all_lines[1],all_lines[-1]),('Model','Model +/- 3 hr','Observed'),loc='lower left',\
                   shadow=True, fancybox=True)

        ltext  = leg.get_texts()  # all the text.Text instance in the legend
        llines = leg.get_lines()  # all the lines.Line2D instance in the legend
        #frame.set_facecolor('0.80')      # set the frame face color to light gray
        #ax.setp(ltext, fontsize='small')    # the legend text fontsize
        #ax.setp(llines, linewidth=1.5)      # the legend linewidth
      
    #ax.set_xlim(0,35)
        
        
def longitudinal(cruise_data,station_data,ax,context_label=None,add_labels=False,xlabel=None,xmin=None,xmax=None,max_depth=None):
    print ("Longitudinal")
    
    maxdepth = 0
    stations = []
    station_dists = []
    bedx=[]
    bed=[]
    for item in cruise_data.keys():
        if (station_data.loc[item].dist_km > 0.0):
            #print "Station %s" % item
            #print cruise_data[item]
            maxdepth=max(maxdepth, max(cruise_data[item][0]))
            
            stations.append(item)        
            station_dists.append(station_data.loc[item].dist_km)
            bedx.append(station_data.loc[item].dist_km)
            bed.append( -max(cruise_data[item][0]))
    station_dists = np.array(station_dists)
    stations = np.array(stations)
    sorted_dists = np.argsort(station_dists)
    stations = stations[sorted_dists]
    station_dists = station_dists[sorted_dists]
    nstation = len(station_dists)
    ndepth = int(maxdepth + 1)
    salt = np.ones((ndepth,nstation),dtype=float) * np.nan
    zloc = np.ones((ndepth,nstation),dtype=float) * np.nan
    from scipy.interpolate import griddata
    for i in range(nstation):
        item = stations[i]
        depth,salinity,time = cruise_data[item]
        salt[:,i] = griddata(depth,salinity,np.arange(ndepth,dtype=float))
        if np.isnan(salt[0,i]): salt[0,i] = salt[1,i]
        #zloc[0:len(salinity),i] = depth

    pdb.set_trace()
    xloc,zloc = np.meshgrid(station_dists, np.arange(ndepth,dtype=float))
    im, cs, ttxt = profile_plot(xloc,zloc,salt,ax,context_label,add_labels,xlabel,xmin,xmax,max_depth)

    return cs
    

def model_data_for_longitude(cruise_data,station_data,x, z, times, model_data, base_date):
    maxdepth = 0
    stations = []
    station_dists = []
    # todo: this is boilerplate
    for item in cruise_data.keys():
        if (station_data[item].dist_km > 0.0):
            maxdepth=max(maxdepth, max(cruise_data[item][0]))
            stations.append(item)        
            station_dists.append(station_data[item].dist_km)
            
    station_dists = np.array(station_dists)
    stations = np.array(stations)
    sorted_dists = np.argsort(station_dists)
    stations = stations[sorted_dists]
    station_dists = station_dists[sorted_dists]
    nstation = len(station_dists)
    ndepth = int(maxdepth + 1)


    long_data = {}
    for station_id in stations:
        cruise_profile = cruise_data[station_id]
        cruise_time = cruise_profile[2]
        rt = (cruise_time - base_date).total_seconds()/(24*3600) 
        zz,profiles = match_cruise(rt, station_data[station_id], x, z, times, model_data)
        prof = profiles[0]
        long_data[station_id] = (zz,prof[1],prof[0])

    return long_data

    
def cruise_xyt(path,station_data,base_time,outfile): 
    print ("cruise_xyt")
    cruisefile = open(path,'r')
    cruisetxt = cruisefile.readlines()[2:]
    cruisefile.close()
    cruiselines = [line.strip().split(",") for line in cruisetxt if (line != "\n")]
    cruise_locs = []
    processed = []
    casts = {}
    for entry in cruiselines:
        if len(entry) < 2: continue
        #time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%m/%d/%Y %H:%M")
        time = dtm.datetime.strptime("%s %s" % (entry[0],entry[1]), "%Y-%m-%d %H:%M")
        elapsed = (time - base_time).total_seconds()
        station = entry[2]
        if station.endswith(".0"): 
            station = station[:-2]
        if not station in processed:
            sd=station_data.loc[station]
            processed.append(station)
            cruise_locs.append((sd.x,sd.y,elapsed,sd.name,station))
    
    with open(outfile,"w") as out:
        out.write("Cruise cast model requests\n%s\n" % len(cruise_locs))
        for i,loc in enumerate(cruise_locs):
            jj = i+1
            locentries = (jj,loc[0],loc[1],loc[2],loc[3])
            out.write("%s %s %s %s   ! %s\n"  % locentries)
            #out.write("%s %s %s      ! %s\n"  % loc)
            #print (locentries)
            casts[jj] = loc
    return casts
        
def gen_profile_plot(base_date,cruise_time,survey_file,model_file,station_file,xytfile):
    filename = survey_file   
    station_data = process_stations(station_file)
    cruise_data =  process_cruise(filename)
    casts = cruise_xyt(filename,station_data,base_date,xytfile)
    model_data = process_xyt(model_file,casts,base_date)
    fig, (ax0,ax1) = plt.subplots(2,1,sharex=True)
    fig.set_size_inches(10,6)
    
    context = cruise_time.strftime("USGS: %d-%b-%Y")

    longitudinal(cruise_data,station_data,ax0,context_label = context ,xmin=20,xmax=104,max_depth=30)

    cs=longitudinal(model_data,station_data,ax1,context_label = "Model",add_labels=True,
                 xlabel="Distance from Golden Gate (km)",xmin=20,xmax=104,max_depth=30)
    # shared colorbar
    fig.subplots_adjust(right=0.8)
   # cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
    cbar_ax = fig.add_axes([0.85, 0.15, 0.05, 0.7])
    cb = fig.colorbar(cs, cax=cbar_ax,shrink=0.01)
    cb.set_label("Salinity (psu)", size = 14)  
    plt.savefig("salinity_profile_"+cruise_time.strftime("%m_%d_%Y"),dpi=300)
    #plt.show() 
        
def main(base_date,cruise_time,obs_file,model_file,station_file,xytfile):
    filename = obs_file
    station_data = process_stations(station_file)
    cruise_data =  process_cruise(filename)  

    casts = cruise_xyt(filename,station_data,base_date,xytfile)
    model_data = process_xyt(model_file,casts,base_date)    
    fig, axes = plt.subplots(2,2,sharex=True)
    
    #x,z,times,model_data = process_data(station_data,model_outfile)
    choices = ["657","649","2","3"]
    #choices = ["10","13","14","15"]


    nchoice = len(choices)
    for ichoice in range(nchoice):
        ax = axes[ichoice%2,int(ichoice/2)]
        #pdb.set_trace()
        choice = choices[ichoice]
        cruise_profile = cruise_data[choice]
        cruise_time = cruise_profile[2]
        station = station_data.loc[choice]
        model_profile = model_data[choice]
        #ax = axes[ichoice%2,ichoice/2]
        title = station.name + "(%s km) " % np.round(station.dist_km)
        ax.set_title(title)
        xlabel = "Salinity (psu)" if ichoice in (1,3) else None
        ylabel = "Depth (m)" if ichoice in (0,1) else None
        print ("ichoice: %s %s" % (ichoice,xlabel))
        #add_legend = (ichoice == (nchoice - 1))
        add_legend = (ichoice == 0)
        surrounding_profiles = [model_profile]
        do_depth_plot(station,cruise_profile, surrounding_profiles,ax,xlabel,ylabel,add_legend)       
    plt.show()
    

    
def gen_station_xyt(base_date,cruise_time,survey_file,station_file,xytfile):
    filename = survey_file   
    station_data = process_stations(station_file)
    cruise_data =  process_cruise(filename)
    casts = cruise_xyt(filename,station_data,base_date,xytfile)
    
    
def create_arg_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog="cruise.py",
        description=textwrap.dedent(
            """
      Loop over a number of USGS polaris cruise water quality data in a folder, read observed salinity
      data, generate station.xyt file and extract SCHISM model salinity from output nc files respectively. 
      Finally plot and compared observed and model transect salinity profile along the centerline took
      by USGS polaris cruise.
      
      Inputs: SCHISM model base time, a path containing SCHISM output files and a path
      containing USGS polaris water quaility data files.
      
      Outputs: A png files comparing observed and model salinity profile.
      
      USGS polaris cruise data should have csv format like below:
          
          Date,Time,Station Number,Depth,Salinity,Temperature
          MM/DD/YYYY,24 hr.,,[meters],[psu],[°C]
          6/22/2017,7:20,2,1,0.14,22.48
          6/22/2017,7:20,2,2,0.13,22.48
          6/22/2017,7:20,2,3,0.13,22.48
          6/22/2017,7:20,2,4,0.13,22.48
          ......
      
      Here is a example of command
      
      python cruise.py --data_path ./ --start 04/18/2017 --schism_output_path I:\\itp\\hist_2017\\
          
    
      Your system should include SCHISM postprocess tool path in the environment.
        
      You can get help by typing $ cruise.py  --help
      """))

   
    parser.add_argument('--data_path', default=None,required=True,
                                help='path contains downloaded USGS crusier water quality data')

    parser.add_argument('--start', type=str,required=True,
                                help='Starting date and time basis for SCHISM model output')
    parser.add_argument('--schism_output_path', default=None,required=True,
                                help='path contains SCHISM output NC files')


    
    return parser

    
if __name__== "__main__":


    usgs_cruise_file_lst=[]
    
    
    aug_parser = create_arg_parser()
    args = aug_parser.parse_args()
    data_folder=args.data_path
    base_date=parser.parse(args.start)
    schism_output_folder=args.schism_output_path
    
    
    schism_vgrid_in=os.path.join(schism_output_folder,"vgrid.in")
    if not(os.path.exists(schism_vgrid_in)):
        raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), schism_vgrid_in)
    schism_output_in=os.path.join(schism_output_folder,"read_output_xyt.in")
    if not(os.path.exists(schism_output_in)):
        raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), schism_output_in)
    
    station_file="usgs_cruise_stations_fix_dry.csv"
    
    
    if not(os.path.exists(os.path.join(data_folder,station_file))):
        raise FileNotFoundError( errno.ENOENT, os.strerror(errno.ENOENT), os.path.join(data_folder,station_file))
            
    usgs_cruise_match=re.compile("usgs_cruise_(?P<date>[0-9]{8}).(csv|txt)")
    for file_name in os.listdir(data_folder):
        match_re=usgs_cruise_match.match(file_name)
        if match_re:
            print("processing crusier data "+file_name)
            cruise_time=parser.parse(match_re.group("date"))
            xyt_file="station.xyt"
            gen_station_xyt(base_date,cruise_time,os.path.join(data_folder,file_name),os.path.join(data_folder,station_file),xyt_file)
            copyfile(xyt_file,os.path.join(schism_output_folder,xyt_file))
            cmd = ['read_output9_xyt']
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,cwd=schism_output_folder)
            for line in p.stdout:
                print(line)
            p.wait()
            if (p.returncode):
                raise ChildProcessError("Fail to extract schism outputs")
            model_salt="salt_"+match_re.group("date")
            copyfile(os.path.join(schism_output_folder,"fort.18"),os.path.join(schism_output_folder,model_salt))
            gen_profile_plot(base_date,cruise_time,os.path.join(data_folder,file_name),os.path.join(schism_output_folder,model_salt),os.path.join(data_folder,station_file),os.path.join(schism_output_folder,xyt_file))
            
            

