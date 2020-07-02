import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .geodesicDensify import GeodesicDensifyAlgorithm
from .geodesicPointDecimate import GeodesicPointDecimateAlgorithm
from .geodesicLineDecimate import GeodesicLineDecimateAlgorithm
from .geodesicLayerMeasure import GeodesicLayerMeasureAlgorithm
from .geodesicTransformation import GeodesicTransformationsAlgorithm
from .xyToLine import XYToLineAlgorithm
from .geodesicFlip import GeodesicFlipAlgorithm
from .createDonut import CreateDonutAlgorithm
from .createEllipse import CreateEllipseAlgorithm
from .createLob import CreateLobAlgorithm
from .createPolygon import CreatePolygonAlgorithm
from .idlbreakline import IdlBreakLineAlgorithm
from .createPie import CreatePieAlgorithm
from .createArc import CreateArcAlgorithm
from .createStar import CreateStarAlgorithm
from .createRose import CreateRoseAlgorithm
from .createHypocycloid import CreateHypocycloidAlgorithm
from .createEpicycloid import CreateEpicycloidAlgorithm
from .createPolyfoil import CreatePolyfoilAlgorithm
from .createHeart import CreateHeartAlgorithm
from .createRadialLines import CreateRadialLinesAlgorithm

class ShapeToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(GeodesicDensifyAlgorithm())
        self.addAlgorithm(GeodesicPointDecimateAlgorithm())
        self.addAlgorithm(GeodesicLineDecimateAlgorithm())
        self.addAlgorithm(IdlBreakLineAlgorithm())
        self.addAlgorithm(GeodesicLayerMeasureAlgorithm())
        self.addAlgorithm(GeodesicTransformationsAlgorithm())
        self.addAlgorithm(XYToLineAlgorithm())
        self.addAlgorithm(GeodesicFlipAlgorithm())
        self.addAlgorithm(CreateEllipseAlgorithm())
        self.addAlgorithm(CreateDonutAlgorithm())
        self.addAlgorithm(CreateLobAlgorithm())
        self.addAlgorithm(CreatePieAlgorithm())
        self.addAlgorithm(CreateArcAlgorithm())
        self.addAlgorithm(CreatePolygonAlgorithm())
        self.addAlgorithm(CreateStarAlgorithm())
        self.addAlgorithm(CreateRoseAlgorithm())
        self.addAlgorithm(CreateEpicycloidAlgorithm())
        self.addAlgorithm(CreateHypocycloidAlgorithm())
        self.addAlgorithm(CreatePolyfoilAlgorithm())
        self.addAlgorithm(CreateHeartAlgorithm())
        self.addAlgorithm(CreateRadialLinesAlgorithm())

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/shapes.png')

    def id(self):
        return 'shapetools'

    def name(self):
        return 'Shape tools'

    def longName(self):
        return self.name()
