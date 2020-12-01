import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsPointXY, QgsFeature, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS

SHAPE_TYPE = [tr("Polygon"), tr("Line")]

class CreateRoseAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmPetals = 'Petals'
    PrmRadius = 'Radius'
    PrmStartingAngle = 'StartingAngle'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
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
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmPetals,
                tr('Number of petals'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=8,
                minValue=1,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmStartingAngle,
                tr('Starting angle'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmRadius,
                tr('Radius'),
                QgsProcessingParameterNumber.Double,
                defaultValue=40.0,
                minValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Radius units of measure'),
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
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        shapetype = self.parameterAsInt(parameters, self.PrmShapeType, context)
        radius = self.parameterAsDouble(parameters, self.PrmRadius, context)
        startAngle = self.parameterAsDouble(parameters, self.PrmStartingAngle, context)
        k = self.parameterAsInt(parameters, self.PrmPetals, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        measureFactor = conversionToMeters(units)
        radius *= measureFactor

        srcCRS = source.sourceCrs()
        fields = source.fields()
        if export_geom:
            names = fields.names()
            name_x, name_y = settings.getGeomNames(names)
            fields.append(QgsField(name_x, QVariant.Double))
            fields.append(QgsField(name_y, QVariant.Double))
        if shapetype == 0:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Polygon, srcCRS)
        else:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.LineString, srcCRS)

        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())

        dist = []
        if k == 1:
            dist.append(0.0)
        step = 1
        angle = -90.0 + step
        while angle < 90.0:
            a = math.radians(angle)
            r = math.cos(a)
            dist.append(r)
            angle += step
        cnt = len(dist)

        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0

        iterator = source.getFeatures()
        for item, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            pts = []
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if srcCRS != epsg4326:
                pt = geomTo4326.transform(pt.x(), pt.y())
            arange = 360.0 / k
            angle = -arange / 2.0
            astep = arange / cnt
            for i in range(k):
                aoffset = arange * (k - 1)
                index = 0
                while index < cnt:
                    r = dist[index] * radius
                    g = geod.Direct(pt.y(), pt.x(), angle + aoffset + startAngle, r, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += astep
                    index += 1
            # repeat the very first point to close the polygon
            pts.append(pts[0])

            makeIdlCrossingsPositive(pts)
            # If the Output crs is not 4326 transform the points to the proper crs
            if srcCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = toSinkCrs.transform(ptout)

            f = QgsFeature()
            if shapetype == 0:
                f.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                f.setGeometry(QgsGeometry.fromPolylineXY(pts))
            attr = feature.attributes()
            if export_geom:
                attr.append(pt_orig_x)
                attr.append(pt_orig_y)
            f.setAttributes(attr)
            sink.addFeature(f)

            if item % 100 == 0:
                feedback.setProgress(int(item * total))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'createrose'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/rose.png'))

    def displayName(self):
        return tr('Create ellipse rose')

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
        return CreateRoseAlgorithm()
