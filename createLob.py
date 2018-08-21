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

from .settings import epsg4326, geod, settings
from .utils import tr, conversionToMeters,DISTANCE_LABELS

class CreateLobAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a line of bearing.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmAzimuthField = 'AzimuthField'
    PrmDistanceField = 'DistanceField'
    PrmDefaultAzimuth = 'DefaultAzimuth'
    PrmDefaultDistance = 'DefaultDistance'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmAzimuthField,
                tr('Azimuth/bearing field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmDistanceField,
                tr('Distance field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultAzimuth,
                tr('Default azimuth/bearing'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultDistance,
                tr('Default distance'),
                QgsProcessingParameterNumber.Double,
                defaultValue=1000.0,
                minValue=0,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Distance units'),
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
        bearingcol = self.parameterAsString(parameters, self.PrmAzimuthField, context)
        distcol = self.parameterAsString(parameters, self.PrmDistanceField, context)
        defaultBearing = self.parameterAsDouble(parameters, self.PrmDefaultAzimuth, context)
        defaultDist = self.parameterAsDouble(parameters, self.PrmDefaultDistance, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measureFactor = conversionToMeters(units)
            
        defaultDist *= measureFactor
        maxseglen = settings.maxSegLength*1000.0 # Needs to be in meters
        maxSegments = settings.maxSegments
        
        srcCRS = source.sourceCrs()
        (sink, dest_id) = self.parameterAsSink(parameters,
            self.PrmOutputLayer, context, source.fields(),
            QgsWkbTypes.LineString, srcCRS)
                
        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        
        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        
        num_features = 0
        numbad = 0
        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            num_features += 1
            try:
                if bearingcol:
                    bearing = float(feature[bearingcol])
                else:
                    bearing = defaultBearing
                if distcol:
                    distance = float(feature[distcol])*measureFactor
                else:
                    distance = defaultDist
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                if srcCRS != epsg4326:
                    pt = geomTo4326.transform(pt.x(), pt.y())
                pts = [pt]
                l = geod.Line(pt.y(), pt.x(), bearing)
                n = int(math.ceil(distance / maxseglen))
                if n > maxSegments:
                    n = maxSegments
                seglen = distance / n
                for i in range(1,n+1):
                    s = seglen * i
                    g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                    pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if srcCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = toSinkCrs.transform(ptout)
                            
                f  = QgsFeature()
                f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except:
                numbad += 1
                
            feedback.setProgress(int(cnt * total))
            
        if numbad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(numbad, featureCount)))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createlob'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/line.png'))
    
    def displayName(self):
        return tr('Create line of bearing')
    
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
        return CreateLobAlgorithm()

