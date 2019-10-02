#!/usr/bin/env python
import sys
import ogr

def read_keyfile(keyfile):
    """ Reads a file pairing labels and values"""
    keys = {}
    with open(keyfile,"r") as kf:
        for line in kf:
            if line and len(line) > 2:
                key, val = line.strip().split()
                keys[key] = float(val)
    return keys

    

def create_poly(shapefile,dsetname,keyfile,polyfile,type,default=None):
    """ Converts a polygon shapefile to the yaml input of the preprocessor"""
    keys = read_keyfile(keyfile)
    names = set()
    
    f=open(polyfile,"w")
    ds = ogr.Open( shapefile )
    if ds is None:
        print("Open failed.\n")
        sys.exit( 1 )
    print("Opening dataset: %s" % ds.GetLayer(0).GetName())
        
    lyr = ds.GetLayerByName(dsetname)

    lyr.ResetReading()
    if default: f.write("default: %s\n\n" % default)
    f.write("polygons:\n")
    
    
    for feat in lyr:
        feat_defn = lyr.GetLayerDefn()
        #name = "poly_" + feat.GetFieldAsString(3).strip()
        label = feat.GetFieldAsString(2).strip()
        print("Name: %s" % (label))

        #print "mindepth %s" %rough
        #for i in range(feat_defn.GetFieldCount()):
            #field_defn = feat_defn.GetFieldDefn(i)

            # # Tests below can be simplified with just :
            # # print feat.GetField(i)
            # if field_defn.GetType() == ogr.OFTInteger:
                # print "int %d" % feat.GetFieldAsInteger(i)
            # elif field_defn.GetType() == ogr.OFTReal:
                # print "real %.3f" % feat.GetFieldAsDouble(i)
            # elif field_defn.GetType() == ogr.OFTString:
                # print "string %s" % feat.GetFieldAsString(i)
            # else:
                # print "string %s" % feat.GetFieldAsString(i)
        
                
        geom = feat.GetGeometryRef()
        if geom is not None and geom.GetGeometryType() == ogr.wkbPolygon:
            val = keys[label]
            f.write("  %s:\n" % label)
            f.write("    attribute: %s \n" % val)
            f.write("    type: %s\n" % type)
            f.write("    vertices:\n")
            for ring in geom:
                #f.write("%s %s %s None\n" %(label,ring.GetPointCount(),val))
                points = ring.GetPointCount()
                for p in range(points):
                    x,y,z = ring.GetPoint(p)
                    f.write("      %s %s\n" % (x,y))
    ds = None
    f.close()
    
def create_arg_parser():
    import argparse
    parser = argparse.ArgumentParser(description='Convert shapefile from SMS into polygon format for preprocessor')
    parser.add_argument(dest='shapefile',default = None, help = 'name of shapefile')
    parser.add_argument(dest='dset',default = None, help = 'name of dataset inside shapefile')
    parser.add_argument('--keyfile', default = None, help = 'file mapping material property names to numerical values (space separated).')
    parser.add_argument('--out',default = None, help='Output polygon file.')
    parser.add_argument('--type',default='min',help='Polygon attribute type (min/max)')
    parser.add_argument('--default',default=None,help='Global default in polygon specs')
    
    return parser


if __name__ == "__main__":
    parser = create_arg_parser()
    args = parser.parse_args()
    shapefile = args.shapefile
    dsetname = args.dset
    keyfile = args.keyfile
    polyfile = args.out
    type = args.type
    default = args.default
    create_poly(shapefile,dsetname,keyfile,polyfile,type,default)
    
    