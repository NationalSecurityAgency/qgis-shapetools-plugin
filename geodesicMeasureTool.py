import os
import math
from geographiclib.geodesic import Geodesic

from qgis.PyQt.QtCore import Qt, QSettings, QVariant, QByteArray
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QTableWidgetItem, QDialog
from qgis.core import (QgsCoordinateTransform, 
    QgsUnitTypes, QgsWkbTypes, QgsGeometry, QgsFields, QgsField, 
    QgsProject, QgsVectorLayer, QgsFeature, 
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt import uic

from .settings import epsg4326, settings

class GeodesicMeasureTool(QgsMapTool):
    
    def __init__(self, iface, parent):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.measureDialog = GeodesicMeasureDialog(iface, parent)
        
    def activate(self):
        '''When activated set the cursor to a crosshair.'''
        self.canvas.setCursor(Qt.CrossCursor)
        self.measureDialog.show()
        
    def closeDialog(self):
        '''Close the geodesic measure tool dialog box.'''
        if self.measureDialog.isVisible():
            self.measureDialog.closeDialog()
        
    def canvasPressEvent(self, event):
        '''Capture the coordinates when the user click on the mouse for measurements.'''
        if not self.measureDialog.isVisible():
            self.measureDialog.show()
            return
        if not self.measureDialog.ready():
            return
        pt = event.mapPoint()
        button = event.button()
        canvasCRS = self.canvas.mapSettings().destinationCrs()
        if canvasCRS != epsg4326:
            transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
            pt = transform.transform(pt.x(), pt.y())
        self.measureDialog.addPoint(pt, button)
        if button == 2:
            self.measureDialog.stop()
        
    def canvasMoveEvent(self, event):
        '''Capture the coordinate as the user moves the mouse over
        the canvas.'''
        if self.measureDialog.motionReady():
            try:
                pt = event.mapPoint()
                canvasCRS = self.canvas.mapSettings().destinationCrs()
                if canvasCRS != epsg4326:
                    transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
                    pt = transform.transform(pt.x(), pt.y())
                self.measureDialog.inMotion(pt)
            except:
                return
            
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/geodesicMeasureDialog.ui'))

UNITS = ['meters', 'kilometers', 'feet', 'yards','miles','nautical miles']

class GeodesicMeasureDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(GeodesicMeasureDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        settings = QSettings()

        self.restoreGeometry(settings.value("ShapeTools/MeasureDialogGeometry",
                                        QByteArray(), type=QByteArray))
        self.closeButton.clicked.connect(self.closeDialog)
        self.newButton.clicked.connect(self.newDialog)
        self.saveToLayerButton.clicked.connect(self.saveToLayer)
        self.saveToLayerButton.setEnabled(False)

        self.unitsComboBox.addItems(UNITS)

        self.tableWidget.setColumnCount(3)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setHorizontalHeaderLabels(['Heading To', 'Heading From', 'Distance'])
        
        self.unitsComboBox.activated.connect(self.unitsChanged)
        
        self.capturedPoints = []
        self.distances = []
        self.geod = Geodesic.WGS84
        self.activeMeasuring = True
        self.unitsChanged()
        self.currentDistance = 0.0
        
        color = QColor(222, 167, 67, 150)
        self.pointRb = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.pointRb.setColor(color)
        self.pointRb.setIconSize(10)
        self.lineRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.lineRb.setColor(color)
        self.lineRb.setWidth(3)
        self.tempRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.tempRb.setColor(color)
        self.tempRb.setWidth(3)

    def ready(self):
        return self.activeMeasuring
        
    def stop(self):
        self.activeMeasuring = False
        
    def closeEvent(self, event):
        self.closeDialog()
        
    def closeDialog(self):
        self.clear()
        QSettings().setValue(
            "ShapeTools/MeasureDialogGeometry", self.saveGeometry())
        self.close()
        
    def newDialog(self):
        self.clear()
        
    def unitsChanged(self):
        label = "Distance [{}]".format(UNITS[self.unitsComboBox.currentIndex()])
        item = QTableWidgetItem(label)
        self.tableWidget.setHorizontalHeaderItem(2, item)
        ptcnt = len(self.capturedPoints)
        if ptcnt >= 2:
            i = 0
            while i < ptcnt-1:
                item = QTableWidgetItem('{:.4f}'.format(self.unitDistance(self.distances[i])))
                self.tableWidget.setItem(i, 2, item)
                i += 1
            self.formatTotal()
        
    def motionReady(self):
        if len(self.capturedPoints) > 0 and self.activeMeasuring:
            return True
        return False
        
    def addPoint(self, pt, button):
        self.currentDistance = 0
        index = len(self.capturedPoints)
        if index > 0 and pt == self.capturedPoints[index-1]:
            # the clicked point is the same as the previous so just ignore it
            return
        self.capturedPoints.append(pt)
        # Add rubber band points
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        ptCanvas = transform.transform(pt.x(), pt.y())
        self.pointRb.addPoint(ptCanvas, True)
        # If there is more than 1 point add it to the table
        if index > 0:
            self.saveToLayerButton.setEnabled(True)
            (distance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index-1], self.capturedPoints[index])
            self.distances.append(distance)
            self.insertParams(index, distance, startAngle, endAngle)
            # Add Rubber Band Line
            linePts = self.getLinePts(distance, self.capturedPoints[index-1], self.capturedPoints[index])
            self.lineRb.addGeometry(QgsGeometry.fromPolylineXY( linePts ), None)
        self.formatTotal()
            
    def inMotion(self, pt):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        (self.currentDistance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index-1], pt)
        self.insertParams(index, self.currentDistance, startAngle, endAngle)
        self.formatTotal()
        linePts = self.getLinePts(self.currentDistance, self.capturedPoints[index-1], pt)
        self.tempRb.setToGeometry(QgsGeometry.fromPolylineXY( linePts ), None)
        
    def calcParameters(self, pt1, pt2):
        l = self.geod.Inverse(pt1.y(), pt1.x(), pt2.y(), pt2.x())
        az2 = (l['azi2'] + 180) %360.0
        if az2 > 180:
            az2 = az2 - 360.0
        az1 = l['azi1']
        
        # Check to see if the azimuth values should be in the range or 0 to 360
        # The default is -180 to 180
        if settings.mtAzMode:
            if az1 < 0:
                az1 += 360.0
            if az2 < 0:
                az2 += 360
        return (l['s12'], az1, az2)
        
    def getLinePts(self, distance, pt1, pt2):
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        pt1c = transform.transform(pt1.x(), pt1.y())
        pt2c = transform.transform(pt2.x(), pt2.y())
        if distance < 10000:
            return [pt1c, pt2c]
        l = self.geod.InverseLine(pt1.y(), pt1.x(), pt2.y(), pt2.x())
        n = int(math.ceil(distance / 10000.0))
        if n > 20:
            n = 20
        seglen = distance / n
        pts = [pt1c]
        for i in range(1,n):
            s = seglen * i
            g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
            ptc = transform.transform(g['lon2'], g['lat2'])
            pts.append( ptc )
        pts.append(pt2c)
        return pts
        
    def saveToLayer(self):
        units = self.unitDesignator()
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        fields = QgsFields()
        fields.append(QgsField("label", QVariant.String))
        fields.append(QgsField("value", QVariant.Double))
        fields.append(QgsField("units", QVariant.String))
        fields.append(QgsField("heading_to", QVariant.Double))
        fields.append(QgsField("heading_from", QVariant.Double))
        
        layer = QgsVectorLayer("LineString?crs={}".format(canvasCrs.authid()), "Measurements", "memory")
        dp = layer.dataProvider()
        dp.addAttributes(fields)
        layer.updateFields()
        
        num = len(self.capturedPoints)
        for i in range(1,num):
            (distance, startA, endA) = self.calcParameters(self.capturedPoints[i-1], self.capturedPoints[i])
            pts = self.getLinePts(distance, self.capturedPoints[i-1], self.capturedPoints[i])
            distance = self.unitDistance(distance)
            feat = QgsFeature(layer.fields())
            feat.setAttribute(0, "{:.2f} {}".format(distance, units))
            feat.setAttribute(1, distance)
            feat.setAttribute(2, units)
            feat.setAttribute(3, startA)
            feat.setAttribute(4, endA)
            feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
            dp.addFeatures([feat])
                
        label = QgsPalLayerSettings()
        label.fieldName = 'label'
        label.placement = QgsPalLayerSettings.AboveLine
        labeling = QgsVectorLayerSimpleLabeling(label)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        
        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def insertParams(self, position, distance, startAngle, endAngle):
        if position > self.tableWidget.rowCount():
            self.tableWidget.insertRow(position-1)
        item = QTableWidgetItem('{:.4f}'.format(self.unitDistance(distance)))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position-1, 2, item)
        item = QTableWidgetItem('{:.4f}'.format(startAngle))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position-1, 0, item)
        item = QTableWidgetItem('{:.4f}'.format(endAngle))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position-1, 1, item)
        
    def formatTotal(self):
        total = self.currentDistance
        ptcnt = len(self.capturedPoints)
        if ptcnt >= 2:
            i = 0
            while i < ptcnt-1:
                total += self.distances[i]
                i += 1
        self.distanceLineEdit.setText('{:.2f}'.format(self.unitDistance(total)))
        
        
    def clear(self):
        self.tableWidget.setRowCount(0)
        self.capturedPoints = []
        self.distances = []
        self.activeMeasuring = True
        self.currentDistance = 0.0
        self.distanceLineEdit.setText('')
        self.pointRb.reset(QgsWkbTypes.PointGeometry)
        self.lineRb.reset(QgsWkbTypes.LineGeometry)
        self.tempRb.reset(QgsWkbTypes.LineGeometry)
        self.saveToLayerButton.setEnabled(False)
        
    def unitDistance(self, distance):
        units = self.unitsComboBox.currentIndex()
        if units == 0: # meters
            return distance
        elif units == 1: # kilometers
            return distance / 1000.0
        elif units == 2: # feet
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet)
        elif units == 3: # yards
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceYards)
        elif units == 4: # miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceMiles)
        else: # nautical miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceNauticalMiles)
    
    def unitDesignator(self):
        units = self.unitsComboBox.currentIndex()
        if units == 0: # meters
            return 'm'
        elif units == 1: # kilometers
            return 'km'
        elif units == 2: # feet
            return 'ft'
        elif units == 3: # yards
            return 'yd'
        elif units == 4: # miles
            return 'mi'
        else: # nautical miles
            return 'nm'
            