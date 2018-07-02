import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .geodesicDensify import GeodesicDensifyAlgorithm

class ShapeToolsProvider(QgsProcessingProvider):

    def __init__(self):
        QgsProcessingProvider.__init__(self)

        # Load algorithms
        self.alglist = [GeodesicDensifyAlgorithm()]

    def unload(self):
        QgsProcessingProvider.unload(self)

    def loadAlgorithms(self):
        for alg in self.alglist:
            self.addAlgorithm( alg )

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        
    def id(self):
        return 'shapetools'

    def name(self):
        return 'Shape tools'

    def longName(self):
        return self.name()