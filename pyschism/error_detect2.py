import matplotlib.pyplot as plt
from read_ts import read_cdec
from vtools.data.api import rts
import numpy as np
import numpy.ma as ma
import sys
from scipy.signal import medfilt
from scipy.stats.mstats import mquantiles
from scipy.stats import iqr as scipy_iqr

'''
    3 functions to detect (and replace with NaN) any outliers or bad data
    
    norepeats: catches any repeated values. This will often occur if the sensor
    is not working properly, and since realistically the value will always be
    slightly changing, repeats are a clear sign of a malfunctioning device.
    
    Inputs: ts:         the time series
            threshold:  the minimum number of repeated values in a row that 
                        should be caught (default value is currently 20 but
                        should be changed)
            copy:       if True (default), a copy is made, leaving the original
                        series intact
    
    Output:             time series object with repeats replaced by NaNs



    bounds: replaces any values outside of user-specified bounds with NaN. This
    is useful for values that are clear sensor errors, such as water
    temperatures of 600 degrees or negative conductivity values.
    
    Inputs: ts:         the time series
            lbound:     the lower bound, default value is None for no bound
            ubound:     the upper bound, default value is None for no bound
            copy:       if True (default), a copy is made, leaving the original
                        series intact
    
    Output:             time series object with bad values replaced by NaNs
    
    
    
    med_outliers: uses a median filter on a rolling window to detect any
    outliers, making two passes. The function subtracts the median of a window
    centered on each value from the value itself, and then compares this
    difference to the interquartile range on said window. If the difference
    is too large relative to the IQR, the value is marked as an outlier. 
    The original concept comes from Basu & Meckesheimer (2007) although they 
    didn't use the interquartile range but rather expert judgment. This is
    an option here as well, if there is a known value that can be inserted,
    but otherwise the IQR is recommended.
    
    The function completes two passes, first a secondary pass on a large window
    (a couple days) and then the main pass on a window of default 7 values. The
    main pass is more accurate, but gets messed up when there are many outliers
    near each other, hence the secondary pass.
    
    Inputs: ts:             the time series
            secfilt:        boolean whether or not to make the secondary pass
                            (default True)
            level:          the number of times the IQR the distance between
                            the median and value can be before the value is
                            considered an outlier (default 3.0)
            scale:          the manual replacement for the IQR (default None)
            filt_len:       the length of the window (must be odd, default 7)
            quantiles:      a tuple of quantiles as the bounds for the IQR
                            (numbers between 0 and 100)
            seclevel:       same as level but for the larger pass
            secscale:       same as scale but for the larger pass
            secfilt_len:    same as filt_len but for the larger pass
            secquantiles:   same as quantiles but for the larger pass
            copy:           if True (default), a copy is made, leaving the
                            original series intact
            
            Output:         time series object with outliers replaced by NaNs
'''

def norepeats(ts, threshold = 20, copy = True):

    import warnings
    ts_out = ts.copy() if copy else ts
    warnings.filterwarnings("ignore")
    a = list(ts.data[0:threshold])

    for k in range(len(ts.data)):
        del a[0]
        a.append(ts.data[k])

        if a[1:] == a[:-1]:
            b = k - (threshold - 1)
            while a[0] == ts.data[k]:
                k += 1
            ts_out.data[b:k] = np.NaN
            a.append(ts.data[k])

    return ts_out    


def bounds(ts, lbound = None, ubound = None, copy = True):

    import warnings
    ts_out = ts.copy() if copy else ts
    warnings.filterwarnings("ignore")

    #Range filter - anything outside of the specified range will be removed
    if not lbound is None:
        ts_out.data[ts_out.data < lbound] = np.nan

    if not ubound is None:
        ts_out.data[ts_out.data > ubound] = np.nan

    return ts_out


