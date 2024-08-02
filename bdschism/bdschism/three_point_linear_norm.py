from matplotlib.colors import Normalize 
from matplotlib import cbook
from numpy import ma
import numpy as np

class ThreePointLinearNorm(Normalize):     
    def __init__(self,linthresh,vmin=None,vmax=None,clip=False): 
        Normalize.__init__(self,vmin,vmax,clip) 
        self.linthresh=float(linthresh) 
 
    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        if cbook.iterable(value):
            vtype = 'array'
            val = ma.asarray(value).astype(np.float)
        else:
            vtype = 'scalar'
            val = ma.array([value]).astype(np.float)

        self.autoscale_None(val)
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin==vmax:
            result = 0.0 * val
        else:
            vmin = float(vmin)
            vmax = float(vmax)
            if clip:
                mask = ma.getmask(val)
                val = ma.array(np.clip(val.filled(vmax), vmin, vmax),
                                mask=mask)
            result = np.where (val <= self.linthresh,0.5*(val-vmin)/(self.linthresh-vmin),0.5+0.5*(val-self.linthresh) / (vmax-self.linthresh))
            
        if vtype == 'scalar':
            result = result[0]
        return result

    def inverse(self, value):
        
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        vmin = float(self.vmin)
        vmax = float(self.vmax)

        if cbook.iterable(value):
            val = ma.asarray(value)
            ret = np.where(val < 0.5, vmin + val*2*(self.linthresh - vmin), self.linthresh + (val-0.5)*2*(vmax-self.linthresh))
            #print val
            #print ret
            return ret
        else:
            if (val < 0.5):
                return vmin + value*2*(self.linthresh - vmin)
            else:
                return self.linthresh + value*2*(vmax-self.linthresh)
                
    def autoscale(self, A):
        '''
        Set *vmin*, *vmax* to min, max of *A*.
        '''
        self.vmin = ma.min(A)
        self.vmax = ma.max(A)

    def autoscale_None(self, A):
        ' autoscale only None-valued vmin or vmax'
        if self.vmin is None: self.vmin = ma.min(A)
        if self.vmax is None: self.vmax = ma.max(A)

    def scaled(self):
        'return true if vmin and vmax set'
        return (self.vmin is not None and self.vmax is not None)
    
    