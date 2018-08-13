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

from .settings import epsg4326
from .utils import geod, tr, conversionToMeters, DISTANCE_LABELS

SHAPE_TYPE=[tr("Polygon"),tr("Line")]

class CreateDonutAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmOuterRadiusField = 'OuterRadiusField'
    PrmInnerRadiusField = 'InnerRadiusField'
    PrmDefaultOuterRadius = 'DefaultOuterRadius'
    PrmDefaultInnerRadius = 'DefaultInnerRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'

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
                self.PrmDrawingSegments,
                tr('Number of drawing segments'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=36,
                minValue=4,
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
        outerCol = self.parameterAsString(parameters, self.PrmOuterRadiusField, context)
        innerCol = self.parameterAsString(parameters, self.PrmInnerRadiusField, context)
        defOuterRadius = self.parameterAsDouble(parameters, self.PrmDefaultOuterRadius, context)
        defInnerRadius = self.parameterAsDouble(parameters, self.PrmDefaultInnerRadius, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measureFactor = conversionToMeters(units)
            
        defInnerRadius *= measureFactor
        defOuterRadius *= measureFactor
        
        ptSpacing = 360.0 / segments
        srcCRS = source.sourceCrs()
        if shapetype == 0:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.Polygon, srcCRS)
        else:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.MultiLineString, srcCRS)
                
        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        
        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        
        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                ptsi = []
                ptso = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                if srcCRS != epsg4326:
                    pt = geomTo4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                angle = 0
                while angle < 360:
                    if innerCol:
                        iRadius = float(feature[innerCol]) * measureFactor
                    else:
                        iRadius = defInnerRadius
                    if outerCol:
                        oRadius = float(feature[outerCol]) * measureFactor
                    else:
                        oRadius = defOuterRadius
                    if iRadius != 0:
                        g = geod.Direct(lat, lon, angle, iRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        ptsi.append(QgsPointXY(g['lon2'], g['lat2']))
                    g = geod.Direct(lat, lon, angle, oRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    ptso.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += ptSpacing
                if iRadius != 0:
                    ptsi.append(ptsi[0])
                ptso.append(ptso[0])
                
                # If the Output crs is not 4326 transform the points to the proper crs
                if srcCRS != epsg4326:
                    if iRadius != 0:
                        for x, ptout in enumerate(ptsi):
                            ptsi[x] = toSinkCrs.transform(ptout)
                    for x, ptout in enumerate(ptso):
                        ptso[x] = toSinkCrs.transform(ptout)
                        
                f = QgsFeature()
                if shapetype == 0:
                    if iRadius == 0:
                        f.setGeometry(QgsGeometry.fromPolygonXY([ptso]))
                    else:
                        f.setGeometry(QgsGeometry.fromPolygonXY([ptso, ptsi]))
                else:
                    if iRadius == 0:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([ptso]))
                    else:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([ptso, ptsi]))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except:
                pass
                
            feedback.setProgress(int(cnt * total))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createdonut'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/donut.png'))
    
    def displayName(self):
        return tr('Create donut')
    
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
        return CreateDonutAlgorithm()

