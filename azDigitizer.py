import os
import math

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.uic import loadUiType
from qgis.core import Qgis, QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsProject, QgsWkbTypes
from qgis.gui import QgsMapToolEmitPoint

from geographiclib.geodesic import Geodesic
from .settings import geod
from .utils import conversionToMeters, DISTANCE_LABELS, tr

from .settings import settings, epsg4326

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/azDistDigitizer.ui'))


class AzDigitizerTool(QgsMapToolEmitPoint):
    """Class to interact with the map canvas to capture the coordinate
    when the mouse button is pressed and to display the coordinate in
    in the status bar."""
    
    def __init__(self, iface):
        QgsMapToolEmitPoint.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.canvasClicked.connect(self.clicked)
        self.azDigitizerDialog = None
        
    def activate(self):
        """When activated set the cursor to a crosshair."""
        self.canvas.setCursor(Qt.CrossCursor)
        
    def clicked(self, pt, b):
        """Capture the coordinate when the mouse button has been released."""
        if self.azDigitizerDialog is None:
            from .azDigitizer import AzDigitizerWidget
            self.azDigitizerDialog = AzDigitizerWidget(self.iface, self.iface.mainWindow())
        
        layer = self.iface.activeLayer()
        if layer is None or layer.wkbType() != QgsWkbTypes.Point:
            self.azDigitizerDialog.includeStartLabel.setEnabled(False)
            self.azDigitizerDialog.checkBox.setEnabled(False)
        else:
            self.azDigitizerDialog.includeStartLabel.setEnabled(True)
            self.azDigitizerDialog.checkBox.setEnabled(True)
        try:
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            transform = QgsCoordinateTransform(canvas_crs, epsg4326, QgsProject.instance())
            pt4326 = transform.transform(pt.x(), pt.y())
            self.azDigitizerDialog.set_point(pt4326)
            self.azDigitizerDialog.show()
        except:
            self.iface.messageBar().pushMessage("", tr("Clicked location is invalid"), level=Qgis.Warning, duration=4)


class AzDigitizerWidget(QDialog, FORM_CLASS):
    
    def __init__(self, iface, parent):
        super(AzDigitizerWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.unitsComboBox.addItems(DISTANCE_LABELS)
        
    def set_point(self, pt):
        self.pt = pt

    def accept(self):
        try:
            distance = float(self.distLineEdit.text())
            azimuth = float(self.azimuthLineEdit.text())
            units = self.unitsComboBox.currentIndex()  # 0 km, 1 m, 2 nm, 3 miles, 4 ft
            start = self.checkBox.isChecked()
        except:
            self.iface.messageBar().pushMessage("", tr("Either distance or azimuth were invalid"), level=Qgis.Warning, duration=4)
            return
        layer = self.iface.activeLayer()
        if layer is None:
            self.iface.messageBar().pushMessage("", tr("No point or line layer selected"), level=Qgis.Warning, duration=4)
            return
        
        measure_factor = conversionToMeters(units)

        distance = distance * measure_factor
        pt = self.pt
        dest_crs = layer.crs()
        transform = QgsCoordinateTransform(epsg4326, dest_crs, QgsProject.instance())
        if layer.wkbType() == QgsWkbTypes.Point:
            g = geod.Direct(pt.y(), pt.x(), azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            if start:
                pt_start = transform.transform(self.pt.x(), self.pt.y())
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(pt_start))
                layer.addFeature(feat)
            pt = transform.transform(g['lon2'], g['lat2'])
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(pt))
            layer.addFeature(feat)
        else:  # It will either be a LineString or MultiLineString
            maxseglen = settings.maxSegLength*1000.0  # Needs to be in meters
            max_segments = settings.maxSegments
            l = geod.Line(pt.y(), pt.x(), azimuth)
            n = int(math.ceil(distance / maxseglen))
            if n > max_segments:
                n = max_segments
            seglen = distance / n
            pts = []
            for i in range(0, n+1):
                s = seglen * i
                g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                ptc = transform.transform(g['lon2'], g['lat2'])
                pts.append(ptc)
            feat = QgsFeature(layer.fields())
            if layer.wkbType() == QgsWkbTypes.LineString:
                feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
            else:
                feat.setGeometry(QgsGeometry.fromMultiPolylineXY([pts]))
            layer.addFeatures([feat])
            
        layer.updateExtents()
        self.iface.mapCanvas().refresh()
        self.close()
