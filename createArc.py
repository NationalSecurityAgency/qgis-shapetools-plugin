import os
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsPointXY, QgsFeature, QgsGeometry, QgsField,
                       QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPropertyDefinition)

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameters,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS, hasIdlCrossing

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class CreateArcAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmShapeType = 'ShapeType'
    PrmAzimuthMode = 'AzimuthMode'
    PrmDefaultAzimuth1 = 'DefaultAzimuth1'
    PrmDefaultAzimuth2 = 'DefaultAzimuth2'
    PrmInnerRadius = 'InnerRadius'
    PrmOuterRadius = 'OuterRadius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmShapeType,
                tr('Shape type'),
                options=SHAPE_TYPE,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmAzimuthMode,
                tr('Azimuth mode'),
                options=[tr('Use beginning and ending azimuths'), tr('Use center azimuth and azimuth width')],
                defaultValue=1,
                optional=False)
        )
        param = QgsProcessingParameterNumber(
            self.PrmDefaultAzimuth1,
            tr('Beginning azimuth / Center azimuth'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmDefaultAzimuth1,
            tr('Ending azimuth / Center azimuth'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
        self.addParameter(param)
        
        param = QgsProcessingParameterNumber(
            self.PrmDefaultAzimuth2,
            tr('Ending azimuth / Azimuth width'),
            QgsProcessingParameterNumber.Double,
            defaultValue=30.0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmDefaultAzimuth2,
            tr('Ending azimuth / Azimuth width'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=40.0,
            minValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=True)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition( QgsPropertyDefinition(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsPropertyDefinition.Double ))
        param.setDynamicLayerParameterName(self.PrmInputLayer)
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
                defaultValue=36,
                minValue=4,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmExportInputGeometry,
                tr('Add input geometry fields to output table'),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        azimuth_mode = self.parameterAsInt(parameters, self.PrmAzimuthMode, context)
        start_angle = self.parameterAsDouble(parameters, self.PrmDefaultAzimuth1, context)
        start_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmDefaultAzimuth1)
        if start_angle_dyn:
            start_angle_property = parameters[ self.PrmDefaultAzimuth1 ]
        end_angle = self.parameterAsDouble(parameters, self.PrmDefaultAzimuth2, context)
        end_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmDefaultAzimuth2)
        if end_angle_dyn:
            end_angle_property = parameters[ self.PrmDefaultAzimuth2 ]
        outer_radius = self.parameterAsDouble(parameters, self.PrmOuterRadius, context)
        outer_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOuterRadius)
        if outer_radius_dyn:
            outer_radius_property = parameters[ self.PrmOuterRadius ]
        inner_radius = self.parameterAsDouble(parameters, self.PrmInnerRadius, context)
        inner_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmInnerRadius)
        if inner_radius_dyn:
            inner_radius_property = parameters[ self.PrmInnerRadius ]
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        measure_factor = conversionToMeters(units)

        inner_radius_converted = inner_radius * measure_factor
        outer_radius_converted = outer_radius * measure_factor

        pt_spacing = 360.0 / segments
        src_crs = source.sourceCrs()
        fields = source.fields()
        if export_geom:
            names = fields.names()
            name_x, name_y = settings.getGeomNames(names)
            fields.append(QgsField(name_x, QVariant.Double))
            fields.append(QgsField(name_y, QVariant.Double))
        if shape_type == 0:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Polygon, src_crs)
        else:
            (sink, dest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLayer, context, fields,
                QgsWkbTypes.LineString, src_crs)

        if src_crs != epsg4326:
            geom_to_4326 = QgsCoordinateTransform(src_crs, epsg4326, QgsProject.instance())
            to_sink_crs = QgsCoordinateTransform(epsg4326, src_crs, QgsProject.instance())
        else:
            geom_to_4326 = None
            to_sink_crs = None
        
        feature_count = source.featureCount()
        total = 100.0 / feature_count if feature_count else 0

        iterator = source.getFeatures()
        num_bad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            try:
                pts = []
                pt = feature.geometry().asPoint()
                pt_orig_x = pt.x()
                pt_orig_y = pt.y()
                # make sure the coordinates are in EPSG:4326
                if geom_to_4326:
                    pt = geom_to_4326.transform(pt.x(), pt.y())
                if start_angle_dyn:
                    sangle,_ = start_angle_property.valueAsDouble(context.expressionContext(), start_angle)
                else:
                    sangle = start_angle
                if end_angle_dyn:
                    eangle,_ = end_angle_property.valueAsDouble(context.expressionContext(), end_angle)
                else:
                    eangle = end_angle
                if azimuth_mode == 1:
                    width = abs(eangle) / 2.0
                    eangle = sangle + width
                    sangle -= width
                if outer_radius_dyn:
                    outer_dist = outer_radius_property.valueAsDouble(context.expressionContext(), outer_radius)[0] * measure_factor
                else:
                    outer_dist = outer_radius_converted
                if inner_radius_dyn:
                    inner_dist = inner_radius_property.valueAsDouble(context.expressionContext(), inner_radius)[0] * measure_factor
                else:
                    inner_dist = inner_radius_converted

                sangle = sangle % 360
                eangle = eangle % 360
                if sangle == eangle:  # Create a donut instead
                    feedback.pushInfo('Creating donut')
                    angle = 0
                    pts_in = []
                    while angle < 360:
                        if inner_dist != 0:
                            g = geod.Direct(pt.y(), pt.x(), angle, inner_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                            pts_in.append(QgsPointXY(g['lon2'], g['lat2']))
                        g = geod.Direct(pt.y(), pt.x(), angle, outer_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts.append(QgsPointXY(g['lon2'], g['lat2']))
                        angle += pt_spacing
                    if inner_dist != 0:
                        pts_in.append(pts_in[0])
                    pts.append(pts[0]) # Outer point ring
                    crosses_idl = hasIdlCrossing(pts)
                    if crosses_idl:
                        if inner_dist != 0:
                            makeIdlCrossingsPositive(pts_in, True)
                        makeIdlCrossingsPositive(pts, True)
                    # If the Output crs is not 4326 transform the points to the proper crs
                    if to_sink_crs:
                        if inner_dist != 0:
                            for x, pt_out in enumerate(pts_in):
                                pts_in[x] = to_sink_crs.transform(pt_out)
                        for x, pt_out in enumerate(pts):
                            pts[x] = to_sink_crs.transform(pt_out)

                    f = QgsFeature()
                    if shape_type == 0:
                        if inner_dist == 0:
                            f.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                        else:
                            f.setGeometry(QgsGeometry.fromPolygonXY([pts, pts_in]))
                    else:
                        if inner_dist == 0:
                            f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts]))
                        else:
                            f.setGeometry(QgsGeometry.fromMultiPolylineXY([pts, pts_in]))
                else:
                    if sangle > eangle:
                        # We are crossing the 0 boundary so lets just subtract
                        # 360 from it.
                        sangle -= 360.0
                    sanglesave = sangle

                    while sangle < eangle:  # Draw the outer arc
                        g = geod.Direct(pt.y(), pt.x(), sangle, outer_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts.append(QgsPointXY(g['lon2'], g['lat2']))
                        sangle += pt_spacing  # add this number of degrees to the angle

                    g = geod.Direct(pt.y(), pt.x(), eangle, outer_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    if inner_dist == 0:  # This will just be a pie wedge
                        pts.append(pt)
                    else:
                        sangle = sanglesave
                        while eangle > sangle:  # Draw the inner arc
                            g = geod.Direct(pt.y(), pt.x(), eangle, inner_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                            pts.append(QgsPointXY(g['lon2'], g['lat2']))
                            eangle -= pt_spacing  # subtract this number of degrees to the angle
                        g = geod.Direct(pt.y(), pt.x(), sangle, inner_dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        pts.append(QgsPointXY(g['lon2'], g['lat2']))

                    pts.append(pts[0])
                    makeIdlCrossingsPositive(pts)
                    # If the Output crs is not 4326 transform the points to the proper crs
                    if to_sink_crs:
                        for x, pt_out in enumerate(pts):
                            pts[x] = to_sink_crs.transform(pt_out)

                    f = QgsFeature()
                    if shape_type == 0:
                        f.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                    else:
                        f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                attr = feature.attributes()
                if export_geom:
                    attr.append(pt_orig_x)
                    attr.append(pt_orig_y)
                f.setAttributes(attr)
                sink.addFeature(f)
            except Exception:
                num_bad += 1

            feedback.setProgress(int(cnt * total))

        if num_bad > 0:
            feedback.pushInfo(
                tr("{} out of {} features had invalid parameters and were ignored.".format(num_bad, feature_count)))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'createarc'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/arc.png'))

    def displayName(self):
        return tr('Create arc wedge')

    def group(self):
        return tr('Geodesic vector creation')

    def groupId(self):
        return 'vectorcreation'

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def createInstance(self):
        return CreateArcAlgorithm()
