from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QIcon, QAction
from qgis.core import QGis, QgsVectorLayer

from .LatLon import LatLon
from .vector2Shape import Vector2ShapeWidget
from .xyToLine import XYToLineWidget
from .settings import SettingsWidget
from .geodesicDensify import GeodesicDensifyWidget
from .geodesicMeasureTool import GeodesicMeasureTool
from .azDigitizer import AzDigitizerTool

import os.path
import webbrowser

try:
    from processing.core.Processing import Processing
    from .provider import ShapeToolsProvider
    processingOk = True
except:
    processingOk = False

class ShapeTools:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settingsDialog = None
        self.shapeDialog = None
        self.xyLineDialog = None
        self.geodesicDensifyDialog = None
        self.azDigitizerTool = None
        self.previousLayer = None
        self.toolbar = self.iface.addToolBar(u'Shape Tools Toolbar')
        self.toolbar.setObjectName(u'ShapeToolsToolbar')
        if processingOk:
            self.provider = ShapeToolsProvider()

    def initGui(self):
        self.azDigitizerTool = AzDigitizerTool(self.iface)
        
        # Initialize the create shape menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.shapeAction = QAction(icon, u'Create Shapes', self.iface.mainWindow())
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.shapeAction)
        self.toolbar.addAction(self.shapeAction)
        
        # Initialize the XY to Line menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, u'XY to Line', self.iface.mainWindow())
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)
        
        # Initialize the Geodesic Densifier menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')
        self.geodesicDensifyAction = QAction(icon, u'Geodesic Shape Densifier', self.iface.mainWindow())
        self.geodesicDensifyAction.triggered.connect(self.geodesicDensifyTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.geodesicDensifyAction)
        self.toolbar.addAction(self.geodesicDensifyAction)
        
        # Initialize Geodesic Measure Tool
        self.geodesicMeasureTool = GeodesicMeasureTool(self.iface, self.iface.mainWindow())
        icon = QIcon(os.path.dirname(__file__) + '/images/measure.png')
        self.measureAction = QAction(icon, u'Geodesic Measure Tool', self.iface.mainWindow())
        self.measureAction.triggered.connect(self.measureTool)
        self.measureAction.setCheckable(True)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.measureAction)
        self.toolbar.addAction(self.measureAction)
        
        # Initialize the Azimuth Distance Digitize function
        icon = QIcon(os.path.dirname(__file__) + '/images/dazdigitize.png')
        self.digitizeAction = QAction(icon, "Azimuth Distance Digitizer", self.iface.mainWindow())
        self.digitizeAction.triggered.connect(self.setShowAzDigitizerTool)
        self.digitizeAction.setCheckable(True)
        self.digitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.digitizeAction)
        self.toolbar.addAction(self.digitizeAction)
        
        # Settings
        icon = QIcon(os.path.dirname(__file__) + '/images/settings.png')
        self.settingsAction = QAction(icon, u'Settings', self.iface.mainWindow())
        self.settingsAction.triggered.connect(self.settings)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.settingsAction)
        
        # Help
        icon = QIcon(os.path.dirname(__file__) + '/images/help.png')
        self.helpAction = QAction(icon, u'Shape Tools Help', self.iface.mainWindow())
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.helpAction)
        
        if processingOk:
            Processing.addProvider(self.provider)
            
        self.iface.currentLayerChanged.connect(self.currentLayerChanged)
        self.canvas.mapToolSet.connect(self.unsetTool)
        self.enableDigitizeTool()
        
    def unsetTool(self, tool):
        try:
            if not isinstance(tool, GeodesicMeasureTool):
                self.measureAction.setChecked(False)
                self.geodesicMeasureTool.closeDialog()
            if not isinstance(tool, AzDigitizerTool):
                self.digitizeAction.setChecked(False)
        except:
            pass

    def unload(self):
        self.canvas.unsetMapTool(self.azDigitizerTool)
        
        # remove from menu
        self.iface.removePluginVectorMenu(u'Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.geodesicDensifyAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.measureAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.digitizeAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.helpAction)
        # Remove from toolbar
        self.iface.removeToolBarIcon(self.shapeAction)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.geodesicDensifyAction)
        self.iface.removeToolBarIcon(self.measureAction)
        self.iface.removeToolBarIcon(self.digitizeAction)
        self.azDigitizerTool = None
        # remove the toolbar
        del self.toolbar

        if processingOk:
            Processing.removeProvider(self.provider)
        
    def shapeTool(self):
        if self.shapeDialog is None:
            self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow())
        self.shapeDialog.show()
        
    def setShowAzDigitizerTool(self):
        self.digitizeAction.setChecked(True)
        self.canvas.setMapTool(self.azDigitizerTool)
        
    def xyLineTool(self):
        if self.xyLineDialog is None:
            self.xyLineDialog = XYToLineWidget(self.iface, self.iface.mainWindow())
        self.xyLineDialog.show()
        
    def geodesicDensifyTool(self):
        if self.geodesicDensifyDialog is None:
            self.geodesicDensifyDialog = GeodesicDensifyWidget(self.iface, self.iface.mainWindow())
        self.geodesicDensifyDialog.show()
        
    def measureTool(self):
        self.measureAction.setChecked(True)
        self.canvas.setMapTool(self.geodesicMeasureTool)
        
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
        self.enableDigitizeTool()

    def layerEditingChanged(self):
        self.enableDigitizeTool()

    def enableDigitizeTool(self):
        self.digitizeAction.setEnabled(False)
        layer = self.iface.activeLayer()
        
        if layer != None and isinstance(layer, QgsVectorLayer) and ((layer.wkbType() == QGis.WKBPoint) or (layer.wkbType() == QGis.WKBLineString) or (layer.wkbType() == QGis.WKBMultiLineString)) and layer.isEditable():
            self.digitizeAction.setEnabled(True)
        else:
            self.digitizeAction.setChecked(False)
