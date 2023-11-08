"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import re
from geographiclib.geodesic import Geodesic
from qgis.core import QgsUnitTypes, QgsPointXY, QgsPoint, QgsGeometry, QgsExpression, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsWkbTypes
from qgis.utils import qgsfunction
from .settings import epsg4326, geod, settings
from .compass import Compass

# import traceback

group_name = 'Shape Tools'

def transform_coords(y, x, crs):
    coord_crs = QgsCoordinateReferenceSystem(crs)
    transform = QgsCoordinateTransform(coord_crs, epsg4326, QgsProject.instance())
    pt = transform.transform(x, y)
    return(pt.y(), pt.x())

def transform_geom(geom, crs):
    coord_crs = QgsCoordinateReferenceSystem(crs)
    transform = QgsCoordinateTransform(coord_crs, epsg4326, QgsProject.instance())
    geom = transform.transform(geom)
    return(geom)

def InitShapeToolsFunctions():
    QgsExpression.registerFunction(st_from_meters)
    QgsExpression.registerFunction(st_to_meters)
    QgsExpression.registerFunction(st_geodesic_distance)
    QgsExpression.registerFunction(st_geodesic_bearing)
    QgsExpression.registerFunction(st_geodesic_transform)
    QgsExpression.registerFunction(st_compass)

def UnloadShapeToolsFunctions():
    QgsExpression.unregisterFunction('st_from_meters')
    QgsExpression.unregisterFunction('st_to_meters')
    QgsExpression.unregisterFunction('st_geodesic_distance')
    QgsExpression.unregisterFunction('st_geodesic_bearing')
    QgsExpression.unregisterFunction('st_geodesic_transform')
    QgsExpression.unregisterFunction('st_compass')

comp = Compass()
def compass(azimuth, res, mode):
    if mode == 'trad':
        if res == 32:  # 32 points
            s = comp.traditional(degree=azimuth)
        elif res == 16:  # 16 points
            s = comp.traditional16(degree=azimuth)
        elif res == 8:  # 8 points
            s = comp.traditional08(degree=azimuth)
        else: # 4 points
            s = comp.traditional04(degree=azimuth)
    elif mode == 'full':
        if res == 32:  # 32 points
            s = comp.point(degree=azimuth)
        elif res == 16:  # 16 points
            s = comp.point16(degree=azimuth)
        elif res == 8:  # 8 points
            s = comp.point08(degree=azimuth)
        else: # 4 points
            s = comp.point04(degree=azimuth)
    else:
        if res == 32:  # 32 points
            s = comp.abbr(azimuth)
        elif res == 16:  # 16 points
            s = comp.abbr16(azimuth)
        elif res == 8:  # 8 points
            s = comp.abbr08(azimuth)
        else: # 4 points
            s = comp.abbr04(azimuth)
    return(s)


@qgsfunction(args=2, group=group_name)
def st_from_meters(values, feature, parent):
    """
    Convert a length in meters to another unit.

    <h4>Syntax</h4>
    <p><b>st_from_meters</b>( <i>length</i>, <i>units</i> )</p>

    <h4>Arguments</h4>
    <ul>
    <li><i>length</i> &rarr; the length in meters to be converted.</li>
    <li><i>units</i> &rarr; conversion unit</li>
    <ul>
    <li><i>'cm'</i> &rarr; centimeters</li>
    <li><i>'m'</i> &rarr; meters</li>
    <li><i>'km'</i> &rarr; kilometers</li>
    <li><i>'in'</i> &rarr; inches</li>
    <li><i>'ft'</i> &rarr; feet</li>
    <li><i>'yard'</i> &rarr; yards</li>
    <li><i>'mi'</i> &rarr; miles</li>
    <li><i>'nm'</i> &rarr; nautical miles</li>
    </ul></ul>

    <h4>Example usage</h4>
    <ul>
      <li><b>st_from_meters</b>(1000, 'km') &rarr; returns 1</li>
    </ul>
    """
    try:
        len = float(values[0])
        unit = values[1]
        if unit == 'cm':
            return (len * 100)
        elif unit == 'm':
            return (len)
        elif unit == 'km':
            return(len * 0.001)
        elif unit == 'in':
            return (len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet) * 12.0)
        elif unit == 'ft':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet))
        elif unit == 'yard':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceYards))
        elif unit == 'mi':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceMiles))
        elif unit == 'nm':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceNauticalMiles))
        else:
            parent.setEvalErrorString("Error: invalid unit")
        return
    except Exception:
        parent.setEvalErrorString("Error: invalid inputs")
        return

