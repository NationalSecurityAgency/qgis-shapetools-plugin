import math
from qgis.core import QgsUnitTypes, QgsPointXY
from qgis.PyQt.QtCore import QCoreApplication

from .settings import geod

def tr(string):
    return QCoreApplication.translate('Processing', string)

DISTANCE_LABELS=[tr("Kilometers"),tr("Meters"),tr("Nautical Miles"),tr("Miles"),tr('Yards'),tr("Feet")]

def conversionToMeters(units):
    if units == 0: # Kilometers
        measureFactor = 1000.0
    elif units == 1: # Meters
        measureFactor = 1.0
    elif units == 2: # Nautical Miles
        measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters)
    elif units == 3: # Miles
        measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceMeters)
    elif units == 4: # Yards
        measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceYards, QgsUnitTypes.DistanceMeters)
    elif units == 5: # Feet
        measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters)
    return measureFactor
    
def normalizeLongitude(pts):
    ptlen = len(pts)
    for i in range(ptlen):
        pts[i].setX( (pts[i].x() + 180) % 360 - 180)
        
def checkIdlCrossings(pts):
    outseg = []
    ptlen = len(pts)
    pts2 = [pts[0]]
    for i in range(1,ptlen):
        if pts[i-1].x() < -120 and pts[i].x() > 120: # We have crossed the date line going west
            ld = geod.Inverse(pts[i-1].y(), pts[i-1].x(), pts[i].y(), pts[i].x())
            try:
                (intrlat, intrlon) = intersection_point(-89,-180, 0, pts[i-1].y(), pts[i-1].x(), ld['azi1'])
                ptnew = QgsPointXY(-180, intrlat)
                pts2.append(ptnew)
                outseg.append(pts2)
                ptnew = QgsPointXY(180, intrlat)
                pts2 = [ptnew]
            except:
                pts2.append(pts[i])
        if pts[i-1].x() > 120 and pts[i].x() < -120: # We have crossed the date line going east
            ld = geod.Inverse(pts[i-1].y(), pts[i-1].x(), pts[i].y(), pts[i].x())
            try:
                (intrlat, intrlon) = intersection_point(-89,180, 0, pts[i-1].y(), pts[i-1].x(), ld['azi1'])
                ptnew = QgsPointXY(180, intrlat)
                pts2.append(ptnew)
                outseg.append(pts2)
                ptnew = QgsPointXY(-180, intrlat)
                pts2 = [ptnew]
            except:
                pts2.append(pts[i])
        else:
            pts2.append(pts[i])
    outseg.append(pts2)

    return(outseg)

def intersection_point(lat1, lon1, bearing1, lat2, lon2, bearing2):
    o1 = math.radians(lat1)
    lam1 = math.radians(lon1)
    o2 = math.radians(lat2)
    lam2 = math.radians(lon2)
    bo_13 = math.radians(bearing1)
    bo_23 = math.radians(bearing2)
    
    diff_fo = o2 - o1
    diff_la = lam2 - lam1
    d12 = 2 * math.asin(math.sqrt(math.sin(diff_fo / 2) * math.sin(diff_fo / 2) + math.cos(o1) * math.cos(o2) * math.sin(diff_la / 2) * math.sin(diff_la / 2)))
    if d12 == 0: # intersection_not_found
        raise ValueError('Intersection not found')

    bo_1 = math.acos((math.sin(o2) - math.sin(o1) * math.cos(d12)) / (math.sin(d12) * math.cos(o1)))
    bo_2 = math.acos((math.sin(o1) - math.sin(o2) * math.cos(d12)) / (math.sin(d12) * math.cos(o2)))
    if math.sin(lam2 - lam1) > 0:
        bo_12 = bo_1
        bo_21 = 2 * math.pi - bo_2
    else:
        bo_12 = 2 * math.pi - bo_1
        bo_21 = bo_2
    a_1 = ((bo_13 - bo_12 + math.pi) % (2 * math.pi)) - math.pi
    a_2 = ((bo_21 - bo_23 + math.pi) % (2 * math.pi)) - math.pi
    if (math.sin(a_1) == 0) and (math.sin(a_2) == 0): # infinite intersections
        raise ValueError('Intersection not found')
    if math.sin(a_1) * math.sin(a_2) < 0: # ambiguous intersection
        raise ValueError('Intersection not found')

    a_3 = math.acos(-math.cos(a_1) * math.cos(a_2) + math.sin(a_1) * math.sin(a_2) * math.cos(d12))
    be_13 = math.atan2(math.sin(d12) * math.sin(a_1) * math.sin(a_2), math.cos(a_2) + math.cos(a_1) * math.cos(a_3))
    fo_3 = math.asin(math.sin(o1) * math.cos(be_13) + math.cos(o1) * math.sin(be_13) * math.cos(bo_13))
    diff_lam13 = math.atan2(math.sin(bo_13) * math.sin(be_13) * math.cos(o1), math.cos(be_13) - math.sin(o1) * math.sin(fo_3))
    la_3 = lam1 + diff_lam13

    return (math.degrees(fo_3), math.degrees(la_3))
        
