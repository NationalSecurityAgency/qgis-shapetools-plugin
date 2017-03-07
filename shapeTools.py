from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

from LatLon import LatLon
from vector2Shape import Vector2ShapeWidget
from xyToLine import XYToLineWidget
import os.path


class ShapeTools:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.shapeDialog = Vector2ShapeWidget(self.iface, self.iface.mainWindow())
        self.xyLineDialog = XYToLineWidget(self.iface, self.iface.mainWindow())

        # Initialize the create shape Dialog Box
        icon = QIcon(os.path.dirname(__file__) + "/images/shapes.png")
        self.shapeAction = QAction(icon, "Create Shapes", self.iface.mainWindow())
        self.shapeAction.triggered.connect(self.shapeTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.shapeAction)
        
        # Initialize the XY to Line Dialog Box
        icon = QIcon(os.path.dirname(__file__) + "/images/xyline.png")
        self.xyLineAction = QAction(icon, "XY to Line", self.iface.mainWindow())
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.xyLineAction)

    def unload(self):
        self.iface.removePluginVectorMenu('Shape Tools', self.shapeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.xyLineAction)
        
    def shapeTool(self):
        self.shapeDialog.show()
        
    def xyLineTool(self):
        self.xyLineDialog.show()
        
