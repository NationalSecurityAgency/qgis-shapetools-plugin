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
    QgsPointXY, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameters,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import epsg4326, geod, settings
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS


class CreateLobAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a line of bearing.
    """

    PrmAzimuth = 'Azimuth'
    PrmDistance = 'Distance'
    PrmUnits = 'Units'
    PrmExportInputGeometry = 'ExportInputGeometry'
    PrmOffset = 'Offset'

    def createInstance(self):
        return CreateLobAlgorithm()

    def name(self):
        return 'createlob'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/line.png'))

    def displayName(self):
        return tr('Create line of bearing')

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
        return (QgsWkbTypes.LineString)

    def outputFields(self, input_fields):
        if self.export_geom:
            name_x, name_y = settings.getGeomNames(input_fields.names())
            input_fields.append(QgsField(name_x, QVariant.Double))
            input_fields.append(QgsField(name_y, QVariant.Double))
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
            tr('Line offset from origin'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmOffset,
            tr('Line offset from origin'),
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
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmExportInputGeometry,
                tr('Add input geometry fields to output table'),
                False,
                optional=True)
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

        units = self.parameterAsInt(parameters, self.PrmUnits, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measureFactor = conversionToMeters(units)

        self.dist_converted = self.dist * self.measureFactor
        self.offset_converted = self.offset * self.measureFactor
        self.maxseglen = settings.maxSegLength * 1000.0  # Needs to be in meters
        self.maxSegments = settings.maxSegments

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
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            gline = geod.Line(pt.y(), pt.x(), bearing)
            n = int(math.ceil((distance-offset) / self.maxseglen))
            if n > self.maxSegments:
                n = self.maxSegments
            seglen = (distance-offset) / n
            if offset == 0:
                pts = [pt]
            else:
                g = gline.Position(offset, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                pts = [QgsPointXY(g['lon2'], g['lat2'])]

            for i in range(1, n + 1):
                s = offset + seglen * i
                g = gline.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))

            makeIdlCrossingsPositive(pts)
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.toSinkCrs:
                for x, ptout in enumerate(pts):
                    pts[x] = self.toSinkCrs.transform(ptout)

            feature.setGeometry(QgsGeometry.fromPolylineXY(pts))
            if self.export_geom:
                attr = feature.attributes()
                attr.append(pt_orig_x)
                attr.append(pt_orig_y)
                feature.setAttributes(attr)
        except Exception:
            self.num_bad += 1
            return []

        return [feature]

    def postProcessAlgorithm(self, context, feedback):
        if self.num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(self.num_bad, self.total_features)))
        return {}
