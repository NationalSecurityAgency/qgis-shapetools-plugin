import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .geodesicDensify import GeodesicDensifyAlgorithm
from .xyToLine import XYToLineAlgorithm
from .createDonut import CreateDonutAlgorithm
from .createLob import CreateLobAlgorithm
from .createPolygon import CreatePolygonAlgorithm
from .idlbreakline import IdlBreakLineAlgorithm

class ShapeToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(GeodesicDensifyAlgorithm())
        self.addAlgorithm(IdlBreakLineAlgorithm())
        self.addAlgorithm(XYToLineAlgorithm())
        self.addAlgorithm(CreateDonutAlgorithm())
        self.addAlgorithm(CreateLobAlgorithm())
        self.addAlgorithm(CreatePolygonAlgorithm())

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        
    def id(self):
        return 'shapetools'

    def name(self):
        return 'Shape tools'

    def longName(self):
        return self.name()
