import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsGeometry, QgsField, QgsPropertyDefinition,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)

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
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS

SHAPE_TYPE = [tr("Polygon"), tr("Line")]

class CreateHypocycloidAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a hypocycloid shape.
    """

    PrmShapeType = 'ShapeType'
    PrmCusps = 'Cusps'
    PrmRadius = 'Radius'
    PrmStartingAngle = 'StartingAngle'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreateHypocycloidAlgorithm()

    def name(self):
        return 'createhypocycloid'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/hypocycloid.png'))

    def displayName(self):
        return tr('Create hypocycloid')

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
            self.PrmCusps,
            tr('Number of cusps'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=4,
            minValue=3,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmCusps,
            tr('Number of cusps'),
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
                tr('Radius units of measure'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDrawingSegments,
                tr('Number of drawing segments'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=720,
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
        self.radius = self.parameterAsDouble(parameters, self.PrmRadius, context)
        self.radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRadius)
        if self.radius_dyn:
            self.radius_property = parameters[self.PrmRadius]
        self.start_angle = self.parameterAsDouble(parameters, self.PrmStartingAngle, context)
        self.start_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmStartingAngle)
        if self.start_angle_dyn:
            self.start_angle_property = parameters[self.PrmStartingAngle]
        self.cusps = self.parameterAsInt(parameters, self.PrmCusps, context)
        self.cusps_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmCusps)
        if self.cusps_dyn:
            self.cusps_property = parameters[self.PrmCusps]
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measureFactor = conversionToMeters(units)
        self.radius_converted = self.radius * self.measureFactor

        self.step = 360.0 / segments

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
            if self.start_angle_dyn:
                sangle, e = self.start_angle_property.valueAsDouble(context.expressionContext(), self.start_angle)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                sangle = self.start_angle
            if self.cusps_dyn:
                cusps2, e = self.cusps_property.valueAsInt(context.expressionContext(), self.cusps)
                if not e or cusps2 < 3:
                    self.num_bad += 1
                    return []
            else:
                cusps2 = self.cusps
            if self.radius_dyn:
                radius2, e = self.radius_property.valueAsDouble(context.expressionContext(), self.radius)
                if not e or radius2 <= 0:
                    self.num_bad += 1
                    return []
                radius2 *= self.measureFactor
            else:
                radius2 = self.radius_converted
            r = radius2 / cusps2
            pts = []
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            angle = 0.0
            while angle <= 360.0:
                a = math.radians(angle)
                x = r * (cusps2 - 1.0) * math.cos(a) + r * math.cos((cusps2 - 1.0) * a)
                y = r * (cusps2 - 1.0) * math.sin(a) - r * math.sin((cusps2 - 1.0) * a)
                a2 = math.degrees(math.atan2(y, x)) + sangle
                dist = math.sqrt(x * x + y * y)
                g = geod.Direct(pt.y(), pt.x(), a2, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += self.step

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
