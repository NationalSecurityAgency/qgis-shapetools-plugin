import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import QSettings


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/settings.ui'))

class Settings():

    def __init__(self):
        self.readSettings()

    def readSettings(self):
        '''Load the user selected settings. The settings are retained even when
        the user quits QGIS.'''
        _settings = QSettings()
        self.guessNames = int(_settings.value('/ShapeTools/GuessNames', 2))
        self.maxSegLength =  float(_settings.value('/ShapeTools/MaxSegLength', 20.0)) # In km
        self.maxSegments =  int(_settings.value('/ShapeTools/MaxSegments', 1000))

settings = Settings()

class SettingsWidget(QtGui.QDialog, FORM_CLASS):
    '''Settings Dialog box.'''
    def __init__(self, iface, parent):
        super(SettingsWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        settings.readSettings()

    def accept(self):
        '''Accept the settings and save them for next time.'''
        settings = QSettings()
        settings.setValue('/ShapeTools/GuessNames', self.guessCheckBox.checkState())
        settings.setValue('/ShapeTools/MaxSegments', self.maxSegmentsSpinBox.value())
        settings.setValue('/ShapeTools/MaxSegLength', self.segLengthSpinBox.value())
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
        
