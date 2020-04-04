import numpy as np
from scipy.optimize import brentq

# Constants for conversions
J1 = -16.072
J2 =  4.1495
J3 = -0.5345
J4 =  0.0261

K1 =  0.0120
K2 = -0.2174
K3 = 25.3283
K4 = 13.7714
K5 = -6.4788
K6 =  2.5842
k = 0.0162
s_sea = 35.
ec_sea=53087.0

M2FT = 3.28084
FT2M = 0.3048
CFS2CMS = 0.028316847
CMS2CFS = 35.31466621


def m_to_ft(x):
    """ Convert meter to foot
        WARNING: The function modifies the input argument if it is TimeSeries
    """
    try:
        x.props['unit'] = 'ft'
        x.data *= M2FT
        return x
    except:
        return x * M2FT


def ft_to_m(x):
    """ Convert foot to meter
    """
    try:
        x.props['unit'] = 'm'
        x.data *= FT2M
        return x
    except:
        return x * FT2M


def cms_to_cfs(x):
    """ Convert cms to cfs
    """
    try:
        x.props['unit'] = 'cfs'
        x.data *= CMS2CFS
        return x
    except:
        return x * CMS2CFS


def cfs_to_cms(x):
    """ Convert cfs to cms
    """
    try:
        x.props['unit'] = 'cms'
        x.data *= CFS2CMS
        return x
    except:
        return x * CFS2CMS


def fahrenheit_to_celcius(x):
    """ Convert cfs to cms
    """
    try:
        x.props['unit'] = 'deg C'
        x.data -= 32.
        x.data *= 5. / 9.
        return x
    except:
        return (x - 32.) * 5. / 9.


def celcius_to_fahrenheit(x):
    """ Convert cfs to cms
    """
    try:
        x.props['unit'] = 'deg F'
        x.data *= 1.8
        x.data += 32.
        return x
    except:
        return x * 1.8 + 32.


def psu_ec_resid(x,psu,hill_correction):
    return  ec_psu_25c(x,hill_correction)-psu


def ec_psu_25c(ts_ec,hill_correction=True):
    """ Convert scalar or vector ec to psu assuming 25C temperature
        and no low salinity correction
        Note: The input argument, ts_ec, will be altered.
    """
    try:
        ts_ec.props['unit'] = 'PSU'
        ec = ts_ec.data
    except:
        ec = ts_ec
    R = np.divide(ec,ec_sea)
    sqrtR = np.sqrt(R)
    Rsq = R * R
    s = K1 + K2*sqrtR + K3*R + K4*R*sqrtR + K5*Rsq + K6*Rsq*sqrtR
    k = 0.0162
    f = (25.-15.)/(1.+k*(25.-15.))
    if hill_correction:
        y = 100.*R
        x = 400.*R
        a_0 = 0.008
        b_0_f = 0.0005*f  # = f(T=25)*0.0005
        sqrty = np.sqrt(y)
        s = s - a_0/(1.0+1.5*x+x*x) - b_0_f/(1.+ sqrty + y+ y*sqrty)
    try:
        ts_ec.props['unit'] = 'PSU'
        ts_ec.data = s
        return ts_ec
    except:
        return s


def psu_ec_25c_scalar(psu,refine=True,hill_correction=True):
    ''' Conversion from psu to ec for a scalar. If used without refinement,
        this is the Schemel conversion, otherwise uses root-finding
        Note that the round trip ec-psu-ec tends to wander a lot without refine = True.
        The refinement usually takes 4-6 iterations
    '''
    if psu < 0.:
        raise ValueError("Negative psu not allowed: {}".format(psu))
    elif np.isnan(psu): return np.nan

    if (hill_correction and not refine):
        raise ValueError("Unrefined (refine=False) psu-to-ec correction cannot have hill_correction")
    if refine:
        if psu > 34.99969:
            raise ValueError("psu is over sea salinity: %s" % psu)
        ec = brentq(psu_ec_resid,1.,ec_sea,args=(psu,hill_correction))
    else:
        sqrtpsu=np.sqrt(psu)
        ec = (psu/s_sea)*ec_sea + psu*(psu-s_sea)*(J1 + J2*sqrtpsu + J3*psu + J4*sqrtpsu*psu)
    return ec


psu_ec_25c_vec = np.vectorize(psu_ec_25c_scalar,otypes='d',excluded=["refine","hill_correction"])


def psu_ec_25c(psu,refine=True,hill_correction=True):
    ''' Conversion from psu to ec. If used without refinement,
        this is the Schemel conversion, otherwise uses root-finding
        Note that the round trip ec-psu-ec tends to wander a lot without refine = True.
        The refinement usually takes 4-6 iterations
    '''
    if type(psu) == float:
        return psu_ec_25c_scalar(psu,refine,hill_correction)
    else:
        try:
            out = psu.copy()
            out.loc[:,:] = psu_ec_25c_vec(psu.to_numpy(),refine,hill_correction)
            return out
        except:	
            return psu_ec_25c_vec(psu,refine,hill_correction)


if __name__ == '__main__':
     import sys
     if "--help" in sys.argv:
         print("Usage:")
         print("unit_conversions.py conversion input [input...]")
         print("where")
         print("conversion is the op to perform, only ec_psu and psu_ec currently supported")
         print("input      can be multiple values")
     elif sys.argv[1] == "ec_psu":
         ec = np.array(sys.argv[2:],dtype='d')
         psu = ec_psu_25c(ec,True)
         print(psu)
     elif sys.argv[1] == "psu_ec":
         psu = np.array(sys.argv[2:],dtype='d')
         ec = psu_ec_25c(psu)
         print(ec)
         #ec_round = psu_ec_25c(psu,True,True)
         #print ec_round
