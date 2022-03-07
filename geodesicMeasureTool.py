import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtCore import QSize, Qt, QSettings, QVariant, QByteArray
from qgis.PyQt.QtWidgets import QTableWidgetItem, QDialog, QApplication, QMenu
from qgis.core import (
    Qgis, QgsCoordinateTransform, QgsCoordinateReferenceSystem,
    QgsUnitTypes, QgsWkbTypes, QgsGeometry, QgsFields, QgsField,
    QgsProject, QgsVectorLayer, QgsFeature, QgsPointXY,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsSettings)
from qgis.gui import QgsMapTool, QgsRubberBand, QgsProjectionSelectionDialog, QgsVertexMarker
from qgis.PyQt import uic
# import traceback

from .settings import epsg4326, settings, geod
from .utils import tr, DISTANCE_LABELS, parseDMSString
unitsAbbr = ['km', 'm', 'cm', 'mi', 'yd', 'ft', 'in', 'nm']

class GeodesicMeasureTool(QgsMapTool):

    def __init__(self, shapetools, iface, parent):
        QgsMapTool.__init__(self, iface.mapCanvas())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.measureDialog = GeodesicMeasureDialog(shapetools, iface, parent)
        self.vertex = None

    def activate(self):
        '''When activated set the cursor to a crosshair.'''
        self.canvas.setCursor(Qt.CrossCursor)
        self.measureDialog.initGeodLabel()
        self.measureDialog.show()
        self.snapcolor = QgsSettings().value( "/qgis/digitizing/snap_color" , QColor( Qt.magenta ) )

    def closeDialog(self):
        '''Close the geodesic measure tool dialog box.'''
        self.removeVertexMarker()
        if self.measureDialog.isVisible():
            self.measureDialog.closeDialog()

    def endInteractiveLine(self):
        if self.measureDialog.isVisible():
            self.measureDialog.endRubberband()

    def keyPressEvent(self, event):
        if not self.measureDialog.isVisible():
            return
        key = event.key()
        self.measureDialog.keyPressed(key)

    def canvasPressEvent(self, event):
        '''Capture the coordinates when the user click on the mouse for measurements.'''
        self.removeVertexMarker()
        if not self.measureDialog.isVisible():
            self.measureDialog.initGeodLabel()
            self.measureDialog.show()
            self.measureDialog.updateRBColor()
            return
        if not self.measureDialog.ready():
            return
        pt = self.snappoint(event.originalPixelPoint())
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
        if self.measureDialog.ready():
            pt = self.snappoint(event.originalPixelPoint())
        if self.measureDialog.motionReady():
            try:
                canvasCRS = self.canvas.mapSettings().destinationCrs()
                if canvasCRS != epsg4326:
                    transform = QgsCoordinateTransform(canvasCRS, epsg4326, QgsProject.instance())
                    pt = transform.transform(pt.x(), pt.y())
                self.measureDialog.inMotion(pt)
            except Exception:
                return

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


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/geodesicMeasureDialog.ui'))