@qgsfunction(args=2, group=group_name)
def st_to_meters(values, feature, parent):
    """
    Convert a length to meters.

    <h4>Syntax</h4>
    <p><b>st_to_meters</b>( <i>length</i>, <i>units</i> )</p>

    <h4>Arguments</h4>
    <ul>
    <li><i>length</i> &rarr; the length to be converted.</li>
    <li><i>units</i> &rarr; units of the length</li>
    <ul>
    <li><i>'cm'</i> &rarr; centimeters</li>
    <li><i>'m'</i> &rarr; meters</li>
    <li><i>'km'</i> &rarr; kilometers</li>
    <li><i>'in'</i> &rarr; inches</li>
    <li><i>'ft'</i> &rarr; feet</li>
    <li><i>'yard'</i> &rarr; yards</li>
    <li><i>'mi'</i> &rarr; miles</li>
    <li><i>'nm'</i> &rarr; nautical miles</li>
    </ul></ul>

    <h4>Example usage</h4>
    <ul>
      <li><b>st_to_meters</b>(1, 'km') &rarr; returns 1000</li>
    </ul>
    """
    try:
        len = float(values[0])
        unit = values[1]
        if unit == 'cm':
            return (len * 0.01)
        elif unit == 'm':
            return (len)
        elif unit == 'km':
            return(len * 1000)
        elif unit == 'in':
            return (len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters) / 12.0)
        elif unit == 'ft':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters))
        elif unit == 'yard':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceYards, QgsUnitTypes.DistanceMeters))
        elif unit == 'mi':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceMeters))
        elif unit == 'nm':
            return(len * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters))
        else:
            parent.setEvalErrorString("Error: invalid unit")
        return
    except Exception:
        parent.setEvalErrorString("Error: invalid inputs")
        return

