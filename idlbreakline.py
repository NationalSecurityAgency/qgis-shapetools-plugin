import os

from qgis.core import QgsCoordinateTransform, QgsFeature, QgsGeometry, QgsProject, QgsWkbTypes

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from .settings import epsg4326
from .utils import checkIdlCrossings, normalizeLongitude, tr
# import traceback

class IdlBreakLineAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm for creating lines from two coordinates within a record.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input layer'),
                [QgsProcessing.TypeFile | QgsProcessing.TypeVectorLine])
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'),
                optional=True,
                createByDefault=True)
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        srcCRS = source.sourceCrs()

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, source.fields(),
            QgsWkbTypes.MultiLineString, srcCRS)

        # Set up CRS transformations
        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())

        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0

        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                if feature.geometry().isMultipart():
                    seg = feature.geometry().asMultiPolyline()
                else:
                    seg = [feature.geometry().asPolyline()]
                numseg = len(seg)
                if numseg < 1 or len(seg[0]) < 2:
                    continue

                outseg = []
                for pts in seg:
                    if srcCRS != epsg4326:
                        for x, pt in enumerate(pts):
                            pts[x] = geomTo4326.transform(pt)
                    normalizeLongitude(pts)
                    newseg = checkIdlCrossings(pts)
                    outseg.extend(newseg)
                if srcCRS != epsg4326:  # Convert each point to the output CRS
                    for y in range(len(outseg)):
                        for x, pt in enumerate(outseg[y]):
                            outseg[y][x] = toSinkCrs.transform(pt)

                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromMultiPolylineXY(outseg))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)

            except Exception:
                '''s = traceback.format_exc()
                feedback.pushInfo(s)'''
                pass

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'linebreak'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/idlbreak.svg')

    def displayName(self):
        return tr('Geodesic line break at -180,180')

    def group(self):
        return tr('Vector geometry')

    def groupId(self):
        return 'vectorgeometry'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def shortHelpString(self):
        file = os.path.dirname(__file__) + '/doc/GeodesicBreakLineAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return IdlBreakLineAlgorithm()
