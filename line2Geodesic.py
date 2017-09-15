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
    os.path.dirname(__file__), 'line2GeodesicDialog.ui'))

class Line2GeodesicWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent, settings):
        super(Line2GeodesicWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.settings = settings
        self.inputLineComboBox.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.epsg4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        self.geodesicLineTypeComboBox.addItems(['Geodesic','Great Circle'])
        self.geod = Geodesic.WGS84
        
    def accept(self):
        layer = self.inputLineComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        layercrs = layer.crs()
        linename = self.geodesicLineNameLineEdit.text()
        discardVertices = self.discardVerticesCheckBox.isChecked()
        lineType = self.geodesicLineTypeComboBox.currentIndex()
                
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and line output layers
        lineLayer = QgsVectorLayer("LineString?crs={}".format(layercrs.authid()), linename, "memory")
        pline = lineLayer.dataProvider()
        pline.addAttributes(fields)
        lineLayer.updateFields()
        
        if layercrs != self.epsg4326:
            transto4326 = QgsCoordinateTransform(layercrs, self.epsg4326)
            transfrom4326 = QgsCoordinateTransform(self.epsg4326, layercrs)
        
        iter = layer.getFeatures()
        num_features = 0
        num_bad = 0
        for feature in iter:
            num_features += 1
            try:
                line = feature.geometry().asPolyline()
                numpoints = len(line)
                if numpoints < 2:
                    continue
                # Create a new Line Feature
                fline = QgsFeature()
                if lineType == 0: # Geodesic
                    # If the input is not 4326 we need to convert it to that and then back to the output CRS
                    ptStart = QgsPoint(line[0][0], line[0][1])
                    if layercrs != self.epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                    pts = [ptStart]
                    if discardVertices:
                        ptEnd = QgsPoint(line[numpoints-1][0], line[numpoints-1][1])
                        if layercrs != self.epsg4326: # Convert to 4326
                            ptEnd = transto4326.transform(ptEnd)
                        l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                        seglen = self.settings.maxSegLength*1000.0
                        n = int(math.ceil(l.s13 / seglen))
                        if n > self.settings.maxSegments:
                            seglen = l.s13 / self.settings.maxSegments
                            n = int(math.ceil(l.s13 / seglen))
                        for i in range(1,n):
                            s = min(seglen * i, l.s13)
                            g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                            pts.append( QgsPoint(g['lon2'], g['lat2']) )
                        pts.append(ptEnd)
                    else:
                        for x in range(1,numpoints):
                            ptEnd = QgsPoint(line[x][0], line[x][1])
                            if layercrs != self.epsg4326: # Convert to 4326
                                ptEnd = transto4326.transform(ptEnd)
                            l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                            seglen = self.settings.maxSegLength*1000.0
                            n = int(math.ceil(l.s13 / seglen))
                            if n > self.settings.maxSegments:
                                seglen = l.s13 / self.settings.maxSegments
                                n = int(math.ceil(l.s13 / seglen))
                            for i in range(1,n):
                                s = min(seglen * i, l.s13)
                                g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                                pts.append( QgsPoint(g['lon2'], g['lat2']) )
                            pts.append(ptEnd)
                            ptStart = ptEnd
 
                    if layercrs != self.epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                else: # Great Circle
                    if discardVertices:
                        ptStart = QgsPoint(line[0][0], line[0][1])
                        ptEnd = QgsPoint(line[numpoints-1][0], line[numpoints-1][1])
                        if layercrs != self.epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                            ptEnd = transto4326.transform(ptEnd)
                        pts = LatLon.getPointsOnLine(ptStart.y(), ptStart.x(),
                            ptEnd.y(), ptEnd.x(),
                            self.settings.maxSegLength*1000.0, # Put it in meters
                            self.settings.maxSegments+1)
                    else:
                        ptStart = QgsPoint(line[0][0], line[0][1])
                        if layercrs != self.epsg4326: # Convert to 4326
                            ptStart = transto4326.transform(ptStart)
                        pts = [ptStart]
                        for x in range(1,numpoints):
                            ptEnd = QgsPoint(line[x][0], line[x][1])
                            if layercrs != self.epsg4326: # Convert to 4326
                                ptEnd = transto4326.transform(ptEnd)
                            pts2 = LatLon.getPointsOnLine(ptStart.y(), ptStart.x(),
                                ptEnd.y(), ptEnd.x(),
                                self.settings.maxSegLength*1000.0, # Put it in meters
                                self.settings.maxSegments+1)
                            # Add these points to my list, skipping the first since it is already on the list
                            pts += pts2[1:]
                            ptStart = ptEnd
                            
                    if layercrs != self.epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                fline.setAttributes(feature.attributes())
                pline.addFeatures([fline])
            except:
                num_bad += 1
                pass
                
        lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(lineLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} out of {} features failed".format(num_bad, num_features), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()
