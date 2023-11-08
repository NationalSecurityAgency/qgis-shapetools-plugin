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
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsGeometry, QgsField, QgsFeature,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameters,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import epsg4326, geod, settings
from .utils import tr, conversionToMeters, conversionFromMeters, DISTANCE_LABELS


class CreatePointsAlongLobAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a line of bearing.
    """

    PrmAzimuth = 'Azimuth'
    PrmDistance = 'Distance'
    PrmOffset = 'Offset'
    PrmUnits = 'Units'
    PrmDistanceBetweenPoints = 'DistanceBetweenPoints'

    def createInstance(self):
        return CreatePointsAlongLobAlgorithm()

    def name(self):
        return 'createpointsalonglob'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/ptline.png'))

    def displayName(self):
        return tr('Create points along a bearing')

    def group(self):
        return tr('Geodesic shapes')

    def groupId(self):
        return 'vectorcreation'

    def outputName(self):
        return tr('Output layer')

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def inputLayerTypes(self):
        return [QgsProcessing.TypeVectorPoint]

    def outputWkbType(self, input_wkb_type):
        return (QgsWkbTypes.Point)

    def outputFields(self, input_fields):
        names = input_fields.names()
        index_name = settings.getUniqueAttributeName('pt_index', names)
        dist_name = settings.getUniqueAttributeName('pt_distance', names)
        input_fields.append(QgsField(index_name, QVariant.Int))
        input_fields.append(QgsField(dist_name, QVariant.Double))
        return(input_fields)

    def  supportInPlaceEdit(self, layer):
        return False

    def initParameters(self, config=None):
        self.export_geom = False
        param = QgsProcessingParameterNumber(
            self.PrmAzimuth,
            tr('Azimuth/bearing'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmAzimuth,
            tr('Azimuth/bearing'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmDistance,
            tr('Distance'),
            QgsProcessingParameterNumber.Double,
            defaultValue=1000.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmDistance,
            tr('Distance'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmOffset,
            tr('Distance from origin to first point'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmOffset,
            tr('Distance from origin to first point'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmDistanceBetweenPoints,
            tr('Distance between points'),
            QgsProcessingParameterNumber.Double,
            defaultValue=50.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmDistanceBetweenPoints,
            tr('Distance between points'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnits,
                tr('Distance units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )

    def prepareAlgorithm(self, parameters, context, feedback):
        self.azimuth = self.parameterAsDouble(parameters, self.PrmAzimuth, context)
        self.azimuth_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmAzimuth)
        if self.azimuth_dyn:
            self.azimuth_property = parameters[self.PrmAzimuth]

        self.dist = self.parameterAsDouble(parameters, self.PrmDistance, context)
        self.dist_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmDistance)
        if self.dist_dyn:
            self.dist_property = parameters[self.PrmDistance]

        self.offset = self.parameterAsDouble(parameters, self.PrmOffset, context)
        self.offset_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOffset)
        if self.offset_dyn:
            self.offset_property = parameters[self.PrmOffset]

        self.inner_dist = self.parameterAsDouble(parameters, self.PrmDistanceBetweenPoints, context)
        self.inner_dist_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmDistanceBetweenPoints)
        if self.inner_dist_dyn:
            self.inner_dist_property = parameters[self.PrmDistanceBetweenPoints]

        units = self.parameterAsInt(parameters, self.PrmUnits, context)

        self.measureFactor = conversionToMeters(units)
        self.fromMetersMeasureFactor = conversionFromMeters(units)

        self.dist_converted = self.dist * self.measureFactor
        self.offset_converted = self.offset * self.measureFactor
        self.inner_dist_converted = self.inner_dist * self.measureFactor

        source = self.parameterAsSource(parameters, 'INPUT', context)
        srcCRS = source.sourceCrs()
        self.total_features = source.featureCount()

        if srcCRS != epsg4326:
            self.geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            self.toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        else:
            self.geomTo4326 = None
            self.toSinkCrs = None
        self.num_bad = 0
        return True

    def processFeature(self, feature, context, feedback):
        features = []
        try:
            if self.azimuth_dyn:
                bearing, e = self.azimuth_property.valueAsDouble(context.expressionContext(), self.azimuth)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                bearing = self.azimuth
            if self.dist_dyn:
                distance, e = self.dist_property.valueAsDouble(context.expressionContext(), self.dist)
                if not e:
                    self.num_bad += 1
                    return []
                distance *= self.measureFactor
            else:
                distance = self.dist_converted
            if self.offset_dyn:
                offset, e = self.offset_property.valueAsDouble(context.expressionContext(), self.offset)
                if not e:
                    self.num_bad += 1
                    return []
                offset *= self.measureFactor
            else:
                offset = self.offset_converted
            if distance - offset <= 0:
                self.num_bad += 1
                return []
            if self.inner_dist_dyn:
                inner_dist, e = self.inner_dist_property.valueAsDouble(context.expressionContext(), self.inner_dist)
                if not e:
                    self.num_bad += 1
                    return []
                inner_dist *= self.measureFactor
            else:
                inner_dist = self.inner_dist_converted
            if inner_dist <= 0: 
                self.num_bad += 1
                return []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            gline = geod.Line(pt.y(), pt.x(), bearing)
            index = 0
            attr = feature.attributes()
            while index*inner_dist + offset < distance:
                d = offset + index*inner_dist
                g = gline.Position(d, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                pt2 = QgsPointXY(g['lon2'], g['lat2'])
                if self.toSinkCrs:
                    pt2 = self.toSinkCrs.transform(pt2)
                f = QgsFeature(feature)
                f.setGeometry(QgsGeometry.fromPointXY(pt2))
                f.setAttributes(attr+[index, d*self.fromMetersMeasureFactor])
                features.append(f)
                index += 1
            # Add the very last point
            g = gline.Position(distance, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
            pt2 = QgsPointXY(g['lon2'], g['lat2'])
            if self.toSinkCrs:
                pt2 = self.toSinkCrs.transform(pt2)
            f = QgsFeature(feature)
            f.setGeometry(QgsGeometry.fromPointXY(pt2))
            f.setAttributes(attr+[index, distance*self.fromMetersMeasureFactor])
            features.append(f)
        except Exception:
            self.num_bad += 1
            return []

        return features

    def postProcessAlgorithm(self, context, feedback):
        if self.num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(self.num_bad, self.total_features)))
        return {}
