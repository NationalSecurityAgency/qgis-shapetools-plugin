import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .geodesicDensify import GeodesicDensifyAlgorithm
from .xyToLine import XYToLineAlgorithm

class ShapeToolsProvider(QgsProcessingProvider):

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        self.addAlgorithm(GeodesicDensifyAlgorithm())
        self.addAlgorithm(XYToLineAlgorithm())

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        
    def id(self):
        return 'shapetools'

    def name(self):
        return 'Shape tools'

    def longName(self):
        return self.name()
