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
    QgsPointXY, QgsGeometry, QgsField, QgsPropertyDefinition,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameters,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class CreatePolygonAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a polygon shape.
    """

    PrmShapeType = 'ShapeType'
    PrmNumberOfSides = 'NumberOfSides'
    PrmStartingAngle = 'StartingAngle'
    PrmRadius = 'Radius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreatePolygonAlgorithm()

    def name(self):
        return 'createpolygon'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/polygon.png'))

    def displayName(self):
        return tr('Create polygon')

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
        if self.shape_type == 0:
            return (QgsWkbTypes.Polygon)
        return (QgsWkbTypes.LineString)

    def  supportInPlaceEdit(self, layer):
        return False

    def outputFields(self, input_fields):
        if self.export_geom:
            name_x, name_y = settings.getGeomNames(input_fields.names())
            input_fields.append(QgsField(name_x, QVariant.Double))
            input_fields.append(QgsField(name_y, QVariant.Double))
        return(input_fields)

    def initParameters(self, config=None):
        self.shape_type = 0
        self.export_geom = False
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmShapeType,
                tr('Shape type'),
                options=SHAPE_TYPE,
                defaultValue=0,
                optional=False)
        )
        param = QgsProcessingParameterNumber(
            self.PrmNumberOfSides,
            tr('Number of sides'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=3,
            minValue=3,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmNumberOfSides,
            tr('Number of sides'),
            QgsPropertyDefinition.Integer))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmStartingAngle,
            tr('Starting angle'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmStartingAngle,
            tr('Starting angle'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmRadius,
            tr('Radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=40.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmRadius,
            tr('Radius'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
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
            QgsProcessingParameterBoolean(
                self.PrmExportInputGeometry,
                tr('Add input geometry fields to output table'),
                False,
                optional=True)
        )

    def prepareAlgorithm(self, parameters, context, feedback):
        self.shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        self.sides = self.parameterAsInt(parameters, self.PrmNumberOfSides, context)
        self.sides_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmNumberOfSides)
        if self.sides_dyn:
            self.sides_property = parameters[self.PrmNumberOfSides]
        self.angle = self.parameterAsDouble(parameters, self.PrmStartingAngle, context)
        self.angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmStartingAngle)
        if self.angle_dyn:
            self.angle_property = parameters[self.PrmStartingAngle]
        self.dist = self.parameterAsDouble(parameters, self.PrmRadius, context)
        if self.dist <= 0:
            feedback.reportError('Radius parameter must be greater than 0')
            return False
        self.dist_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRadius)
        if self.dist_dyn:
            self.dist_property = parameters[self.PrmRadius]
        unitOfDist = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measureFactor = conversionToMeters(unitOfDist)

        self.dist_converted = self.dist * self.measureFactor

        source = self.parameterAsSource(parameters, 'INPUT', context)
        self.total_features = source.featureCount()
        srcCRS = source.sourceCrs()

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
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            if self.sides_dyn:
                s, e = self.sides_property.valueAsInt(context.expressionContext(), self.sides)
                if not e or s <= 2:
                    self.num_bad += 1
                    return []
            else:
                s = self.sides
            if self.angle_dyn:
                startangle, e = self.angle_property.valueAsDouble(context.expressionContext(), self.angle)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                startangle = self.angle
            if self.dist_dyn:
                d, e = self.dist_property.valueAsDouble(context.expressionContext(), self.dist)
                d = d * self.measureFactor
                if not e or d <= 0:
                    self.num_bad += 1
                    return []
            else:
                d = self.dist_converted
            pts = []
            i = s
            while i >= 0:
                a = (i * 360.0 / s) + startangle
                i -= 1
                g = geod.Direct(pt.y(), pt.x(), a, d, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))

            makeIdlCrossingsPositive(pts)
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.toSinkCrs:
                for x, ptout in enumerate(pts):
                    pts[x] = self.toSinkCrs.transform(ptout)

            if self.shape_type == 0:
                feature.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
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
