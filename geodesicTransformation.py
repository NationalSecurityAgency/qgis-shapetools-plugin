import os
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsPoint, QgsProject, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameters,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS


class GeodesicTransformationsAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to transform geometry shapes.
    """

    PrmTransformRotation = 'TransformRotation'
    PrmTransformScale = 'TransformScale'
    PrmTransformAzimuth = 'TransformAzimuth'
    PrmTransformDistance = 'TransformDistance'
    PrmTransformUnits = 'TransformUnits'

    def createInstance(self):
        return GeodesicTransformationsAlgorithm()

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

    def outputName(self):
        return tr('Transformed layer')

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

    def inputLayerTypes(self):
        return [QgsProcessing.TypeVectorAnyGeometry]

    def outputWkbType(self, input_wkb_type):
        return input_wkb_type

    def initParameters(self, config=None):
        param = QgsProcessingParameterNumber(
            self.PrmTransformRotation,
            tr('Rotation angle about the centroid'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmTransformRotation,
            tr('Rotation angle about the centroid'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmTransformScale,
            tr('Scale factor about the centroid'),
            QgsProcessingParameterNumber.Double,
            defaultValue=1,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmTransformScale,
            tr('Scale factor about the centroid'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmTransformDistance,
            tr('Translation distance'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmTransformDistance,
            tr('Translation distance'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmTransformAzimuth,
            tr('Translation azimuth'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmTransformAzimuth,
            tr('Translation azimuth'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmTransformUnits,
                tr('Translation distance units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )

    def prepareAlgorithm(self, parameters, context, feedback):
        self.angle = self.parameterAsDouble(parameters, self.PrmTransformRotation, context)
        self.angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmTransformRotation)
        if self.angle_dyn:
            self.angle_property = parameters[self.PrmTransformRotation]

        self.scale = self.parameterAsDouble(parameters, self.PrmTransformScale, context)
        self.scale_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmTransformScale)
        if self.scale_dyn:
            self.scale_property = parameters[self.PrmTransformScale]

        distance = self.parameterAsDouble(parameters, self.PrmTransformDistance, context)
        self.distance_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmTransformDistance)
        if self.distance_dyn:
            self.distance_property = parameters[self.PrmTransformDistance]

        self.azimuth = self.parameterAsDouble(parameters, self.PrmTransformAzimuth, context)
        self.azimuth_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmTransformAzimuth)
        if self.azimuth_dyn:
            self.azimuth_property = parameters[self.PrmTransformAzimuth]

        units = self.parameterAsInt(parameters, self.PrmTransformUnits, context)

        self.to_meters = conversionToMeters(units)
        self.distance = distance * self.to_meters

        source = self.parameterAsSource(parameters, 'INPUT', context)
        src_crs = source.sourceCrs()
        self.geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
        self.to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())
        return True

    def processFeature(self, feature, context, feedback):
        # Check each parameter to see if it is useing data defined expressions
        if self.angle_dyn:
            angle, _ = self.angle_property.valueAsDouble(context.expressionContext(), self.angle)
        else:
            angle = self.angle

        if self.scale_dyn:
            scale, _ = self.scale_property.valueAsDouble(context.expressionContext(), self.scale)
        else:
            scale = self.scale

        if self.azimuth_dyn:
            azimuth, _ = self.azimuth_property.valueAsDouble(context.expressionContext(), self.azimuth)
        else:
            azimuth = self.azimuth

        if self.distance_dyn:
            distance, _ = self.distance_property.valueAsDouble(context.expressionContext(), self.distance)
            distance = distance * self.to_meters
        else:
            distance = self.distance
        geom = feature.geometry()
        # Find the centroid of the vector shape. We will resize everything based on this
        centroid = geom.centroid().asPoint()
        centroid = self.geom_to_4326.transform(centroid.x(), centroid.y())
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
            v = self.geom_to_4326.transform(vertex.x(), vertex.y())
            gline = geod.Inverse(cy, cx, v.y(), v.x())
            vdist = gline['s12']
            vazi = gline['azi1']
            if scale != 1:
                vdist = vdist * scale
            if angle != 0:
                vazi += angle
            g = geod.Direct(ncy, ncx, vazi, vdist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            new_vertex = self.to_sink_crs.transform(g['lon2'], g['lat2'])
            geom.moveVertex(new_vertex.x(), new_vertex.y(), vcnt)
        feature.setGeometry(geom)
        return [feature]
