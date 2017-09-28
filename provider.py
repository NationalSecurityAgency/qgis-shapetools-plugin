from processing.core.AlgorithmProvider import AlgorithmProvider
from line2Geodesic import Line2GeodesicAlgorithm

class ShapeToolsProvider(AlgorithmProvider):

    def __init__(self):
        AlgorithmProvider.__init__(self)

        self.activate = True

        # New algorithms should be added to this list
        self.alglist = [Line2GeodesicAlgorithm()]
        for alg in self.alglist:
            alg.provider = self

    def supportsNonFileBasedOutput(self):
        return True

    def initializeSettings(self):
        AlgorithmProvider.initializeSettings(self)

    def unload(self):
        AlgorithmProvider.unload(self)

    def getName(self):
        return 'shapetools'

    def getDescription(self):
        return 'Shape tools'

    def _loadAlgorithms(self):
        self.algs = self.alglist