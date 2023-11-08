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

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, makeIdlCrossingsPositive
# import traceback

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


def geodesicEllipse(geod, lat, lon, sma, smi, orient, segments):
    segments = int(math.ceil(segments / 2))
    if smi < 0.0001:
        smi = 0.0001
    if sma < 0.0001:
        sma = 0.0001
    if sma < smi:
        temp = sma
        sma = smi
        smi = temp
        orient += 90
    ab = sma * smi
    step = 18.0 * smi / sma
    if step < 1.0:
        minimum = step
    else:
        minimum = 1.0

    maxang = math.pi / 6 * minimum
    delta = ab * math.pi / segments
    pts = []
    azi = 0
    while azi < math.tau:
        cos_azi = math.cos(azi)
        sin_azi = math.sin(azi)
        rad = ab / math.sqrt(sma * sma * sin_azi * sin_azi + smi * smi * cos_azi * cos_azi)
        g = geod.Direct(lat, lon, math.degrees(azi) + orient, rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
        pts.append(QgsPointXY(g['lon2'], g['lat2']))
        delo = delta / (rad * rad)
        if maxang < delo:
            delo = maxang
        azi += delo

    # Append the starting point to close the shape
    pts.append(pts[0])
    makeIdlCrossingsPositive(pts)
    return(pts)


class CreateEllipseAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create an ellipse shape.
    """

    PrmShapeType = 'ShapeType'
    PrmSemiMajorAxis = 'SemiMajorAxis'
    PrmSemiMinorAxis = 'SemiMinorAxis'
    PrmOrientation = 'Orientation'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreateEllipseAlgorithm()

    def name(self):
        return 'createellipse'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/ellipse.png'))

    def displayName(self):
        return tr('Create ellipse')

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
            self.PrmSemiMajorAxis,
            tr('Semi-major axis'),
            QgsProcessingParameterNumber.Double,
            defaultValue=40.0,
            minValue=0.00001,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmSemiMajorAxis,
            tr('Semi-major axis'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmSemiMinorAxis,
            tr('Semi-minor axis'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0.00001,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmSemiMinorAxis,
            tr('Semi-minor axis'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmOrientation,
            tr('Orientation of axis'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            minValue=-360,
            maxValue=360,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmOrientation,
            tr('Orientation of axis'),
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
                tr('Number of drawing segments (approximate)'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=64,
                minValue=8,
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
        self.semi_major = self.parameterAsDouble(parameters, self.PrmSemiMajorAxis, context)
        self.semi_major_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmSemiMajorAxis)
        if self.semi_major_dyn:
            self.semi_major_property = parameters[self.PrmSemiMajorAxis]
        self.semi_minor = self.parameterAsDouble(parameters, self.PrmSemiMinorAxis, context)
        self.semi_minor_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmSemiMinorAxis)
        if self.semi_minor_dyn:
            self.semi_minor_property = parameters[self.PrmSemiMinorAxis]
        if self.semi_major <= 0 or self.semi_minor <= 0:
            feedback.reportError('Semi Major and Mindor parameters must be greater than 0')
            return False
        self.orientation = self.parameterAsDouble(parameters, self.PrmOrientation, context)
        self.orientation_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOrientation)
        if self.orientation_dyn:
            self.orientation_property = parameters[self.PrmOrientation]
        self.segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measure_factor = conversionToMeters(units)

        self.semi_major_converted = self.semi_major * self.measure_factor
        self.semi_minor_converted = self.semi_minor * self.measure_factor

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
            pts = []
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if self.geom_to_4326:
                pt = self.geom_to_4326.transform(pt.x(), pt.y())
            lat = pt.y()
            lon = pt.x()
            if self.semi_major_dyn:
                sma, e = self.semi_major_property.valueAsDouble(context.expressionContext(), self.semi_major)
                sma *= self.measure_factor
                if not e or sma <= 0:
                    self.num_bad += 1
                    return []
            else:
                sma = self.semi_major_converted
            if self.semi_minor_dyn:
                smi, e = self.semi_minor_property.valueAsDouble(context.expressionContext(), self.semi_minor)
                smi *= self.measure_factor
                if not e or smi <= 0:
                    self.num_bad += 1
                    return []
            else:
                smi = self.semi_minor_converted
            if self.orientation_dyn:
                orient = self.orientation_property.valueAsDouble(context.expressionContext(), self.orientation)[0]
            else:
                orient = self.orientation

            pts = geodesicEllipse(geod, lat, lon, sma, smi, orient, self.segments)

            # If the Output crs is not 4326 transform the points to the proper crs
            if self.to_sink_crs:
                for x, ptout in enumerate(pts):
                    pts[x] = self.to_sink_crs.transform(ptout)

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
            '''s = traceback.format_exc()
            feedback.pushInfo(s)'''
            self.num_bad += 1
            return []
        return [feature]

    def postProcessAlgorithm(self, context, feedback):
        if self.num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(self.num_bad, self.total_features)))
        return {}
