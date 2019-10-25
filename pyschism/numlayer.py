
import random

import numpy

from deap import algorithms
from deap import base
from deap import creator
from deap import tools
import numpy as np


def evalOneMax(individual):
    return sum(individual),

def cxTwoPointCopy(ind1, ind2):
    """Execute a two points crossover with copy on the input individuals. The
    copy is required because the slicing in numpy returns a view of the data,
    which leads to a self overwritting in the swap operation. It prevents
    ::
    
        >>> import numpy
        >>> a = numpy.array((1,2,3,4))
        >>> b = numpy.array((5.6.7.8))
        >>> a[1:3], b[1:3] = b[1:3], a[1:3]
        >>> print(a)
        [1 6 7 4]
        >>> print(b)
        [5 6 7 8]
    """
    size = len(ind1)
    cxpoint1 = random.randint(1, size)
    cxpoint2 = random.randint(1, size - 1)
    if cxpoint2 >= cxpoint1:
        cxpoint2 += 1
    else: # Swap the two cx points
        cxpoint1, cxpoint2 = cxpoint2, cxpoint1

    ind1[cxpoint1:cxpoint2], ind2[cxpoint1:cxpoint2] \
        = ind2[cxpoint1:cxpoint2].copy(), ind1[cxpoint1:cxpoint2].copy()
        
    return ind1, ind2
    
    
def cxUniform(ind1, ind2):
    """Executes a uniform crossover that modify in place the two
    :term:`sequence` individuals. The attributes are swapped accordingto the
    *indpb* probability.
    
    :param ind1: The first individual participating in the crossover.
    :param ind2: The second individual participating in the crossover.
    :param indpb: Independent probabily for each attribute to be exchanged.
    :returns: A tuple of two individuals.
    
    This function uses the :func:`~random.random` function from the python base
    :mod:`random` module.
    """
    do_cross = np.random.rand(len(ind1)) < 0.5
    ind1_copy = ind1.copy()
    ind1[do_cross] = ind2[do_cross]
    ind2[do_cross] = ind1_copy[do_cross]
    return ind1, ind2



class LayerEval(object):
    def __init__(self,depth,sides,nlayer,minlayer,maxlayer):
        self.depth=depth
        self.sides=sides
        self.nlayer_base = nlayer.copy()
        self.uniform_width = depth/nlayer
        self.minlayer = minlayer
        #self.changeable =  (nlayer >= minlayer) & (nlayer < maxlayer) & (depth>1.0) & (maxlayer > minlayer)
        globalmaxnlayer = np.max(maxlayer)
        self.changeable =  (nlayer >= minlayer) & (nlayer < globalmaxnlayer) & (depth>1.0)         
        self.state_size = np.count_nonzero(self.changeable)
        self.multiplier = 1.5
        self.sidethresh = self.multiplier*(depth[sides[:,0]] + depth[sides[:,1]])
        self.sidethresh /= (self.nlayer_base[sides[:,0]] + self.nlayer_base[sides[:,1]])  
        sidediff = np.abs(depth[sides[:,0]] - depth[sides[:,1]])        
        sidegood = sidediff<self.sidethresh
        self.eligible_edge=sides[sidegood,0:2]   
        self.depthdiff = depth[self.eligible_edge[:,0]] - depth[self.eligible_edge[:,1] ]        
        
    def __call__(self,individual):
        nlayer = self.nlayer_base.copy()
        nlayer[self.changeable] += individual
        layerdiff = nlayer[self.eligible_edge[:,0]] - nlayer[self.eligible_edge[:,1]]
        layerdepthprod = layerdiff*self.depthdiff
        alignfac = np.where(layerdepthprod>0.,1.,2.)
        alignfac[self.depthdiff==0]=1.5
        bad = np.sum(np.absolute(layerdiff)*alignfac,axis=0)
        return bad,
        
    #def benefit(self):
        
