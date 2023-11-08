"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import re

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.uic import loadUiType
from qgis.core import Qgis, QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsPoint, QgsProject, QgsWkbTypes, QgsSettings
from qgis.gui import QgsMapToolEmitPoint, QgsVertexMarker

from geographiclib.geodesic import Geodesic
from .settings import epsg4326, geod
from .utils import conversionToMeters, DISTANCE_LABELS

def tr(string):
    return QCoreApplication.translate('Processing', string)


FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/lineDigitizer.ui'))

class LineDigitizerTool(QgsMapToolEmitPoint):
    '''Class to interact with the map canvas to capture the coordinate
    when the mouse button is pressed and to display the coordinate in
    in the status bar.'''

    def __init__(self, iface):
        QgsMapToolEmitPoint.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.lineDigitizerDialog = None
        self.vertex = None

    def activate(self):
        '''When activated set the cursor to a crosshair.'''
        self.canvas.setCursor(Qt.CrossCursor)
        self.snapcolor = QgsSettings().value( "/qgis/digitizing/snap_color" , QColor( Qt.magenta ) )

    def deactivate(self):
        self.removeVertexMarker()

    def canvasPressEvent(self, event):
        '''Capture the coordinate when the mouse button has been released.'''
        pt = self.snappoint(event.originalPixelPoint())
        self.removeVertexMarker()
        layer = self.iface.activeLayer()
        if layer is None:
            return
        if self.lineDigitizerDialog is None:
            from .lineDigitizer import LineDigitizerWidget
            self.lineDigitizerDialog = LineDigitizerWidget(self.iface, self.iface.mainWindow())

        if layer.geometryType() == QgsWkbTypes.LineGeometry:
            self.lineDigitizerDialog.closeLineCheckBox.setEnabled(True)
        else:
            self.lineDigitizerDialog.closeLineCheckBox.setEnabled(False)
        try:
            canvasCRS = self.canvas.mapSettings().destinationCrs()
            transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
            pt4326 = transform.transform(pt.x(), pt.y())
            self.lineDigitizerDialog.setPoint(pt4326)
            self.lineDigitizerDialog.valuesTextEdit.clear()
            self.lineDigitizerDialog.show()
        except Exception:
            self.iface.messageBar().pushMessage("", tr("Clicked location is invalid"), level=Qgis.Warning, duration=4)

    def canvasMoveEvent(self, event):
        '''Show when the user mouses over a vector vertex in snapping mode.'''
        self.snappoint(event.originalPixelPoint()) # input is QPoint

    def snappoint(self, qpoint):
        match = self.canvas.snappingUtils().snapToMap(qpoint)
        if match.isValid():
            if self.vertex is None:
                self.vertex = QgsVertexMarker(self.canvas)
                self.vertex.setIconSize(12)
                self.vertex.setPenWidth(2)
                self.vertex.setColor(self.snapcolor)
                self.vertex.setIconType(QgsVertexMarker.ICON_BOX)
            self.vertex.setCenter(match.point())
            return (match.point()) # Returns QgsPointXY
        else:
            self.removeVertexMarker()
            return self.toMapCoordinates(qpoint) # QPoint input, returns QgsPointXY

    def removeVertexMarker(self):
        if self.vertex is not None:
            self.canvas.scene().removeItem(self.vertex)
            self.vertex = None

class LineDigitizerWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(LineDigitizerWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.unitsComboBox.addItems(DISTANCE_LABELS)

    def setPoint(self, pt):
        self.pt = pt

    def accept(self):
        closeline = self.closeLineCheckBox.isChecked()
        declination = self.declinationSpinBox.value()
        try:
            valuestr = str(self.valuesTextEdit.toPlainText()).strip()
            values = re.split(r'[\s,;]+', valuestr)
            if (len(values) == 0) or (len(values) & 1) == 1:
                self.iface.messageBar().pushMessage("", tr("Enter bearing distance pairs"), level=Qgis.Warning, duration=4)
                return
            for x, v in enumerate(values):
                values[x] = float(v)
            units = self.unitsComboBox.currentIndex()  # 0 km, 1 m, 2 nm, 3 miles, 4 yards, 5 feet, 6 inches, 7 cm
        except Exception:
            self.iface.messageBar().pushMessage("", tr("One or more entered values were invalid"), level=Qgis.Warning, duration=4)
            return
        layer = self.iface.activeLayer()
        if layer is None:
            self.iface.messageBar().pushMessage("", tr("No point or line layer selected"), level=Qgis.Warning, duration=4)
            return

        numpairs = len(values) >> 1  # Divide by 2
        measureFactor = conversionToMeters(units)

        pt = self.pt
        destCRS = layer.crs()
        transform = QgsCoordinateTransform(epsg4326, destCRS, QgsProject.instance())
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            # output the clicked on point
            ptStart = transform.transform(self.pt.x(), self.pt.y())
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPointXY(ptStart))
            layer.addFeature(feat)
            for x in range(numpairs):
                azimuth = values[x << 1] + declination
                distance = values[(x << 1) + 1] * measureFactor
                g = geod.Direct(pt.y(), pt.x(), azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pt = QgsPoint(g['lon2'], g['lat2'])  # Keep this in EPSG:4326
                pt_trans = transform.transform(g['lon2'], g['lat2'])  # Transformed version
                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(pt_trans))
                layer.addFeature(feat)
        else:  # It will either be a Line or Polygon
            ptStart = transform.transform(self.pt.x(), self.pt.y())
            pts = [ptStart]
            for x in range(numpairs):
                azimuth = values[x << 1] + declination
                distance = values[(x << 1) + 1] * measureFactor
                g = geod.Direct(pt.y(), pt.x(), azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pt = QgsPoint(g['lon2'], g['lat2'])  # Keep this in EPSG:4326
                pt_trans = transform.transform(g['lon2'], g['lat2'])  # Transformed version
                pts.append(pt_trans)
            if layer.geometryType() == QgsWkbTypes.PolygonGeometry or closeline:
                pts.append(ptStart)

            feat = QgsFeature(layer.fields())
            if layer.geometryType() == QgsWkbTypes.LineGeometry:
                feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
            else:
                feat.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            layer.addFeatures([feat])

        layer.updateExtents()
        self.iface.mapCanvas().refresh()
        self.close()
