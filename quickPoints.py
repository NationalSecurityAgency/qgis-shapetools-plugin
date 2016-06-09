import os
import re
import math

from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import *
from LatLon import LatLon



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'pointsDialog.ui'))


class QuickPointsWidget(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(QuickPointsWidget, self).__init__(parent)
        self.setupUi(self)
        self.buttonBox.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.iface = iface
        self.evaluateDataButton.clicked.connect(self.evaluateHeader)
        self.clearButton.clicked.connect(self.clear)
        self.pointLayer = None
    
    def clear(self):
        self.latComboBox.clear()
        self.lonComboBox.clear()
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
        colnames.pop(0)
        latcol = loncol = -1
        for x, item in enumerate(colnames):
            lcitem = item.lower()
            if lcitem.startswith('lat'):
                latcol = x
            elif lcitem.startswith('lon'):
                loncol = x
        if latcol != -1:
            self.latComboBox.setCurrentIndex(latcol+1)
        if loncol != -1:
            self.lonComboBox.setCurrentIndex(loncol+1)
        self.colnames = colnames
        
    def showErrorMessage(self, message):
        self.iface.messageBar().pushMessage("", message, level=QgsMessageBar.WARNING, duration=2)
        
    def processData(self):
        # Find what columns have been selected. We at least need lat and lon
        # There is a blank line at the first position so we need to subtract -1
        latcol = self.latComboBox.currentIndex() - 1
        loncol = self.lonComboBox.currentIndex() - 1
        
        if latcol == -1 or loncol == -1:
            # Nothing to do because we don't have a lat and lon
            self.showErrorMessage("Latitude and Longitude columns need to be specified")
            return
        
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
        
        self.pointLayer = QgsVectorLayer("point?crs=epsg:4326", basename, "memory")
        ppoint = self.pointLayer.dataProvider()
        ppoint.addAttributes(attr)
        self.pointLayer.updateFields()
        
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
            except:
                # Just skip any lines that are badly formed
                pass
                    
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
