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
    QgsPointXY, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameters,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, makeIdlCrossingsPositive, hasIdlCrossing

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class CreateCircleAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a circle shape.
    """

    PrmShapeType = 'ShapeType'
    PrmRadius = 'Radius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreateCircleAlgorithm()

    def name(self):
        return 'createcircle'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/circle.png'))

    def displayName(self):
        return tr('Create circle')

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

    def outputFields(self, input_fields):
        if self.export_geom:
            name_x, name_y = settings.getGeomNames(input_fields.names())
            input_fields.append(QgsField(name_x, QVariant.Double))
            input_fields.append(QgsField(name_y, QVariant.Double))
        return(input_fields)

    def  supportInPlaceEdit(self, layer):
        return False

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
            self.PrmRadius,
            tr('Circle radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmRadius,
            tr('Circle radius'),
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
            QgsProcessingParameterNumber(
                self.PrmDrawingSegments,
                tr('Number of drawing segments'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=36,
                minValue=4,
                optional=True)
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
        self.outer_radius = self.parameterAsDouble(parameters, self.PrmRadius, context)
        if self.outer_radius <= 0:
            feedback.reportError('Outer radius parameter must be greater than 0')
            return False
        self.outer_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRadius)
        if self.outer_radius_dyn:
            self.outer_radius_property = parameters[self.PrmRadius]
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measure_factor = conversionToMeters(units)

        self.outer_radius_converted = self.outer_radius * self.measure_factor

        self.pt_spacing = 360.0 / segments
        source = self.parameterAsSource(parameters, 'INPUT', context)
        src_crs = source.sourceCrs()
        self.total_features = source.featureCount()

        if src_crs != epsg4326:
            self.geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
            self.to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())
        else:
            self.geom_to_4326 = None
            self.to_sink_crs = None
        self.num_bad = 0
        return True

    def processFeature(self, feature, context, feedback):
        try:
            pts_in = []
            pts_out = []
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if self.geom_to_4326:
                pt = self.geom_to_4326.transform(pt.x(), pt.y())
            lat = pt.y()
            lon = pt.x()
            if self.outer_radius_dyn:
                outer_rad, e = self.outer_radius_property.valueAsDouble(context.expressionContext(), self.outer_radius)
                outer_rad *= self.measure_factor
                if not e or outer_rad <= 0:
                    self.num_bad += 1
                    return []
            else:
                outer_rad = self.outer_radius_converted
            angle = 0
            while angle < 360:
                g = geod.Direct(lat, lon, angle, outer_rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts_out.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += self.pt_spacing
            pts_out.append(pts_out[0])
            crosses_idl = hasIdlCrossing(pts_out)
            if crosses_idl:
                makeIdlCrossingsPositive(pts_out, True)

            # If the Output crs is not 4326 transform the points to the proper crs
            if self.to_sink_crs:
                for x, pt_out in enumerate(pts_out):
                    pts_out[x] = self.to_sink_crs.transform(pt_out)

            if self.shape_type == 0:
                feature.setGeometry(QgsGeometry.fromPolygonXY([pts_out]))
            else:
                feature.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out]))
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
