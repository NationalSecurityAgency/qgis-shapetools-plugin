import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsCoordinateReferenceSystem, QgsVectorLayer,
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
from .settings import settings

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/line2GeodesicDialog.ui'))

epsg4326 = QgsCoordinateReferenceSystem('EPSG:4326')

class Line2GeodesicWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(Line2GeodesicWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.inputLineComboBox.setFilters(QgsMapLayerProxyModel.LineLayer)

    def accept(self):
        layer = self.inputLineComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        discardVertices = self.discardVerticesCheckBox.isChecked()

        layercrs = layer.crs()
        wkbtype = layer.wkbType()
        linename = self.geodesicLineNameLineEdit.text()

        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and line output layers
        if wkbtype == QGis.WKBLineString or discardVertices:
            lineLayer = QgsVectorLayer("LineString?crs={}".format(layercrs.authid()), linename, "memory")
        else:
            lineLayer = QgsVectorLayer("MultiLineString?crs={}".format(layercrs.authid()), linename, "memory")
        pline = lineLayer.dataProvider()
        pline.addAttributes(fields)
        lineLayer.updateFields()
        
        num_bad = process(layer, lineLayer)
                
        lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(lineLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} out of {} features failed".format(num_bad, num_features), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()


class Line2GeodesicAlgorithm(GeoAlgorithm):

    LAYER = 'LAYER'
    OUTPUT = 'OUTPUT'
    DISCARDVERTICES = 'DISCARDVERTICES'

    def processAlgorithm(self, progress):
        filename = self.getParameterValue(self.LAYER)
        layer = dataobjects.getObjectFromUri(filename)     
        discardVertices = self.getParameterValue(self.DISCARDVERTICES)
              
        output = self.getOutputFromName(self.OUTPUT)

        outputType = QGis.WKBLineString if (layer.wkbType() == QGis.WKBLineString 
            or discardVertices) else QGis.WKBMultiLineString
        
        writerLines = output.getVectorWriter(layer.pendingFields(), outputType, self.crs)

        process(layer, output)

        del writerLines

    def getIcon(self):
        return QIcon(os.path.dirname(__file__) + '/images/line2geodesic.png')

    def defineCharacteristics(self):
        self.name = 'Line2Geodesic'
        self.i18n_name = self.name
        self.group = 'Shape tools'
        self.i18n_group = self.group
        self.addParameter(ParameterVector(self.LAYER, 'Lines layer', ParameterVector.VECTOR_TYPE_LINE))
        self.addParameter(ParameterBoolean(self.DISCARDVERTICES, "Discard vertices"))
        self.addOutput(OutputVector(self.OUTPUT, 'Output layer'))
        
def process(layer, output):
    layercrs = layer.crs()
    if layercrs != epsg4326:
        transto4326 = QgsCoordinateTransform(layercrs, epsg4326)
        transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs)
    
    iterator = layer.getFeatures()
    num_features = 0
    num_bad = 0
    maxseglen = settings.maxSegLength * 1000.0
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
                l = Geodesic.WGS84.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
                        l = Geodesic.WGS84.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
                            l = Geodesic.WGS84.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
            pline.addFeatures([fline])
        except:
            num_bad += 1
            pass

    return num_bad