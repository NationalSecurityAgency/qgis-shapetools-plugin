import os
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPoint, QgsGeometry, QgsLineString, QgsMultiLineString, QgsField,
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
# import traceback

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS


class CreateRadialLinesAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmOuterRadius = 'OuterRadius'
    PrmInnerRadius = 'InnerRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmNumberOfLines = 'NumberOfLines'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreateRadialLinesAlgorithm()

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
        return (QgsWkbTypes.MultiLineString)

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
            self.PrmNumberOfLines,
            tr('Number of radial lines'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=5,
            minValue=1,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmNumberOfLines,
            tr('Number of radial lines'),
            QgsPropertyDefinition.Integer))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmInnerRadius,
            tr('Inner radius'),
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
        self.nlines = self.parameterAsInt(parameters, self.PrmNumberOfLines, context)
        self.nlines_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmNumberOfLines)
        if self.nlines_dyn:
            self.nlines_property = parameters[self.PrmNumberOfLines]
        self.outer_radius = self.parameterAsDouble(parameters, self.PrmOuterRadius, context)
        if self.outer_radius <= 0:
            feedback.reportError('Outer radius parameter must be greater than 0')
            return False
        self.outer_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOuterRadius)
        if self.outer_radius_dyn:
            self.outer_radius_property = parameters[self.PrmOuterRadius]
        self.inner_radius = self.parameterAsDouble(parameters, self.PrmInnerRadius, context)
        self.inner_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmInnerRadius)
        if self.inner_radius_dyn:
            self.inner_radius_property = parameters[self.PrmInnerRadius]
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measure_factor = conversionToMeters(units)

        self.inner_radius_converted = self.inner_radius * self.measure_factor
        self.outer_radius_converted = self.outer_radius * self.measure_factor

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
            line_strings = []
            pt = feature.geometry().asPoint()
            pt_orig = QgsPoint(pt)
            # make sure the coordinates are in EPSG:4326
            if self.geom_to_4326:
                pt = self.geom_to_4326.transform(pt.x(), pt.y())
            lat = pt.y()
            lon = pt.x()
            if self.inner_radius_dyn:
                inner_rad, e = self.inner_radius_property.valueAsDouble(context.expressionContext(), self.inner_radius)
                if not e:
                    self.num_bad += 1
                    return []
                inner_rad *= self.measure_factor
            else:
                inner_rad = self.inner_radius_converted
            if self.outer_radius_dyn:
                outer_rad, e = self.outer_radius_property.valueAsDouble(context.expressionContext(), self.outer_radius)
                if not e or outer_rad <= 0:
                    self.num_bad += 1
                    return []
                outer_rad *= self.measure_factor
            else:
                outer_rad = self.outer_radius_converted
            if self.nlines_dyn:
                num_lines, e = self.nlines_property.valueAsInt(context.expressionContext(), self.nlines)
                if not e or num_lines < 1:
                    self.num_bad += 1
                    return []
            else:
                num_lines = self.nlines
            angle = 0
            angle_step = 360.0 / num_lines
            while angle < 360:
                if inner_rad == 0:
                    pt_start = pt_orig
                else:
                    g = geod.Direct(lat, lon, angle, inner_rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pt_start = QgsPoint(g['lon2'], g['lat2'])
                    if self.to_sink_crs:
                        pt_start = self.to_sink_crs.transform(pt_start)
                g = geod.Direct(lat, lon, angle, outer_rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pt_end = QgsPoint(g['lon2'], g['lat2'])
                if self.to_sink_crs:
                    pt_end = self.to_sink_crs.transform(pt_end)

                line_str = QgsLineString([pt_start, pt_end])
                line_strings.append(line_str)
                angle += angle_step

            if len(line_strings) == 1:
                feature.setGeometry(QgsGeometry(line_strings[0]))
            else:
                g = QgsMultiLineString()
                for line_str in line_strings:
                    g.addGeometry(line_str)
                feature.setGeometry(QgsGeometry(g))
            if self.export_geom:
                attr = feature.attributes()
                attr.append(pt_orig.x())
                attr.append(pt_orig.y())
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
