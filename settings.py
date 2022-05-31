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


historical_ellipsoids = {
    '165': ['165', 6378165.000, 298.3],
    'ans': ['ANS', 6378160, 298.25],
    'clrk58': ['CLARKE 1858', 6378293.645, 294.26],
    'intl24': ['International 1924', 6378388, 297],
}

class Ellipsoids():
    acronymList = {}

    def __init__(self):
        # This returns the acronym, description, & parameters
        definitions = QgsEllipsoidUtils.definitions()

        # Create a dictionary of definitions keyed on the acronym
        for item in definitions:
            self.acronymList[item.acronym] = item

    def ellipsoidDescription(self, acronym):
        '''Return an acronym's description'''
        if acronym == 'WGS84':
            return('WGS 84')
        elif acronym in self.acronymList:
            return(self.acronymList[acronym].description)
        elif acronym in historical_ellipsoids:
            return(historical_ellipsoids[acronym][0])
        else:
            return(None)

    def valid(self, acronym):
        '''Check for a valid acronym'''
        if acronym == 'WGS84':
            return(True)
        elif acronym in self.acronymList:
            return(True)
        elif acronym in historical_ellipsoids:
            return(True)
        else:
            return(False)

    def isSystemEllipsoid(self, acronym):
        if acronym in self.acronymList:
            return(True)
        return(False)

    def isHistoricalEllipsoid(self, acronym):
        if acronym in historical_ellipsoids:
            return(True)
        return(False)

    def ellipsoid(self, acronym):
        '''Return the ellipsoid associated with the acronym'''
        if acronym == 'WGS84':
            return (Geodesic.WGS84)
        elif acronym in self.acronymList:
            param = self.acronymList[acronym].parameters
            return(Geodesic(param.semiMajor, 1.0 / param.inverseFlattening))
        elif acronym in historical_ellipsoids:
            return(Geodesic(historical_ellipsoids[acronym][1], 1.0 / historical_ellipsoids[acronym][2]))
        else:
            return(None)


ellipsoids = Ellipsoids()

