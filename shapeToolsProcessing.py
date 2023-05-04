from qgis.core import QgsApplication

from .provider import ShapeToolsProvider
from .stFunctions import InitShapeToolsFunctions, UnloadShapeToolsFunctions

class ShapeTools(object):
    def __init__(self):
        self.provider = None

    def initProcessing(self):
        self.provider = ShapeToolsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)
        InitShapeToolsFunctions()

    def initGui(self):
        self.initProcessing()

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        UnloadShapeToolsFunctions()
