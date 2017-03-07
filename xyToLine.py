import os
import re
import math

from qgis.core import *
from qgis.gui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from LatLon import LatLon



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'xyToLineDialog.ui'))

class XYToLineWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(XYToLineWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.inputMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.NoGeometry)
        self.inputMapLayerComboBox.layerChanged.connect(self.layerChanged)
        self.epsg4326 = QgsCoordinateReferenceSystem('EPSG:4326')
        self.inputQgsProjectionSelectionWidget.setCrs(self.epsg4326)
        self.outputQgsProjectionSelectionWidget.setCrs(self.epsg4326)
        self.lineTypeComboBox.addItems(['Direct','Great Circle'])
        
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
        
        iter = layer.getFeatures()
        num_features = 0
        num_bad = 0
        for feature in iter:
            num_features += 1
            try:
                if startUseGeom == True:
                    pt = feature.geometry().asPoint()
                    startx = pt.x()
                    starty = pt.y()
                else:
                    startx = float(feature[startXcol])
                    starty = float(feature[startYcol])
                ptStart = transform.transform(startx, starty)
                if endUseGeom == True:
                    pt = feature.geometry().asPoint()
                    endx = pt.x()
                    endy = pt.y()
                else:
                    endx = float(feature[endXcol])
                    endy = float(feature[endYcol])
                ptEnd = transform.transform(endx, endy)
                # Add the Line Feature
                fline = QgsFeature()
                if lineType == 0: # Direct
                    fline.setGeometry(QgsGeometry.fromPolyline([ptStart, ptEnd]))
                else:
                    pts = LatLon.getPointsOnLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x(), 151)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
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
