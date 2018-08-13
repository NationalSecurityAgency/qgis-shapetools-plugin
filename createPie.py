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
import traceback
SHAPE_TYPE=[tr("Polygon"),tr("Line")]

class CreatePieAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmAzimuthMode='AzimuthMode'
    PrmAzimuth1Field = 'Azimuth1Field'
    PrmAzimuth2Field = 'Azimuth2Field'
    PrmRadiusField = 'RadiusField'
    PrmDefaultAzimuth1 = 'DefaultAzimuth1'
    PrmDefaultAzimuth2 = 'DefaultAzimuth2'
    PrmDefaultRadius = 'DefaultRadius'
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
            QgsProcessingParameterEnum(
                self.PrmAzimuthMode,
                tr('Azimuth mode'),
                options=[tr('Use beginning and ending azimuths'),tr('Use center azimuth and width')],
                defaultValue=1,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmAzimuth1Field,
                tr('Starting azimuth field / Center azimuth field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmAzimuth2Field,
                tr('Ending azimuth field / Azimuth width field'),
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
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Radius units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultAzimuth1,
                tr('Default starting azimuth / Default center azimuth'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultAzimuth2,
                tr('Default ending azimuth / Default azimuth width'),
                QgsProcessingParameterNumber.Double,
                defaultValue=30.0,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultRadius,
                tr('Default radius'),
                QgsProcessingParameterNumber.Double,
                defaultValue=20.0,
                minValue=0,
                optional=True)
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
        azimuthmode = self.parameterAsInt(parameters, self.PrmAzimuthMode, context)
        startanglecol = self.parameterAsString(parameters, self.PrmAzimuth1Field, context)
        endanglecol = self.parameterAsString(parameters, self.PrmAzimuth2Field, context)
        radiusCol = self.parameterAsString(parameters, self.PrmRadiusField, context)
        startangle = self.parameterAsDouble(parameters, self.PrmDefaultAzimuth1, context)
        endangle = self.parameterAsDouble(parameters, self.PrmDefaultAzimuth2, context)
        radius = self.parameterAsDouble(parameters, self.PrmDefaultRadius, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measureFactor = conversionToMeters(units)
            
        radius *= measureFactor
        
        ptSpacing = 360.0 / segments
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
                pts.append(pt)
                if startanglecol:
                    sangle = float(feature[startanglecol])
                else:
                    sangle = startangle
                if endanglecol:
                    eangle = float(feature[endanglecol])
                else:
                    eangle = endangle
                if azimuthmode == 1:
                    width = abs(eangle) / 2.0
                    eangle = sangle + width
                    sangle -= width
                if radiusCol:
                    dist = float(feature[radiusCol]) * measureFactor
                else:
                    dist = radius
                    
                sangle = sangle % 360
                eangle = eangle % 360
                
                if sangle > eangle:
                    # We are crossing the 0 boundry so lets just subtract
                    # 360 from it.
                    sangle -= 360.0
                while sangle < eangle:
                    g = geod.Direct(pt.y(), pt.x(), sangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    sangle += ptSpacing # add this number of degrees to the angle
                    
                g = geod.Direct(pt.y(), pt.x(), eangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                pts.append(pt)
                    
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
        return 'createpie'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/pie.png'))
    
    def displayName(self):
        return tr('Create pie wedge')
    
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
        return CreatePieAlgorithm()

