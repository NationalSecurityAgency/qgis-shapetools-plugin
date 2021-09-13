import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsUnitTypes, QgsVectorLayer,
    QgsPointXY, QgsFeature, QgsFields, QgsField, QgsGeometry, 
    QgsProject, QgsWkbTypes, QgsCoordinateTransform, QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling)

from qgis.core import (
    QgsProcessing,
    QgsProcessingLayerPostProcessorInterface,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl, QVariant

from .settings import epsg4326, geod, settings
from .utils import tr, DISTANCE_LABELS

unitsAbbr = ['km','m','cm','mi','yd','ft','in','nm']

class GeodesicLayerMeasureAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a line of bearing.
    """

    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmMeasureTotalLength = 'MeasureTotalLength'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmAutomaticStyline = 'AutomaticStyline'
    PrmRetainAttributes = 'RetainAttributes'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Line or polygon layer'),
                [QgsProcessing.TypeVectorLine, QgsProcessing.TypeVectorPolygon])
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmMeasureTotalLength,
                tr('Measure total length rather than each line segment'),
                True,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmRetainAttributes,
                tr("Retain the original feature's attributes"),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Distance units'),
                options=DISTANCE_LABELS,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmAutomaticStyline,
                tr('Use automatic styling'),
                True,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        measureTotal = self.parameterAsBool(parameters, self.PrmMeasureTotalLength, context)
        retain_attributes = self.parameterAsBool(parameters, self.PrmRetainAttributes, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        autoStyle = self.parameterAsBool(parameters, self.PrmAutomaticStyline, context)

        srcCRS = source.sourceCrs()

        f = QgsFields()
        f.append(QgsField("label", QVariant.String))
        f.append(QgsField("distance", QVariant.Double))
        f.append(QgsField("units", QVariant.String))
        if not measureTotal:
            f.append(QgsField("heading_to", QVariant.Double))
            f.append(QgsField("total_distance", QVariant.Double))
        if retain_attributes:
            fields = source.fields()
            for fld in fields:
                if not f.append(fld):
                    name = '_'+fld.name()
                    fld.setName(name)
                    f.append(fld)
            

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, f, QgsWkbTypes.LineString, srcCRS)

        if srcCRS != epsg4326:
            geomTo4326 = QgsCoordinateTransform(srcCRS, epsg4326, QgsProject.instance())
            toSinkCrs = QgsCoordinateTransform(epsg4326, srcCRS, QgsProject.instance())

        wkbtype = source.wkbType()
        geomtype = QgsWkbTypes.geometryType(wkbtype)

        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0

        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break

            if geomtype == QgsWkbTypes.LineGeometry:
                if feature.geometry().isMultipart():
                    ptdata = [feature.geometry().asMultiPolyline()]
                else:
                    ptdata = [[feature.geometry().asPolyline()]]
            else: #polygon
                if feature.geometry().isMultipart():
                    ptdata = feature.geometry().asMultiPolygon()
                else:
                    ptdata = [feature.geometry().asPolygon()]
            if len(ptdata) < 1:
                continue

            for seg in ptdata:
                if len(seg) < 1:
                    continue
                if measureTotal:
                    for pts in seg:
                        numpoints = len(pts)
                        if numpoints < 2:
                            continue
                        f = QgsFeature()
                        f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                        ptStart = QgsPointXY(pts[0].x(), pts[0].y())
                        if srcCRS != epsg4326: # Convert to 4326
                            ptStart = geomTo4326.transform(ptStart)
                        # Calculate the total distance of this line segment
                        distance = 0.0
                        for x in range(1,numpoints):
                            ptEnd = QgsPointXY(pts[x].x(), pts[x].y())
                            if srcCRS != epsg4326: # Convert to 4326
                                ptEnd = geomTo4326.transform(ptEnd)
                            l = geod.Inverse(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                            distance += l['s12']
                            ptStart = ptEnd

                        distance = self.unitDistance(units, distance) # Distance converted to the selected unit of measure
                        attr = ["{:.2f} {}".format(distance, unitsAbbr[units]), distance, unitsAbbr[units] ]
                        if retain_attributes:
                            f.setAttributes(attr + feature.attributes())
                        else:
                            f.setAttributes(attr)
                        sink.addFeature(f)
                else:
                    for pts in seg:
                        numpoints = len(pts)
                        if numpoints < 2:
                            continue
                        ptStart = QgsPointXY(pts[0].x(), pts[0].y())
                        if srcCRS != epsg4326: # Convert to 4326
                            ptStart = geomTo4326.transform(ptStart)
                        # Calculate the total distance of this line segment
                        totalDistance = 0.0
                        for x in range(1,numpoints):
                            ptEnd = QgsPointXY(pts[x].x(), pts[x].y())
                            if srcCRS != epsg4326: # Convert to 4326
                                ptEnd = geomTo4326.transform(ptEnd)
                            l = geod.Inverse(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                            totalDistance += l['s12']
                            ptStart = ptEnd

                        totalDistance = self.unitDistance(units, totalDistance) # Distance converted to the selected unit of measure

                        ptStart = QgsPointXY(pts[0].x(), pts[0].y())
                        if srcCRS != epsg4326: # Convert to 4326
                            pt1 = geomTo4326.transform(ptStart)
                        else:
                            pt1 = ptStart
                        for x in range(1,numpoints):
                            ptEnd = QgsPointXY(pts[x].x(), pts[x].y())
                            f = QgsFeature()
                            f.setGeometry(QgsGeometry.fromPolylineXY([ptStart, ptEnd]))
                            if srcCRS != epsg4326: # Convert to 4326
                                pt2 = geomTo4326.transform(ptEnd)
                            else:
                                pt2 = ptEnd
                            l = geod.Inverse(pt1.y(), pt1.x(), pt2.y(), pt2.x())
                            ptStart = ptEnd
                            pt1 = pt2
                            distance = self.unitDistance(units, l['s12'])
                            attr = ["{:.2f} {}".format(distance, unitsAbbr[units]), distance, unitsAbbr[units], l['azi1'],totalDistance ]
                            if retain_attributes:
                                f.setAttributes(attr + feature.attributes())
                            else:
                                f.setAttributes(attr)
                            sink.addFeature(f)

            if cnt % 100 == 0:
                feedback.setProgress(int(cnt * total))
        if autoStyle and context.willLoadLayerOnCompletion(dest_id):
            context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(StylePostProcessor.create())

        return {self.PrmOutputLayer: dest_id}

    def unitDistance(self, units, distance):
        if units == 0: # kilometers
            return distance / 1000.0
        elif units == 1: # meters
            return distance
        elif units == 2: # centimeters
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceCentimeters)
        elif units == 3: # miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceMiles)
        elif units == 4: # yards
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceYards)
        elif units == 5: # feet
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet)
        elif units == 6: # inches
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceFeet) * 12
        elif units == 7: # nautical miles
            return distance * QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceNauticalMiles)

    def name(self):
        return 'measurelayer'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/measureLine.svg'))

    def displayName(self):
        return tr('Geodesic measurement layer')

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
        return GeodesicLayerMeasureAlgorithm()

class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    instance = None

    def postProcessLayer(self, layer, context, feedback):

        if not isinstance(layer, QgsVectorLayer):
            return

        label = QgsPalLayerSettings()
        label.fieldName = 'label'
        label.placement = QgsPalLayerSettings.Line
        format = label.format()
        format.setColor(settings.measureTextColor)
        format.setNamedStyle('Bold')
        label.setFormat(format)
        labeling = QgsVectorLayerSimpleLabeling(label)
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        renderer = layer.renderer()
        renderer.symbol().setColor(settings.measureLineColor)
        renderer.symbol().setWidth(0.5)

    # Hack to work around sip bug!
    @staticmethod
    def create() -> 'StylePostProcessor':
        """
        Returns a new instance of the post processor, keeping a reference to the sip
        wrapper so that sip doesn't get confused with the Python subclass and call
        the base wrapper implementation instead... ahhh sip, you wonderful piece of sip
        """
        StylePostProcessor.instance = StylePostProcessor()
        return StylePostProcessor.instance