class GeodesicMeasureDialog(QDialog, FORM_CLASS):
    def __init__(self, shapetools, iface, parent):
        super(GeodesicMeasureDialog, self).__init__(parent)
        self.setupUi(self)
        self.shapetools = shapetools
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.pointDigitizerDialog = AddMeasurePointWidget(self, iface, parent)
        qset = QSettings()

        self.manualEntryButton.setIcon(QIcon(os.path.dirname(__file__) + "/images/manualpoint.png"))
        self.manualEntryButton.clicked.connect(self.showManualEntryDialog)
        self.settingsButton.setIcon(QIcon(':/images/themes/default/mActionOptions.svg'))
        self.settingsButton.clicked.connect(self.showSettings)

        self.restoreGeometry(qset.value("ShapeTools/MeasureDialogGeometry", QByteArray(), type=QByteArray))
        self.closeButton.clicked.connect(self.closeDialog)
        self.newButton.clicked.connect(self.newDialog)
        self.saveToLayerButton.clicked.connect(self.saveToLayer)
        self.saveToLayerButton.setEnabled(False)

        self.unitsComboBox.addItems(DISTANCE_LABELS)
        saved_default_unit = int(qset.value('/ShapeTools/DefaultMeasureUnit', 0))
        self.unitsComboBox.setCurrentIndex(saved_default_unit)

        self.tableWidget.setColumnCount(3)
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setHorizontalHeaderLabels([tr('Heading To'), tr('Heading From'), tr('Distance')])

        self.unitsComboBox.activated.connect(self.unitsChanged)

        self.capturedPoints = []
        self.distances = []
        self.activeMeasuring = True
        self.lastMotionPt = None
        self.unitsChanged()
        self.currentDistance = 0.0

        self.pointRb = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.pointRb.setColor(settings.rubberBandColor)
        self.pointRb.setIconSize(10)
        self.lineRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.lineRb.setColor(settings.rubberBandColor)
        self.lineRb.setWidth(3)
        self.tempRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.tempRb.setColor(settings.rubberBandColor)
        self.tempRb.setWidth(3)

    def showManualEntryDialog(self):
        self.pointDigitizerDialog.show()

    def showSettings(self):
        self.shapetools.settings()

    def ready(self):
        return self.activeMeasuring

    def stop(self):
        self.activeMeasuring = False
        self.lastMotionPt = None

    def closeEvent(self, event):
        self.closeDialog()

    def closeDialog(self):
        self.clear()
        QSettings().setValue(
            "ShapeTools/MeasureDialogGeometry", self.saveGeometry())
        self.close()
        self.pointDigitizerDialog.closeDialog()

    def newDialog(self):
        self.clear()
        self.initGeodLabel()

    def initGeodLabel(self):
        label = tr('Ellipsoid: ') + settings.ellipseDescription
        self.geodLabel.setText(label)

    def keyPressed(self, key):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        if key == Qt.Key_Escape:
            self.endRubberband()
        if self.motionReady():
            if self.lastMotionPt is None:
                return
            (distance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index - 1], self.lastMotionPt)
        else:
            if index < 2:
                return
            (distance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index - 2], self.capturedPoints[index - 1])

        distance = self.unitDistance(distance)
        clipboard = QApplication.clipboard()
        if key == Qt.Key_1 or key == Qt.Key_F:
            s = '{:.{prec}f}'.format(startAngle, prec=settings.measureSignificantDigits)
            clipboard.setText(s)
            self.iface.messageBar().pushMessage("", "Heading to {} copied to the clipboard".format(s), level=Qgis.Info, duration=3)
        elif key == Qt.Key_2 or key == Qt.Key_T:
            s = '{:.{prec}f}'.format(endAngle, prec=settings.measureSignificantDigits)
            clipboard.setText(s)
            self.iface.messageBar().pushMessage("", "Heading from {} copied to the clipboard".format(s), level=Qgis.Info, duration=3)
        elif key == Qt.Key_3 or key == Qt.Key_D:
            s = '{:.{prec}f}'.format(distance, prec=settings.measureSignificantDigits)
            clipboard.setText(s)
            self.iface.messageBar().pushMessage("", "Distance {} copied to the clipboard".format(s), level=Qgis.Info, duration=3)
        elif key == Qt.Key_4 or key == Qt.Key_A:
            total = 0.0
            num = len(self.capturedPoints)
            for i in range(1, num):
                (d, startA, endA) = self.calcParameters(self.capturedPoints[i - 1], self.capturedPoints[i])
                total += d
            total = self.unitDistance(total)
            # Add in the motion distance
            if self.motionReady():
                total += distance
            s = '{:.{prec}f}'.format(total, prec=settings.measureSignificantDigits)
            clipboard.setText(s)
            self.iface.messageBar().pushMessage("", "Total distance {} copied to the clipboard".format(s), level=Qgis.Info, duration=3)
        else:
            return

    def unitsChanged(self):
        qset = QSettings()
        selected_unit = self.unitsComboBox.currentIndex()
        qset.setValue('/ShapeTools/DefaultMeasureUnit', selected_unit)
        label = "Distance [{}]".format(DISTANCE_LABELS[selected_unit])
        item = QTableWidgetItem(label)
        self.tableWidget.setHorizontalHeaderItem(2, item)
        ptcnt = len(self.capturedPoints)
        if ptcnt >= 2:
            i = 0
            while i < ptcnt - 1:
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
        if index > 0 and pt == self.capturedPoints[index - 1]:
            # the clicked point is the same as the previous so just ignore it
            return
        self.capturedPoints.append(pt)
        # Add rubber band points
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        ptCanvas = transform.transform(pt.x(), pt.y())
        self.pointRb.addPoint(ptCanvas, True)
        # If there is more than 1 captured point add it to the table
        if index > 0:
            self.saveToLayerButton.setEnabled(True)
            (distance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index - 1], self.capturedPoints[index])
            self.distances.append(distance)
            self.insertParams(index, distance, startAngle, endAngle)
            # Add Rubber Band Line
            linePts = self.getLinePts(distance, self.capturedPoints[index - 1], self.capturedPoints[index])
            self.lineRb.addGeometry(QgsGeometry.fromPolylineXY(linePts), None)
        self.formatTotal()

    def endRubberband(self):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        if index == 1:
            self.newDialog()
            return
        if self.motionReady():
            if self.lastMotionPt is not None:
                self.lastMotionPt = None
                self.tempRb.reset(QgsWkbTypes.LineGeometry)
                self.tableWidget.setRowCount(self.tableWidget.rowCount() - 1)
        self.stop()
        self.currentDistance = 0
        self.formatTotal()
        
    def inMotion(self, pt):
        index = len(self.capturedPoints)
        if index <= 0:
            return
        (self.currentDistance, startAngle, endAngle) = self.calcParameters(self.capturedPoints[index - 1], pt)
        self.insertParams(index, self.currentDistance, startAngle, endAngle)
        self.formatTotal()
        linePts = self.getLinePts(self.currentDistance, self.capturedPoints[index - 1], pt)
        self.lastMotionPt = pt
        self.tempRb.setToGeometry(QgsGeometry.fromPolylineXY(linePts), None)

    def calcParameters(self, pt1, pt2):
        gline = geod.Inverse(pt1.y(), pt1.x(), pt2.y(), pt2.x())
        az2 = (gline['azi2'] + 180) % 360.0
        if az2 > 180:
            az2 = az2 - 360.0
        az1 = gline['azi1']

        # Check to see if the azimuth values should be in the range or 0 to 360
        # The default is -180 to 180
        if settings.mtAzMode:
            if az1 < 0:
                az1 += 360.0
            if az2 < 0:
                az2 += 360
        return (gline['s12'], az1, az2)

    def getLinePts(self, distance, pt1, pt2):
        canvasCrs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(epsg4326, canvasCrs, QgsProject.instance())
        pt1c = transform.transform(pt1.x(), pt1.y())
        pt2c = transform.transform(pt2.x(), pt2.y())
        if distance < 10000:
            return [pt1c, pt2c]
        gline = geod.InverseLine(pt1.y(), pt1.x(), pt2.y(), pt2.x())
        n = int(math.ceil(distance / 10000.0))
        if n > 20:
            n = 20
        seglen = distance / n
        pts = [pt1c]
        for i in range(1, n):
            s = seglen * i
            g = gline.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
            ptc = transform.transform(g['lon2'], g['lat2'])
            pts.append(ptc)
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
        fields.append(QgsField("total_dist", QVariant.Double))

        layer = QgsVectorLayer("LineString?crs={}".format(canvasCrs.authid()), "Measurements", "memory")
        dp = layer.dataProvider()
        dp.addAttributes(fields)
        layer.updateFields()

        num = len(self.capturedPoints)
        total = 0.0
        for i in range(1, num):
            (distance, startA, endA) = self.calcParameters(self.capturedPoints[i - 1], self.capturedPoints[i])
            total += distance
        total = self.unitDistance(total)
        for i in range(1, num):
            (distance, startA, endA) = self.calcParameters(self.capturedPoints[i - 1], self.capturedPoints[i])
            pts = self.getLinePts(distance, self.capturedPoints[i - 1], self.capturedPoints[i])
            distance = self.unitDistance(distance)
            feat = QgsFeature(layer.fields())
            feat.setAttribute(0, "{:.{prec}f} {}".format(distance, units,prec=settings.saveToLayerSignificantDigits))
            feat.setAttribute(1, distance)
            feat.setAttribute(2, units)
            feat.setAttribute(3, startA)
            feat.setAttribute(4, endA)
            feat.setAttribute(5, total)
            feat.setGeometry(QgsGeometry.fromPolylineXY(pts))
            dp.addFeatures([feat])

        label = QgsPalLayerSettings()
        label.fieldName = 'label'
        try:
            label.placement = QgsPalLayerSettings.Line
        except Exception:
            label.placement = QgsPalLayerSettings.AboveLine
        format = label.format()
        format.setColor(settings.measureTextColor)
        format.setNamedStyle('Bold')
        label.setFormat(format)
        labeling = QgsVectorLayerSimpleLabeling(label)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        renderer = layer.renderer()
        renderer.symbol().setColor(settings.measureLineColor)
        renderer.symbol().setWidth(0.5)

        layer.updateExtents()
        QgsProject.instance().addMapLayer(layer)

    def insertParams(self, position, distance, startAngle, endAngle):
        if position > self.tableWidget.rowCount():
            self.tableWidget.insertRow(position - 1)
        item = QTableWidgetItem('{:.4f}'.format(self.unitDistance(distance)))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position - 1, 2, item)
        item = QTableWidgetItem('{:.4f}'.format(startAngle))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position - 1, 0, item)
        item = QTableWidgetItem('{:.4f}'.format(endAngle))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.tableWidget.setItem(position - 1, 1, item)

    def formatTotal(self):
        total = self.currentDistance
        ptcnt = len(self.capturedPoints)
        if ptcnt >= 2:
            i = 0
            while i < ptcnt - 1:
                total += self.distances[i]
                i += 1
        self.distanceLineEdit.setText('{:.2f}'.format(self.unitDistance(total)))

    def updateRBColor(self):
        self.pointRb.setColor(settings.rubberBandColor)
        self.lineRb.setColor(settings.rubberBandColor)
        self.tempRb.setColor(settings.rubberBandColor)

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
        self.updateRBColor()

    def unitDistance(self, distance):
        units = self.unitsComboBox.currentIndex()
        if units == 0:  # kilometers
            return distance / 1000.0
        elif units == 1:  # meters
            return distance
        elif units == 2:  # centimeters
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceCentimeters)
        elif units == 3:  # miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceMiles)
        elif units == 4:  # yards
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceYards)
        elif units == 5:  # feet
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet)
        elif units == 6:  # inches
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet) * 12
        elif units == 7:  # nautical miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceNauticalMiles)

    def unitDesignator(self):
        units = self.unitsComboBox.currentIndex()
        return unitsAbbr[units]


