import matplotlib.pyplot as plt


import numpy as np
import numpy.ma as ma
import sys
from scipy.signal import medfilt
from scipy.stats.mstats import mquantiles

def med_outliers(ts,level=4.,scale = None,\
                 filt_len=7,range=(None,None),
                 quantiles = (0.25,0.75),
                 copy = True):
    """
    Detect outliers by running a median filter, subtracting it
    from the original series and comparing the resulting residuals
    to a global robust range of scale (the interquartile range).
    Individual time points are rejected if the residual at that time point is more than level times the range of scale. 

    The original concept comes from Basu & Meckesheimer (2007)
    although they didn't use the interquartile range but rather
    expert judgment. To use this function effectively, you need to
    be thoughtful about what the interquartile range will be. For instance,
    for a strongly tidal flow station it is likely to 
    
    level: Number of times the scale or interquantile range the data has to be
           to be rejected.d

    scale: Expert judgment of the scale of maximum variation over a time step.
           If None, the interquartile range will be used. Note that for a 
           strongly tidal station the interquartile range may substantially overestimate the reasonable variation over a single time step, in which case the filter will work fine, but level should be set to 
           a number (less than one) accordingly.

    filt_len: length of median filter, default is 5
    
    quantiles : tuple of quantiles defining the measure of scale. Ignored
          if scale is given directly. Default is interquartile range, and
          this is almost always a reasonable choice.

    copy: if True, a copy is made leaving original series intact

    You can also specify rejection of values based on a simple range

    Returns: copy of series with outliers replaced by nan
    """
    print("level")
    print(level)
    import warnings
    ts_out = ts.copy() if copy else ts
    warnings.filterwarnings("ignore")
    if not range[0] is None:
        ts_out.data[ts_out.data < range[0]] = np.nan
        
    if not range[1] is None:
        ts_out.data[ts_out.data> range[1]] = np.nan

    #ts_out.data = ts_out.data.flatten()
    if ts_out.data.ndim == 1:
        filt = medfilt(ts_out.data,filt_len)
    else:
        filt = np.apply_along_axis(medfilt,0,ts_out.data,filt_len)
    res = ts_out.data - filt

    if not scale:
        low,high = mquantiles(res[~ np.isnan(res)],quantiles)
        scale = high - low 
        print("scale")
        print(scale)
    outlier = (np.absolute(res) > level*scale) | (np.absolute(res) < -level*scale)
    ts_out.data[outlier]= np.nan

    warnings.resetwarnings()

    filt = None #rts(filt,ts.start,ts.interval)
    
    return ts_out, filt

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
    from read_ts import read_cdec
    station = sys.argv[1]
    ts = read_cdec("cdec_download/%s.csv"%station,start=None,end=None)

    filt = medfilt(ts.data, kernel_size=5)
    ts,filt = med_outliers(ts,quantiles=[0.2,0.8],range=[120.,None],copy = False)

    plt.plot(ts.times,ts.data,label="data")
    plt.plot(ts.times,filt.data,label="filt")
    plt.plot(ts.times,ts.data-filt.data,label="res")
    plt.legend()
    plt.show()