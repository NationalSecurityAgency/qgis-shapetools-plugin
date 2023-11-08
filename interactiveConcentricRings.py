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
import os
import re
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsGeometry, QgsFeature, QgsField, QgsFields,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterPoint,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, DISTANCE_ABBREVIATIONS, makeIdlCrossingsPositive, hasIdlCrossing

class InteractiveConcentricRingsAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a concentric rings.
    """

    PrmShapeType = 'ShapeType'
    PrmDistance = 'Distance'
    PrmStartingRadius = 'StartingRadius'
    PrmRingCount = 'RingCount'
    PrmRingDistances = 'RingDistances'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'
    PrmCoordinate = 'Coordinate'
    PrmRadials = 'Radials'
    PrmCircleOutput = 'CircleOutput'
    PrmRadialLineOutput = 'RadialLineOutput'
    PrmStartingRadialAngle = 'StartingRadialAngle'

    def createInstance(self):
        return InteractiveConcentricRingsAlgorithm()

    def name(self):
        return 'interactiverings'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/concentricrings.png'))

    def displayName(self):
        return tr('Interactive concentric rings')

    def group(self):
        return tr('Interactive geodesic shapes')

    def groupId(self):
        return 'interactiveshapes'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def supportInPlaceEdit(self, layer):
        return True

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterPoint(
                self.PrmCoordinate,
                tr('Select an input coordinate'),
                optional=False)
        )

        param = QgsProcessingParameterNumber(
            self.PrmStartingRadius,
            tr('Starting ring radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10,
            minValue=0,
            optional=False)
        self.addParameter(param)
        
        param = QgsProcessingParameterNumber(
            self.PrmDistance,
            tr('Distance between rings'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=False)
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmRingCount,
                tr('Number of rings'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=2,
                minValue=1,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.PrmRingDistances,
                tr('Alternative comma/space separated numbers of ring distances from origin'),
                optional=True)
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Radius units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDrawingSegments,
                tr('Number of drawing segments'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=360,
                minValue=4,
                optional=True)
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmRadials,
                tr('Number of radial lines'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=0,
                minValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmStartingRadialAngle,
                tr('Starting radial line angle (degrees)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                maxValue=360,
                minValue=-360,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmCircleOutput,
                tr('Concentric circle output'))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmRadialLineOutput,
                tr('Radial line output'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        pt = self.parameterAsPoint(parameters, self.PrmCoordinate, context, crs=epsg4326)
        starting_radius = self.parameterAsDouble(parameters, self.PrmStartingRadius, context)
        distance = self.parameterAsDouble(parameters, self.PrmDistance, context)
        ring_cnt = self.parameterAsInt(parameters, self.PrmRingCount, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        radial_cnt = self.parameterAsInt(parameters, self.PrmRadials, context)
        starting_radial_angle = self.parameterAsDouble(parameters, self.PrmStartingRadialAngle, context)
        ring_distance_str = self.parameterAsString(parameters, self.PrmRingDistances, context)
        if ring_distance_str:
            ring_distance_str = ring_distance_str.strip()

        measure_factor = conversionToMeters(units)
        unit_str = DISTANCE_ABBREVIATIONS[units]

        inner_rad = starting_radius * measure_factor
        distance = distance * measure_factor

        pt_spacing = 360.0 / segments
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('radius', QVariant.Double))
        fields.append(QgsField('unit', QVariant.String))
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmCircleOutput,
            context, fields, QgsWkbTypes.LineString, epsg4326)
        if radial_cnt:
            fields = QgsFields()
            fields.append(QgsField('id', QVariant.Int))
            fields.append(QgsField('angle', QVariant.Double))
            (sink_radials, dest_id_radials) = self.parameterAsSink(
                parameters, self.PrmRadialLineOutput,
                context, fields, QgsWkbTypes.LineString, epsg4326)
            
        if ring_distance_str:
            try:
                rads = [float(x) * measure_factor for x in re.split('[, \t]+', ring_distance_str)]
            except Exception:
                raise QgsProcessingException(tr('Invalid list of ring distances from origin'))
        else:
            rads = []
            for i in range(0, ring_cnt):
                rads.append(i*distance + inner_rad)
        
        lat = pt.y()
        lon = pt.x()

        try:
            for idx, dist in enumerate(rads):
                pts_out = []
                angle = 0
                while angle < 360:
                    g = geod.Direct(lat, lon, angle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts_out.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += pt_spacing
                pts_out.append(pts_out[0])
                crosses_idl = hasIdlCrossing(pts_out)
                if crosses_idl:
                    makeIdlCrossingsPositive(pts_out, True)
                f = QgsFeature()
                f.setAttributes([idx, dist, unit_str])
                f.setGeometry(QgsGeometry.fromPolylineXY(pts_out))
                sink.addFeature(f)
            if radial_cnt:
                # This will be the number of points to draw the radials
                num_radial_pts = int(segments / 6)
                if num_radial_pts < 2:
                    num_radial_pts = 2
                for i in range(radial_cnt):
                    angle = starting_radial_angle + i * 360 / radial_cnt
                    pts_out = [pt]
                    for j in range(1, num_radial_pts + 1):
                        dist2 = dist * j / num_radial_pts
                        g = geod.Direct(lat, lon, angle, dist2, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts_out.append(QgsPointXY(g['lon2'], g['lat2']))
                    f = QgsFeature()
                    f.setAttributes([i, angle])
                    f.setGeometry(QgsGeometry.fromPolylineXY(pts_out))
                    sink_radials.addFeature(f)
        except Exception:
            raise QgsProcessingException('Somthing went wrong')

        if radial_cnt:
            return {self.PrmRadialLineOutput: dest_id_radials, self.PrmCircleOutput: dest_id}
        return {self.PrmCircleOutput: dest_id}