def GCdistanceTo(lat1, lon1, lat2, lon2, R=6371000.0):
    '''Compute the distance between two points. The average earth
       radius is 6371000 meters. The returned distance is in the same
       units as R which by default is meters'''
    phi1 = math.radians(lat1)
    lambda1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lambda2 = math.radians(lon2)
    deltaphi = phi2 - phi1
    deltalambda = lambda2 - lambda1
    a = (math.sin(deltaphi/2.0) * math.sin(deltaphi/2.0)
          + math.cos(phi1) * math.cos(phi2)
          * math.sin(deltalambda/2.0) * math.sin(deltalambda/2.0))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))
    d = R * c
    return d

def GCintermediatePointTo(lat1, lon1, lat2, lon2, fraction):
    '''Return the fractional point between [lat1, lon1] and [lat2, lon2]
       Coordinates are in degrees and fraction is between 0 and 1'''
    phi1 = math.radians(lat1)
    lambda1 = math.radians(lon1)
    phi2 = math.radians(lat2)
    lambda2 = math.radians(lon2)
    sinphi1 = math.sin(phi1)
    cosphi1 = math.cos(phi1)
    sinlambda1 = math.sin(lambda1)
    coslambda1 = math.cos(lambda1)
    sinphi2 = math.sin(phi2)
    cosphi2 = math.cos(phi2)
    sinlambda2 = math.sin(lambda2)
    coslambda2 = math.cos(lambda2)

    # distance between points
    deltaphi = phi2 - phi1
    deltalambda = lambda2 - lambda1
    a = math.sin(deltaphi/2.0) * math.sin(deltaphi/2.0) + math.cos(phi1) * math.cos(phi2) * math.sin(deltalambda/2.0) * math.sin(deltalambda/2.0)
    delta = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0-a))

    A = math.sin((1.0-fraction)*delta) / math.sin(delta)
    B = math.sin(fraction*delta) / math.sin(delta)

    x = A * cosphi1 * coslambda1 + B * cosphi2 * coslambda2
    y = A * cosphi1 * sinlambda1 + B * cosphi2 * sinlambda2
    z = A * sinphi1 + B * sinphi2

    phi3 = math.atan2(z, math.sqrt(x*x + y*y))
    lambda3 = math.atan2(y, x)

    # Returns lat, lon and normalize lon from -180 to 180 degrees
    return math.degrees(phi3), ((math.degrees(lambda3)+540.0)%360.0 - 180.0)

def GCgetPointsOnLine(lat1, lon1, lat2, lon2, minSegLength=1000.0, maxNodes=500):
    '''Get points along a great circle line between the two coordinates.
       minSegLength is the minimum segment length in meters before a new
       node point is created. maxNodes is the maximum number of points on
       the line to create.'''
    dist = GCdistanceTo(lat1, lon1, lat2, lon2)
    numPoints = int(dist / minSegLength)
    if numPoints > maxNodes:
        numPoints = maxNodes
    pts = [QgsPointXY(lon1, lat1)]
    f = 1.0 / (numPoints - 1.0)
    i = 1
    while i < numPoints-1:
        newlat, newlon = GCintermediatePointTo(lat1, lon1, lat2, lon2, f * i)
        pts.append(QgsPointXY(newlon, newlat))
        i += 1
    pts.append(QgsPointXY(lon2, lat2))
    return pts