FORM_CLASS2, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/measureaddnode.ui'))


class AddMeasurePointWidget(QDialog, FORM_CLASS2):
    inputProjection = 0
    inputXYOrder = 1

    def __init__(self, md, iface, parent):
        super(AddMeasurePointWidget, self).__init__(parent)
        self.setupUi(self)
        self.measureDialog = md
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.xymenu = QMenu()
        icon = QIcon(os.path.dirname(__file__) + '/images/yx.svg')
        a = self.xymenu.addAction(icon, "Y, X (Lat, Lon) Order")
        a.setData(0)
        icon = QIcon(os.path.dirname(__file__) + '/images/xy.svg')
        a = self.xymenu.addAction(icon, "X, Y (Lon, Lat) Order")
        a.setData(1)
        self.xyButton.setIconSize(QSize(24, 24))
        self.xyButton.setIcon(icon)
        self.xyButton.setMenu(self.xymenu)
        self.xyButton.triggered.connect(self.xyTriggered)

        self.crsmenu = QMenu()
        icon = QIcon(os.path.dirname(__file__) + '/images/wgs84Projection.svg')
        a = self.crsmenu.addAction(icon, "WGS 84 (latitude & longitude)")
        a.setData(0)
        icon = QIcon(os.path.dirname(__file__) + '/images/projProjection.svg')
        a = self.crsmenu.addAction(icon, "Project CRS")
        a.setData(1)
        icon = QIcon(os.path.dirname(__file__) + '/images/customProjection.svg')
        a = self.crsmenu.addAction(icon, "Specify CRS")
        a.setData(2)
        self.crsButton.setIconSize(QSize(24, 24))
        self.crsButton.setIcon(icon)
        self.crsButton.setMenu(self.crsmenu)
        self.crsButton.triggered.connect(self.crsTriggered)

        self.addButton.clicked.connect(self.addPoint)
        self.exitButton.clicked.connect(self.closeDialog)

        self.readSettings()
        self.configButtons()
        
        self.restoreGeometry(QSettings().value("ShapeTools/AddMeasurePointGeometry", QByteArray(), type=QByteArray))

    def showEvent(self, e):
        self.labelUpdate()

    def closeDialog(self):
        QSettings().setValue(
            "ShapeTools/AddMeasurePointGeometry", self.saveGeometry())
        self.close()

    def addPoint(self):
        text = self.lineEdit.text().strip()
        if text == "":
            return
        try:
            if (self.inputProjection == 0) or (text[0] == '{'):
                # If this is GeoJson it does not matter what inputProjection is
                if text[0] == '{':  # This may be a GeoJSON point
                    codec = QTextCodec.codecForName("UTF-8")
                    fields = QgsJsonUtils.stringToFields(text, codec)
                    fet = QgsJsonUtils.stringToFeatureList(text, fields, codec)
                    if (len(fet) == 0) or not fet[0].isValid():
                        raise ValueError('Invalid Coordinates')

                    geom = fet[0].geometry()
                    if geom.isEmpty() or (geom.wkbType() != QgsWkbTypes.Point):
                        raise ValueError('Invalid GeoJSON Geometry')
                    pt = geom.asPoint()
                    lat = pt.y()
                    lon = pt.x()
                elif re.search(r'POINT\(', text) is not None:
                    m = re.findall(r'POINT\(\s*([+-]?\d*\.?\d*)\s+([+-]?\d*\.?\d*)', text)
                    if len(m) != 1:
                        raise ValueError('Invalid Coordinates')
                    lon = float(m[0][0])
                    lat = float(m[0][1])
                else:
                    lat, lon = parseDMSString(text, self.inputXYOrder)
                srcCrs = epsg4326
            else:  # Is either the project or custom CRS
                if re.search(r'POINT\(', text) is None:
                    coords = re.split(r'[\s,;:]+', text, 1)
                    if len(coords) < 2:
                        raise ValueError('Invalid Coordinates')
                    if self.inputXYOrder == 0:  # Y, X Order
                        lat = float(coords[0])
                        lon = float(coords[1])
                    else:
                        lon = float(coords[0])
                        lat = float(coords[1])
                else:
                    m = re.findall(r'POINT\(\s*([+-]?\d*\.?\d*)\s+([+-]?\d*\.?\d*)', text)
                    if len(m) != 1:
                        raise ValueError('Invalid Coordinates')
                    lon = float(m[0][0])
                    lat = float(m[0][1])
                if self.inputProjection == 1:  # Project CRS
                    srcCrs = self.canvas.mapSettings().destinationCrs()
                else:
                    srcCrs = QgsCoordinateReferenceSystem(self.inputCustomCRS)
        except Exception:
            # traceback.print_exc()
            self.iface.messageBar().pushMessage("", "Invalid Coordinate", level=Qgis.Warning, duration=2)
            return
        self.lineEdit.clear()
        if srcCrs != epsg4326:
            transform = QgsCoordinateTransform(srcCrs, epsg4326, QgsProject.instance())
            # Transform the input coordinate projection to the layer CRS
            lon, lat = transform.transform(float(lon), float(lat))
        pt = QgsPointXY(lon, lat)
        self.measureDialog.addPoint(pt, 1)

    def labelUpdate(self):
        if self.isWgs84():
            if self.inputXYOrder == 0:
                o = "Lat, Lon"
            else:
                o = "Lon, Lat"
            proj = "Wgs84"
        else:
            if self.inputXYOrder == 0:
                o = "Y, X"
            else:
                o = "X, Y"
            if self.inputProjection == 1:  # Project Projection
                proj = self.canvas.mapSettings().destinationCrs().authid()
            else:
                proj = self.inputCustomCRS
        s = "Input Projection: {} - Coordinate Order: {}".format(proj, o)
        self.infoLabel.setText(s)

    def configButtons(self):
        self.xyButton.setDefaultAction(self.xymenu.actions()[self.inputXYOrder])
        self.crsButton.setDefaultAction(self.crsmenu.actions()[self.inputProjection])

    def readSettings(self):
        settings = QSettings()
        self.inputProjection = int(settings.value('/ShapeTools/DigitizerProjection', 0))
        self.inputXYOrder = int(settings.value('/ShapeTools/DigitizerXYOrder', 0))
        self.inputCustomCRS = settings.value('/ShapeTools/DigitizerCustomCRS', 'EPSG:4326')
        if self.inputProjection < 0 or self.inputProjection > 2:
            self.inputProjection = 0
        if self.inputXYOrder < 0 or self.inputXYOrder > 1:
            self.inputXYOrder = 1
        self.labelUpdate()

    def saveSettings(self):
        settings = QSettings()
        settings.setValue('/ShapeTools/DigitizerProjection', self.inputProjection)
        settings.setValue('/ShapeTools/DigitizerXYOrder', self.inputXYOrder)
        settings.setValue('/ShapeTools/DigitizerCustomCRS', self.inputCustomCRS)
        self.labelUpdate()

    def crsTriggered(self, action):
        self.crsButton.setDefaultAction(action)
        self.inputProjection = action.data()
        if self.inputProjection == 2:
            selector = QgsProjectionSelectionDialog()
            selector.setCrs(QgsCoordinateReferenceSystem(self.inputCustomCRS))
            if selector.exec():
                self.inputCustomCRS = selector.crs().authid()
            else:
                self.inputCustomCRS = 'EPSG:4326'
        self.saveSettings()

    def xyTriggered(self, action):
        self.xyButton.setDefaultAction(action)
        self.inputXYOrder = action.data()
        self.saveSettings()

    def isWgs84(self):
        if self.inputProjection == 0:  # WGS 84
            return True
        elif self.inputProjection == 1:  # Projection Projection
            if self.canvas.mapSettings().destinationCrs() == epsg4326:
                return True
        return False
