import os
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPoint, QgsFeature, QgsGeometry, QgsLineString, QgsMultiLineString, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl
import traceback

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS


class CreateRadialLinesAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmOuterRadiusField = 'OuterRadiusField'
    PrmInnerRadiusField = 'InnerRadiusField'
    PrmNumberOfLinesField = 'NumberOfLinesField'
    PrmDefaultOuterRadius = 'DefaultOuterRadius'
    PrmDefaultInnerRadius = 'DefaultInnerRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDefaultNumberOfLines = 'DefaultNumberOfLines'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmOuterRadiusField,
                tr('Outer radius field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmInnerRadiusField,
                tr('Inner radius field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmNumberOfLinesField,
                tr('Number of radial lines field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultOuterRadius,
                tr('Default outer radius'),
                QgsProcessingParameterNumber.Double,
                defaultValue=20.0,
                minValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultInnerRadius,
                tr('Default inner radius'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0,
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
                self.PrmDefaultNumberOfLines,
                tr('Default number of radial lines'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=5,
                minValue=1,
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
        outer_col = self.parameterAsString(parameters, self.PrmOuterRadiusField, context)
        inner_col = self.parameterAsString(parameters, self.PrmInnerRadiusField, context)
        lines_col = self.parameterAsString(parameters, self.PrmNumberOfLinesField, context)
        def_outer_radius = self.parameterAsDouble(parameters, self.PrmDefaultOuterRadius, context)
        def_inner_radius = self.parameterAsDouble(parameters, self.PrmDefaultInnerRadius, context)
        def_lines = self.parameterAsDouble(parameters, self.PrmDefaultNumberOfLines, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        measure_factor = conversionToMeters(units)

        def_inner_radius *= measure_factor
        def_outer_radius *= measure_factor

        src_crs = source.sourceCrs()
        fields = source.fields()
        if export_geom:
            names = fields.names()
            name_x, name_y = settings.getGeomNames(names)
            fields.append(QgsField(name_x, QVariant.Double))
            fields.append(QgsField(name_y, QVariant.Double))
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, fields,
            QgsWkbTypes.MultiLineString, src_crs)

        if src_crs != epsg4326:
            geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
            to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())

        feature_count = source.featureCount()
        total = 100.0 / feature_count if feature_count else 0

        iterator = source.getFeatures()
        num_bad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                line_strings = []
                pt = feature.geometry().asPoint()
                pt_orig = QgsPoint(pt)
                # make sure the coordinates are in EPSG:4326
                if src_crs != epsg4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                if inner_col:
                    inner_radius = float(feature[inner_col]) * measure_factor
                else:
                    inner_radius = def_inner_radius
                if outer_col:
                    outer_radius = float(feature[outer_col]) * measure_factor
                else:
                    outer_radius = def_outer_radius
                if lines_col:
                    num_lines = int(feature[lines_col])
                else:
                    num_lines = def_lines
                if num_lines <= 0:
                    num_bad += 1
                    continue
                angle = 0
                angle_step = 360.0 / num_lines
                while angle < 360:
                    if inner_radius == 0:
                        pt_start = pt_orig
                    else:
                        g = geod.Direct(lat, lon, angle, inner_radius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pt_start = QgsPoint(g['lon2'], g['lat2'])
                        if src_crs != epsg4326:
                            pt_start = to_sink_crs.transform(pt_start)
                    g = geod.Direct(lat, lon, angle, outer_radius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pt_end = QgsPoint(g['lon2'], g['lat2'])
                    if src_crs != epsg4326:
                        pt_end = to_sink_crs.transform(pt_end)
                    
                    line_str = QgsLineString([pt_start, pt_end])
                    line_strings.append(line_str)
                    angle += angle_step

                f = QgsFeature()
                if len(line_strings) == 1:
                    f.setGeometry(QgsGeometry(line_strings[0]))
                else:
                    g = QgsMultiLineString()
                    for line_str in line_strings:
                        g.addGeometry(line_str)
                    f.setGeometry(QgsGeometry(g))
                attr = feature.attributes()
                if export_geom:
                    attr.append(pt_orig.x())
                    attr.append(pt_orig.y())
                f.setAttributes(attr)
                sink.addFeature(f)
            except Exception:
                s = traceback.format_exc()
                feedback.pushInfo(s)
                num_bad += 1

            feedback.setProgress(int(cnt * total))

        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, feature_count)))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'createradiallines'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/radialLines.png'))

    def displayName(self):
        return tr('Create radial lines')

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
        return CreateRadialLinesAlgorithm()
