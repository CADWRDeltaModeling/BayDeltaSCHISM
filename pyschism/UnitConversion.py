# -*- coding: utf-8 -*-
"""
Created on Fri Nov  8 16:04:28 2019

@author: zzhang
"""

def Salinity2SpConductance(salinity):
    """ converting salinity (psu) to specific conductance at 25 degC (uS/cm@25degC)
    Reference: https://water.ca.gov/LegacyFiles/iep/newsletters/2001/IEPNewsletterWinter2001.pdf
    """
    J1 = -16.072
    J2 = 4.1495
    J3 = -0.5345
    J4 = 0.0261
    X25 =  (salinity/35)*53087.0 + \
    salinity*(salinity-35)*(J1 + J2*salinity**0.5 + J3*salinity + J4*salinity**1.5)
    return X25

def SpConductance2Salinity(SpConductance):
    """ converting specific conductance at 25 degC with unit uS/cm@25degC
    and return salinity (psu or parts per thousand)
    Reference: https://water.ca.gov/LegacyFiles/iep/newsletters/2001/IEPNewsletterWinter2001.pdf
    """
    # convert input us/cm to ms/cm first;53.087 corrsponds to seawater salinity (35)
    R = SpConductance/1000/53.087
    k1 = 0.0120
    k2 = -0.2174
    k3 = 25.3283
    k4 = 13.7714
    k5 = -6.4788
    k6 = 2.5842

    salinity = k1 + k2*R**0.5 + k3*R + k4*R**(3/2) + k5*R**2 + k6*R**(5/2)
    return salinity

if __name__ == "__main__":
    salinity = 10
    SpConductance = Salinity2SpConductance(salinity)
    salinity_solved = SpConductance2Salinity(SpConductance)
    print(salinity_solved)