def tabu_numlayer(depth,sides,nlayer,minlayer,maxlayer,ngen=60):
    from collections import deque

    # todo hardwire 1.0
    changeable =  (nlayer >= minlayer) & (nlayer < maxlayer) & (depth>1.0) & (maxlayer > minlayer)
    
    layer_eval = LayerEval(depth,sides,nlayer,minlayer,maxlayer)    
    changeable = layer_eval.changeable
    if not np.any(changeable):
        print("No nodes had a changeable # layers")
        return nlayer.copy()
    else:
        print("%s changeable nodes" % np.sum(changeable))
    
    gafit = layer_eval(0*nlayer[changeable])
    print("Initial GA fitness %s" % gafit)    
    MAXTABU = 300
    base = nlayer.copy()       
    best = np.zeros_like(base)    # list of best 0-1 increments to nlayer so far at each node
    active = best.copy()
    tabu_list = deque([])
    benefit = np.zeros_like(base,dtype='d')   # accumulates benefit of node swapping zero and one in best
    
    eligible_edge=layer_eval.eligible_edge
    depthdiff = layer_eval.depthdiff 
    
    since_improve = 0
    best_ever = 1e10
    best_nlayer = None
    iter = 0
    cumben = 0.
    best_cumben=0.
    while since_improve  < 400:
        #print "Iteration %s: " % iter
        benefit[:] = 0.             # every iteration we reset to zero and icrement edge-by-edge
        work = base + active        # current best nlayer, including base and adjustment
        # difference in nlayer across edge using best soln' so far
        work_layer_diff = work[eligible_edge[:,0]] - work[eligible_edge[:,1] ]
        layerdepthprod = work_layer_diff*depthdiff
        alignfac =      np.where(layerdepthprod>0,1.,2.)
        alignfac[depthdiff==0.]=1.5
        alignfac_lo = alignfac
        alignfac_hi = alignfac
        alignfac_lo[work_layer_diff==0] = np.where(depthdiff>0,1,2)[work_layer_diff==0]
        alignfac_hi[work_layer_diff==0] = np.where(depthdiff>0,2,1)[work_layer_diff==0]
        
        # this is the only change allowed, adding one to a node of zero, subtracting one from a node of 1
        change = np.where(active==0,1,-1)
        
        # note that benefits can be less than zero
        benefit_lo = np.where(work_layer_diff<0,change[eligible_edge[:,0]]*alignfac_lo,-change[eligible_edge[:,0]]*alignfac_lo)
        benefit_lo[work_layer_diff==0] = -1*alignfac_lo[work_layer_diff==0]

        benefit_hi = np.where(work_layer_diff>0,change[eligible_edge[:,1]]*alignfac_hi,-change[eligible_edge[:,1]]*alignfac_hi)
        benefit_hi[work_layer_diff==0] = -1*alignfac_hi[work_layer_diff==0]

        np.add.at(benefit,eligible_edge[:,0],benefit_lo) 
        np.add.at(benefit,eligible_edge[:,1],benefit_hi)

        for tabu in tabu_list:
            ndx = np.abs(tabu) - 1
            if tabu < 0 and change[ndx] < 0: benefit[ndx] = -10000
            if tabu > 0 and change[ndx] > 0: benefit[ndx] = -10000
        benefit[~changeable] = -10000
        
        best_candidate =  np.argmax(benefit)
        
        #print "Best candidate = %s and benefit = %s" % (best_candidate,benefit[best_candidate])        
        
        #preveval = layer_eval(active[changeable])
        active[best_candidate] += change[best_candidate]        

        # The added +1 here is needed so that index zero is handled OK 
        # when multiplied by change    
        tabu_list.append((1+best_candidate)*change[best_candidate])
        if len(tabu_list) > MAXTABU: 
            #print tabu_list
            tabu_list.popleft()
        
        nlayernew = base + active

        bad = layer_eval(active[changeable])
        #print "Actual change: %s" % (bad[0]-preveval[0])
        
        
        if bad[0] < best_ever: 
            best_ever = bad[0]
            best_nlayer = nlayernew
            best_adjust = active
            since_improve = 0
        else:
            since_improve += 1
        evalfit = layer_eval(active[changeable])
        
        if iter % 100 == 0 or since_improve == 400:
            print("Iteration %s: Badness: %s Best ever = %s" % (iter,bad,best_ever))
        iter +=1
              
    return best_nlayer
