import os
from geographiclib.geodesic import Geodesic

from qgis.core import (
    QgsField, QgsPointXY, QgsGeometry, QgsPropertyDefinition,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)

from qgis.core import (
    QgsProcessing,
    QgsProcessingFeatureBasedAlgorithm,
    QgsProcessingParameters,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, makeIdlCrossingsPositive, DISTANCE_LABELS

SHAPE_TYPE = [tr("Polygon"), tr("Line")]


class CreatePieAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmShapeType = 'ShapeType'
    PrmAzimuthMode = 'AzimuthMode'
    PrmAzimuth1Field = 'Azimuth1Field'
    PrmAzimuth2Field = 'Azimuth2Field'
    PrmRadiusField = 'RadiusField'
    PrmAzimuth1 = 'Azimuth1'
    PrmAzimuth2 = 'Azimuth2'
    PrmRadius = 'Radius'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmDrawingSegments = 'DrawingSegments'
    PrmExportInputGeometry = 'ExportInputGeometry'

    def createInstance(self):
        return CreatePieAlgorithm()

    def name(self):
        return 'createpie'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/pie.png'))

    def displayName(self):
        return tr('Create pie wedge')

    def group(self):
        return tr('Geodesic vector creation')

    def groupId(self):
        return 'vectorcreation'

    def outputName(self):
        return tr('Output layer')

    def helpUrl(self):
        file = os.path.dirname(__file__) + '/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)

    def inputLayerTypes(self):
        return [QgsProcessing.TypeVectorPoint]

    def outputWkbType(self, input_wkb_type):
        if self.shape_type == 0:
            return (QgsWkbTypes.Polygon)
        return (QgsWkbTypes.LineString)

    def outputFields(self, input_fields):
        if self.export_geom:
            name_x, name_y = settings.getGeomNames(input_fields.names())
            input_fields.append(QgsField(name_x, QVariant.Double))
            input_fields.append(QgsField(name_y, QVariant.Double))
        return(input_fields)

    def  supportInPlaceEdit(self, layer):
        return False

    def initParameters(self, config=None):
        self.shape_type = 0
        self.export_geom = False
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
            self.PrmAzimuth1,
            tr('Beginning azimuth / Center azimuth'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmAzimuth1,
            tr('Beginning azimuth / Center azimuth'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmAzimuth2,
            tr('Ending azimuth / Azimuth width'),
            QgsProcessingParameterNumber.Double,
            defaultValue=30.0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmAzimuth2,
            tr('Ending azimuth / Azimuth width'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmRadius,
            tr('Radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmRadius,
            tr('Radius'),
            QgsPropertyDefinition.Double))
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

    def prepareAlgorithm(self, parameters, context, feedback):
        self.shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        self.azimuthmode = self.parameterAsInt(parameters, self.PrmAzimuthMode, context)
        self.start_angle = self.parameterAsDouble(parameters, self.PrmAzimuth1, context)
        self.start_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmAzimuth1)
        if self.start_angle_dyn:
            self.start_angle_property = parameters[self.PrmAzimuth1]
        self.end_angle = self.parameterAsDouble(parameters, self.PrmAzimuth2, context)
        self.end_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmAzimuth2)
        if self.end_angle_dyn:
            self.end_angle_property = parameters[self.PrmAzimuth2]
        self.radius = self.parameterAsDouble(parameters, self.PrmRadius, context)
        if self.radius <= 0:
            feedback.reportError('Radius parameter must be greater than 0')
            return False
        self.radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmRadius)
        if self.radius_dyn:
            self.radius_property = parameters[self.PrmRadius]
        segments = self.parameterAsInt(parameters, self.PrmDrawingSegments, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        self.export_geom = self.parameterAsBool(parameters, self.PrmExportInputGeometry, context)

        self.measureFactor = conversionToMeters(units)

        self.radius_converted = self.radius * self.measureFactor

        self.ptSpacing = 360.0 / segments
        source = self.parameterAsSource(parameters, 'INPUT', context)
        srcCRS = source.sourceCrs()
        self.total_features = source.featureCount()

        if srcCRS != epsg4326:
            self.geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            self.toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())
        else:
            self.geomTo4326 = None
            self.toSinkCrs = None
        self.num_bad = 0
        return True

    def processFeature(self, feature, context, feedback):
        try:
            pts = []
            pt = feature.geometry().asPoint()
            pt_orig_x = pt.x()
            pt_orig_y = pt.y()
            # make sure the coordinates are in EPSG:4326
            if self.geomTo4326:
                pt = self.geomTo4326.transform(pt.x(), pt.y())
            pts.append(pt)
            if self.start_angle_dyn:
                sangle, e = self.start_angle_property.valueAsDouble(context.expressionContext(), self.start_angle)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                sangle = self.start_angle
            if self.end_angle_dyn:
                eangle, e = self.end_angle_property.valueAsDouble(context.expressionContext(), self.end_angle)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                eangle = self.end_angle
            if self.azimuthmode == 1:
                width = abs(eangle) / 2.0
                eangle = sangle + width
                sangle -= width
            if self.radius_dyn:
                dist, e = self.radius_property.valueAsDouble(context.expressionContext(), self.radius)
                if not e or dist <= 0:
                    self.num_bad += 1
                    return []
                dist *= self.measureFactor
            else:
                dist = self.radius_converted

            sangle = sangle % 360
            eangle = eangle % 360

            if sangle > eangle:
                # We are crossing the 0 boundry so lets just subtract
                # 360 from it.
                sangle -= 360.0
            while sangle < eangle:
                g = geod.Direct(pt.y(), pt.x(), sangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                sangle += self.ptSpacing  # add this number of degrees to the angle

            g = geod.Direct(pt.y(), pt.x(), eangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
            pts.append(QgsPointXY(g['lon2'], g['lat2']))
            pts.append(pt)

            makeIdlCrossingsPositive(pts)
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.toSinkCrs:
                for x, ptout in enumerate(pts):
                    pts[x] = self.toSinkCrs.transform(ptout)

            if self.shape_type == 0:
                feature.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                feature.setGeometry(QgsGeometry.fromPolylineXY(pts))
            if self.export_geom:
                attr = feature.attributes()
                attr.append(pt_orig_x)
                attr.append(pt_orig_y)
                feature.setAttributes(attr)
        except Exception:
            self.num_bad += 1
            return []
        return [feature]

    def postProcessAlgorithm(self, context, feedback):
        if self.num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(self.num_bad, self.total_features)))
        return {}
