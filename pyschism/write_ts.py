
def write_ts(ts,fname,dateformat="%Y-%m-%d %H:%M",fmt="%.2f",header=None,sep=','):
    """ Estimate missing values within a time series by interpolation. 

    Parameters
    ----------

    ts: :class:`~vtools.data.timeseries.TimeSeries`
        The time series to be stored
    fname: string
        Output file name or path    
    dateformat: string
        Date format compatible with datetime.datetime.strftime        
    fmt: string
        Value format compatible withy numpy.savetxt        
    header: string
        Header to add to top of file        
    sep: string
        Delimieter for fields, often a space or comma

    Returns
    -------
    
    Examples
    --------
    
    Writing csv format with date format 2009-03-15 21:00 and space separated values
    
    >>> write_ts(ts,"test.csv","%Y-%m-%d %H:%M","%.2f,%.2f","Datetime,u,v",",")

    Write vtide format with same format and space separated values,
    this time taking advantage of defaults
    
    >>> write_ts(ts,"test_vtide.dat",sep = " ")
    
    Writing cdec format, with csv values and date and time separated. The header
    is generated with the cdec_header helper function
    
    >>> head = cdec_header("practice.csv",ts,"PST","Wind Vel","m/s")
    >>> write_ts(ts,"test_cdec.csv",CDECDATEFMT,"%.2f",header=head)

    
    """
    with open(fname,'w') as f:
        if not header is None:
            head = header if header.endswith('\n') else header + '\n'
            f.write(header+'\n')
        
        v0 = ts[0].value
        fmtval = lambda x: fmt % x       
        try:
            test = fmtval(v0)
        except:
            try:
                fmtval = lambda x: fmt % tuple(x)
            except:
                fmtval = lambda z: sep.join([fmt % x for x in z])
                try:
                    fmtval(v0)
                except:
                    raise ValueError("Can't use supplied format %s to format value: %s" % (fmt,v0))
        for el in ts:
            dstring = el.time.strftime(dateformat)
            vstring = fmtval(el.value)
            f.write("%s%s%s\n" % (dstring,sep,vstring))
            

def cdec_header(fname,ts,tz,var=None,unit=None):
    """ Helper function to create a cdec-like header
    Requres some metadata like time zone, variable name and unit which will be
    pulled from series if omitted from input.
    
    Parameters
    ----------
    fname: str
        Output file name or path

    ts: :class:`~vtools.data.timeseries.TimeSeries`
        The time series to be stored
        
    tz: string
        Time zone of data 
        
    var: string
        Variable name      
        
    unit: string
        Unit of the time series
        
    Returns
    -------
    head: string
        CDEC-style header    
        
    """

    title = "Title: \"%s\"\n" % fname.upper()
    if var is None:
        var = ts.props[VARIABLE]
        unit = ts.props[UNIT]
    line2 = "0000,%s,\'%s (%s)\'" % (tz,var,unit)
    return title+line2
    
CDECDATEFMT = "%Y%m%d,%H%M"


#write_ts(ts,"test.csv","%Y-%m-%d %H:%M","%.2f,%.2f","Datetime,u,v",",")
#header=cdec_header("practice.csv","UTC","Wind Vel","m/s")
#write_ts(ts,"test_cdec.csv",CDECDATEFMT,"%.2f",header=cdec_header("practice.csv","UTC","Wind Vel","m/s"))
#write_ts(ts,"test_vtide.dat",sep = " ")


