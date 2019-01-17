import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsPointXY, QgsFeature, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)
    
from qgis.core import (QgsProcessing,
    QgsFeatureSink,
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
from .utils import tr, conversionToMeters, DISTANCE_LABELS

SHAPE_TYPE=[tr("Polygon"),tr("Line")]

class CreatePolygonAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmNumberOfSidesField = 'NumberOfSidesField'
    PrmStartingAngleField = 'StartingAngleField'
    PrmRadiusField = 'RadiusField'
    PrmDefaultNumberOfSides = 'DefaultNumberOfSides'
    PrmDefaultStartingAngle = 'DefaultStartingAngle'
    PrmDefaultRadius = 'DefaultRadius'
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
            QgsProcessingParameterField(
                self.PrmNumberOfSidesField,
                tr('Number of sides field'),
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
            QgsProcessingParameterField(
                self.PrmRadiusField,
                tr('Radius field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultNumberOfSides,
                tr('Default number of sides'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=3,
                minValue=3,
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
            QgsProcessingParameterNumber(
                self.PrmDefaultRadius,
                tr('Default radius'),
                QgsProcessingParameterNumber.Double,
                defaultValue=40.0,
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
        sidescol = self.parameterAsString(parameters, self.PrmNumberOfSidesField, context)
        anglecol = self.parameterAsString(parameters, self.PrmStartingAngleField, context)
        distcol = self.parameterAsString(parameters, self.PrmRadiusField, context)
        sides = self.parameterAsInt(parameters, self.PrmDefaultNumberOfSides, context)
        angle = self.parameterAsDouble(parameters, self.PrmDefaultStartingAngle, context)
        defaultDist = self.parameterAsInt(parameters, self.PrmDefaultRadius, context)
        unitOfDist = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)
        
        measureFactor = conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
        
        srcCRS = source.sourceCrs()
        fields = source.fields()
        if export_geom:
            names = fields.names()
            name_x, name_y = settings.getGeomNames(names)
            fields.append(QgsField(name_x, QVariant.Double))
            fields.append(QgsField(name_y, QVariant.Double))
        if shapetype == 0:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Polygon, srcCRS)
        else:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fields,
                QgsWkbTypes.LineString, srcCRS)
                
        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        
        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        
        iterator = source.getFeatures()
        numbad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                pt = feature.geometry().asPoint()
                pt_orig_x = pt.x()
                pt_orig_y = pt.y()
                if srcCRS != epsg4326:
                    pt = geomTo4326.transform(pt.x(), pt.y())
                if sidescol:
                    s = int(feature[sidescol])
                else:
                    s = sides
                if anglecol:
                    startangle = float(feature[anglecol])
                else:
                    startangle = angle
                if distcol:
                    d = float(feature[distcol])*measureFactor
                else:
                    d = defaultDist
                pts = []
                i = s
                while i >= 0:
                    a = (i * 360.0 / s)+startangle
                    i -= 1
                    g = geod.Direct(pt.y(), pt.x(), a, d, Geodesic.LATITUDE | Geodesic.LONGITUDE)
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
                attr = feature.attributes()
                if export_geom:
                    attr.append(pt_orig_x)
                    attr.append(pt_orig_y)
                f.setAttributes(attr)
                sink.addFeature(f)
            except:
                numbad += 1
                
            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))
            
        if numbad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(numbad, featureCount)))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createpolygon'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/polygon.png'))
    
    def displayName(self):
        return tr('Create polygon')
    
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
        return CreatePolygonAlgorithm()

