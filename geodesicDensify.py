import os
import re
import math
import sys
from geographiclib.geodesic import Geodesic
#import traceback

from qgis.core import (QgsVectorLayer,
    QgsCoordinateTransform, QgsPointXY, QgsFeature, QgsGeometry, 
    QgsProject, Qgis, QgsMapLayerProxyModel, QgsWkbTypes)

'''from processing.core.GeoAlgorithm import GeoAlgorithm
from processing.core.parameters import ParameterVector, ParameterBoolean
from processing.core.outputs import OutputVector
from processing.tools import dataobjects, vector, raster
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException'''

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import uic

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
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=Qgis.Warning, duration=4)
        discardVertices = self.discardVerticesCheckBox.isChecked()
        
        layercrs = layer.crs()
        wkbtype = layer.wkbType()
        newlayername = self.geodesicLineNameLineEdit.text()
                
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.fields()
        
        # Create the points and line output layers
        if (wkbtype == QgsWkbTypes.LineString) or (wkbtype == QgsWkbTypes.MultiLineString):
            if wkbtype == QgsWkbTypes.LineString or discardVertices:
                newLayer = QgsVectorLayer("LineString?crs={}".format(layercrs.authid()), newlayername, "memory")
            elif wkbtype == QgsWkbTypes.MultiLineString:
                newLayer = QgsVectorLayer("MultiLineString?crs={}".format(layercrs.authid()), newlayername, "memory")
            dp = newLayer.dataProvider()
            dp.addAttributes(fields)
            newLayer.updateFields()
            num_bad = processLine(layer, dp, discardVertices, False)
        else:
            if wkbtype == QgsWkbTypes.Polygon:
                newLayer = QgsVectorLayer("Polygon?crs={}".format(layercrs.authid()), newlayername, "memory")
            else:
                newLayer = QgsVectorLayer("MultiPolygon?crs={}".format(layercrs.authid()), newlayername, "memory")
            dp = newLayer.dataProvider()
            dp.addAttributes(fields)
            newLayer.updateFields()
            num_bad = processPoly(layer, dp, False)
        
        newLayer.updateExtents()
        QgsProject.instance().addMapLayer(newLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} features failed".format(num_bad), level=Qgis.Warning, duration=3)
       
        self.close()

'''class GeodesicDensifyAlgorithm(GeoAlgorithm):

    LAYER = 'LAYER'
    OUTPUT = 'OUTPUT'
    DISCARDVERTICES = 'DISCARDVERTICES'

    def processAlgorithm(self, progress):
        filename = self.getParameterValue(self.LAYER)
        layer = dataobjects.getObjectFromUri(filename)     
        discardVertices = self.getParameterValue(self.DISCARDVERTICES)
              
        output = self.getOutputFromName(self.OUTPUT)

        wkbtype = layer.wkbType()
        if wkbtype == QgsWkbTypes.LineString or wkbtype == QgsWkbTypes.MultiLineString:
            outputType = QgsWkbTypes.LineString if (wkbtype == QgsWkbTypes.LineString 
                or discardVertices) else QgsWkbTypes.MultiLineString
            
            writerLines = output.getVectorWriter(layer.fields(), outputType, self.crs)

            processLine(layer, writerLines, discardVertices, True)
        else:
            outputType = QgsWkbTypes.Polygon if wkbtype == QgsWkbTypes.Polygon else QgsWkbTypes.MultiPolygon
            writerLines = output.getVectorWriter(layer.fields(), outputType, self.crs)
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
        self.addParameter(ParameterBoolean(self.DISCARDVERTICES, "Discard inner line vertices"))'''

def processPoly(layer, writerLines, isProcessing):
    layercrs = layer.crs()
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs, QgsProject.instance())
    
    iterator = layer.getFeatures()
    num_features = 0
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for feature in iterator:
        num_features += 1
        try:
            wkbtype = feature.geometry().wkbType()
            if wkbtype == QgsWkbTypes.Polygon:
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
                    if isProcessing:
                        writerLines.addFeature(featureout)
                    else:
                        writerLines.addFeatures([featureout])
        except:
            num_bad += 1
            #traceback.print_exc()
            pass
                
    return num_bad
        
def processLine(layer, writerLines, discardVertices, isProcessing):
    layercrs = layer.crs()    
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs, QgsProject.instance())
    
    iterator = layer.getFeatures()
    num_features = 0
    num_bad = 0
    maxseglen = settings.maxSegLength*1000.0
    maxSegments = settings.maxSegments
    for feature in iterator:
        num_features += 1
        try:
            wkbtype = feature.geometry().wkbType()
            if wkbtype == QgsWkbTypes.LineString:
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
                if wkbtype == QgsWkbTypes.LineString:
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
            if isProcessing:
                writerLines.addFeature(fline)
            else:
                writerLines.addFeatures([fline])
        except:
            num_bad += 1
            #traceback.print_exc()
            pass
            
    return num_bad