@qgsfunction(-1, group=group_name)
def st_geodesic_distance(values, feature, parent):
    """
    Returns the geodesic distance in meters between two y, x (latitude, longitude) coordinates or two geometry points.

    <h4>Syntax</h4>
    <p><b>st_geodesic_distance</b>( <i>y1, x1, y2, x2[, crs='EPSG:4326']</i> )</p>
    <p><b>st_geodesic_distance</b>( <i>geom1, geom2[, crs='EPSG:4326']</i> )</p>

    <h4>Arguments</h4>
    <p><i>y1</i> &rarr; the y or latitude coordinate for the first point.<br />
    <i>x1</i> &rarr; the x or longitude coordinate for the first point.<br />
    <i>y2</i> &rarr; the y or latitude coordinate for the second point.<br />
    <i>x2</i> &rarr; the x or longitude coordinate for the second point.</p>
    <p><i>geom1</i> &rarr; the first point geometry.<br />
    <i>geom2</i> &rarr; the second point geometry.</p>
    <p><i>crs</i> &rarr; optional coordinate reference system of the y, x coordinates. Default value is 'EPSG:4326' if not specified.</p>

    <h4>Example usage</h4>
    <ul>
      <li><b>st_geodesic_distance</b>(40.0124, -105.2713, 39.7407, -104.9880) &rarr; 38696.715933</li>
      <li><b>st_geodesic_distance</b>(4867744, -11718747, 4828332, -11687210, 'EPSG:3857') &rarr; 38697.029390</li>
      <li><b>st_geodesic_distance</b>(<b>make_point</b>(-105.2713, 40.0124), <b>make_point</b>(-104.9880, 39.7407)) &rarr; 38696.715933</li>
      <li><b>st_geodesic_distance</b>(<b>make_point</b>(-11718747, 4867744), <b>make_point</b>(-11687210, 4828332), 'EPSG:3857') &rarr; 38697.029390</li>
    </ul>
    """
    num_args = len(values)
    if num_args < 2 or num_args > 5:
        parent.setEvalErrorString("Error: invalid number of arguments")
        return
    try:
        if num_args >= 4:
            y1 = float(values[0])
            x1 = float(values[1])
            y2 = float(values[2])
            x2 = float(values[3])
            if num_args == 5:
                crs = values[4]
                if crs and crs != 'EPSG:4326':
                    y1, x1 = transform_coords(y1, x1, crs)
                    y2, x2 = transform_coords(y2, x2, crs)
        else:
            geom1 = values[0]
            geom2 = values[1]
            if geom1.type() != QgsWkbTypes.PointGeometry  or geom2.type() != QgsWkbTypes.PointGeometry:
                parent.setEvalErrorString("Error: invalid point geometry")
            pt1 = geom1.asPoint()
            pt2 = geom2.asPoint()
            if num_args == 3:
                crs = values[2]
                pt1 = transform_geom(pt1, crs)
                pt2 = transform_geom(pt2, crs)
            y1 = pt1.y()
            x1 = pt1.x()
            y2 = pt2.y()
            x2 = pt2.x()
        l = geod.Inverse(y1, x1, y2, x2)
        return(l['s12'])
    except Exception:
        parent.setEvalErrorString("Error: invalid  parameters")
        '''s = traceback.format_exc()
        parent.setEvalErrorString(s)'''
        return

@qgsfunction(-1, group=group_name)
def st_geodesic_bearing(values, feature, parent):
    """
    Returns the geodesic azimuth starting from the first y, x (latitude, longitude) coordinate in the direction of the second coordinate.

    <h4>Syntax</h4>
    <p><b>st_geodesic_bearing</b>( <i>y1, x1, y2, x2[, crs='EPSG:4326']</i> )</p>
    <p><b>st_geodesic_bearing</b>( <i>geom1, geom2[, crs='EPSG:4326']</i> )</p>

    <h4>Arguments</h4>
    <p><i>y1</i> &rarr; the y or latitude coordinate for the first point.<br />
    <i>x1</i> &rarr; the x or longitude coordinate for the first point.<br />
    <i>y2</i> &rarr; the y or latitude coordinate for the second point.<br />
    <i>x2</i> &rarr; the x or longitude coordinate for the second point.</p>
    <p><i>geom1</i> &rarr; the first point geometry.<br />
    <i>geom2</i> &rarr; the second point geometry.</p>
    <p><i>crs</i> &rarr; optional coordinate reference system of the y, x coordinates. Default value is 'EPSG:4326' if not specified.</p>

    <h4>Example usage</h4>
    <ul>
      <li><b>st_geodesic_bearing</b>(40.0124, -105.2713, 39.7407, -104.9880) &rarr; 141.131805</li>
      <li><b>st_geodesic_bearing</b>(4867744, -11718747, 4828332, -11687210, 'EPSG:3857') &rarr; 141.1319</li>
      <li><b>st_geodesic_bearing</b>(<b>make_point</b>(-105.2713, 40.0124), <b>make_point</b>(-104.9880, 39.7407)) &rarr; 141.131805</li>
      <li><b>st_geodesic_bearing</b>(<b>make_point</b>(-11718747, 4867744), <b>make_point</b>(-11687210, 4828332), 'EPSG:3857') &rarr; 141.1319</li>
    </ul>
    """
    num_args = len(values)
    if num_args < 2 or num_args > 5:
        parent.setEvalErrorString("Error: invalid number of arguments")
        return
    try:
        if num_args >= 4:
            y1 = float(values[0])
            x1 = float(values[1])
            y2 = float(values[2])
            x2 = float(values[3])
            if num_args == 5:
                crs = values[4]
                if crs and crs != 'EPSG:4326':
                    y1, x1 = transform_coords(y1, x1, crs)
                    y2, x2 = transform_coords(y2, x2, crs)
        else:
            geom1 = values[0]
            geom2 = values[1]
            if geom1.type() != QgsWkbTypes.PointGeometry  or geom2.type() != QgsWkbTypes.PointGeometry:
                parent.setEvalErrorString("Error: invalid point geometry")
            pt1 = geom1.asPoint()
            pt2 = geom2.asPoint()
            if num_args == 3:
                crs = values[2]
                pt1 = transform_geom(pt1, crs)
                pt2 = transform_geom(pt2, crs)
            y1 = pt1.y()
            x1 = pt1.x()
            y2 = pt2.y()
            x2 = pt2.x()
        l = geod.Inverse(y1, x1, y2, x2)
        return(l['azi1'])
    except Exception:
        parent.setEvalErrorString("Error: invalid  parameters")
        return

