from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .LatLon import LatLon
from .vector2Shape import Vector2ShapeWidget
from .xyToLine import XYToLineWidget
from .settings import SettingsWidget
from .geodesicDensify import GeodesicDensifyWidget
from .geodesicMeasureTool import GeodesicMeasureTool
import os.path
import webbrowser
'''
try:
    from processing.core.Processing import Processing
    from .provider import ShapeToolsProvider
    processingOk = True
except:
    processingOk = False'''

class ShapeTools:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settingsDialog = None
        self.shapeDialog = None
        self.xyLineDialog = None
        self.geodesicDensifyDialog = None
        self.toolbar = self.iface.addToolBar('Shape Tools Toolbar')
        self.toolbar.setObjectName('ShapeToolsToolbar')
        #if processingOk:
        #    self.provider = ShapeToolsProvider()

    def initGui(self):
        # Initialize the create shape menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.shapeAction = QAction(icon, 'Create Shapes', self.iface.mainWindow())
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.shapeAction)
        self.toolbar.addAction(self.shapeAction)
        
        # Initialize the XY to Line menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, 'XY to Line', self.iface.mainWindow())
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)
        
        # Initialize the Geodesic Densifier menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')
        self.geodesicDensifyAction = QAction(icon, 'Geodesic Shape Densifier', self.iface.mainWindow())
        self.geodesicDensifyAction.triggered.connect(self.geodesicDensifyTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.toolbar.addAction(self.geodesicDensifyAction)
        
        # Initialize Geodesic Measure Tool
        self.geodesicMeasureTool = GeodesicMeasureTool(self.iface, self.iface.mainWindow())
        self.canvas.mapToolSet.connect(self.unsetTool)
        icon = QIcon(os.path.dirname(__file__) + '/images/measure.png')
        self.measureAction = QAction(icon, 'Geodesic Measure Tool', self.iface.mainWindow())
        self.measureAction.triggered.connect(self.measureTool)
        self.measureAction.setCheckable(True)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureAction)
        self.toolbar.addAction(self.measureAction)
        
        # Settings
        icon = QIcon(os.path.dirname(__file__) + '/images/settings.png')
        self.settingsAction = QAction(icon, 'Settings', self.iface.mainWindow())
        self.settingsAction.triggered.connect(self.settings)
        self.iface.addPluginToVectorMenu('Shape Tools', self.settingsAction)
        
        # Help
        icon = QIcon(os.path.dirname(__file__) + '/images/help.png')
        self.helpAction = QAction(icon, 'Shape Tools Help', self.iface.mainWindow())
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu('Shape Tools', self.helpAction)
        
        '''if processingOk:
            Processing.addProvider(self.provider)'''
        
    def unsetTool(self, tool):
        try:
            if not isinstance(tool, GeodesicMeasureTool):
                self.measureAction.setChecked(False)
                self.geodesicMeasureTool.closeDialog()
        except:
            pass

    def unload(self):
        # remove from menu
        self.iface.removePluginVectorMenu('Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.measureAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.helpAction)
        # Remove from toolbar
        self.iface.removeToolBarIcon(self.shapeAction)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.geodesicDensifyAction)
        self.iface.removeToolBarIcon(self.measureAction)
        # remove the toolbar
        del self.toolbar

        '''if processingOk:
            Processing.removeProvider(self.provider)'''
        
    def shapeTool(self):
        if self.shapeDialog is None:
            self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow())
        self.shapeDialog.show()
        
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
        
