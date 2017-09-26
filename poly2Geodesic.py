import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsCoordinateReferenceSystem, QgsVectorLayer,
    QgsCoordinateTransform, QgsPoint, QgsFeature, QgsGeometry, 
    QgsMapLayerRegistry, QGis)
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel

from PyQt4.QtGui import QDialog
from PyQt4 import uic

from .LatLon import LatLon

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/poly2GeodesicDialog.ui'))

class Poly2GeodesicWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent, settings):
        super(Poly2GeodesicWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.settings = settings
        self.inputPolyComboBox.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.epsg4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        self.geod = Geodesic.WGS84
        
    def accept(self):
        layer = self.inputPolyComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        layercrs = layer.crs()
        wkbtype = layer.wkbType()
        polyname = self.geodesicPolyNameLineEdit.text()
                
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and polygon output layers
        if wkbtype == QGis.WKBPolygon:
            polyLayer = QgsVectorLayer("Polygon?crs={}".format(layercrs.authid()), polyname, "memory")
        else:
            polyLayer = QgsVectorLayer("MultiPolygon?crs={}".format(layercrs.authid()), polyname, "memory")
        ppoly = polyLayer.dataProvider()
        ppoly.addAttributes(fields)
        polyLayer.updateFields()
        
        if layercrs != self.epsg4326:
            transto4326 = QgsCoordinateTransform(layercrs, self.epsg4326)
            transfrom4326 = QgsCoordinateTransform(self.epsg4326, layercrs)
        
        iter = layer.getFeatures()
        num_features = 0
        num_bad = 0
        maxseglen = self.settings.maxSegLength*1000.0
        maxSegments = self.settings.maxSegments
        for feature in iter:
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
                        if layercrs != self.epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPoint(points[x][0], points[x][1])
                            if layercrs != self.epsg4326: # Convert to 4326
                                ptEnd = transto4326.transform(ptEnd)
                            l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
         
                            if layercrs != self.epsg4326: # Convert each point to the output CRS
                                for x, pt in enumerate(pts):
                                    pts[x] = transfrom4326.transform(pt)
                        ptset.append(pts)
                            
                    if len(ptset) > 0:
                        featureout = QgsFeature()
                        featureout.setGeometry(QgsGeometry.fromPolygon(ptset))
                                    
                        featureout.setAttributes(feature.attributes())
                        ppoly.addFeatures([featureout])
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
                            if layercrs != self.epsg4326: # Convert to 4326
                                ptStart = transto4326.transform(ptStart)
                            pts = [ptStart]
                            for x in range(1,numpoints):
                                ptEnd = QgsPoint(points[x][0], points[x][1])
                                if layercrs != self.epsg4326: # Convert to 4326
                                    ptEnd = transto4326.transform(ptEnd)
                                l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
             
                                if layercrs != self.epsg4326: # Convert each point to the output CRS
                                    for x, pt in enumerate(pts):
                                        pts[x] = transfrom4326.transform(pt)
                            ptset.append(pts)
                        multiset.append(ptset)
                            
                    if len(multiset) > 0:
                        featureout = QgsFeature()
                        featureout.setGeometry(QgsGeometry.fromMultiPolygon(multiset))
                                    
                        featureout.setAttributes(feature.attributes())
                        ppoly.addFeatures([featureout])
            except:
                num_bad += 1
                pass
                
        polyLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polyLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} out of {} features failed".format(num_bad, num_features), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()
