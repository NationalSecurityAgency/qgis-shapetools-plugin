import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsPointXY, QgsFeature, QgsGeometry, 
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)
    
from qgis.core import (QgsProcessing,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS
import traceback

SHAPE_TYPE=[tr("Polygon"),tr("Line")]

class CreateStarAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmStarPointsField = 'StarPointsField'
    PrmOuterRadiusField = 'OuterRadiusField'
    PrmInnerRadiusField = 'InnerRadiusField'
    PrmStartingAngleField = 'StartingAngleField'
    PrmDefaultStarPoints = 'DefaultStarPoints'
    PrmDefaultOuterRadius = 'DefaultOuterRadius'
    PrmDefaultInnerRadius = 'DefaultInnerRadius'
    PrmDefaultStartingAngle = 'DefaultStartingAngle'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'

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
            QgsProcessingParameterField(
                self.PrmStarPointsField,
                tr('Number of star points field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
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
                self.PrmStartingAngleField,
                tr('Starting angle field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultStarPoints,
                tr('Default number of points on the star'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=5,
                minValue=3,
                optional=True)
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
            QgsProcessingParameterNumber(
                self.PrmDefaultStartingAngle,
                tr('Default starting angle'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
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
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
            )
    
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        shapetype = self.parameterAsInt(parameters, self.PrmShapeType, context)
        outerCol = self.parameterAsString(parameters, self.PrmOuterRadiusField, context)
        innerCol = self.parameterAsString(parameters, self.PrmInnerRadiusField, context)
        starPointsCol = self.parameterAsString(parameters, self.PrmStarPointsField, context)
        startAngleCol = self.parameterAsString(parameters, self.PrmStartingAngleField, context)
        outerRadius = self.parameterAsDouble(parameters, self.PrmDefaultOuterRadius, context)
        innerRadius = self.parameterAsDouble(parameters, self.PrmDefaultInnerRadius, context)
        startAngle = self.parameterAsDouble(parameters, self.PrmDefaultStartingAngle, context)
        numPoints = self.parameterAsInt(parameters, self.PrmDefaultStarPoints, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measureFactor = conversionToMeters(units)
        innerRadius *= measureFactor
        outerRadius *= measureFactor

        srcCRS = source.sourceCrs()
        if shapetype == 0:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.Polygon, srcCRS)
        else:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.LineString, srcCRS)
                
        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        
        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        
        half = (360.0 / numPoints) / 2.0

        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                pts = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                if srcCRS != epsg4326:
                    pt = geomTo4326.transform(pt.x(), pt.y())
                    
                if outerCol:
                    oradius = float(feature[outerCol]) * measureFactor
                else:
                    oradius = outerRadius
                if innerCol:
                    iradius = float(feature[innerCol]) * measureFactor
                else:
                    iradius = innerRadius
                if startAngleCol:
                    sangle = float(feature[startAngleCol])
                else:
                    sangle = startAngle
                if starPointsCol:
                    spoints = float(feature[starPointsCol])
                    shalf = (360.0 / spoints) / 2.0
                else:
                    spoints = numPoints
                    shalf = half
                    
                i = spoints - 1
                while i >= 0:
                    i -= 1
                    angle = (i * 360.0 / spoints) + sangle
                    g = geod.Direct(pt.y(), pt.x(), angle, oradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    g = geod.Direct(pt.y(), pt.x(), angle-shalf, iradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if srcCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = toSinkCrs.transform(ptout)
                        
                f = QgsFeature()
                if shapetype == 0:
                    f.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                else:
                    f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except:
                s = traceback.format_exc()
                feedback.pushInfo(s)
                pass
                
            feedback.setProgress(int(cnt * total))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createstar'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/star.png'))
    
    def displayName(self):
        return tr('Create star')
    
    def group(self):
        return tr('Geodesic vector creation')
        
    def groupId(self):
        return 'vectorcreation'
        
    def helpUrl(self):
        file = os.path.dirname(__file__)+'/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)
        
    def createInstance(self):
        return CreateStarAlgorithm()

