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
    os.path.dirname(__file__), 'vector2Shape.ui'))

DISTANCE_MEASURE=["Nautical Miles","Kilometers","Meters","Miles","Feet"]
class Vector2ShapeWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(Vector2ShapeWidget, self).__init__(parent)
        self.setupUi(self)
        self.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mMapLayerComboBox.layerChanged.connect(self.findFields)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.iface = iface
        self.unitOfAxisComboBox.addItems(DISTANCE_MEASURE)
        self.unitOfDistanceComboBox.addItems(DISTANCE_MEASURE)
        self.polygonLayer = None

    def apply(self):
        '''process the data'''
        tab = self.tabWidget.currentIndex()
        layer = self.mMapLayerComboBox.currentLayer()
        outname = self.layerNameLineEdit.text()
        if not layer:
            self.showErrorMessage("No valid layer to process")
            return
        
        # We need to make sure all the points in the layer are transformed to EPSG:4326
        layerCRS = layer.crs()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        self.transform = QgsCoordinateTransform(layerCRS, epsg4326)
        
        if tab == 0: # Ellipse
            self.processEllipse(layer, outname,
                self.semiMajorComboBox.currentIndex()-1,
                self.semiMinorComboBox.currentIndex()-1,
                self.orientationComboBox.currentIndex()-1,
                self.unitOfAxisComboBox.currentIndex())
        elif tab == 1: # LOB
            try:
                distance = float(self.defaultDistanceLineEdit.text())
            except:
                self.showErrorMessage("Invalid Distance. Fix and try again")
                return
            self.processLOB(layer, outname,
                self.bearingComboBox.currentIndex()-1,
                self.distanceComboBox.currentIndex()-1,
                self.unitOfDistanceComboBox.currentIndex(),
                distance)
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(Vector2ShapeWidget, self).showEvent(event)
        self.findFields()
        
    def findFields(self):
        if not self.isVisible():
            return
        layer = self.mMapLayerComboBox.currentLayer()
        if not layer:
            self.clearLayerFields()
        else:
            header = [u"--- Select Column ---"]
            default = [u"[ Use Default ]"]
            fields = layer.pendingFields()
            for field in fields.toList():
                # force it to be lower case - makes matching easier
                name = field.name()
                header.append(name)
                default.append(name)
            self.configureLayerFields(header, default)

    def configureLayerFields(self, header, default):
        self.clearLayerFields()
        self.semiMajorComboBox.addItems(header)
        self.semiMinorComboBox.addItems(header)
        self.orientationComboBox.addItems(header)
        
        self.bearingComboBox.addItems(header)
        self.distanceComboBox.addItems(default)
        
        orientcol = semimajorcol = semiminorcol = -1
        bearingcol = distancecol = -1
        for x, item in enumerate(header):
            # Skip the first entry
            if x == 0:
                continue
            lcitem = item.lower()
            if lcitem.startswith('orient'):
                orientcol = x
            elif bool(re.match('semi.*maj', lcitem)):
                semimajorcol = x
            elif bool(re.match('semi.*min', lcitem)):
                semiminorcol = x
            elif bool(re.search('bearing', lcitem)):
                bearingcol = x
            elif bool(re.match('dist', lcitem)):
                distancecol = x
                
        if orientcol != -1:
            self.orientationComboBox.setCurrentIndex(orientcol)
        if semimajorcol != -1:
            self.semiMajorComboBox.setCurrentIndex(semimajorcol)
        if semiminorcol != -1:
            self.semiMinorComboBox.setCurrentIndex(semiminorcol)
        if bearingcol != -1:
            self.bearingComboBox.setCurrentIndex(bearingcol)
        if distancecol != -1:
            self.distanceComboBox.setCurrentIndex(distancecol)
        
    def clearLayerFields(self):
        self.semiMajorComboBox.clear()
        self.semiMinorComboBox.clear()
        self.orientationComboBox.clear()
        self.bearingComboBox.clear()
        self.distanceComboBox.clear()
            
    def showErrorMessage(self, message):
        self.iface.messageBar().pushMessage("", message, level=QgsMessageBar.WARNING, duration=3)
        
    def processEllipse(self, layer, outname, semimajorcol, semiminorcol, orientcol, unitOfMeasure):
        if semimajorcol == -1 or semiminorcol == -1 or orientcol == -1:
            self.showErrorMessage('The semi-major, semi-minor, and orientation fields must be specified')
            return
        
        # The ellipse calculation is done in Nautical Miles. This converts
        # the semi-major and minor axis to nautical miles
        if unitOfMeasure == 0:
            measureFactor = 1.0
        elif unitOfMeasure == 1:
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Meters, QGis.NauticalMiles)*1000.0
        elif unitOfMeasure == 2:
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Meters, QGis.NauticalMiles)
        elif unitOfMeasure == 3:
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.NauticalMiles)*5280.0
        elif unitOfMeasure == 4:
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.NauticalMiles)
        
        fields = layer.pendingFields()
        
        self.polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = self.polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        self.polygonLayer.updateFields()
        
        iter = layer.getFeatures()
        num_features = 0
        num_good = 0
        for feature in iter:
            num_features += 1
            try:
                semi_major = float(feature[semimajorcol])
                semi_minor = float(feature[semiminorcol])
                orient = float(feature[orientcol])
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                geom = LatLon.getEllipseCoords(pt.y(), pt.x(), semi_major*measureFactor,
                    semi_minor*measureFactor, orient)
                featureout = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolygon([geom]))
                featureout.setAttributes(feature.attributes())
                ppolygon.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                pass
        self.polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(self.polygonLayer)
        self.iface.messageBar().pushMessage("", "{} Ellipses created from {} records".format(num_good, num_features), level=QgsMessageBar.INFO, duration=3)
        
    def processLOB(self, layer, outname, bearingcol, distcol, unitOfDist, defaultDist):
        if bearingcol == -1:
            self.showErrorMessage('A Bearing field must be specified')
            return
            
        if unitOfDist == 0: # Nautical Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.NauticalMiles, QGis.Meters)
        elif unitOfDist == 1: # Kilometers
            measureFactor = 1000.0
        elif unitOfDist == 2: # Meters
            measureFactor = 1.0
        elif unitOfDist == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)*5280.0
        elif unitOfDist == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)
            
        defaultDist *= measureFactor
        
        fields = layer.pendingFields()
        
        self.lineLayer = QgsVectorLayer("LineString?crs=epsg:4326", outname, "memory")
        pline = self.lineLayer.dataProvider()
        pline.addAttributes(fields)
        self.lineLayer.updateFields()
        
        iter = layer.getFeatures()
        num_features = 0
        num_good = 0
        for feature in iter:
            num_features += 1
            try:
                bearing = float(feature[bearingcol])
                if distcol != -1:
                    distance = float(feature[distcol])*measureFactor
                else:
                    distance = defaultDist
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                verticies = LatLon.getLineCoords(pt.y(), pt.x(), bearing, distance, 256, 2000)
                featureout  = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolyline(verticies))
                featureout.setAttributes(feature.attributes())
                pline.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                pass
        self.lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(self.lineLayer)
        self.iface.messageBar().pushMessage("", "{} lines of bearing created from {} records".format(num_good, num_features), level=QgsMessageBar.INFO, duration=3)
        
        
    def accept(self):
        self.apply()
        self.close()
