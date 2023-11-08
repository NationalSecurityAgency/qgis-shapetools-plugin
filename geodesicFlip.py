"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsProject, QgsMapLayer, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import epsg4326, geod
from .utils import tr

class GeodesicFlipAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to flip shapes horizontally or vertically.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmFlipMode = 'FlipMode'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input vector layer'),
                [QgsProcessing.TypeVectorAnyGeometry])
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmFlipMode,
                tr('Transform function'),
                options=[tr('Flip Horizontal'), tr('Flip Vertical'), tr('Rotate 180\xb0'), tr('Rotate 90\xb0 CW'), tr('Rotate 90\xb0 CCW')],
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
        mode = self.parameterAsInt(parameters, self.PrmFlipMode, context)

        src_crs = source.sourceCrs()
        wkbtype = source.wkbType()

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context,
            source.fields(), wkbtype, src_crs)

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

            vertices = geom.vertices()
            for vcnt, vertex in enumerate(vertices):
                v = geom_to_4326.transform(vertex.x(), vertex.y())
                gline = geod.Inverse(cy, cx, v.y(), v.x())
                vdist = gline['s12']
                vazi = gline['azi1']
                if mode == 0:  # flip horizontally
                    vazi = -1.0 * vazi
                elif mode == 1:  # Flip vertically
                    vazi = -1.0 * (vazi + 180)
                elif mode == 2:  # Rotate 180
                    vazi += 180
                elif mode == 3:  # Rotate 90
                    vazi += 90
                else:
                    vazi -= 90  # Rotate -90
                g = geod.Direct(cy, cx, vazi, vdist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                new_vertex = to_sink_crs.transform(g['lon2'], g['lat2'])
                geom.moveVertex(new_vertex.x(), new_vertex.y(), vcnt)
            feature.setGeometry(geom)
            sink.addFeature(feature)

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'geodesicflip'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/flip.svg'))

    def displayName(self):
        return tr('Geodesic flip and rotate')

    def group(self):
        return tr('Vector geometry')

    def groupId(self):
        return 'vectorgeometry'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def createInstance(self):
        return GeodesicFlipAlgorithm()

def flipLayer(iface, layer, mode):
    if not layer or not layer.isValid() or (layer.type() != QgsMapLayer.VectorLayer) or not layer.isEditable():
        return
    src_crs = layer.sourceCrs()
    geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
    to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())

    if layer.selectedFeatureCount():
        iterator = layer.getSelectedFeatures()
    else:
        iterator = layer.getFeatures()
    for cnt, feature in enumerate(iterator):
        geom = feature.geometry()
        # Find the centroid of the vector shape. We will resize everything based on this
        centroid = geom.centroid().asPoint()
        centroid = geom_to_4326.transform(centroid.x(), centroid.y())
        cy = centroid.y()
        cx = centroid.x()

        vertices = geom.vertices()
        for vcnt, vertex in enumerate(vertices):
            v = geom_to_4326.transform(vertex.x(), vertex.y())
            gline = geod.Inverse(cy, cx, v.y(), v.x())
            vdist = gline['s12']
            vazi = gline['azi1']
            if mode == 0:  # flip horizontally
                vazi = -1.0 * vazi
            elif mode == 1:  # Flip vertically
                vazi = -1.0 * (vazi + 180)
            elif mode == 2:  # Rotate 180
                vazi += 180
            elif mode == 3:  # Rotate 90
                vazi += 90
            else:
                vazi -= 90  # Rotate -90
            g = geod.Direct(cy, cx, vazi, vdist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            new_vertex = to_sink_crs.transform(g['lon2'], g['lat2'])
            geom.moveVertex(new_vertex.x(), new_vertex.y(), vcnt)
        layer.changeGeometry(feature.id(), geom)
    layer.updateExtents()
    iface.mapCanvas().refresh()
