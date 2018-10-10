import os
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

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


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
        shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        outer_col = self.parameterAsString(parameters, self.PrmOuterRadiusField, context)
        inner_col = self.parameterAsString(parameters, self.PrmInnerRadiusField, context)
        def_outer_radius = self.parameterAsDouble(parameters, self.PrmDefaultOuterRadius, context)
        def_inner_radius = self.parameterAsDouble(parameters, self.PrmDefaultInnerRadius, context)
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        
        measure_factor = conversionToMeters(units)
            
        def_inner_radius *= measure_factor
        def_outer_radius *= measure_factor
        
        pt_spacing = 360.0 / segments
        src_crs = source.sourceCrs()
        if shape_type == 0:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.Polygon, src_crs)
        else:
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, source.fields(),
                QgsWkbTypes.MultiLineString, src_crs)
                
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
                pts_in = []
                pts_out = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                if src_crs != epsg4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                angle = 0
                while angle < 360:
                    if inner_col:
                        inner_radius = float(feature[inner_col]) * measure_factor
                    else:
                        inner_radius = def_inner_radius
                    if outer_col:
                        outer_radius = float(feature[outer_col]) * measure_factor
                    else:
                        outer_radius = def_outer_radius
                    if inner_radius != 0:
                        g = geod.Direct(lat, lon, angle, inner_radius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts_in.append(QgsPointXY(g['lon2'], g['lat2']))
                    g = geod.Direct(lat, lon, angle, outer_radius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts_out.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += pt_spacing
                if inner_radius != 0:
                    pts_in.append(pts_in[0])
                pts_out.append(pts_out[0])
                
                # If the Output crs is not 4326 transform the points to the proper crs
                if src_crs != epsg4326:
                    if inner_radius != 0:
                        for x, pt_out in enumerate(pts_in):
                            pts_in[x] = to_sink_crs.transform(pt_out)
                    for x, pt_out in enumerate(pts_out):
                        pts_out[x] = to_sink_crs.transform(pt_out)
                        
                f = QgsFeature()
                if shape_type == 0:
                    if inner_radius == 0:
                        f.setGeometry(QgsGeometry.fromPolygonXY([pts_out]))
                    else:
                        f.setGeometry(QgsGeometry.fromPolygonXY([pts_out, pts_in]))
                else:
                    if inner_radius == 0:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out]))
                    else:
                        f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts_out, pts_in]))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except:
                num_bad += 1
                
            feedback.setProgress(int(cnt * total))
            
        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, feature_count)))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'createdonut'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/donut.png'))
    
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