@qgsfunction(args=-1, group=group_name)
def st_geodesic_transform(values, feature, parent):
    """
    Geodesically transfrom a shape (point, line, polygon) using rotation, translation, and scaling.

    <h4>Syntax</h4>
    <p><b>st_geodesic_transform</b>( <i>geom [, scale=1, rotate=0, distance=0, azimuth=0, unit='m', crs='EPSG:4326'</i>)</p>

    <h4>Arguments</h4>
    <ul>
    <li><i>geom</i> &rarr; input geometry (point, line, polygon).</li>
    <li><i>scale</i> &rarr; the scale factor. Default is 1.0.</li>
    <li><i>rotate</i> &rarr; the rotation angle in degrees. Default is 0 degrees.</li>
    <li><i>distance</i> &rarr; the translation distance. Default is 0.</li>
    <li><i>azimuth</i> &rarr; the translation azimuth in degrees. Default is 0.</li>
    <li><i>unit</i> &rarr; translation distance units</li>
    <li><i>crs</i> &rarr; optional coordinate reference system of the input geometry. Default value is 'EPSG:4326' if not specified.</li>
    <ul>
    <li><i>'cm'</i> &rarr; centimeters</li>
    <li><i>'m'</i> &rarr; meters</li>
    <li><i>'km'</i> &rarr; kilometers</li>
    <li><i>'in'</i> &rarr; inches</li>
    <li><i>'ft'</i> &rarr; feet</li>
    <li><i>'yard'</i> &rarr; yards</li>
    <li><i>'mi'</i> &rarr; miles</li>
    <li><i>'nm'</i> &rarr; nautical miles</li>
    </ul></ul>

    <h4>Example usage</h4>
    <ul>
      <li>geom_to_wkt(st_geodesic_transform(make_line(make_point(2,4),make_point(3,5)), 1.0, 45, 1000, 90, 'km')) &rarr; returns 'LineString (10.80438811 4.44561039, 12.21595371 4.44309579)'</li>
    </ul>
    """
    num_args = len(values)
    if num_args < 1 or num_args > 7:
        parent.setEvalErrorString("Error: invalid number of arguments")
        return
    scale = 1.0
    rotate = 0.0
    distance = 0.0
    azimuth = 0.0
    unit = 'm'
    crs = 'EPSG:4326'
    try:
        geom = values[0]
        if num_args > 1:
            scale = float(values[1])
        if num_args > 2:
            rotate = float(values[2])
        if num_args > 3:
            distance = float(values[3])
        if num_args > 4:
            azimuth = float(values[4])
        if num_args > 5:
            unit = values[5]
        if num_args > 6:
            crs = values[6]
            
        crs = QgsCoordinateReferenceSystem(crs)
        geom_to_4326 = QgsCoordinateTransform(crs, epsg4326, QgsProject.instance())
        to_crs = QgsCoordinateTransform(epsg4326, crs, QgsProject.instance())


        if unit == 'cm':
            factor = 0.01
        elif unit == 'm':
            factor = 1.0
        elif unit == 'km':
            factor = 1000.0
        elif unit == 'in':
            factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters) / 12.0
        elif unit == 'ft':
            factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters)
        elif unit == 'yard':
            factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceYards, QgsUnitTypes.DistanceMeters)
        elif unit == 'mi':
            factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceMeters)
        elif unit == 'nm':
            factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters)
        else:
            parent.setEvalErrorString("Error: invalid unit")

        centroid = geom.centroid().asPoint()
        centroid = geom_to_4326.transform(centroid.x(), centroid.y())
        cy = centroid.y()
        cx = centroid.x()
        if distance != 0:
            distance *= factor
            g = geod.Direct(cy, cx, azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            new_centroid = QgsPoint(g['lon2'], g['lat2'])
        else:
            new_centroid = centroid

        # Find the x & y coordinates of the new centroid
        ncy = new_centroid.y()
        ncx = new_centroid.x()

        vertices = geom.vertices()
        for vcnt, vertex in enumerate(vertices):
            v = geom_to_4326.transform(vertex.x(), vertex.y())
            gline = geod.Inverse(cy, cx, v.y(), v.x())
            vdist = gline['s12']
            vazi = gline['azi1']
            if scale != 1:
                vdist = vdist * scale
            if rotate != 0:
                vazi += rotate
            g = geod.Direct(ncy, ncx, vazi, vdist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            new_vertex = to_crs.transform(g['lon2'], g['lat2'])
            geom.moveVertex(new_vertex.x(), new_vertex.y(), vcnt)
        return(geom)
    except Exception:
        '''s = traceback.format_exc()
        parent.setEvalErrorString(s)'''
        parent.setEvalErrorString("Error: invalid input")
        return

@qgsfunction(-1, group=group_name)
def st_compass(values, feature, parent):
    """
    Returns the cardinal or compass direction given an azimuth as a string.

    <h4>Syntax</h4>
    <p><b>st_compass</b>( <i>azimuth[, npt=16, mode='abbr']</i> )</p>

    <h4>Arguments</h4>
    <p><i>azimuth</i> &rarr; specifies the azimuth and can be between -180 to 180 or 0 to 360 where 0 degrees is north.<br />
    <i>npt</i> &rarr; the number compass directions. Valid values are 4, 8, 16, and 32.<br />
    <i>mode</i> &rarr; 'abbr' returns the abbreviated compass direction, 'full' returns the full name and 'trad' returns the traditional name of the Mediterranean basin.<br />

    <h4>Example usage</h4>
    <ul>
      <li><b>st_compass</b>(33) &rarr; 'NNE'</li>
      <li><b>st_compass</b>(33, 8) &rarr; 'NE'</li>
      <li><b>st_compass</b>(33, 32) &rarr; 'NEbN'</li>
      <li><b>st_compass</b>(33, 16,'full') &rarr; 'north-northeast'</li>
      <li><b>st_compass</b>(33, 32,'full') &rarr; 'northeast by north'</li>
      <li><b>st_compass</b>(33, 32,'trad') &rarr; 'Quarto di Greco verso Tramontana'</li>
    </ul>
    """
    num_args = len(values)
    if num_args < 1 or num_args > 3:
        parent.setEvalErrorString("Error: invalid number of arguments")
        return
    try:
        azimuth = float(values[0])
        npt = 16
        mode = 'abbr'
        if num_args >= 2:
            npt = float(values[1])
        if num_args == 3:
            mode = values[2].strip()
        s = compass(azimuth, npt, mode)
        return(s)
    except Exception:
        parent.setEvalErrorString("Error: invalid  parameters")
        return

