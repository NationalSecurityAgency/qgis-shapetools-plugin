import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QDialog

from qgis.core import QgsCoordinateReferenceSystem

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/settings.ui'))

class Settings():

    def __init__(self):
        self.readSettings()

    def readSettings(self):
        '''Load the user selected settings. The settings are retained even when
        the user quits QGIS.'''
        qset = QSettings()
        self.guessNames = int(qset.value('/ShapeTools/GuessNames', 2))
        self.maxSegLength =  float(qset.value('/ShapeTools/MaxSegLength', 20.0)) # In km
        self.maxSegments =  int(qset.value('/ShapeTools/MaxSegments', 1000))
        self.mtAzMode = int(qset.value('/ShapeTools/MtAzMode', 0))

settings = Settings()

class SettingsWidget(QDialog, FORM_CLASS):
    '''Settings Dialog box.'''
    def __init__(self, iface, parent):
        super(SettingsWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.mtAzComboBox.addItems(['Azimuth Range -180 to 180', 'Azimuth Range 0 tp 360'])
        settings.readSettings()
        
    def accept(self):
        '''Accept the settings and save them for next time.'''
        qset = QSettings()
        qset.setValue('/ShapeTools/GuessNames', self.guessCheckBox.checkState())
        qset.setValue('/ShapeTools/MaxSegments', self.maxSegmentsSpinBox.value())
        qset.setValue('/ShapeTools/MaxSegLength', self.segLengthSpinBox.value())
        qset.setValue('/ShapeTools/MtAzMode', self.mtAzComboBox.currentIndex())
        settings.readSettings()
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
        
