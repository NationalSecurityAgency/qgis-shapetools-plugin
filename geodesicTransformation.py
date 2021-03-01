import os
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsPoint, QgsProject, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS

class GeodesicTransformationsAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to transform geometry shapes.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmTransformRotation = 'TransformRotation'
    PrmTransformScale = 'TransformScale'
    PrmTransformAzimuth = 'TransformAzimuth'
    PrmTransformDistance = 'TransformDistance'
    PrmTransformUnits = 'TransformUnits'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input vector layer'),
                [QgsProcessing.TypeVectorAnyGeometry])
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmTransformRotation,
                tr('Rotation angle about the centroid'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmTransformScale,
                tr('Scale factor about the centroid'),
                QgsProcessingParameterNumber.Double,
                defaultValue=1,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmTransformDistance,
                tr('Translation distance'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmTransformAzimuth,
                tr('Translation azimuth'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmTransformUnits,
                tr('Translation distance units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        angle = self.parameterAsDouble(parameters, self.PrmTransformRotation, context)
        scale = self.parameterAsDouble(parameters, self.PrmTransformScale, context)
        azimuth = self.parameterAsDouble(parameters, self.PrmTransformAzimuth, context)
        distance = self.parameterAsDouble(parameters, self.PrmTransformDistance, context)
        units = self.parameterAsInt(parameters, self.PrmTransformUnits, context)

        to_meters = conversionToMeters(units)
        distance = distance * to_meters
        src_crs = source.sourceCrs()
        wkbtype = source.wkbType()

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, source.fields(), wkbtype, src_crs)

        geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
        to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())

        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0

        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            geom = feature.geometry()
            # Find the centroid of the vector shape. We will resize everything based on this
            centroid = geom.centroid().asPoint()
            centroid = geom_to_4326.transform(centroid.x(), centroid.y())
            cy = centroid.y()
            cx = centroid.x()
            if distance != 0:
                g = geod.Direct(cy, cx, azimuth, distance, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                new_centroid = QgsPoint(g['lon2'], g['lat2'])
            else:
                new_centroid = centroid

            # Find the x & y coordinates of the new centroid
            ncy = new_centroid.y()
            ncx = new_centroid.x()

            vertices = geom.vertices()
            for vcnt, vertex in enumerate(vertices):
                v = geom_to_4326.transform(vertex.x(), vertex.y())
                gline = geod.Inverse(cy, cx, v.y(), v.x())
                vdist = gline['s12']
                vazi = gline['azi1']
                if scale != 1:
                    vdist = vdist * scale
                if angle != 0:
                    vazi += angle
                g = geod.Direct(ncy, ncx, vazi, vdist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                new_vertex = to_sink_crs.transform(g['lon2'], g['lat2'])
                geom.moveVertex(new_vertex.x(), new_vertex.y(), vcnt)
            feature.setGeometry(geom)
            sink.addFeature(feature)

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'geodesictransformations'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/transformShape.svg'))

    def displayName(self):
        return tr('Geodesic transformations')

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
        file = os.path.dirname(__file__) + '/doc/GeodesicTransformationsAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return GeodesicTransformationsAlgorithm()
