from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QIcon, QAction

from .LatLon import LatLon
from .vector2Shape import Vector2ShapeWidget
from .xyToLine import XYToLineWidget
from .settings import SettingsWidget
from .line2Geodesic import Line2GeodesicWidget
from .poly2Geodesic import Poly2GeodesicWidget
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
        self.settingsDialog = None
        self.shapeDialog = None
        self.xyLineDialog = None
        self.geodesicLineDialog = None
        self.toolbar = self.iface.addToolBar(u'Shape Tools Toolbar')
        self.toolbar.setObjectName(u'ShapeToolsToolbar')
        if processingOk:
            self.provider = ShapeToolsProvider()

    def initGui(self):
        # Initialize the create shape Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.shapeAction = QAction(icon, u'Create Shapes', self.iface.mainWindow())
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.shapeAction)
        self.toolbar.addAction(self.shapeAction)
        
        # Initialize the XY to Line Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, u'XY to Line', self.iface.mainWindow())
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)
        
        # Initialize the Line to Geodesic Line Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/line2geodesic.png')
        self.line2GeodesicAction = QAction(icon, u'Line to Geodesic Line', self.iface.mainWindow())
        self.line2GeodesicAction.triggered.connect(self.line2GeodesicTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.line2GeodesicAction)
        self.toolbar.addAction(self.line2GeodesicAction)
        
        # Initialize the Polygon to Geodesic Polygon Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/poly2geodesic.png')
        self.poly2GeodesicAction = QAction(icon, u'Polygon to Geodesic Polygon', self.iface.mainWindow())
        self.poly2GeodesicAction.triggered.connect(self.poly2GeodesicTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.poly2GeodesicAction)
        self.toolbar.addAction(self.poly2GeodesicAction)
        
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
        
    def initDialogs(self):
        '''We will not allocate resources to the plugin unless it is used.'''
        if self.settingsDialog is None:
            self.settingsDialog = SettingsWidget(self.iface, self.iface.mainWindow())
            self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow())
            self.xyLineDialog = XYToLineWidget(self.iface, self.iface.mainWindow(), self.settingsDialog)
            self.geodesicLineDialog = Line2GeodesicWidget(self.iface, self.iface.mainWindow(), self.settingsDialog)
            self.geodesicPolyDialog = Poly2GeodesicWidget(self.iface, self.iface.mainWindow(), self.settingsDialog)

    def unload(self):
        # remove from menu
        self.iface.removePluginVectorMenu(u'Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.line2GeodesicAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.poly2GeodesicAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.helpAction)
        # Remove from toolbar
        self.iface.removeToolBarIcon(self.shapeAction)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.line2GeodesicAction)
        self.iface.removeToolBarIcon(self.poly2GeodesicAction)
        # remove the toolbar
        del self.toolbar

        if processingOk:
            Processing.removeProvider(self.provider)
        
    def shapeTool(self):
        self.initDialogs()
        self.shapeDialog.show()
        
    def xyLineTool(self):
        self.initDialogs()
        self.xyLineDialog.show()
        
    def line2GeodesicTool(self):
        self.initDialogs()
        self.geodesicLineDialog.show()
        
    def poly2GeodesicTool(self):
        self.initDialogs()
        self.geodesicPolyDialog.show()
        
    def settings(self):
        self.initDialogs()
        self.settingsDialog.show()
    
    def help(self):
        '''Display a help page'''
        url = QUrl.fromLocalFile(os.path.dirname(__file__) + '/index.html').toString()
        webbrowser.open(url, new=2)
        
