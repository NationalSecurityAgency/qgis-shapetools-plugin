from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *

# Initialize Qt resources from file resources.py
import resources

from LatLon import LatLon
from ellipse import EllipseWidget
from quickPoints import QuickPointsWidget
from quicklob import QuickLOBWidget
import os.path


class ShapeTools:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.ellipseDialog = EllipseWidget(self.iface, self.iface.mainWindow())
        self.quickPointsDialog = QuickPointsWidget(self.iface, self.iface.mainWindow())
        self.lobDialog = QuickLOBWidget(self.iface, self.iface.mainWindow())

        # Initialize the Quick Points Dialog Box
        pointsicon = QIcon(':/plugins/shapetools/images/points.png')
        self.pointsAction = QAction(pointsicon, "Quick Points", 
                    self.iface.mainWindow())
        self.pointsAction.triggered.connect(self.pointsTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.pointsAction)

        # Initialize the Ellipse Dialog Box
        ellipseicon = QIcon(':/plugins/shapetools/images/ellipse.png')
        self.ellipseAction = QAction(ellipseicon, "Quick Ellipse", 
                    self.iface.mainWindow())
        self.ellipseAction.triggered.connect(self.ellipseTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.ellipseAction)

        # Initialize the line of bearing Dialog Box
        lobicon = QIcon(':/plugins/shapetools/images/lob.png')
        self.lobAction = QAction(lobicon, "Quick Line of Bearing", 
                    self.iface.mainWindow())
        self.lobAction.triggered.connect(self.lobTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.lobAction)

    def unload(self):
        self.iface.removePluginVectorMenu('Shape Tools', self.pointsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.ellipseAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.lobAction)
        
    def pointsTool(self):
        self.quickPointsDialog.show()
        
    def ellipseTool(self):
        self.ellipseDialog.show()
        
    def lobTool(self):
        self.lobDialog.show()
        
