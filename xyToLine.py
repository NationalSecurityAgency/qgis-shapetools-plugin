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
import math
from geographiclib.geodesic import Geodesic

from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsFeature, QgsGeometry, QgsProject, QgsWkbTypes

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from .settings import settings, epsg4326, geod
from .utils import checkIdlCrossings, tr, GCgetPointsOnLine
# import traceback

class XYToLineAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm for creating lines from two coordinates within a record.
    """

    LINE_TYPE = ['Geodesic', 'Great Circle', 'Simple Line']
    PrmInputLayer = 'InputLayer'
    PrmOutputPointLayer = 'OutputPointLayer'
    PrmOutputLineLayer = 'OutputLineLayer'
    PrmInputCRS = 'InputCRS'
    PrmOutputCRS = 'OutputCRS'
    PrmLineType = 'LineType'
    PrmStartUseLayerGeom = 'StartUseLayerGeom'
    PrmStartXField = 'StartXField'
    PrmStartYField = 'StartYField'
    PrmEndUseLayerGeom = 'EndUseLayerGeom'
    PrmEndXField = 'EndXField'
    PrmEndYField = 'EndYField'
    PrmShowStartPoint = 'ShowStartPoint'
    PrmShowEndPoint = 'ShowEndPoint'
    PrmDateLineBreak = 'DateLineBreak'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input layer'),
                [QgsProcessing.TypeFile | QgsProcessing.TypeVectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.PrmInputCRS,
                tr('Input CRS for coordinates within the vector fields'),
                'EPSG:4326')
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.PrmOutputCRS,
                tr('Output layer CRS'),
                'EPSG:4326')
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmLineType,
                tr('Line type'),
                options=self.LINE_TYPE,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmStartUseLayerGeom,
                tr('Use the point geometry for the line starting point'),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmStartXField,
                tr('Starting X Field (lon)'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmStartYField,
                tr('Starting Y Field (lat)'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmEndUseLayerGeom,
                tr('Use the point geometry for the line ending point'),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmEndXField,
                tr('Ending X Field (lon)'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmEndYField,
                tr('Ending Y Field (lat)'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmShowStartPoint,
                tr('Show starting point'),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmShowEndPoint,
                tr('Show ending point'),
                True,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmDateLineBreak,
                tr('Break lines at -180, 180 boundary for better rendering'),
                False,
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLineLayer,
                tr('Output line layer'))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputPointLayer,
                tr('Output point layer'),
                optional=True,
                createByDefault=True)
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        sourceCrs = self.parameterAsCrs(parameters, self.PrmInputCRS, context)
        sinkCrs = self.parameterAsCrs(parameters, self.PrmOutputCRS, context)
        lineType = self.parameterAsInt(parameters, self.PrmLineType, context)
        startUseGeom = self.parameterAsBool(parameters, self.PrmStartUseLayerGeom, context)
        startXcol = self.parameterAsString(parameters, self.PrmStartXField, context)
        startYcol = self.parameterAsString(parameters, self.PrmStartYField, context)
        endUseGeom = self.parameterAsBool(parameters, self.PrmEndUseLayerGeom, context)
        endXcol = self.parameterAsString(parameters, self.PrmEndXField, context)
        endYcol = self.parameterAsString(parameters, self.PrmEndYField, context)
        showStart = self.parameterAsBool(parameters, self.PrmShowStartPoint, context)
        showEnd = self.parameterAsBool(parameters, self.PrmShowEndPoint, context)
        dateLine = self.parameterAsBool(parameters, self.PrmDateLineBreak, context)

        if startUseGeom and endUseGeom:
            msg = tr('The layer geometry cannot be used for both the starting and ending points.')
            raise QgsProcessingException(msg)

        if (startUseGeom or endUseGeom) and (source.wkbType() != QgsWkbTypes.Point):
            msg = tr('In order to use the layer geometry for the start or ending points, the input layer must be of type Point')
            raise QgsProcessingException(msg)

        if (not startUseGeom and (not startXcol or not startYcol)) or (not endUseGeom and (not endXcol or not endYcol)):
            msg = tr('Please select valid starting and ending point columns')
            raise QgsProcessingException(msg)

        if dateLine and lineType <= 1:
            isMultiPart = True
        else:
            isMultiPart = False

        if isMultiPart:
            (lineSink, lineDest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLineLayer, context, source.fields(),
                QgsWkbTypes.MultiLineString, sinkCrs)
        else:
            (lineSink, lineDest_id) = self.parameterAsSink(
                parameters, self.PrmOutputLineLayer, context, source.fields(),
                QgsWkbTypes.LineString, sinkCrs)

        skip_pt = True if self.PrmOutputPointLayer not in parameters or parameters[self.PrmOutputPointLayer] is None else False
        if (showStart or showEnd) and not skip_pt:
            (ptSink, ptDest_id) = self.parameterAsSink(
                parameters, self.PrmOutputPointLayer, context, source.fields(),
                QgsWkbTypes.Point, sinkCrs)
        else:
            if showStart or showEnd:
                feedback.pushInfo(tr('Output point layer was set to [skip output]. No point layer will be generated.'))
                showStart = False
                showEnd = False
            else:
                feedback.pushInfo(tr('No beginning or ending points were selected so a point layer will not be generated.'))

        # Set up CRS transformations
        geomCrs = source.sourceCrs()
        if (startUseGeom or endUseGeom) and (geomCrs != epsg4326):
            geomTo4326 = QgsCoordinateTransform(geomCrs, epsg4326, QgsProject.instance())
        if sourceCrs != epsg4326:
            sourceTo4326 = QgsCoordinateTransform(sourceCrs, epsg4326, QgsProject.instance())
        if sinkCrs != epsg4326:
            toSinkCrs = QgsCoordinateTransform(epsg4326, sinkCrs, QgsProject.instance())

        featureCount = source.featureCount()
        total = 100.0 / featureCount if featureCount else 0
        numBad = 0
        maxseglen = settings.maxSegLength * 1000.0
        maxSegments = settings.maxSegments
        beginning_ending_same = False

        iterator = source.getFeatures()
        for cnt, feature in enumerate(iterator):
            if (cnt % 100 == 0) and feedback.isCanceled():
                break
            try:
                if startUseGeom:
                    ptStart = feature.geometry().asPoint()
                    if geomCrs != epsg4326:
                        ptStart = geomTo4326.transform(ptStart)
                else:
                    ptStart = QgsPointXY(float(feature[startXcol]), float(feature[startYcol]))
                    if sourceCrs != epsg4326:
                        ptStart = sourceTo4326.transform(ptStart)
                if endUseGeom:
                    ptEnd = feature.geometry().asPoint()
                    if geomCrs != epsg4326:
                        ptEnd = geomTo4326.transform(ptEnd)
                else:
                    ptEnd = QgsPointXY(float(feature[endXcol]), float(feature[endYcol]))
                    if sourceCrs != epsg4326:
                        ptEnd = sourceTo4326.transform(ptEnd)
                pts = [ptStart]
                if ptStart == ptEnd:  # We cannot have a line that begins and ends at the same point
                    numBad += 1
                    beginning_ending_same = True
                    continue

                if lineType == 0:  # Geodesic
                    gline = geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                    if gline.s13 > maxseglen:
                        n = int(math.ceil(gline.s13 / maxseglen))
                        if n > maxSegments:
                            n = maxSegments
                        seglen = gline.s13 / n
                        for i in range(1, n + 1):
                            s = seglen * i
                            g = gline.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                            pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    else:  # The line segment is too short so it is from ptStart to ptEnd
                        pts.append(ptEnd)
                elif lineType == 1:  # Great circle
                    pts = GCgetPointsOnLine(
                        ptStart.y(), ptStart.x(),
                        ptEnd.y(), ptEnd.x(),
                        settings.maxSegLength * 1000.0,  # Put it in meters
                        settings.maxSegments + 1)
                else:  # Simple line
                    pts.append(ptEnd)
                f = QgsFeature()
                if isMultiPart:
                    outseg = checkIdlCrossings(pts)
                    if sinkCrs != epsg4326:  # Convert each point to the output CRS
                        for y in range(len(outseg)):
                            for x, pt in enumerate(outseg[y]):
                                outseg[y][x] = toSinkCrs.transform(pt)
                    f.setGeometry(QgsGeometry.fromMultiPolylineXY(outseg))
                else:
                    if sinkCrs != epsg4326:  # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = toSinkCrs.transform(pt)
                    f.setGeometry(QgsGeometry.fromPolylineXY(pts))
                f.setAttributes(feature.attributes())
                lineSink.addFeature(f)

                if showStart:
                    f = QgsFeature()
                    if sinkCrs != epsg4326:
                        f.setGeometry(QgsGeometry.fromPointXY(toSinkCrs.transform(ptStart)))
                    else:
                        f.setGeometry(QgsGeometry.fromPointXY(ptStart))
                    f.setAttributes(feature.attributes())
                    ptSink.addFeature(f)
                if showEnd:
                    f = QgsFeature()
                    if sinkCrs != epsg4326:
                        f.setGeometry(QgsGeometry.fromPointXY(toSinkCrs.transform(ptEnd)))
                    else:
                        f.setGeometry(QgsGeometry.fromPointXY(ptEnd))
                    f.setAttributes(feature.attributes())
                    ptSink.addFeature(f)
            except Exception:
                numBad += 1
                '''s = traceback.format_exc()
                feedback.pushInfo(s)'''

            if cnt % 100 == 0:  # Set the progress after every 100 entries
                feedback.setProgress(int(cnt * total))

        if numBad > 0:
            if beginning_ending_same:
                feedback.pushInfo(tr("One of more features had the same beginning and ending coordinate and are invalid."))
            feedback.pushInfo(tr("{} out of {} features from the input layer were invalid and were ignored.".format(numBad, featureCount)))

        r = {}
        r[self.PrmOutputLineLayer] = lineDest_id
        if showStart or showEnd:
            r[self.PrmOutputPointLayer] = ptDest_id

        return (r)

    def name(self):
        return 'xy2line'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/xyline.svg')

    def displayName(self):
        return tr('XY to line')

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
        file = os.path.dirname(__file__) + '/doc/XYtoLineAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return XYToLineAlgorithm()
