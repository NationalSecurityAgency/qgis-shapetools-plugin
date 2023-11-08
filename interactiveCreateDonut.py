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
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsGeometry, QgsFeature,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsFields, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameters,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterPoint,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, makeIdlCrossingsPositive, hasIdlCrossing

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class InteractiveCreateDonutAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmShapeType = 'ShapeType'
    PrmOuterRadius = 'OuterRadius'
    PrmInnerRadius = 'InnerRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'
    PrmCoordinate = 'Coordinate'
    PrmOutput = 'OUTPUT'

    def createInstance(self):
        return InteractiveCreateDonutAlgorithm()

    def name(self):
        return 'interactivedonut'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/donut.png'))

    def displayName(self):
        return tr('Interactive donut')

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
        self.shape_type = 0
        self.addParameter(
            QgsProcessingParameterPoint(
                self.PrmCoordinate,
                tr('Select an input coordinate'),
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmShapeType,
                tr('Shape type'),
                options=SHAPE_TYPE,
                defaultValue=0,
                optional=False)
        )
        param = QgsProcessingParameterNumber(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=False)
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=False)
        self.addParameter(param)

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
                defaultValue=72,
                minValue=4,
                optional=True)
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutput,
                tr('Donut polygon'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        outer_radius = self.parameterAsDouble(parameters, self.PrmOuterRadius, context)
        if outer_radius <= 0:
            raise QgsProcessingException('Outer radius parameter must be greater than 0')
        inner_radius = self.parameterAsDouble(parameters, self.PrmInnerRadius, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        pt = self.parameterAsPoint(parameters, self.PrmCoordinate, context, crs=epsg4326)

        measure_factor = conversionToMeters(units)

        inner_rad = inner_radius * measure_factor
        outer_rad = outer_radius * measure_factor

        pt_spacing = 360.0 / segments
        if shape_type == 0:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutput,
                context, QgsFields(), QgsWkbTypes.Polygon, epsg4326)
        else:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutput,
                context, QgsFields(), QgsWkbTypes.MultiLineString, epsg4326)

        try:
            pts_in = []
            pts_out = []
            lat = pt.y()
            lon = pt.x()
            angle = 0
            while angle < 360:
                if inner_rad != 0:
                    g = geod.Direct(lat, lon, angle, inner_rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts_in.append(QgsPointXY(g['lon2'], g['lat2']))
                g = geod.Direct(lat, lon, angle, outer_rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts_out.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += pt_spacing
            if inner_rad != 0:
                pts_in.append(pts_in[0])
            pts_out.append(pts_out[0])
            crosses_idl = hasIdlCrossing(pts_out)
            if crosses_idl:
                if inner_rad != 0:
                    makeIdlCrossingsPositive(pts_in, True)
                makeIdlCrossingsPositive(pts_out, True)
            feature = QgsFeature()
            if shape_type == 0:
                if inner_rad == 0:
                    feature.setGeometry(QgsGeometry.fromPolygonXY([pts_out]))
                else:
                    feature.setGeometry(QgsGeometry.fromPolygonXY([pts_out, pts_in]))
            else:
                if inner_rad == 0:
                    feature.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out]))
                else:
                    feature.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out, pts_in]))
            sink.addFeature(feature)
        except Exception:
            raise QgsProcessingException('Invalid coordinate')

        return {self.PrmOutput: dest_id}
