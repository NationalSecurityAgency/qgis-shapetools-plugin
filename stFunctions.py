import re
from qgis.core import QgsUnitTypes, QgsPointXY, QgsGeometry, QgsExpression, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsWkbTypes
from qgis.utils import qgsfunction
from .settings import epsg4326, geod, settings

import traceback

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
    QgsExpression.registerFunction(st_to_meters)
    QgsExpression.registerFunction(st_geodesic_distance)
    QgsExpression.registerFunction(st_geodesic_bearing)

def UnloadShapeToolsFunctions():
    QgsExpression.unregisterFunction('st_to_meters')
    QgsExpression.unregisterFunction('st_geodesic_distance')
    QgsExpression.unregisterFunction('st_geodesic_bearing')

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
    <li><i>'cm<'/i> &rarr; centimeters</li>
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
    <p><b>st_geodesic_distance</b>( <i>geom_1, geom_2[, crs='EPSG:4326']</i> )</p>

    <h4>Arguments</h4>
    <p><i>y1</i> &rarr; the y or latitude coordinate for the first point.</p>
    <p><i>x1</i> &rarr; the x or longitude coordinate for the first point.</p>
    <p><i>y2</i> &rarr; the y or latitude coordinate for the second point.</p>
    <p><i>x2</i> &rarr; the x or longitude coordinate for the second point.</p>
    <p><i>crs</i> &rarr; optional coordinate reference system of the y, x coordinates. Default value is 'EPSG:4326' if not specified.</p>
    <p>&nbsp</p>
    <p><i>geom1</i> &rarr; the first point geometry.</p>
    <p><i>geom2</i> &rarr; the second point geometry.</p>


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
    Returns the geodesic azimuth or bearing starting from the first y, x (latitude, longitude) coordinate in the direction of the second coordinate.

    <h4>Syntax</h4>
    <p><b>st_geodesic_bearing</b>( <i>y1, x1, y2, x2[, crs='EPSG:4326']</i> )</p>
    <p><b>st_geodesic_bearing</b>( <i>geom_1, geom_2[, crs='EPSG:4326']</i> )</p>

    <h4>Arguments</h4>
    <p><i>y1</i> &rarr; the y or latitude coordinate for the first point.</p>
    <p><i>x1</i> &rarr; the x or longitude coordinate for the first point.</p>
    <p><i>y2</i> &rarr; the y or latitude coordinate for the second point.</p>
    <p><i>x2</i> &rarr; the x or longitude coordinate for the second point.</p>
    <p><i>crs</i> &rarr; optional coordinate reference system of the y, x coordinates. Default value is 'EPSG:4326' if not specified.</p>
    <p>&nbsp</p>
    <p><i>geom1</i> &rarr; the first point geometry.</p>
    <p><i>geom2</i> &rarr; the second point geometry.</p>


    <h4>Example usage</h4>
    <ul>
      <li><b>st_geodesic_bearing</b>(40.0124, -105.2713, 39.7407, -104.9880) &rarr; 141.131805</li>
      <li><b>st_geodesic_bearing</b>(4867744, -11718747, 4828332, -11687210, 'EPSG:3857') &rarr; 141.131900</li>
      <li><b>st_geodesic_bearing</b>(<b>make_point</b>(-105.2713, 40.0124), <b>make_point</b>(-104.9880, 39.7407)) &rarr; 141.131805</li>
      <li><b>st_geodesic_bearing</b>(<b>make_point</b>(-11718747, 4867744), <b>make_point</b>(-11687210, 4828332), 'EPSG:3857') &rarr; 141.131900</li>
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
