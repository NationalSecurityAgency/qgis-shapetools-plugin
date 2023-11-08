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
import traceback

from qgis.core import (
    QgsCoordinateTransform, QgsPointXY, QgsFeature, QgsGeometry,
    QgsProject, QgsWkbTypes, QgsFeatureRequest)

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS

class GeodesicLineDecimateAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to gedesci decimate lines.
    """
    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmPreserveFinalPoint = 'PreserveFinalPoint'
    PrmMinDistance = 'MinDistance'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input line layer'),
                [QgsProcessing.TypeVectorLine])
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmPreserveFinalPoint,
                tr('Preserve final vertex'),
                True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmMinDistance,
                tr('Decimation minimum distance between vertices'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmUnitsOfMeasure,
                tr('Distance units'),
                options=DISTANCE_LABELS,
                defaultValue=1)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        preserve_final_pt = self.parameterAsBool(parameters, self.PrmPreserveFinalPoint, context)
        min_distance = self.parameterAsDouble(parameters, self.PrmMinDistance, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)

        # Get the minimum distance in meters
        min_distance = min_distance * conversionToMeters(units)

        wkbtype = source.wkbType()

        num_bad = 0
        if QgsWkbTypes.geometryType(wkbtype) != QgsWkbTypes.LineGeometry:
            feedback.reportError(tr("Please select a valid line layer."))
            return({})
            
        layercrs = source.sourceCrs()
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, source.fields(), wkbtype, layercrs)

        if layercrs != epsg4326:
            transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
            transfrom4326 = QgsCoordinateTransform(epsg4326, layercrs, QgsProject.instance())

        total = 100.0 / source.featureCount() if source.featureCount() else 0
        iterator = source.getFeatures()
        num_bad = 0
        for cnt, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            geom = feature.geometry()
            # Force the geometry to be in degrees so that we can use the geodesic algorithms
            if layercrs != epsg4326:
                results = geom.transform(transto4326)
                
            num_parts = geom.constGet().partCount()
            # feedback.pushInfo('num_parts {}'.format(num_parts))
            try:
                fline = QgsFeature()
                fgeom = QgsGeometry()
                is_valid = False
                for part in geom.constGet().parts():
                    vertex_cnt = part.vertexCount()
                    # feedback.pushInfo('vertex_cnt {}'.format(vertex_cnt))
                    if vertex_cnt <= 1: # line of 1 or less points is invalid
                        continue
                    pts = []
                    for vcnt, vertex in enumerate(part.vertices()):
                        if vcnt == 0:
                            # This is the first point so we will save it
                            pts.append(vertex)
                            ptLast = vertex
                        else:
                            ptNext = vertex
                            gline = geod.InverseLine(ptLast.y(), ptLast.x(), ptNext.y(), ptNext.x())
                            if gline.s13 >= min_distance:
                                pts.append(ptNext)
                                ptLast = ptNext
                            elif (vcnt == vertex_cnt - 1) and preserve_final_pt:
                                if len(pts) >= 2:
                                    # We have two or more points already on our pts list. Check to see if
                                    # the next to last entry distance and the end point are greater than the 
                                    # the minimum distance. If so replace the last entry with this one else
                                    # because the user has selected to preserve the last end point we will
                                    # accept the end point.
                                    gline = geod.InverseLine(pts[-2].y(), pts[-2].x(), ptNext.y(), ptNext.x())
                                    if gline.s13 >= min_distance:
                                        pts[-1] = ptNext
                                    else:
                                        pts.append(ptNext)
                                elif len(pts) == 1:
                                    # We have only the beginning point of the line and because the user has
                                    # selected that the last point to be preserved we will allow a distance less
                                    # than the minimum so that the line can be preserved.
                                    pts.append(ptNext)
                    if len(pts) > 1: # There must be more than one point to make a valid line
                        fgeom.addPoints(pts, QgsWkbTypes.LineGeometry)
                        is_valid = True
                if is_valid: # Only save the feature if it is valid
                    fline.setAttributes(feature.attributes())
                    if layercrs != epsg4326:
                        fgeom.transform(transfrom4326)
                    fline.setGeometry(fgeom)
                    sink.addFeature(fline)
                else:
                    num_bad += 1
            except Exception:
                '''s = traceback.format_exc()
                feedback.pushInfo(s)'''
                num_bad += 1
            
            feedback.setProgress(int(cnt * total))

        if num_bad > 0:
            feedback.pushInfo(tr("{} out of {} features from input layer were invalid and were skipped.".format(num_bad, source.featureCount())))

        return {self.PrmOutputLayer: dest_id}

    def name(self):
        return 'geodesiclinedecimate'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/geodesicLineDecimate.svg')

    def displayName(self):
        return tr('Geodesic line decimate')

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
        file = os.path.dirname(__file__) + '/doc/GeodesicLineDecimateAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return GeodesicLineDecimateAlgorithm()
