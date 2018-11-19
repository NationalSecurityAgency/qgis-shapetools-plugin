from qgis.PyQt.QtCore import QUrl, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolButton
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsWkbTypes, QgsProcessingAlgorithm, QgsApplication
import processing

from .vector2Shape import Vector2ShapeWidget
from .settings import SettingsWidget
from .geodesicMeasureTool import GeodesicMeasureTool
from .azDigitizer import AzDigitizerTool
from .lineDigitizer import LineDigitizerTool

import os.path
import webbrowser
from .provider import ShapeToolsProvider
from .geodesicFlip import flipLayer

def tr(string):
    return QCoreApplication.translate('Processing', string)

class ShapeTools(object):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settingsDialog = None
        self.shapeDialog = None
        self.xyLineDialog = None
        self.geodesicDensifyDialog = None
        self.azDigitizerTool = None
        self.lineDigitizerTool = None
        self.previousLayer = None
        self.toolbar = self.iface.addToolBar('Shape Tools Toolbar')
        self.toolbar.setObjectName('ShapeToolsToolbar')
        self.provider = ShapeToolsProvider()

    def initGui(self):
        self.azDigitizerTool = AzDigitizerTool(self.iface)
        self.lineDigitizerTool = LineDigitizerTool(self.iface)
        
        # Initialize the create shape menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.shapeAction = QAction(icon, tr('Create shapes'), self.iface.mainWindow())
        self.shapeAction.setObjectName('stCreateShapes')
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.shapeAction)
        self.toolbar.addAction(self.shapeAction)
        
        # Initialize the XY to Line menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, tr('XY to Line'), self.iface.mainWindow())
        self.xyLineAction.setObjectName('stXYtoLine')        
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)
        
        # Initialize the Geodesic Densifier menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')
        self.geodesicDensifyAction = QAction(icon, tr('Geodesic shape densifier'), self.iface.mainWindow())
        self.geodesicDensifyAction.setObjectName('stGeodesicDensifier')        
        self.geodesicDensifyAction.triggered.connect(self.geodesicDensifyTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.toolbar.addAction(self.geodesicDensifyAction)
        
        # Initialize the Geodesic line break menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/idlbreak.png')
        self.geodesicLineBreakAction = QAction(icon, tr('Geodesic line break at -180,180'), self.iface.mainWindow())
        self.geodesicLineBreakAction.setObjectName('stGeodesicLineBreak')        
        self.geodesicLineBreakAction.triggered.connect(self.geodesicLineBreakTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicLineBreakAction)
        self.toolbar.addAction(self.geodesicLineBreakAction)
        
        # Initialize Geodesic Measure Tool
        self.geodesicMeasureTool = GeodesicMeasureTool(self.iface, self.iface.mainWindow())
        icon = QIcon(os.path.dirname(__file__) + '/images/measure.png')
        self.measureAction = QAction(icon, tr('Geodesic measure tool'), self.iface.mainWindow())
        self.measureAction.setObjectName('stGeodesicMeasureTool')        
        self.measureAction.triggered.connect(self.measureTool)
        self.measureAction.setCheckable(True)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureAction)
        self.toolbar.addAction(self.measureAction)
        
        # Initialize Geodesic Measurement layer
        icon = QIcon(os.path.dirname(__file__) + '/images/measureLine.png')
        self.measureLayerAction = QAction(icon, tr('Geodesic measurement layer'), self.iface.mainWindow())
        self.measureLayerAction.setObjectName('stGeodesicLineBreak')        
        self.measureLayerAction.triggered.connect(self.measureLayerTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureLayerAction)
        self.toolbar.addAction(self.measureLayerAction)
        
        menu = QMenu()
        # Initialize Geodesic transformation tool
        icon = QIcon(os.path.dirname(__file__) + '/images/transformShape.png')
        self.transformationsAction = menu.addAction(icon, tr('Geodesic transformations'), self.transformTool)
        self.transformationsAction.setObjectName('stGeodesicTransformations')
        
        icon = QIcon(os.path.dirname(__file__) + '/images/flip.png')
        self.flipRotateAction = menu.addAction(icon, tr('Geodesic flip and rotate'), self.flipRotateTool)
        self.flipRotateAction.setObjectName('stGeodesicFlipRotate')
        
        icon = QIcon(os.path.dirname(__file__) + '/images/flipHorizontal.png')
        self.flipHorizontalAction = menu.addAction(icon, tr('Flip horizontal'), self.flipHorizontalTool)
        self.flipHorizontalAction.setObjectName('stGeodesicFlipHorizontal')
        self.flipHorizontalAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/flipVertical.png')
        self.flipVerticalAction = menu.addAction(icon, tr('Flip vertical'), self.flipVerticalTool)
        self.flipVerticalAction.setObjectName('stGeodesicFlipVertical')
        self.flipVerticalAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotate180.png')
        self.rotate180Action = menu.addAction(icon, tr('Rotate 180\xb0'), self.rotate180Tool)
        self.rotate180Action.setObjectName('stGeodesicRotate180')
        self.rotate180Action.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotatecw.png')
        self.rotate90CWAction = menu.addAction(icon, tr('Rotate 90\xb0 CW'), self.rotate90CWTool)
        self.rotate90CWAction.setObjectName('stGeodesicRotate90CW')
        self.rotate90CWAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotateccw.png')
        self.rotate90CCWAction = menu.addAction(icon, tr('Rotate 90\xb0 CCW'), self.rotate90CCWTool)
        self.rotate90CCWAction.setObjectName('stGeodesicRotate90CCW')
        self.rotate90CCWAction.setEnabled(False)
        self.transformsAction = QAction(icon, tr('Geodesic Transforms'), self.iface.mainWindow())
        self.transformsAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.transformsAction)
        
        self.transformationButton = QToolButton()
        self.transformationButton.setMenu(menu)
        self.transformationButton.setDefaultAction(self.transformationsAction)
        self.transformationButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.transformationButton.triggered.connect(self.toolButtonTriggered)
        self.tranformToolbar = self.toolbar.addWidget(self.transformationButton)
        
        # Initialize the Azimuth Distance Digitize function
        icon = QIcon(os.path.dirname(__file__) + '/images/dazdigitize.png')
        self.digitizeAction = QAction(icon, tr('Azimuth distance digitizer'), self.iface.mainWindow())
        self.digitizeAction.setObjectName('stAzDistanceDigitizer')        
        self.digitizeAction.triggered.connect(self.setShowAzDigitizerTool)
        self.digitizeAction.setCheckable(True)
        self.digitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.digitizeAction)
        self.toolbar.addAction(self.digitizeAction)
        
        # Initialize the multi point azimuth Digitize function
        icon = QIcon(os.path.dirname(__file__) + '/images/linedigitize.png')
        self.lineDigitizeAction = QAction(icon, tr('Azimuth distance sequence digitizer'), self.iface.mainWindow())
        self.lineDigitizeAction.setObjectName('stLineDigitizer')        
        self.lineDigitizeAction.triggered.connect(self.setShowLineDigitizeTool)
        self.lineDigitizeAction.setCheckable(True)
        self.lineDigitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.lineDigitizeAction)
        self.toolbar.addAction(self.lineDigitizeAction)
        
        # Settings
        icon = QIcon(os.path.dirname(__file__) + '/images/settings.png')
        self.settingsAction = QAction(icon, tr('Settings'), self.iface.mainWindow())
        self.settingsAction.setObjectName('shapeToolsSettings')        
        self.settingsAction.triggered.connect(self.settings)
        self.iface.addPluginToVectorMenu('Shape Tools', self.settingsAction)
        
        # Help
        icon = QIcon(os.path.dirname(__file__) + '/images/help.png')
        self.helpAction = QAction(icon, tr('Shape Tools help'), self.iface.mainWindow())
        self.helpAction.setObjectName('shapeToolsHelp')        
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu('Shape Tools', self.helpAction)
        
        self.iface.currentLayerChanged.connect(self.currentLayerChanged)
        self.canvas.mapToolSet.connect(self.unsetTool)
        self.enableTools()
        
        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)
        
    def unsetTool(self, tool):
        try:
            if not isinstance(tool, GeodesicMeasureTool):
                self.measureAction.setChecked(False)
                self.geodesicMeasureTool.closeDialog()
            if not isinstance(tool, AzDigitizerTool):
                self.digitizeAction.setChecked(False)
            if not isinstance(tool, LineDigitizerTool):
                self.lineDigitizeAction.setChecked(False)
        except:
            pass

    def unload(self):
        self.canvas.unsetMapTool(self.azDigitizerTool)
        self.canvas.unsetMapTool(self.lineDigitizerTool)
        
        # remove from menu
        self.iface.removePluginVectorMenu('Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicLineBreakAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.measureAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.measureLayerAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.transformsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.digitizeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.lineDigitizeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.helpAction)
        # Remove from toolbar
        self.iface.removeToolBarIcon(self.shapeAction)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.geodesicDensifyAction)
        self.iface.removeToolBarIcon(self.geodesicLineBreakAction)
        self.iface.removeToolBarIcon(self.measureAction)
        self.iface.removeToolBarIcon(self.measureLayerAction)
        self.iface.removeToolBarIcon(self.transformationsAction)
        self.iface.removeToolBarIcon(self.digitizeAction)
        self.iface.removeToolBarIcon(self.lineDigitizeAction)
        self.iface.removeToolBarIcon(self.tranformToolbar)
        self.azDigitizerTool = None
        self.lineDigitizerTool = None
        # remove the toolbar
        del self.toolbar

        QgsApplication.processingRegistry().removeProvider(self.provider)
    
    def toolButtonTriggered(self, action):
        self.transformationButton.setDefaultAction(action)
    
    def shapeTool(self):
        if self.shapeDialog is None:
            self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow())
        self.shapeDialog.show()
        
    def setShowAzDigitizerTool(self):
        self.digitizeAction.setChecked(True)
        self.canvas.setMapTool(self.azDigitizerTool)
        
    def setShowLineDigitizeTool(self):
        self.lineDigitizeAction.setChecked(True)
        self.canvas.setMapTool(self.lineDigitizerTool)
        
    def xyLineTool(self):
        results = processing.execAlgorithmDialog('shapetools:xy2line', {})
        
    def geodesicDensifyTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesicdensifier', {})
        
    def geodesicLineBreakTool(self):
        results = processing.execAlgorithmDialog('shapetools:linebreak', {})
        
    def measureTool(self):
        self.measureAction.setChecked(True)
        self.canvas.setMapTool(self.geodesicMeasureTool)
        
    def measureLayerTool(self):
        results = processing.execAlgorithmDialog('shapetools:measurelayer', {})
        
    def transformTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesictransformations', {})
        
    def flipRotateTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesicflip', {})
        
    def flipHorizontalTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 0)
        
    def flipVerticalTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 1)
        
    def rotate180Tool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 2)
        
    def rotate90CWTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 3)
        
    def rotate90CCWTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 4)
        
    def settings(self):
        if self.settingsDialog is None:
            self.settingsDialog = SettingsWidget(self.iface, self.iface.mainWindow())
        self.settingsDialog.show()
    
    def help(self):
        '''Display a help page'''
        url = QUrl.fromLocalFile(os.path.dirname(__file__) + '/index.html').toString()
        webbrowser.open(url, new=2)
        
    def currentLayerChanged(self):
        layer = self.iface.activeLayer()
        if self.previousLayer != None:
            try:
                self.previousLayer.editingStarted.disconnect(self.layerEditingChanged)
            except:
                pass
            try:
                self.previousLayer.editingStopped.disconnect(self.layerEditingChanged)
            except:
                pass
        self.previousLayer = None
        if layer != None:
            if isinstance(layer, QgsVectorLayer):
                layer.editingStarted.connect(self.layerEditingChanged)
                layer.editingStopped.connect(self.layerEditingChanged)
                self.previousLayer = layer
        self.enableTools()

    def layerEditingChanged(self):
        self.enableTools()

    def enableTools(self):
        self.digitizeAction.setEnabled(False)
        self.lineDigitizeAction.setEnabled(False)
        self.flipHorizontalAction.setEnabled(False)
        self.flipVerticalAction.setEnabled(False)
        self.rotate180Action.setEnabled(False)
        self.rotate90CWAction.setEnabled(False)
        self.rotate90CCWAction.setEnabled(False)
        layer = self.iface.activeLayer()
        
        if not layer or not layer.isValid() or (layer.type() != QgsMapLayer.VectorLayer) or not layer.isEditable():
            return
        wkbtype = layer.wkbType()
        geomtype = QgsWkbTypes.geometryType(wkbtype)
        self.lineDigitizeAction.setEnabled(True)
        if geomtype == QgsWkbTypes.PointGeometry or geomtype == QgsWkbTypes.LineGeometry:
            self.digitizeAction.setEnabled(True)
        if geomtype == QgsWkbTypes.LineGeometry or geomtype == QgsWkbTypes.PolygonGeometry :
            self.flipHorizontalAction.setEnabled(True)
            self.flipVerticalAction.setEnabled(True)
            self.rotate180Action.setEnabled(True)
            self.rotate90CWAction.setEnabled(True)
            self.rotate90CCWAction.setEnabled(True)

