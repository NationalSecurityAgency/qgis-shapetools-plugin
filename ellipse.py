import os
import re
import math

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import *
from LatLon import LatLon



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ellipseDialog.ui'))


class EllipseWidget(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(EllipseWidget, self).__init__(parent)
        self.setupUi(self)
        self.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.iface = iface
        self.evaluateDataButton.clicked.connect(self.evaluateHeader)
        self.clearButton.clicked.connect(self.clear)
        self.unitOfMeasureComboBox.addItems(["Nautical Miles","Kilometers","Meters","Miles","Feet"])
        self.pointLayer = None
        self.polygonLayer = None
    
    def clear(self):
        self.latComboBox.clear()
        self.lonComboBox.clear()
        self.semiMajorComboBox.clear()
        self.semiMinorComboBox.clear()
        self.orientationComboBox.clear()
        self.inputTextEdit.clear()
          
    def evaluateHeader(self):
        inputtext = unicode(self.inputTextEdit.toPlainText())
        lines = inputtext.splitlines()
        if len(lines) < 2:
            self.showErrorMessage("There needs to be at least a header and 1 line of data")
            return
        header = lines.pop(0).strip()
        self.delimiter = self.getDelim(header)
        colnames = re.split(' *'+self.delimiter+' *', header)
        if len(colnames) < 2:
            self.showErrorMessage("Insufficient Columns")
            return
        colnames.insert(0,'')
        self.latComboBox.clear()
        self.latComboBox.addItems(colnames)
        self.lonComboBox.clear()
        self.lonComboBox.addItems(colnames)
        self.semiMajorComboBox.clear()
        self.semiMajorComboBox.addItems(colnames)
        self.semiMinorComboBox.clear()
        self.semiMinorComboBox.addItems(colnames)
        self.orientationComboBox.clear()
        self.orientationComboBox.addItems(colnames)
        colnames.pop(0)
        latcol = loncol = semimajorcol = semiminorcol = orientcol = -1
        for x, item in enumerate(colnames):
            lcitem = item.lower()
            if lcitem.startswith('lat'):
                latcol = x
            elif lcitem.startswith('lon'):
                loncol = x
            elif lcitem.startswith('orient'):
                orientcol = x
            elif bool(re.match('semi.*maj', lcitem)):
                semimajorcol = x
            elif bool(re.match('semi.*min', lcitem)):
                semiminorcol = x
        if latcol != -1:
            self.latComboBox.setCurrentIndex(latcol+1)
        if loncol != -1:
            self.lonComboBox.setCurrentIndex(loncol+1)
        if semimajorcol != -1:
            self.semiMajorComboBox.setCurrentIndex(semimajorcol+1)
        if semiminorcol != -1:
            self.semiMinorComboBox.setCurrentIndex(semiminorcol+1)
        if orientcol != -1:
            self.orientationComboBox.setCurrentIndex(orientcol+1)
        self.colnames = colnames
        
    def showErrorMessage(self, message):
        self.iface.messageBar().pushMessage("", message, level=QgsMessageBar.WARNING, duration=2)
        
    def processData(self):
        # Find what columns have been selected. We at least need lat and lon
        # There is a blank line at the first position so we need to subtract -1
        latcol = self.latComboBox.currentIndex() - 1
        loncol = self.lonComboBox.currentIndex() - 1
        semimajorcol = self.semiMajorComboBox.currentIndex() - 1
        semiminorcol = self.semiMinorComboBox.currentIndex() - 1
        orientcol = self.orientationComboBox.currentIndex() - 1
        
        # The ellipse calculation is done in Nautical Miles. This converts
        # the semi-major and minor axis to nautical miles
        unitOfMeasure = self.unitOfMeasureComboBox.currentIndex()
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
        
        
        if latcol == -1 or loncol == -1:
            # Nothing to do because we don't have a lat and lon
            self.showErrorMessage("Latitude and Longitude columns need to be specified")
            return
        
        if semimajorcol == -1 or semiminorcol == -1 or orientcol == -1:
            hasEllipse = False
        else:
            hasEllipse = True
        
        # Read the Data
        inputtext = unicode(self.inputTextEdit.toPlainText())
        lines = inputtext.splitlines()
        if len(lines) < 2:
            self.showErrorMessage("There needs to be at least a header and 1 line of data")
            return
        lines.pop(0) # Get rid of the header line

        # Get the Column Information
        basename = str(self.baseName.text())
        attr = []
        for name in self.colnames:
            attr.append(QgsField(name, QVariant.String))
        
        self.pointLayer = QgsVectorLayer("point?crs=epsg:4326", basename + "_Points", "memory")
        ppoint = self.pointLayer.dataProvider()
        ppoint.addAttributes(attr)
        self.pointLayer.updateFields()
        
        if hasEllipse:
            self.polygonLayer = QgsVectorLayer("polygon?crs=epsg:4326", basename + "_Polygon", "memory")
            ppolygon = self.polygonLayer.dataProvider()
            ppolygon.addAttributes(attr)
            self.polygonLayer.updateFields()
        
        for line in lines:
            line = line.strip()
            fields = re.split(' *'+self.delimiter+' *', line)
            try:
                lat = LatLon.parseDMSStringSingle(fields[latcol])
                lon = LatLon.parseDMSStringSingle(fields[loncol])
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(lon,lat)))
                attr = []
                for index in range(len(self.colnames)):
                    attr.append(fields[index])
                feature.setAttributes(attr)
                ppoint.addFeatures([feature])
                if hasEllipse:
                    feature  = QgsFeature()
                    features = LatLon.getEllipseCoords(lat, lon, float(fields[semimajorcol])*measureFactor,
                        float(fields[semiminorcol])*measureFactor, float(fields[orientcol]))
                    feature.setGeometry(QgsGeometry.fromPolygon([features]))
                    feature.setAttributes(attr)
                    ppolygon.addFeatures([feature])
            except:
                # Just skip any lines that are badly formed
                pass
        
        if hasEllipse:
            self.polygonLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(self.polygonLayer)
            
        self.pointLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(self.pointLayer)

       
    def getDelim(self, line):
        if line.count('\t') > line.count(','):
            delim = '\t'
        else:
            delim = ','
        return delim
        
    def apply(self):
        self.processData()
        
    def accept(self):
        self.processData()
        self.close()
