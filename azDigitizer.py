import os
import math

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.uic import loadUiType
from qgis.core import Qgis, QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsPoint, QgsUnitTypes, QgsProject, QgsWkbTypes
from qgis.gui import QgsMapToolEmitPoint

from geographiclib.geodesic import Geodesic
from .settings import epsg4326
#import traceback

from .settings import settings, epsg4326

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/azDistDigitizer.ui'))

class AzDigitizerTool(QgsMapToolEmitPoint):
    '''Class to interact with the map canvas to capture the coordinate
    when the mouse button is pressed and to display the coordinate in
    in the status bar.'''
    
    def __init__(self, iface):
        QgsMapToolEmitPoint.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.canvasClicked.connect(self.clicked)
        self.azDigitizerDialog = None
        
    def activate(self):
        '''When activated set the cursor to a crosshair.'''
        self.canvas.setCursor(Qt.CrossCursor)
        
    def clicked(self, pt, b):
        '''Capture the coordinate when the mouse button has been released.'''
        if self.azDigitizerDialog == None:
            from .azDigitizer import AzDigitizerWidget
            self.azDigitizerDialog = AzDigitizerWidget(self.iface, self.iface.mainWindow())
        
        layer = self.iface.activeLayer()
        if layer == None or layer.wkbType() != QgsWkbTypes.Point:
            self.azDigitizerDialog.includeStartLabel.setEnabled(False)
            self.azDigitizerDialog.checkBox.setEnabled(False)
        else:
            self.azDigitizerDialog.includeStartLabel.setEnabled(True)
            self.azDigitizerDialog.checkBox.setEnabled(True)
        try:
            canvasCRS = self.canvas.mapSettings().destinationCrs()
            transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
            pt4326 = transform.transform(pt.x(), pt.y())
            self.azDigitizerDialog.setPoint(pt4326)
            self.azDigitizerDialog.show()
        except:
            self.iface.messageBar().pushMessage("", "Clicked location is invalid", level=Qgis.Warning, duration=4)
            
class AzDigitizerWidget(QDialog, FORM_CLASS):
    
    def __init__(self, iface, parent):
        super(AzDigitizerWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.unitsComboBox.addItems(["Kilometers","Meters","Nautical Miles","Miles","Yards", "Feet"])
        self.geod = Geodesic.WGS84
        
    def setPoint(self, pt):
        self.pt = pt

    def accept(self):
        try:
            distance = float(self.distLineEdit.text())
            azimuth = float(self.azimuthLineEdit.text())
            units = self.unitsComboBox.currentIndex() # 0 km, 1 m, 2 nm, 3 miles, 4 ft
            start = self.checkBox.isChecked()
        except:
            self.iface.messageBar().pushMessage("", "Either distance or azimuth were invalid", level=Qgis.Warning, duration=4)
            return
        layer = self.iface.activeLayer()
        if layer == None:
            self.iface.messageBar().pushMessage("", "No point or line layer selected", level=Qgis.Warning, duration=4)
            return
            
        if units == 0: # Kilometers
            measureFactor = 1000.0
        elif units == 1: # Meters
            measureFactor = 1.0
        elif units == 2: # Nautical Miles
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceNauticalMiles, QgsUnitTypes.DistanceMeters)
        elif units == 3: # Miles
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceMeters)
        elif units == 4: # Yards
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceYards, QgsUnitTypes.DistanceMeters)
        elif units == 5: # Feet
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceMeters)

        distance = distance * measureFactor
        pt = self.pt
        destCRS = layer.crs()
        transform = QgsCoordinateTransform(epsg4326, destCRS, QgsProject.instance())
        if layer.wkbType() == QgsWkbTypes.Point:
            g = self.geod.Direct(pt.y(), pt.x(), azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            if start:
                ptStart = transform.transform(self.pt.x(),self.pt.y())
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(ptStart))
                layer.addFeature(feat)
            pt = transform.transform(g['lon2'],g['lat2'])
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(pt))
            layer.addFeature(feat)
        else: # It will either be a LineString or MultiLineString
            maxseglen = settings.maxSegLength*1000.0 # Needs to be in meters
            maxSegments = settings.maxSegments
            l = self.geod.Line(pt.y(), pt.x(), azimuth)
            n = int(math.ceil(distance / maxseglen))
            if n > maxSegments:
                n = maxSegments
            seglen = distance / n
            pts = []
            for i in range(0,n+1):
                s = seglen * i
                g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                ptc = transform.transform(g['lon2'], g['lat2'])
                pts.append( ptc )
            feat  = QgsFeature(layer.fields())
            if layer.wkbType() == QgsWkbTypes.LineString:
                feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
            else:
                feat.setGeometry(QgsGeometry.fromMultiPolylineXY([pts]))
            layer.addFeatures([feat])
            
        layer.updateExtents()
        self.iface.mapCanvas().refresh()
        self.close()
        
