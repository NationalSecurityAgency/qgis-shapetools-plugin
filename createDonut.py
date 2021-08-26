import os
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsFeature, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameters,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, makeIdlCrossingsPositive, hasIdlCrossing

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class CreateDonutAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmOuterRadius = 'OuterRadius'
    PrmInnerRadius = 'InnerRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
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
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
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
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        outer_radius = self.parameterAsDouble(parameters, self.PrmOuterRadius, context)
        outer_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOuterRadius)
        if outer_radius_dyn:
            outer_radius_property = parameters[ self.PrmOuterRadius ]
        inner_radius = self.parameterAsDouble(parameters, self.PrmInnerRadius, context)
        inner_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmInnerRadius)
        if inner_radius_dyn:
            inner_radius_property = parameters[ self.PrmInnerRadius ]
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        measure_factor = conversionToMeters(units)

        inner_radius_converted = inner_radius * measure_factor
        outer_radius_converted = outer_radius * measure_factor

        pt_spacing = 360.0 / segments
        src_crs = source.sourceCrs()
        fields = source.fields()
        if export_geom:
            names = fields.names()
            name_x, name_y = settings.getGeomNames(names)
            fields.append(QgsField(name_x, QVariant.Double))
            fields.append(QgsField(name_y, QVariant.Double))
        if shape_type == 0:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Polygon, src_crs)
        else:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.MultiLineString, src_crs)

        if src_crs != epsg4326:
            geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
            to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())
        else:
            geom_to_4326 = None
            to_sink_crs = None

        feature_count = source.featureCount()
        total = 100.0 / feature_count if feature_count else 0

        iterator = source.getFeatures()
        num_bad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                pts_in = []
                pts_out = []
                pt = feature.geometry().asPoint()
                pt_orig_x = pt.x()
                pt_orig_y = pt.y()
                # make sure the coordinates are in EPSG:4326
                if geom_to_4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                if inner_radius_dyn:
                    inner_rad = inner_radius_property.valueAsDouble(context.expressionContext(), inner_radius)[0] * measure_factor
                else:
                    inner_rad = inner_radius_converted
                if outer_radius_dyn:
                    outer_rad = outer_radius_property.valueAsDouble(context.expressionContext(), outer_radius)[0] * measure_factor
                else:
                    outer_rad = outer_radius_converted
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

                # If the Output crs is not 4326 transform the points to the proper crs
                if to_sink_crs:
                    if inner_rad != 0:
                        for x, pt_out in enumerate(pts_in):
                            pts_in[x] = to_sink_crs.transform(pt_out)
                    for x, pt_out in enumerate(pts_out):
                        pts_out[x] = to_sink_crs.transform(pt_out)

                f = QgsFeature()
                if shape_type == 0:
                    if inner_rad == 0:
                        f.setGeometry(QgsGeometry.fromPolygonXY([pts_out]))
                    else:
                        f.setGeometry(QgsGeometry.fromPolygonXY([pts_out, pts_in]))
                else:
                    if inner_rad == 0:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out]))
                    else:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out, pts_in]))
                attr = feature.attributes()
                if export_geom:
                    attr.append(pt_orig_x)
                    attr.append(pt_orig_y)
                f.setAttributes(attr)
                sink.addFeature(f)
            except Exception:
                num_bad += 1

            feedback.setProgress(int(cnt * total))

        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, feature_count)))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'createdonut'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/donut.png'))

    def displayName(self):
        return tr('Create donut')

    def group(self):
        return tr('Geodesic vector creation')

    def groupId(self):
        return 'vectorcreation'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def createInstance(self):
        return CreateDonutAlgorithm()
