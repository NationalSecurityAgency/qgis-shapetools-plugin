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

    def initParameters(self, config=None):
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
        self.dist_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRadius)
        if self.dist_dyn:
            self.dist_property = parameters[self.PrmRadius]
        unitOfDist = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measureFactor = conversionToMeters(unitOfDist)

        self.dist_converted = self.dist * self.measureFactor

        source = self.parameterAsSource(parameters, 'INPUT', context)
        srcCRS = source.sourceCrs()

        if srcCRS != epsg4326:
            self.geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            self.toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        else:
            self.geomTo4326 = None
            self.toSinkCrs = None
        return True

    def processFeature(self, feature, context, feedback):
        try:
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            if self.sides_dyn:
                s = self.sides_property.valueAsInt(context.expressionContext(), self.sides)[0]
            else:
                s = self.sides
            if self.angle_dyn:
                startangle = self.angle_property.valueAsDouble(context.expressionContext(), self.angle)[0]
            else:
                startangle = self.angle
            if self.dist_dyn:
                d = self.dist_property.valueAsDouble(context.expressionContext(), self.dist)[0] * self.measureFactor
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
            return []
        return [feature]
