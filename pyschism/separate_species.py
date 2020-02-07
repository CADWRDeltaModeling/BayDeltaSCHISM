""" Separation of tidal data into species
    The key function in this module is separate_species, which decomposes
    tides into subtidal, diurnal, semidiurnal and noise components. 
    A demo function is also provided that reads tide series (6min intervl) 
    from input files, seperates  the species, writes results and optionally plots
    an example
"""
import argparse
from vtools.datastore.read_ts import read_ts
import datetime as dtm
from vtools.functions.filter import cosine_lanczos
from vtools.data.vtime import hours,minutes


def separate_species(ts,noise_thresh_min=40):
    """Separate species into subtidal, diurnal, semidiurnal and noise components

        Input:
             ts: timeseries to be decomposed into species, assumed to be
             at six minute intervals. The filters used
             have long lenghts, so avoid missing data and allow for four extra
             days worth of data on each end.

        Output:
              four regular time series, representing subtidal, diurnal, semi-diurnal and noise
    """
    
    # the first filter eliminates noise
    ts_denoise= cosine_lanczos(ts,cutoff_period=minutes(noise_thresh_min))
    ts_noise=ts-ts_denoise   # this is the residual, the part that IS noise
    
    # the filter length assumes 6 minute data. The resulting filter is 90 hours
    # long which is MUCH longer than the default because this filter has to be
    # really sharp
    assert ts.index.freq == minutes(6)
    # 14.5 hours = 870min
    ts_diurnal_and_low=cosine_lanczos(ts_denoise,cutoff_period=minutes(870),
                                      filter_len=900)
    ts_semidiurnal_and_high=ts_denoise-ts_diurnal_and_low

    # The resulting filter is again 90 hours
    # long which is still a bit longer than the default. Again,
    # we want this filter to be pretty sharp.
    #ts_sub_tide=cosine_lanczos(ts_diurnal_and_low,cutoff_period=hours(40),
    #                           filter_len=900)
    ts_sub_tide=cosine_lanczos(ts_denoise,cutoff_period=hours(40),
                               filter_len=900)
    ts_diurnal=ts_diurnal_and_low-ts_sub_tide
    return ts_sub_tide,ts_diurnal,ts_semidiurnal_and_high, ts_noise
    
    
def write_th(filename,ts_output):
    """This works fine for fairly big series"""
    fout=open(filename,"w")
    st = ts_output.ticks[0]
    for el in ts_output:
        tck = float(el.ticks - st)
        fout.write("%-12.1f %6.4f\n" % (tck,el.value))
    fout.close()   
    

def plot_result(ts,ts_semi,ts_diurnal,ts_sub_tide,station):
    import matplotlib.pyplot as plt
    fig, ((ax1,ax2),(ax3,ax4)) = plt.subplots(2,2,sharex=True)
            
    ax1.plot(ts.times,ts.data,color="black",linewidth=1,label="Original data")
    ax1.legend(loc="lower right") #,prop=legend_font)     
    ax1.set_ylabel("Elev (m)")
    ax1.grid(b=True, which='both', color='0.9', linestyle='-', linewidth=0.5)
   

    ax2.plot(ts_semi.times,ts_semi.data,
             color="black",linewidth=1,label="Semidiurnal") 
    ax2.legend(loc="lower right")
    ax2.set_ylabel("Elev (m)")
    ax2.grid(b=True, which='both', color='0.9', linestyle='-', linewidth=0.5)
    
    ax3.plot(ts_diurnal.times,ts_diurnal.data,
             color="black",linewidth=1,label="Diurnal") 
    ax3.legend(loc="lower right")
    ax3.set_ylabel("Elev (m)")
    ax3.grid(b=True, which='both', color='0.9', linestyle='-', linewidth=0.5)

    ax4.plot(ts_sub_tide.times,ts_sub_tide.data,
             color="black",linewidth=1,label="Subtidal")         
    ax4.legend(loc="lower right") 
    ax4.set_ylabel("Elev (m)")
    ax4.grid(b=True, which='both', color='0.9', linestyle='-', linewidth=0.5)

    fig.tight_layout()    
    fig.autofmt_xdate()
    plt.show()
    #plt.savefig('tidal_species_%s.png'%station,bbox_inches=0)
    plt.close(fig)
    

################# command line application #####################
def create_arg_parser():
    import textwrap
    parser = argparse.ArgumentParser(
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog = textwrap.dedent(
      """ 
         ============== Example ==================
      > separate_species.py --stime=2009-03-12 --etime=2010-01-01 --label="San Francisco" --outprefix=sf --plot 9414290_gageheight.csv
      """),
      description= """Script to filter a tide into its subtidal, diurnal and semidiurnal components (and residual noise"""
    )
    parser.add_argument('--stime',default = None, required=False, help = "Start time in ISO-like format 2009-03-12T00:00:00. Time part and 'T' are optional.")
    parser.add_argument('--etime', default = None, required=False, help = 'End time.')
    parser.add_argument('--plot',default = False, required=False, action='store_true', help = 'Plot time series in matplotlib')
    parser.add_argument('--label',default='Tide',required=False,help='Label for station in plots')
    parser.add_argument('--outprefix', default=None, help = 'Output file prefix (species name will be added). If omitted, the label will be used')    
    parser.add_argument('infile', help = 'Input file.')
    
    return parser


def main():   
    parser = create_arg_parser()
    args = parser.parse_args()
    if args.stime:
        sdate=dtm.datetime(*list(map(int, re.split('[^\d]', args.stime)))) # convert start time string input to datetime
    else:
        sdate = None
    if args.etime:
        edate=dtm.datetime(*list(map(int, re.split('[^\d]', args.etime)))) # convert start time string input to datetime
    else:
        edate = None
    data_file = args.infile
    station_name = args.label
    outprefix = args.outprefix
    if not outprefix: 
        outprefix=station_name.replace(" ","_")
    do_plot=args.plot
    
    ts= read_ts(data_file, None, None)
    astart = max(ts.start,sdate-days(5)) if sdate else ts.start
    aend = min(ts.end,edate+days(5)) if edate else ts.end
    ts_sub,ts_diurnal,ts_semi, ts_noise=separate_species(ts.window(astart,aend))   
   
    
    comps = [(ts_noise,"noise"), 
             (ts_semi,"semi_over"),
             (ts_diurnal,"diurnal"),
             (ts_sub,"subtidal")]   
 
    for comp in comps:
        ts_output=comp[0].window(sdate,edate)
        output_file=outprefix+"_"+comp[1]+".th"
        write_th(output_file,ts_output)

    if do_plot:
        plot_result(ts.window(sdate,edate),
                ts_semi.window(sdate,edate),
                ts_diurnal.window(sdate,edate),
                ts_sub.window(sdate,edate),
                station_name)



def run_example():
    """ This is the data for the example. 
        Note that you want the data to 
        be at least 4 days longer than the desired output
    """
    start=dtm.datetime(2009,2,18)
    end=dtm.datetime(2010,11,24)

    out_st=dtm.datetime(2009,3,12)
    out_end=dtm.datetime(2010,11,2)

    sf_path="../9415020_gageheight.csv"
    ts= read_ts(sf_path, start, end)

    print("separating reys...")
    separate_species(ts,"rey",out_st,out_end,do_plot=True)

    print("all done")



if __name__=='__main__':
    main()
    #run_example()
