# -*- coding: utf-8 -*-
"""

"""


# Define Infinite (Using INT_MAX 
# caused overflow problems)
INT_MAX = 10000
 
# Given three collinear points p, q, r, 
# the function checks if point q lies
# on line segment 'pr'
def onSegment(p:tuple, q:tuple, r:tuple) -> bool:
     
    if ((q[0] <= max(p[0], r[0])) &
        (q[0] >= min(p[0], r[0])) &
        (q[1] <= max(p[1], r[1])) &
        (q[1] >= min(p[1], r[1]))):
        return True
         
    return False
 
# To find orientation of ordered triplet (p, q, r).
# The function returns following values
# 0 --> p, q and r are collinear
# 1 --> Clockwise
# 2 --> Counterclockwise
def orientation(p:tuple, q:tuple, r:tuple) -> int:
     
    val = (((q[1] - p[1]) *
            (r[0] - q[0])) -
           ((q[0] - p[0]) *
            (r[1] - q[1])))
            
    if val == 0:
        return 0
    if val > 0:
        return 1 # Collinear
    else:
        return 2 # Clock or counterclock
 
def doIntersect(p1, q1, p2, q2):
     
    # Find the four orientations needed for 
    # general and special cases
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)
 
    # General case
    if (o1 != o2) and (o3 != o4):
        return True
     
    # Special Cases
    # p1, q1 and p2 are collinear and
    # p2 lies on segment p1q1
    if (o1 == 0) and (onSegment(p1, p2, q1)):
        return True
 
    # p1, q1 and p2 are collinear and
    # q2 lies on segment p1q1
    if (o2 == 0) and (onSegment(p1, q2, q1)):
        return True
 
    # p2, q2 and p1 are collinear and
    # p1 lies on segment p2q2
    if (o3 == 0) and (onSegment(p2, p1, q2)):
        return True
 
    # p2, q2 and q1 are collinear and
    # q1 lies on segment p2q2
    if (o4 == 0) and (onSegment(p2, q1, q2)):
        return True
 
    return False
 
# Returns true if the point p lies 
# inside the polygon[] with n vertices
def is_inside_polygon(points:list, p:tuple) -> bool:
     
    n = len(points)
     
    # There must be at least 3 vertices
    # in polygon
    if n < 3:
        return False
         
    # Create a point for line segment
    # from p to infinite
    extreme = (INT_MAX, p[1])
    count = i = 0
     
    while True:
        next = (i + 1) % n
         
        # Check if the line segment from 'p' to 
        # 'extreme' intersects with the line 
        # segment from 'polygon[i]' to 'polygon[next]'
        if (doIntersect(points[i],
                        points[next],
                        p, extreme)):
                             
            # If the point 'p' is collinear with line 
            # segment 'i-next', then check if it lies 
            # on segment. If it lies, return true, otherwise false
            if orientation(points[i], p,
                           points[next]) == 0:
                return onSegment(points[i], p,
                                 points[next])
                                  
            count += 1
             
        i = next
         
        if (i == 0):
            break
         
    # Return true if count is odd, false otherwise
    return (count % 2 == 1)



###############################################################################################
#
# Read coarse grid
coarse_path = ".//bay_delta_coarse_v4.gr3"
coarse_f = open(coarse_path,'r')
coarse_data = coarse_f.readlines()
numEN = coarse_data[1].split()
nCoarseEle = int(numEN[0])
nCoarseNd = int(numEN[1])

c_nID = []
c_nX = []
c_nY = []

c_eID = []
c_eNd_List = []
c_eNum_Nd = []

for ii in range(2,nCoarseNd+2):
    line_data = coarse_data[ii].split()
    c_nID.append(int(line_data[0]))
    c_nX.append(float(line_data[1]))
    c_nY.append(float(line_data[2]))
    
startEl = nCoarseNd+2
endEl = nCoarseNd+2 + nCoarseEle

for ii in range(startEl,endEl):
    line_data = coarse_data[ii].split()
    c_eID.append(int(line_data[0]))
    c_eNum_Nd.append(int(line_data[1]))
    c_eNd_List.append(line_data[2:])
    
coarse_f.close()


# Read fine grid
fine_path = ".//hgrid.gr3"
fine_f = open(fine_path,'r')
fine_data = fine_f.readlines()
numEN = fine_data[1].split()
nFineEle = int(numEN[0])
nFineNd = int(numEN[1])

f_nID = []
f_nX = []
f_nY = []

f_eID = []
f_eNd_List = []
f_eNum_Nd = []

for ii in range(2,nFineNd+2):
    line_data = fine_data[ii].split()
    f_nID.append(int(line_data[0]))
    f_nX.append(float(line_data[1]))
    f_nY.append(float(line_data[2])) 

    
fine_f.close()

# Build map and weights
f_c_ele_map = []
f_c_ele_wghts = []
map_f = open(".//mapped_dwr.txt",'w')
for ii in range(nFineNd):
    #find encompassing element
    print(ii)
    f_point = [f_nX[ii],f_nY[ii]]
    
    isInElement = 0
    
    for jj in range(nCoarseEle):
        #get point list
        points = []
        for kk in range(c_eNum_Nd[jj]):
            indx = int(c_eNd_List[jj][kk])-1
            points.append([c_nX[indx],c_nY[indx]])
            
        if(is_inside_polygon(points,f_point)):
            #save element node indices #1-based index
            f_c_ele_map.append(c_eNd_List[jj])
            isInElement = 1
            
            #compute and save weighting factors
            weights = []
            for kk in range(len(points)):
                dx = points[kk][0]-f_point[0]
                dy = points[kk][1]-f_point[1]
                dist2 = dx*dx + dy*dy
                
                if(dist2 > 0):
                    weights.append(1.0/dist2)
                else:
                    weights.clear()
                    for ll in range(len(points)):
                        if(ll!=kk):
                            weights.append(0.0)
                        else:
                            weights.append(1.0)
                    break
             
            f_c_ele_wghts.append(weights)               
            break                 
       
        points.clear()
    
    if(isInElement == 0):
        #find closest element
        closest = 0
        dx = c_nX[0]-f_point[0]
        dy = c_nY[0]-f_point[1]
        closest_dist = dx*dx+dy*dy
        for jj in range(1,nCoarseNd):
            dx = c_nX[jj]-f_point[0]
            dy = c_nY[jj]-f_point[1]
            dist = dx*dx+dy*dy
            if dist < closest_dist:
                closest = jj
                closest_dist = dist
            
        f_c_ele_map.append([closest])
        f_c_ele_wghts.append([1])

    

        
    numElNodes=len(f_c_ele_map[ii]) #1-based index
    map_f.write("{0} {1}".format(f_nID[ii], numElNodes))
                
    for jj in range(numElNodes): #1-based index
        map_f.write(" {0}".format(f_c_ele_map[ii][jj]))
        
    for jj in range(numElNodes):    
        map_f.write(" {0}".format(f_c_ele_wghts[ii][jj]))
        
    map_f.write("\n")
    
    f_point.clear()

map_f.close()