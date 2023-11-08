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

from qgis.core import (
    QgsPointXY, QgsFeature, QgsGeometry, QgsField,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (
    QgsProcessing,
    QgsProcessingParameters,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS, makeIdlCrossingsPositive, hasIdlCrossing


class ConcentricRingsAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create concentric geodesic rings with radial lines.
    """

    PrmStartingRadius = 'StartingRadius'
    PrmDistance = 'Distance'
    PrmRingCount = 'RingCount'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmRadials = 'Radials'
    PrmStartingRadialAngle = 'StartingRadialAngle'

    def createInstance(self):
        return ConcentricRingsAlgorithm()

    def name(self):
        return 'createrings'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/concentricrings.png'))

    def displayName(self):
        return tr('Create rings')

    def group(self):
        return tr('Geodesic shapes')

    def groupId(self):
        return 'vectorcreation'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def supportInPlaceEdit(self, layer):
        return False

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT',
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
        )
        param = QgsProcessingParameterNumber(
            self.PrmStartingRadius,
            tr('Radius of first ring. If 0, distance between rings is used'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmStartingRadius,
            tr('Radius of first ring. If 0, distance between rings is used'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmDistance,
            tr('Distance between rings'),
            QgsProcessingParameterNumber.Double,
            defaultValue=10.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmDistance,
            tr('Distance between rings'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmRingCount,
            tr('Number of rings'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=4.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmRingCount,
            tr('Number of rings'),
            QgsPropertyDefinition.Integer))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Radius units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmDrawingSegments,
                tr('Number of drawing segments'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=90,
                minValue=4,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmRadials,
                tr('Number of radial lines'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=0,
                minValue=0,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmStartingRadialAngle,
                tr('Starting radial line angle (degrees)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0,
                maxValue=360,
                minValue=-360,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, 'INPUT', context)
        expressionContext = self.createExpressionContext(parameters, context, source)
        radial_line_cnt = self.parameterAsInt(parameters, self.PrmRadials, context)
        starting_radial_angle = self.parameterAsDouble(parameters, self.PrmStartingRadialAngle, context)

        # The radius of the first ring. If 0 sue the distance from one ring to the next
        starting_radius = self.parameterAsDouble(parameters, self.PrmStartingRadius, context)
        starting_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmStartingRadius)
        if starting_radius_dyn:
            starting_radius_property = parameters[self.PrmStartingRadius]

        # The distance from one ring to the next
        ring_distance = self.parameterAsDouble(parameters, self.PrmDistance, context)
        ring_distance_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmDistance)
        if ring_distance_dyn:
            ring_distance_property = parameters[self.PrmDistance]

        # If the starting radius is set to 0, change it to the ring_distance radius
        if starting_radius == 0:
            starting_radius = ring_distance

        # How many rings will be drawn
        ring_count = self.parameterAsInt(parameters, self.PrmRingCount, context)
        ring_count_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRingCount)
        if ring_count_dyn:
            ring_count_property = parameters[self.PrmRingCount]

        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)

        measure_factor = conversionToMeters(units)

        ring_distance_converted = ring_distance * measure_factor
        starting_radius_converted = starting_radius * measure_factor

        pt_spacing = 360.0 / segments
        source = self.parameterAsSource(parameters, 'INPUT', context)
        src_crs = source.sourceCrs()
        total_features = source.featureCount()

        if src_crs != epsg4326:
            geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
            to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())
        else:
            geom_to_4326 = None
            to_sink_crs = None

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT',
            context, source.fields(), QgsWkbTypes.MultiLineString, source.sourceCrs())

        total = 100.0 / source.featureCount() if source.featureCount() else 0
        iterator = source.getFeatures()
        num_bad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            expressionContext.setFeature(feature)
            try:
                pt = feature.geometry().asPoint()
                pt_orig_x = pt.x()
                pt_orig_y = pt.y()
                # make sure the coordinates are in EPSG:4326
                if geom_to_4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()

                # Get the radius of the first ring
                if starting_radius_dyn:
                    sradius, e = starting_radius_property.valueAsDouble(expressionContext, starting_radius)
                    sradius *= measure_factor
                    if not e or sradius < 0:
                        num_bad += 1
                        continue
                else:
                    sradius = starting_radius_converted

                # Get the distance between rings
                if ring_distance_dyn:
                    ring_dist, e = ring_distance_property.valueAsDouble(expressionContext, ring_distance)
                    if not e:
                        num_bad += 1
                        continue
                    ring_dist *= measure_factor
                else:
                    ring_dist = ring_distance_converted

                if sradius == 0:
                    sradius = ring_dist

                # Get the number of rings to draw
                if ring_count_dyn:
                    rcount, e = ring_count_property.valueAsInt(expressionContext, ring_count)
                    if not e:
                        num_bad += 1
                        continue
                else:
                    rcount = ring_count

                multi_line = []
                for ring in range(0, rcount):
                    dist = sradius + ring * ring_dist
                    pts = []
                    angle = 0
                    while angle < 360:
                        g = geod.Direct(lat, lon, angle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts.append(QgsPointXY(g['lon2'], g['lat2']))
                        angle += pt_spacing
                    pts.append(pts[0])
                    crosses_idl = hasIdlCrossing(pts)
                    if crosses_idl:
                        makeIdlCrossingsPositive(pts, True)

                    # If the Output crs is not 4326 transform the points to the proper crs
                    if to_sink_crs:
                        for x, vtx in enumerate(pts):
                            pts[x] = to_sink_crs.transform(vtx)
                    multi_line.append(pts)
                if radial_line_cnt:
                    # This will be the number of points to draw the radials
                    num_radial_pts = int(segments / 6)
                    if num_radial_pts < 2:
                        num_radial_pts = 2
                    for i in range(radial_line_cnt):
                        angle = starting_radial_angle + i * 360 / radial_line_cnt
                        pts = [pt]
                        for j in range(1, num_radial_pts + 1):
                            dist2 = dist * j / num_radial_pts
                            g = geod.Direct(lat, lon, angle, dist2, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                            pts.append(QgsPointXY(g['lon2'], g['lat2']))
                        if to_sink_crs:
                            for x, vtx in enumerate(pts):
                                pts[x] = to_sink_crs.transform(vtx)
                        multi_line.append(pts)

                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromMultiPolylineXY(multi_line))
                f.setAttributes(feature.attributes())
                sink.addFeature(f)
            except Exception:
                num_bad += 1

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))

        if num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, total_features)))
        return {'OUTPUT': dest_id}
