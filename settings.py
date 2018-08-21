import os
from geographiclib.geodesic import Geodesic

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QSettings, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QColor

from qgis.core import QgsCoordinateReferenceSystem, QgsEllipsoidUtils

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
geod = Geodesic.WGS84

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/settings.ui'))
    
def tr(string):
    return QCoreApplication.translate('Processing', string)

class Ellipsoids():
    acronymList = {}
    def __init__(self):
        definitions = QgsEllipsoidUtils.definitions()
        
        for item in definitions:
            self.acronymList[item.acronym] = item
    
    def ellipsoidDescription(self, acronym):
        if acronym in self.acronymList:
            return(self.acronymList[acronym].description)
        else:
            return(None)
            
    def ellipsoidParameters(self, acronym):
        if acronym in self.acronymList:
            return(self.acronymList[acronym].parameters)
        else:
            return(None)
    
    def valid(self, acronym):
        if acronym in self.acronymList:
            return( True )
        else:
            return( False )
            
    def ellipsoid(self, acronym):
        if acronym == 'WGS84':
            return (Geodesic.WGS84)
        elif acronym in self.acronymList:
            param = self.acronymList[acronym].parameters
            return(Geodesic(param.semiMajor, 1.0 / param.inverseFlattening))
        else:
            return(None)
            
ellipsoids = Ellipsoids()
            
    
class Settings():

    def __init__(self):
        self.readSettings()
        self.rubberBandColor = QColor(222, 167, 67, 150)

    def readSettings(self):
        '''Load the user selected settings. The settings are retained even when
        the user quits QGIS.'''
        qset = QSettings()
        self.guessNames = int(qset.value('/ShapeTools/GuessNames', 2))
        self.maxSegLength =  float(qset.value('/ShapeTools/MaxSegLength', 20.0)) # In km
        self.maxSegments =  int(qset.value('/ShapeTools/MaxSegments', 1000))
        self.mtAzMode = int(qset.value('/ShapeTools/MtAzMode', 0))
        acronym = qset.value('ShapeTools/Ellipsoid', 'WGS84')
        self.ellipsoidMode = int(qset.value('ShapeTools/EllipsoidMode', 0))
        self.setEllipsoid(acronym)
        
    def setEllipsoid(self, acronym):
        if not ellipsoids.valid(acronym):
            acronym = 'WGS84'
        geod = ellipsoids.ellipsoid(acronym)
        p = ellipsoids.ellipsoidParameters(acronym)
        self.ellipseAcronym = acronym
        self.ellipseDescription = ellipsoids.ellipsoidDescription(acronym)
            
            
settings = Settings()

class SettingsWidget(QDialog, FORM_CLASS):
    '''Settings Dialog box.'''
    def __init__(self, iface, parent):
        super(SettingsWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        ellipseDef = QgsEllipsoidUtils.definitions()
        self.wgs84index = 0
        for i,item in enumerate(ellipseDef):
            desc = item.description
            if item.description != item.acronym:
                desc += " ("+item.acronym+")"
            self.systemEllipsoidComboBox.addItem(desc, item.acronym)
            if item.acronym == 'WGS84':
                self.wgs84index = i
        self.mtAzComboBox.addItems([tr('Azimuth Range -180 to 180'), tr('Azimuth Range 0 tp 360')])
        self.ellipsoidComboBox.addItems(['WGS84', tr('System Ellipsoids')])
        self.ellipsoidComboBox.activated.connect(self.initEllipsoid)
        self.rubberBandColor.setAllowOpacity(True)
        self.rubberBandColor.setColor(settings.rubberBandColor)
        settings.readSettings()
        self.initEllipsoid()
        
    def initEllipsoid(self):
        if self.ellipsoidComboBox.currentIndex() == 0:
            self.systemEllipsoidComboBox.setCurrentIndex(self.wgs84index)
            self.systemEllipsoidComboBox.setEnabled(False)
        else:
            index = self.systemEllipsoidComboBox.findData(settings.ellipseAcronym, flags=Qt.MatchExactly)
            if index == -1:
                settings.setEllipsoid('WGS84')
                index = self.wgs84index
            self.systemEllipsoidComboBox.setCurrentIndex(index)
            self.systemEllipsoidComboBox.setEnabled(True)
        
    def accept(self):
        '''Accept the settings and save them for next time.'''
        qset = QSettings()
        qset.setValue('/ShapeTools/GuessNames', self.guessCheckBox.checkState())
        qset.setValue('/ShapeTools/MaxSegments', self.maxSegmentsSpinBox.value())
        qset.setValue('/ShapeTools/MaxSegLength', self.segLengthSpinBox.value())
        qset.setValue('/ShapeTools/MtAzMode', self.mtAzComboBox.currentIndex())
        qset.setValue('/ShapeTools/EllipsoidMode', self.ellipsoidComboBox.currentIndex())
        # the ellipsoid combobox has the descriptions and not the acronym
        # we have put the acronymns in the data field
        if self.ellipsoidComboBox.currentIndex() == 0:
            name = 'WGS84'
        else:
            index = self.systemEllipsoidComboBox.currentIndex()
            name = self.systemEllipsoidComboBox.itemData(index)
        qset.setValue('/ShapeTools/Ellipsoid', name)
        settings.readSettings()
        settings.rubberBandColor = self.rubberBandColor.color()
        self.close()
        
    def showEvent(self, e):
        '''The user has selected the settings dialog box so we need to
        read the settings and update the dialog box with the previously
        selected settings.'''
        settings.readSettings()
        self.guessCheckBox.setCheckState(settings.guessNames)
        self.maxSegmentsSpinBox.setValue(settings.maxSegments)
        self.segLengthSpinBox.setValue(settings.maxSegLength)
        self.mtAzComboBox.setCurrentIndex(settings.mtAzMode)
        self.ellipsoidComboBox.blockSignals(True)
        self.ellipsoidComboBox.setCurrentIndex(settings.ellipsoidMode)
        self.ellipsoidComboBox.blockSignals(False)
        self.initEllipsoid()
            
        
