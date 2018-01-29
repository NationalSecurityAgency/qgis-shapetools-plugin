import os
import re
import math
import sys
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsCoordinateTransform, QgsPoint, QgsFeature, QgsGeometry, 
    QgsMapLayerRegistry, QGis)
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel

from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterBoolean
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector, raster
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

from PyQt4.QtGui import QDialog, QIcon
from PyQt4 import uic

from .LatLon import LatLon
from .settings import settings, epsg4326

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/geodesicDensifyDialog.ui'))
    
geod = Geodesic.WGS84

class GeodesicDensifyWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(GeodesicDensifyWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.inputLineComboBox.setFilters(QgsMapLayerProxyModel.LineLayer | QgsMapLayerProxyModel.PolygonLayer)
        
    def accept(self):
        layer = self.inputLineComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        discardVertices = self.discardVerticesCheckBox.isChecked()
        
        layercrs = layer.crs()
        wkbtype = layer.wkbType()
        newlayername = self.geodesicLineNameLineEdit.text()
                
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and line output layers
        isline = False
        if wkbtype == QGis.WKBLineString or discardVertices:
            newLayer = QgsVectorLayer("LineString?crs={}".format(layercrs.authid()), newlayername, "memory")
            isline = True
        elif wkbtype == QGis.WKBMultiLineString:
            newLayer = QgsVectorLayer("MultiLineString?crs={}".format(layercrs.authid()), newlayername, "memory")
            isline = True
        elif wkbtype == QGis.WKBPolygon:
            newLayer = QgsVectorLayer("Polygon?crs={}".format(layercrs.authid()), newlayername, "memory")
        else:
            newLayer = QgsVectorLayer("MultiPolygon?crs={}".format(layercrs.authid()), newlayername, "memory")
        dp = newLayer.dataProvider()
        dp.addAttributes(fields)
        newLayer.updateFields()
        
        if isline:
            num_bad = processLine(layer, dp, discardVertices, False)
        else:
            num_bad = processPoly(layer, dp, False)
        
        newLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(newLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} features failed".format(num_bad), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()

class GeodesicDensifyAlgorithm(GeoAlgorithm):

    LAYER = 'LAYER'
    OUTPUT = 'OUTPUT'
    DISCARDVERTICES = 'DISCARDVERTICES'

    def processAlgorithm(self, progress):
        filename = self.getParameterValue(self.LAYER)
        layer = dataobjects.getObjectFromUri(filename)     
        discardVertices = self.getParameterValue(self.DISCARDVERTICES)
              
        output = self.getOutputFromName(self.OUTPUT)

        wkbtype = layer.wkbType()
        if wkbtype == QGis.WKBLineString or wkbtype == QGis.WKBMultiLineString:
            outputType = QGis.WKBLineString if (wkbtype == QGis.WKBLineString 
                or discardVertices) else QGis.WKBMultiLineString
            
            writerLines = output.getVectorWriter(layer.pendingFields(), outputType, self.crs)

            processLine(layer, writerLines, discardVertices, True)
        else:
            outputType = QGis.WKBPolygon if wkbtype == QGis.WKBPolygon else QGis.WKBMultiPolygon
            writerLines = output.getVectorWriter(layer.pendingFields(), outputType, self.crs)
            processPoly(layer, writerLines, True)
            

        del writerLines

    def getIcon(self):
        return QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')

    def defineCharacteristics(self):
        self.name = 'Geodesic Shape Densifier'
        self.i18n_name = self.name
        self.group = 'Vector geometry tools'
        self.i18n_group = self.group
        self.addParameter(ParameterVector(self.LAYER, 'Line or polygon layer', [ParameterVector.VECTOR_TYPE_LINE, ParameterVector.VECTOR_TYPE_POLYGON]))
        self.addOutput(OutputVector(self.OUTPUT, 'Output layer'))
        self.addParameter(ParameterBoolean(self.DISCARDVERTICES, "Discard inner line vertices"))

def processPoly(layer, writerLines, isProcessing):
    layercrs = layer.crs()    
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326)
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs)
    
    wkbtype = layer.wkbType()
    iterator = layer.getFeatures()
    num_features = 0
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for feature in iterator:
        num_features += 1
        try:
            if wkbtype == QGis.WKBPolygon:
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
                    ptStart = QgsPoint(points[0][0], points[0][1])
                    if layercrs != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                    pts = [ptStart]
                    for x in range(1,numpoints):
                        ptEnd = QgsPoint(points[x][0], points[x][1])
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
                            pts.append( QgsPoint(g['lon2'], g['lat2']) )
                        pts.append(ptEnd)
                        ptStart = ptEnd
     
                        if layercrs != epsg4326: # Convert each point to the output CRS
                            for x, pt in enumerate(pts):
                                pts[x] = transfrom4326.transform(pt)
                    ptset.append(pts)
                        
                if len(ptset) > 0:
                    featureout = QgsFeature()
                    featureout.setGeometry(QgsGeometry.fromPolygon(ptset))
                                
                    featureout.setAttributes(feature.attributes())
                    if isProcessing:
                        writerLines.addFeature(featureout)
                    else:
                        writerLines.addFeatures([featureout])
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
                        ptStart = QgsPoint(points[0][0], points[0][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPoint(points[x][0], points[x][1])
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
                                pts.append( QgsPoint(g['lon2'], g['lat2']) )
                            pts.append(ptEnd)
                            ptStart = ptEnd
         
                            if layercrs != epsg4326: # Convert each point to the output CRS
                                for x, pt in enumerate(pts):
                                    pts[x] = transfrom4326.transform(pt)
                        ptset.append(pts)
                    multiset.append(ptset)
                        
                if len(multiset) > 0:
                    featureout = QgsFeature()
                    featureout.setGeometry(QgsGeometry.fromMultiPolygon(multiset))
                                
                    featureout.setAttributes(feature.attributes())
                    if isProcessing:
                        writerLines.addFeature(featureout)
                    else:
                        writerLines.addFeatures([featureout])
        except:
            num_bad += 1
            pass
                
    return num_bad
        
def processLine(layer, writerLines, discardVertices, isProcessing):
    layercrs = layer.crs()    
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326)
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs)
    
    wkbtype = layer.wkbType()
    iterator = layer.getFeatures()
    num_features = 0
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for feature in iterator:
        num_features += 1
        try:
            if wkbtype == QGis.WKBLineString:
                seg = [feature.geometry().asPolyline()]
            else:
                seg = feature.geometry().asMultiPolyline()
            numseg = len(seg)
            if numseg < 1 or len(seg[0]) < 2:
                continue
            # Create a new Line Feature
            fline = QgsFeature()
            # If the input is not 4326 we need to convert it to that and then back to the output CRS
            if discardVertices:
                ptStart = QgsPoint(seg[0][0][0], seg[0][0][1])
                if layercrs != epsg4326: # Convert to 4326
                    ptStart = transto4326.transform(ptStart)
                pts = [ptStart]
                numpoints = len(seg[numseg-1])
                ptEnd = QgsPoint(seg[numseg-1][numpoints-1][0], seg[numseg-1][numpoints-1][1])
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
                        pts.append( QgsPoint(g['lon2'], g['lat2']) )
                pts.append(ptEnd)
                
                if layercrs != epsg4326: # Convert each point back to the output CRS
                    for x, pt in enumerate(pts):
                        pts[x] = transfrom4326.transform(pt)
                fline.setGeometry(QgsGeometry.fromPolyline(pts))
            else:
                if wkbtype == QGis.WKBLineString:
                    line = seg[0]
                    numpoints = len(line)
                    ptStart = QgsPoint(line[0][0], line[0][1])
                    if layercrs != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                    pts = [ptStart]
                    for x in range(1,numpoints):
                        ptEnd = QgsPoint(line[x][0], line[x][1])
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
                                pts.append( QgsPoint(g['lon2'], g['lat2']) )
                        pts.append(ptEnd)
                        ptStart = ptEnd
                
                    if layercrs != epsg4326: # Convert each point back to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                else: # MultiLineString
                    outseg = []
                    for line in seg:
                        numpoints = len(line)
                        ptStart = QgsPoint(line[0][0], line[0][1])
                        if layercrs != epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPoint(line[x][0], line[x][1])
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
                                    pts.append( QgsPoint(g['lon2'], g['lat2']) )
                            pts.append(ptEnd)
                            ptStart = ptEnd
                            
                        if layercrs != epsg4326: # Convert each point back to the output CRS
                            for x, pt in enumerate(pts):
                                pts[x] = transfrom4326.transform(pt)
                        outseg.append(pts)
                
                    fline.setGeometry(QgsGeometry.fromMultiPolyline(outseg))
                    
            fline.setAttributes(feature.attributes())
            if isProcessing:
                writerLines.addFeature(fline)
            else:
                writerLines.addFeatures([fline])
        except:
            num_bad += 1
            pass
            
    return num_bad
