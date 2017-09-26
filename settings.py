import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import QSettings


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/settings.ui'))


class SettingsWidget(QtGui.QDialog, FORM_CLASS):
    '''Settings Dialog box.'''
    def __init__(self, iface, parent):
        super(SettingsWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.readSettings()

    def readSettings(self):
        '''Load the user selected settings. The settings are retained even when
        the user quits QGIS.'''
        settings = QSettings()
        self.guessNames = int(settings.value('/ShapeTools/GuessNames', 2))
        self.maxSegLength =  float(settings.value('/ShapeTools/MaxSegLength', 20.0)) # In km
        self.maxSegments =  int(settings.value('/ShapeTools/MaxSegments', 1000))
        
    def accept(self):
        '''Accept the settings and save them for next time.'''
        settings = QSettings()
        settings.setValue('/ShapeTools/GuessNames', self.guessCheckBox.checkState())
        settings.setValue('/ShapeTools/MaxSegments', self.maxSegmentsSpinBox.value())
        settings.setValue('/ShapeTools/MaxSegLength', self.segLengthSpinBox.value())
        self.readSettings()
        self.close()
        
    def showEvent(self, e):
        '''The user has selected the settings dialog box so we need to
        read the settings and update the dialog box with the previously
        selected settings.'''
        self.readSettings()
        self.guessCheckBox.setCheckState(self.guessNames)
        self.maxSegmentsSpinBox.setValue(self.maxSegments)
        self.segLengthSpinBox.setValue(self.maxSegLength)
        
