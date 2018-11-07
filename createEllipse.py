import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsPointXY, QgsFeature, QgsGeometry,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)
    
from qgis.core import (QgsProcessing,
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
SHAPE_TYPE = [tr("Polygon"), tr("Line")]

def geodesicEllipse(geod, lat, lon, sma, smi, orient, segments):
    segments = int(math.ceil(segments / 2))
    if smi < 0.0001: smi = 0.0001
    if sma < 0.0001: sma = 0.0001
    if sma < smi:
        temp = sma
        sma = smi
        smi = temp
        orient += 90
    ab = sma * smi
    step = 18.0 * smi / sma
    if step < 1.0:
        minimum = step
    else:
        minimum = 1.0
        
    maxang = math.pi / 6 * minimum
    delta = ab * math.pi / segments
    pts = []
    azi = 0
    while azi < math.tau:
        cos_azi = math.cos(azi)
        sin_azi = math.sin(azi)
        rad = ab / math.sqrt(sma * sma * sin_azi * sin_azi + smi * smi * cos_azi * cos_azi)
        g = geod.Direct(lat, lon, math.degrees(azi) + orient, rad, Geodesic.LATITUDE | Geodesic.LONGITUDE)
        pts.append(QgsPointXY(g['lon2'], g['lat2']))
        delo = delta / (rad * rad)
        if maxang < delo:
            delo = maxang
        azi += delo
        
    # Append the starting point to close the shape
    pts.append(pts[0])
    return( pts )
    

class CreateEllipseAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create an ellipse shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmSemiMajorAxisField = 'SemiMajorAxisField'
    PrmSemiMinorAxisField = 'SemiMinorAxisField'
    PrmOrientationField   = 'OrientationField'
    PrmDefaultSemiMajorAxis = 'DefaultSemiMajorAxis'
    PrmDefaultSemiMinorAxis = 'DefaultSemiMinorAxis'
    PrmDefaultOrientation = 'DefaultOrientation'
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
                self.PrmSemiMajorAxisField,
                tr('Semi-major axis field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmSemiMinorAxisField,
                tr('Semi-minor axis field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmOrientationField,
                tr('Orientation of axis field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultSemiMajorAxis,
                tr('Default semi-major axis'),
                QgsProcessingParameterNumber.Double,
                defaultValue=40.0,
                minValue=0.00001,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultSemiMinorAxis,
                tr('Default semi-minor axis'),
                QgsProcessingParameterNumber.Double,
                defaultValue=20.0,
                minValue=0.00001,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDefaultOrientation,
                tr('Default orientation of axis'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                minValue=-360,
                maxValue=360,
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
                tr('Number of drawing segments (approximate)'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=64,
                minValue=8,
                optional=True)
            )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
            )
    
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        semi_major_col = self.parameterAsString(parameters, self.PrmSemiMajorAxisField, context)
        semi_minor_col = self.parameterAsString(parameters, self.PrmSemiMinorAxisField, context)
        orientation_col = self.parameterAsString(parameters, self.PrmOrientationField, context)
        default_semi_major = self.parameterAsDouble(parameters, self.PrmDefaultSemiMajorAxis, context)
        default_semi_minor = self.parameterAsDouble(parameters, self.PrmDefaultSemiMinorAxis, context)
        def_orientation = self.parameterAsDouble(parameters, self.PrmDefaultOrientation, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measure_factor = conversionToMeters(units)
        
        default_semi_major *= measure_factor
        default_semi_minor *= measure_factor
        
        src_crs = source.sourceCrs()
        if shape_type == 0:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.Polygon, src_crs)
        else:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.LineString, src_crs)
                
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
                pts = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                if src_crs != epsg4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                if semi_major_col:
                    sma = float(feature[semi_major_col]) * measure_factor
                else:
                    sma = default_semi_major
                if semi_minor_col:
                    smi = float(feature[semi_minor_col]) * measure_factor
                else:
                    smi = default_semi_minor
                if orientation_col:
                    orient = float(feature[orientation_col])
                else:
                    orient = def_orientation
                
                pts = geodesicEllipse(geod, lat, lon, sma, smi, orient, segments)
                
                # If the Output crs is not 4326 transform the points to the proper crs
                if src_crs != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = to_sink_crs.transform(ptout)
                        
                f = QgsFeature()
                if shape_type == 0:
                    f.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                else:
                    f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except:
                num_bad += 1
                '''s = traceback.format_exc()
                feedback.pushInfo(s)'''
                
            feedback.setProgress(int(cnt * total))
            
        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, feature_count)))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createellipse'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/ellipse.png'))
    
    def displayName(self):
        return tr('Create ellipse')
    
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
        return CreateEllipseAlgorithm()