class Settings():
    def __init__(self):
        self.readSettings()

    def readSettings(self):
        '''Load the user selected settings. The settings are retained even when
        the user quits QGIS.'''
        qset = QSettings()
        self.geomXName = qset.value('/ShapeTools/GeomXName', 'geom_x')
        self.geomYName = qset.value('/ShapeTools/GeomYName', 'geom_y')
        self.maxSegLength = float(qset.value('/ShapeTools/MaxSegLength', 20.0))  # In km
        self.maxSegments = int(qset.value('/ShapeTools/MaxSegments', 1000))
        self.mtAzMode = int(qset.value('/ShapeTools/MtAzMode', 0))
        self.measureSignificantDigits = int(qset.value('/ShapeTools/MeasureSignificantDigits', 2))
        self.saveToLayerSignificantDigits = int(qset.value('/ShapeTools/SaveToLayerSignificantDigits', 2))
        color = qset.value('/ShapeTools/RubberBandColor', '#dea743')
        self.rubberBandColor = QColor(color)
        value = int(qset.value('/ShapeTools/RubberBandOpacity', 192))
        self.rubberBandColor.setAlpha(value)
        color = qset.value('/ShapeTools/MeasureLineColor', '#000000')
        self.measureLineColor = QColor(color)
        color = qset.value('/ShapeTools/MeasureTextColor', '#000000')
        self.measureTextColor = QColor(color)
        acronym = qset.value('/ShapeTools/Ellipsoid', 'WGS84')
        self.setEllipsoid(acronym)

    def getUniqueAttributeName(self, newname, names=[]):
        index = 1
        names = set(names)
        name = newname
        while name in names:
            name = '{}{}'.format(newname, index)
            index += 1
        return (name)

    def getGeomNames(self, names=[]):
        index = 1
        name_x = self.geomXName
        names = set(names)
        while name_x in names:
            name_x = '{}{}'.format(self.geomXName, index)
            index += 1
        name_y = self.geomYName
        while name_y in names:
            name_y = '{}{}'.format(self.geomYName, index)
            index += 1
        return (name_x, name_y)

    def setEllipsoid(self, acronym):
        if not ellipsoids.valid(acronym):
            acronym = 'WGS84'
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
        for i, item in enumerate(ellipseDef):
            desc = item.description
            if item.description != item.acronym:
                desc += " (" + item.acronym + ")"
            self.systemEllipsoidComboBox.addItem(desc, item.acronym)
            if item.acronym == 'WGS84':
                self.wgs84index = i
        for key in historical_ellipsoids.keys():
            desc = historical_ellipsoids[key][0]
            self.historicalEllipsoidComboBox.addItem(desc, key)

        self.mtAzComboBox.addItems([tr('Azimuth Range -180 to 180'), tr('Azimuth Range 0 tp 360')])
        self.ellipsoidComboBox.addItems(['WGS84', tr('System Ellipsoids'), tr('Historical Ellipsoids')])
        self.ellipsoidComboBox.activated.connect(self.initEllipsoid)
        self.rubberBandColorButton.setAllowOpacity(True)
        settings.readSettings()
        if settings.ellipseAcronym == 'WGS84':
            self.ellipsoidComboBox.setCurrentIndex(0)
        elif ellipsoids.isSystemEllipsoid(settings.ellipseAcronym):
            self.ellipsoidComboBox.setCurrentIndex(1)
        else:
            self.ellipsoidComboBox.setCurrentIndex(2)
        self.initEllipsoid()

    def initEllipsoid(self):
        if self.ellipsoidComboBox.currentIndex() == 0:  # WGS84
            self.systemEllipsoidComboBox.setCurrentIndex(self.wgs84index)
            self.systemEllipsoidComboBox.setEnabled(False)
            self.historicalEllipsoidComboBox.setEnabled(False)
        elif self.ellipsoidComboBox.currentIndex() == 2:  # Historical Ellipsoids
            index = self.historicalEllipsoidComboBox.findData(settings.ellipseAcronym, flags=Qt.MatchExactly)
            if index == -1:
                index = 0
            self.historicalEllipsoidComboBox.setCurrentIndex(index)
            self.systemEllipsoidComboBox.setEnabled(False)
            self.historicalEllipsoidComboBox.setEnabled(True)
        else:  # System Ellipsoids
            index = self.systemEllipsoidComboBox.findData(settings.ellipseAcronym, flags=Qt.MatchExactly)
            if index == -1:
                settings.setEllipsoid('WGS84')
                index = self.wgs84index
            self.systemEllipsoidComboBox.setCurrentIndex(index)
            self.systemEllipsoidComboBox.setEnabled(True)
            self.historicalEllipsoidComboBox.setEnabled(False)

    def accept(self):
        '''Accept the settings and save them for next time.'''
        qset = QSettings()
        name = self.xColumnNameLineEdit.text()
        if name == '':
            name = 'geom_x'
        qset.setValue('/ShapeTools/GeomXName', name)
        name = self.yColumnNameLineEdit.text()
        if name == '':
            name = 'geom_y'
        qset.setValue('/ShapeTools/GeomYName', name)
        qset.setValue('/ShapeTools/MaxSegments', self.maxSegmentsSpinBox.value())
        qset.setValue('/ShapeTools/MaxSegLength', self.segLengthSpinBox.value())
        qset.setValue('/ShapeTools/MtAzMode', self.mtAzComboBox.currentIndex())
        # the ellipsoid combobox has the descriptions and not the acronym
        # we have put the acronymns in the data field
        if self.ellipsoidComboBox.currentIndex() == 0:
            name = 'WGS84'
        elif self.ellipsoidComboBox.currentIndex() == 2:  # Historical ellipsoids
            index = self.historicalEllipsoidComboBox.currentIndex()
            name = self.historicalEllipsoidComboBox.itemData(index)
        else:
            index = self.systemEllipsoidComboBox.currentIndex()
            name = self.systemEllipsoidComboBox.itemData(index)
        qset.setValue('/ShapeTools/Ellipsoid', name)
        settings.rubberBandColor = self.rubberBandColorButton.color()
        settings.measureLineColor = self.measureLineColorButton.color()
        settings.measureTextColor = self.measureTextColorButton.color()
        qset.setValue('/ShapeTools/RubberBandColor', settings.rubberBandColor.name())
        qset.setValue('/ShapeTools/RubberBandOpacity', settings.rubberBandColor.alpha())
        qset.setValue('/ShapeTools/MeasureLineColor', settings.measureLineColor.name())
        qset.setValue('/ShapeTools/MeasureTextColor', settings.measureTextColor.name())
        qset.setValue('/ShapeTools/MeasureSignificantDigits', self.significantDigitsSpinBox.value())
        qset.setValue('/ShapeTools/SaveToLayerSignificantDigits', self.saveToLayerSignificantDigitsSpinBox.value())
        settings.readSettings()
        self.close()

    def showEvent(self, e):
        '''The user has selected the settings dialog box so we need to
        read the settings and update the dialog box with the previously
        selected settings.'''
        settings.readSettings()
        self.xColumnNameLineEdit.setText(settings.geomXName)
        self.yColumnNameLineEdit.setText(settings.geomYName)
        self.maxSegmentsSpinBox.setValue(settings.maxSegments)
        self.segLengthSpinBox.setValue(settings.maxSegLength)
        self.significantDigitsSpinBox.setValue(settings.measureSignificantDigits)
        self.saveToLayerSignificantDigitsSpinBox.setValue(settings.saveToLayerSignificantDigits)
        self.mtAzComboBox.setCurrentIndex(settings.mtAzMode)
        self.rubberBandColorButton.setColor(settings.rubberBandColor)
        self.measureLineColorButton.setColor(settings.measureLineColor)
        self.measureTextColorButton.setColor(settings.measureTextColor)
        self.ellipsoidComboBox.blockSignals(True)
        self.ellipsoidComboBox.blockSignals(False)
        self.initEllipsoid()
