import os
import math
from geographiclib.geodesic import Geodesic
#import traceback

from qgis.core import (QgsVectorLayer,
    QgsCoordinateTransform, QgsPointXY, QgsFeature, QgsGeometry, 
    QgsProject, Qgis, QgsMapLayerProxyModel, QgsWkbTypes)
    
from qgis.core import (QgsProcessing,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl, QCoreApplication

from .settings import settings, epsg4326
    
geod = Geodesic.WGS84

def tr(string):
    return QCoreApplication.translate('Processing', string)

class GeodesicDensifyAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to densify lines and polygons using geodesic calculations.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmDiscardVertices = 'DiscardVertices'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Line or polygon layer'),
                [QgsProcessing.TypeVectorLine, QgsProcessing.TypeVectorPolygon])
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
            )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmDiscardVertices,
                tr('Discard inner line vertices'),
                False,
                optional=True)
            )
    
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        discardVertices = self.parameterAsBool(parameters, self.PrmDiscardVertices, context)
        
        wkbtype = source.wkbType()
        
        if wkbtype == QgsWkbTypes.LineString or wkbtype == QgsWkbTypes.MultiLineString:
            outputType = QgsWkbTypes.LineString if (wkbtype == QgsWkbTypes.LineString 
                or discardVertices) else QgsWkbTypes.MultiLineString
                
            (sink, dest_id) = self.parameterAsSink(parameters, self.PrmOutputLayer,
                context, source.fields(), outputType, source.sourceCrs())

            num_bad = processLine(source, sink, feedback, discardVertices)
        else:
            outputType = QgsWkbTypes.Polygon if wkbtype == QgsWkbTypes.Polygon else QgsWkbTypes.MultiPolygon
            
            (sink, dest_id) = self.parameterAsSink(parameters, self.PrmOutputLayer,
                context, source.fields(), outputType, source.sourceCrs())
                
            num_bad = processPoly(source, sink, feedback)
            
        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features from input layer failed to process correctly.".format(num_bad, source.featureCount())))
            
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'geodesicdensifier'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')
    
    def displayName(self):
        return tr('Geodesic densifier')
    
    def group(self):
        return tr('Vector geometry')
        
    def groupId(self):
        return 'vectorgeometry'
        
    def helpUrl(self):
        file = os.path.dirname(__file__)+'/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)
    
    def shortHelpString(self):
        file = os.path.dirname(__file__)+'/doc/GeodesicDensifyAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help=helpf.read()
        return help
        
    def createInstance(self):
        return GeodesicDensifyAlgorithm()

