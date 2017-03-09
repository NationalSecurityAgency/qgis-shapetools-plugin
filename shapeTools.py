from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

from LatLon import LatLon
from vector2Shape import Vector2ShapeWidget
from xyToLine import XYToLineWidget
from settings import SettingsWidget
import os.path
import webbrowser

class ShapeTools:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.settingsDialog = SettingsWidget(self.iface, self.iface.mainWindow())
        self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow(), self.settingsDialog)
        self.xyLineDialog = XYToLineWidget(self.iface, self.iface.mainWindow(), self.settingsDialog)

        # Initialize the create shape Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.shapeAction = QAction(icon, u'Create Shapes', self.iface.mainWindow())
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.shapeAction)
        
        # Initialize the XY to Line Dialog Box
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, u'XY to Line', self.iface.mainWindow())
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.xyLineAction)
        
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

    def unload(self):
        self.iface.removePluginVectorMenu(u'Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu(u'Shape Tools', self.helpAction)
        
    def shapeTool(self):
        self.shapeDialog.show()
        
    def xyLineTool(self):
        self.xyLineDialog.show()
        
    def settings(self):
        self.settingsDialog.show()
    
    def help(self):
        '''Display a help page'''
        url = QUrl.fromLocalFile(os.path.dirname(__file__) + '/index.html').toString()
        webbrowser.open(url, new=2)
        