def med_outliers(ts,secfilt=True,level=3.0,scale=None,filt_len=7,
                 quantiles=(25,75),seclevel=3.0,secscale=None,
                 secfilt_len=241,secquantiles=(25,75),copy=True):

    import warnings
    ts_out = ts.copy() if copy else ts
    warnings.filterwarnings("ignore")
    
    #Secondary filter - median filter is first applied on a larger scale
    if secfilt:
            #ts_out.data = ts_out.data.flatten()
        if ts_out.data.ndim == 1:
            filt = medfilt(ts_out.data,secfilt_len)
        else:
            filt = np.apply_along_axis(medfilt,0,ts_out.data,secfilt_len)
        res = ts_out.data - filt


        for k in range(len(ts.data)):
            if not secscale:
                slicelow = int(max(0, k-((secfilt_len - 1)/2)))
                slicehigh = int(min(len(ts.data), k + ((secfilt_len - 1)/2) + 1))
                rwindow = ts.data[slicelow:slicehigh]
                iqr = scipy_iqr(rwindow[~np.isnan(rwindow)], None, secquantiles)
                #low,high = mquantiles(rwindow[~ np.isnan(rwindow)],secquantiles)
                #iqr = high - low
            else:
                iqr = secscale
                
            if (res[k] > seclevel*iqr) or (res[k] < -seclevel*iqr):
                ts_out.data[k]= np.nan

    #Main filter - performs a median filter on the data
    #ts_out.data = ts_out.data.flatten()
    if ts_out.data.ndim == 1:
        filt = medfilt(ts_out.data,filt_len)
    else:
        filt = np.apply_along_axis(medfilt,0,ts_out.data,filt_len)
    res = ts_out.data - filt

    for k in range(len(ts.data)):
        if not scale:
            slicelow = int(max(0, k-((filt_len - 1)/2)))
            slicehigh = int(min(len(ts.data), k + ((filt_len - 1)/2) + 1))
            rwindow = ts.data[slicelow:slicehigh]
            iqr = scipy_iqr(rwindow[~np.isnan(rwindow)], None, secquantiles)
            #low,high = mquantiles(rwindow[~ np.isnan(rwindow)],quantiles)
            #iqr = high - low
        else:
            iqr = scale

        if (res[k] > level*iqr) or (res[k] < -level*iqr):
            ts_out.data[k]= np.nan

    warnings.resetwarnings()

    filt = None #rts(filt,ts.start,ts.interval)

    return ts_out

def rolling_window(data, block):
    shape = data.shape[:-1] + (data.shape[-1] - block + 1, block)
    strides = data.strides + (data.strides[-1],)
    return np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)


def despike(arr, n1=2, n2=20, block=10):
    offset = arr.min()
    arr -= offset
    data = arr.copy()
    roll = rolling_window(data, block)
    roll = ma.masked_invalid(roll)
    std = n1 * roll.std(axis=1)
    mean = roll.mean(axis=1)
    # Use the last value to fill-up.
    std = np.r_[std, np.tile(std[-1], block - 1)]
    mean = np.r_[mean, np.tile(mean[-1], block - 1)]
    mask = (np.abs(data - mean.filled(fill_value=np.NaN)) >
            std.filled(fill_value=np.NaN))
    data[mask] = np.NaN
    # Pass two: recompute the mean and std without the flagged values from pass
    # one now removing the flagged data.
    roll = rolling_window(data, block)
    roll = ma.masked_invalid(roll)
    std = n2 * roll.std(axis=1)
    mean = roll.mean(axis=1)
    # Use the last value to fill-up.
    std = np.r_[std, np.tile(std[-1], block - 1)]
    mean = np.r_[mean, np.tile(mean[-1], block - 1)]
    mask = (np.abs(arr - mean.filled(fill_value=np.NaN)) >
            std.filled(fill_value=np.NaN))
    arr[mask] = np.NaN
    return arr + offset


if __name__ == '__main__':
    # Just an example
    station = sys.argv[1]
    ts = read_cdec("cdec_download/%s.csv"%station,start=None,end=None)

    filt = medfilt(ts.data, kernel_size=5)
    ts,filt = med_outliers(ts,quantiles=[0.2,0.8],range=[120.,None],copy=False)

    plt.plot(ts.times,ts.data,label="data")
    plt.plot(ts.times,filt.data,label="filt")
    plt.plot(ts.times,ts.data-filt.data,label="res")
    plt.legend()
    plt.show()