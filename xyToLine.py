import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsCoordinateTransform, QgsPoint, QgsFeature, QgsGeometry, 
    QgsMapLayerRegistry, QGis)
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel

from PyQt4.QtGui import QDialog
from PyQt4 import uic

from .LatLon import LatLon
from .settings import settings, epsg4326

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/xyToLineDialog.ui'))

class XYToLineWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(XYToLineWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.inputMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.NoGeometry)
        self.inputMapLayerComboBox.layerChanged.connect(self.layerChanged)
        self.inputQgsProjectionSelectionWidget.setCrs(epsg4326)
        self.outputQgsProjectionSelectionWidget.setCrs(epsg4326)
        self.lineTypeComboBox.addItems(['Geodesic','Great Circle','Simple Line'])
        self.geod = Geodesic.WGS84
        
    def accept(self):
        layer = self.inputMapLayerComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        pointname = self.pointsNameLineEdit.text()
        linename = self.lineNameLineEdit.text()
        startXcol = self.startXFieldComboBox.currentIndex() # Returns -1 if none selected
        startYcol = self.startYFieldComboBox.currentIndex()
        endXcol = self.endXFieldComboBox.currentIndex()
        endYcol = self.endYFieldComboBox.currentIndex()
        startUseGeom = self.startCheckBox.isChecked()
        endUseGeom = self.endCheckBox.isChecked()
        inCRS = self.inputQgsProjectionSelectionWidget.crs()
        outCRS = self.outputQgsProjectionSelectionWidget.crs()
        lineType = self.lineTypeComboBox.currentIndex()
        showStart = self.showStartCheckBox.isChecked()
        showEnd = self.showEndCheckBox.isChecked()
        
        if (startUseGeom == False) and (startXcol == -1 or startYcol == -1):
            self.iface.messageBar().pushMessage("", "Must specify valid starting point columns", level=QgsMessageBar.WARNING, duration=4)
            return
        if (endUseGeom == False) and (endXcol == -1 or endYcol == -1):
            self.iface.messageBar().pushMessage("", "Must specify valid ending point columns", level=QgsMessageBar.WARNING, duration=4)
            return
        
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and line output layers
        lineLayer = QgsVectorLayer("LineString?crs={}".format(outCRS.authid()), linename, "memory")
        pline = lineLayer.dataProvider()
        pline.addAttributes(fields)
        lineLayer.updateFields()
        
        if showStart or showEnd:
            pointLayer = QgsVectorLayer("Point?crs={}".format(outCRS.authid()), pointname, "memory")
            ppoint = pointLayer.dataProvider()
            ppoint.addAttributes(fields)
            pointLayer.updateFields()
        
        transform = QgsCoordinateTransform(inCRS, outCRS)
        if inCRS != epsg4326:
            transto4326 = QgsCoordinateTransform(inCRS, epsg4326)
        if outCRS != epsg4326:
            transfrom4326 = QgsCoordinateTransform(epsg4326, outCRS)
        
        iter = layer.getFeatures()
        num_features = 0
        num_bad = 0
        maxseglen = settings.maxSegLength*1000.0
        maxSegments = settings.maxSegments
        for feature in iter:
            num_features += 1
            try:
                if startUseGeom == True:
                    ptStart = feature.geometry().asPoint()
                else:
                    ptStart = QgsPoint(float(feature[startXcol]), float(feature[startYcol]))
                if endUseGeom == True:
                    ptEnd = feature.geometry().asPoint()
                else:
                    ptEnd = QgsPoint(float(feature[endXcol]), float(feature[endYcol]))
                # Create a new Line Feature
                fline = QgsFeature()
                if lineType == 0: # Geodesic
                    # If the input is not 4326 we need to convert it to that and then back to the output CRS
                    if inCRS != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                        ptEnd = transto4326.transform(ptEnd)
                    pts = [ptStart]
                    l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
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
                    if outCRS != epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                elif lineType == 1: # Great Circle
                    # If the input is not 4326 we need to convert it to that and then back to the output CRS
                    if inCRS != epsg4326: # Convert to 4326
                        ptStart = transto4326.transform(ptStart)
                        ptEnd = transto4326.transform(ptEnd)
                    pts = LatLon.getPointsOnLine(ptStart.y(), ptStart.x(),
                        ptEnd.y(), ptEnd.x(),
                        settings.maxSegLength*1000.0, # Put it in meters
                        settings.maxSegments+1)
                    if outCRS != epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                else: # Simple line
                    '''Transform the starting and end points if the input CRS
                       and the output CRS are not the same and then create a 
                       2 point polyline'''
                    if inCRS != outCRS:
                        ptStart = transform.transform(ptStart)
                        ptEnd = transform.transform(ptEnd)
                    fline.setGeometry(QgsGeometry.fromPolyline([ptStart, ptEnd]))
                fline.setAttributes(feature.attributes())
                pline.addFeatures([fline])
                # Add two point features
                if showStart:
                    fpoint = QgsFeature()
                    fpoint.setGeometry(QgsGeometry.fromPoint(ptStart))
                    fpoint.setAttributes(feature.attributes())
                    ppoint.addFeatures([fpoint])
                if showEnd:
                    fpoint = QgsFeature()
                    fpoint.setGeometry(QgsGeometry.fromPoint(ptEnd))
                    fpoint.setAttributes(feature.attributes())
                    ppoint.addFeatures([fpoint])
            except:
                num_bad += 1
                pass
                
        lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(lineLayer)
        if showStart or showEnd:
            pointLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(pointLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} out of {} features failed".format(num_bad, num_features), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()
        
    def layerChanged(self):
        if not self.isVisible():
            return
        layer = self.inputMapLayerComboBox.currentLayer()
        self.startXFieldComboBox.setLayer(layer)
        self.startYFieldComboBox.setLayer(layer)
        self.endXFieldComboBox.setLayer(layer)
        self.endYFieldComboBox.setLayer(layer)

        if not layer:
            return
            
        geomType = layer.geometryType()
        if geomType == QGis.Point:
            self.startCheckBox.setEnabled(True)
            self.endCheckBox.setEnabled(True)
        else:
            self.startCheckBox.setChecked(False)
            self.endCheckBox.setChecked(False)
            self.startCheckBox.setEnabled(False)
            self.endCheckBox.setEnabled(False)
        
        name = layer.name()
        self.pointsNameLineEdit.setText(name + " points")
        self.lineNameLineEdit.setText(name + " line")
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(XYToLineWidget, self).showEvent(event)
        self.layerChanged()
