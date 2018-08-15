import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .geodesicDensify import GeodesicDensifyAlgorithm
from .xyToLine import XYToLineAlgorithm
from .createDonut import CreateDonutAlgorithm
from .createLob import CreateLobAlgorithm
from .createPolygon import CreatePolygonAlgorithm
from .idlbreakline import IdlBreakLineAlgorithm
from .createPie import CreatePieAlgorithm
from .createArc import CreateArcAlgorithm
from .createStar import CreateStarAlgorithm
from .createRose import CreateRoseAlgorithm

class ShapeToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(GeodesicDensifyAlgorithm())
        self.addAlgorithm(IdlBreakLineAlgorithm())
        self.addAlgorithm(XYToLineAlgorithm())
        self.addAlgorithm(CreateDonutAlgorithm())
        self.addAlgorithm(CreateLobAlgorithm())
        self.addAlgorithm(CreatePieAlgorithm())
        self.addAlgorithm(CreateArcAlgorithm())
        self.addAlgorithm(CreatePolygonAlgorithm())
        self.addAlgorithm(CreateStarAlgorithm())
        self.addAlgorithm(CreateRoseAlgorithm())

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        
    def id(self):
        return 'shapetools'

    def name(self):
        return 'Shape tools'

    def longName(self):
        return self.name()