def processPoly(source, sink, feedback):
    layercrs = source.sourceCrs()
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs, QgsProject.instance())
    
    total = 100.0 / source.featureCount() if source.featureCount() else 0
    iterator = source.getFeatures()
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for cnt, feature in enumerate(iterator):
        if feedback.isCanceled():
            break
        try:
            if not feature.geometry().isMultipart():
                poly = feature.geometry().asPolygon()
                numpolygons = len(poly)
                if numpolygons < 1:
                    continue
                
                ptset = []
                for points in poly:
                    numpoints = len(points)
                    if numpoints < 2:
                        continue
                    # If the input is not 4326 we need to convert it to that and then back to the output CRS
                    ptStart = QgsPointXY(points[0][0], points[0][1])
                    if layercrs != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                    pts = [ptStart]
                    for x in range(1,numpoints):
                        ptEnd = QgsPointXY(points[x][0], points[x][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptEnd = transto4326.transform(ptEnd)
                        l = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                        n = int(math.ceil(l.s13 / maxseglen))
                        if n > maxSegments:
                            n = maxSegments
                            
                        seglen = l.s13 / n
                        for i in range(1,n):
                            s = seglen * i
                            g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                            pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                        pts.append(ptEnd)
                        ptStart = ptEnd
     
                    if layercrs != epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    ptset.append(pts)
                        
                if len(ptset) > 0:
                    featureout = QgsFeature()
                    featureout.setGeometry(QgsGeometry.fromPolygonXY(ptset))
                                
                    featureout.setAttributes(feature.attributes())
                    sink.addFeature(featureout)
            else:
                multipoly = feature.geometry().asMultiPolygon()
                multiset = []
                for poly in multipoly:
                    ptset = []
                    for points in poly:
                        numpoints = len(points)
                        if numpoints < 2:
                            continue
                        # If the input is not 4326 we need to convert it to that and then back to the output CRS
                        ptStart = QgsPointXY(points[0][0], points[0][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPointXY(points[x][0], points[x][1])
                            if layercrs != epsg4326: # Convert to 4326
                                ptEnd = transto4326.transform(ptEnd)
                            l = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                            n = int(math.ceil(l.s13 / maxseglen))
                            if n > maxSegments:
                                n = maxSegments
                                
                            seglen = l.s13 / n
                            for i in range(1,n):
                                s = seglen * i
                                g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                                pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                            pts.append(ptEnd)
                            ptStart = ptEnd
         
                        if layercrs != epsg4326: # Convert each point to the output CRS
                            for x, pt in enumerate(pts):
                                pts[x] = transfrom4326.transform(pt)
                        ptset.append(pts)
                    multiset.append(ptset)
                        
                if len(multiset) > 0:
                    featureout = QgsFeature()
                    featureout.setGeometry(QgsGeometry.fromMultiPolygonXY(multiset))
                                
                    featureout.setAttributes(feature.attributes())
                    sink.addFeature(featureout)
        except:
            num_bad += 1
            #traceback.print_exc()
            pass
        feedback.setProgress(int(cnt * total))
    return num_bad
        
def processLine(source, sink, feedback, discardVertices):
    layercrs = source.sourceCrs()
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs, QgsProject.instance())
    
    total = 100.0 / source.featureCount() if source.featureCount() else 0
    iterator = source.getFeatures()
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for cnt, feature in enumerate(iterator):
        if feedback.isCanceled():
            break
        try:
            if feature.geometry().isMultipart():
                seg = feature.geometry().asMultiPolyline()
            else:
                seg = [feature.geometry().asPolyline()]
            numseg = len(seg)
            if numseg < 1 or len(seg[0]) < 2:
                continue
            # Create a new Line Feature
            fline = QgsFeature()
            # If the input is not 4326 we need to convert it to that and then back to the output CRS
            if discardVertices:
                ptStart = QgsPointXY(seg[0][0][0], seg[0][0][1])
                if layercrs != epsg4326: # Convert to 4326
                    ptStart = transto4326.transform(ptStart)
                pts = [ptStart]
                numpoints = len(seg[numseg-1])
                ptEnd = QgsPointXY(seg[numseg-1][numpoints-1][0], seg[numseg-1][numpoints-1][1])
                if layercrs != epsg4326: # Convert to 4326
                    ptEnd = transto4326.transform(ptEnd)
                l = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                if l.s13 > maxseglen:
                    n = int(math.ceil(l.s13 / maxseglen))
                    if n > maxSegments:
                        n = maxSegments
                    seglen = l.s13 / n
                    for i in range(1,n):
                        s = seglen * i
                        g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                        pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                pts.append(ptEnd)
                
                if layercrs != epsg4326: # Convert each point back to the output CRS
                    for x, pt in enumerate(pts):
                        pts[x] = transfrom4326.transform(pt)
                fline.setGeometry(QgsGeometry.fromPolylineXY(pts))
            else:
                if not feature.geometry().isMultipart():
                    line = seg[0]
                    numpoints = len(line)
                    ptStart = QgsPointXY(line[0][0], line[0][1])
                    if layercrs != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                    pts = [ptStart]
                    for x in range(1,numpoints):
                        ptEnd = QgsPointXY(line[x][0], line[x][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptEnd = transto4326.transform(ptEnd)
                        l = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                        n = int(math.ceil(l.s13 / maxseglen))
                        if l.s13 > maxseglen:
                            if n > maxSegments:
                                n = maxSegments
                            seglen = l.s13 / n
                            for i in range(1,n):
                                s = seglen * i
                                g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                                pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                        pts.append(ptEnd)
                        ptStart = ptEnd
                
                    if layercrs != epsg4326: # Convert each point back to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolylineXY(pts))
                else: # MultiLineString
                    outseg = []
                    for line in seg:
                        numpoints = len(line)
                        ptStart = QgsPointXY(line[0][0], line[0][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPointXY(line[x][0], line[x][1])
                            if layercrs != epsg4326: # Convert to 4326
                                ptEnd = transto4326.transform(ptEnd)
                            l = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                            n = int(math.ceil(l.s13 / maxseglen))
                            if l.s13 > maxseglen:
                                if n > maxSegments:
                                    n = maxSegments
                                seglen = l.s13 / n
                                for i in range(1,n):
                                    s = seglen * i
                                    g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                                    pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                            pts.append(ptEnd)
                            ptStart = ptEnd
                            
                        if layercrs != epsg4326: # Convert each point back to the output CRS
                            for x, pt in enumerate(pts):
                                pts[x] = transfrom4326.transform(pt)
                        outseg.append(pts)
                
                    fline.setGeometry(QgsGeometry.fromMultiPolylineXY(outseg))
                    
            fline.setAttributes(feature.attributes())
            sink.addFeature(fline)
        except:
            num_bad += 1
            #traceback.print_exc()
            pass
        feedback.setProgress(int(cnt * total))
            
    return num_bad
