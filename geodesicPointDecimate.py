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
# import traceback

from qgis.core import (
    QgsCoordinateTransform, QgsPointXY, QgsFeature, QgsGeometry,
    QgsProject, QgsWkbTypes, QgsFeatureRequest)

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS

class GeodesicPointDecimateAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to densify lines and polygons using geodesic calculations.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    PrmInputLayer = 'InputLayer'
    PrmOutputLayer = 'OutputLayer'
    PrmPreserveFinalPoint = 'PreserveFinalPoint'
    PrmDecimateByDistance = 'DecimateByDistance'
    PrmDecimateByTime = 'DecimateByTime'
    PrmMinDistance = 'MinDistance'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmOrderField = 'OrderField'
    PrmGroupField = 'GroupField'
    PrmTimeField = 'TimeField'
    PrmMinTime = 'MinTime'
    PrmTimeUnits = 'TimeUnits'
    PrmTwoConditionResponnse = 'TwoConditionResponnse'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.PrmInputLayer,
                tr('Input point layer'),
                [QgsProcessing.TypeVectorPoint])
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmOrderField,
                tr('Point order field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmGroupField,
                tr('Point grouuping field'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.Any,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmPreserveFinalPoint,
                tr('Preserve final point'),
                True)
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.PrmDecimateByDistance,
                tr('Remove points that are less than the minimum distance'),
                True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmMinDistance,
                tr('Minimum distance between points'),
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
            QgsProcessingParameterBoolean(
                self.PrmDecimateByTime,
                tr('Remove points by minumum time interval'),
                False)
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.PrmTimeField,
                tr('Time field (Must be a DateTime field)'),
                parentLayerParameterName=self.PrmInputLayer,
                type=QgsProcessingParameterField.DateTime,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmMinTime,
                tr('Minimum time between points'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmTimeUnits,
                tr('Time units'),
                options=[tr('Seconds'),tr('Minutes'),tr('Hours'),tr('Days')],
                defaultValue=1)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmTwoConditionResponnse,
                tr('When both decimate by distance and time are selected, preserve points if'),
                options=[tr('Distance AND time requrements are met'),tr('Distance OR time requirement is met')],
                defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.PrmInputLayer, context)
        decimate_by_distance = self.parameterAsBool(parameters, self.PrmDecimateByDistance, context)
        decimate_by_time = self.parameterAsBool(parameters, self.PrmDecimateByTime, context)
        preserve_final_pt = self.parameterAsBool(parameters, self.PrmPreserveFinalPoint, context)
        min_distance = self.parameterAsDouble(parameters, self.PrmMinDistance, context)
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)
        min_time = self.parameterAsDouble(parameters, self.PrmMinTime, context)
        time_units = self.parameterAsInt(parameters, self.PrmTimeUnits, context)
        is_or_condition = self.parameterAsInt(parameters, self.PrmTwoConditionResponnse, context)
        fields = source.fields()

        if self.PrmTimeField not in parameters or parameters[self.PrmTimeField] is None or parameters[self.PrmTimeField] == '':
            time_field = None
            time_idx = None
        else:
            time_field = self.parameterAsString(parameters, self.PrmTimeField, context)
            time_idx = fields.indexOf(time_field)

        if decimate_by_time and time_field is None:
            msg = tr('Please select a DateTime field when decimating by time')
            feedback.reportError(msg)
            raise QgsProcessingException(msg)

        if self.PrmOrderField not in parameters or parameters[self.PrmOrderField] is None or parameters[self.PrmOrderField] == '':
            order_field = None
        else:
            order_field = self.parameterAsString(parameters, self.PrmOrderField, context)

        if self.PrmGroupField not in parameters or parameters[self.PrmGroupField] is None or parameters[self.PrmGroupField] == '':
            group_field = None
        else:
            group_field = self.parameterAsString(parameters, self.PrmGroupField, context)

        wkbtype = source.wkbType()

        if QgsWkbTypes.isMultiType(wkbtype):
            msg = tr('Only supports single part Point geometry')
            feedback.reportError(msg)
            raise QgsProcessingException(msg)

        layercrs = source.sourceCrs()

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.PrmOutputLayer, context, fields, wkbtype, layercrs)

        if layercrs != epsg4326:
            transto4326 = QgsCoordinateTransform(layercrs, epsg4326, QgsProject.instance())
        
        num_pts = source.featureCount()
        total = 100.0 / num_pts if num_pts else 0
        min_time_s = self.convert_time_to_s(min_time, time_units)
        min_distance = min_distance * conversionToMeters(units)
        if group_field:
            grp_indx = fields.indexOf(group_field)
            groups = source.uniqueValues(grp_indx)
            request = QgsFeatureRequest()
            if order_field:
                request.addOrderBy(order_field)
            index = 0
            for group in groups:
                filter = '"{}" = \'{}\''.format(group_field, group)
                request.setFilterExpression( filter )
                iterator = source.getFeatures(request)
                last_decimated = False
                first_feature = True
                for feature in iterator:
                    index += 1
                    if feedback.isCanceled():
                        break
                    pt = feature.geometry().asPoint()
                    if layercrs != epsg4326:  # Convert to 4326
                        pt4326 = transto4326.transform(pt)
                    else:
                        pt4326 = pt

                    if first_feature:
                        first_feature = False
                        sink.addFeature(feature)
                        pt_last = pt4326
                        if decimate_by_time:
                            last_time = feature[time_idx]
                    else:
                        d_keep = True
                        t_keep = True
                        if decimate_by_distance:
                            gline = geod.InverseLine(pt_last.y(), pt_last.x(), pt4326.y(), pt4326.x())
                            if gline.s13 < min_distance:
                                d_keep = False
                        if decimate_by_time:
                            cur_time = feature[time_idx]
                            try:
                                diff = abs(cur_time.toMSecsSinceEpoch() - last_time.toMSecsSinceEpoch()) / 1000.0
                                if diff < min_time_s:
                                    t_keep = False
                            except Exception:
                                pass

                        if is_or_condition and (d_keep or t_keep):
                            if decimate_by_distance:
                                pt_last = pt4326
                            if decimate_by_time:
                                last_time = cur_time
                            last_decimated = False
                            sink.addFeature(feature)
                        elif d_keep and t_keep:
                            if decimate_by_distance:
                                pt_last = pt4326
                            if decimate_by_time:
                                last_time = cur_time
                            last_decimated = False
                            sink.addFeature(feature)
                        else:
                            last_decimated = True

                    if index % 100:
                        feedback.setProgress(int(index * total))

                if preserve_final_pt and last_decimated:
                    # feature contains the last item from the above for loop which is valid in Python
                    sink.addFeature(feature)
        else:
            if order_field:
                request = QgsFeatureRequest()
                request.addOrderBy(order_field)
                iterator = source.getFeatures(request)
            else:
                iterator = source.getFeatures()
            for cnt, feature in enumerate(iterator):
                if feedback.isCanceled():
                    break
                pt = feature.geometry().asPoint()
                if layercrs != epsg4326:  # Convert to 4326
                    pt4326 = transto4326.transform(pt)
                else:
                    pt4326 = pt
                if cnt == 0: # This is the first point so it is saved
                    sink.addFeature(feature)
                    pt_last = pt4326
                    if decimate_by_time:
                        last_time = feature[time_idx]
                else:
                    d_keep = True
                    t_keep = True
                    if decimate_by_distance:
                        gline = geod.InverseLine(pt_last.y(), pt_last.x(), pt4326.y(), pt4326.x())
                        if gline.s13 < min_distance:
                            d_keep = False
                    if decimate_by_time:
                        cur_time = feature[time_idx]
                        try:
                            diff = abs(cur_time.toMSecsSinceEpoch() - last_time.toMSecsSinceEpoch()) / 1000.0
                            if diff < min_time_s:
                                t_keep = False
                        except Exception:
                            pass
                    if is_or_condition and (d_keep or t_keep):
                        if decimate_by_distance:
                            pt_last = pt4326
                        if decimate_by_time:
                            last_time = cur_time
                        sink.addFeature(feature)
                    elif d_keep and t_keep:
                        if decimate_by_distance:
                            pt_last = pt4326
                        if decimate_by_time:
                            last_time = cur_time
                        sink.addFeature(feature)
                    elif preserve_final_pt and (cnt == num_pts - 1):
                        sink.addFeature(feature)
                if cnt % 100:
                    feedback.setProgress(int(cnt * total))

        return {self.PrmOutputLayer: dest_id}

    def convert_time_to_s(self, time, units):
        if units == 0: # seconds
            pass
        elif units == 1:
            time = time * 60.0 # 60 seconds per minute
        elif units == 2:
            time = time * 3600.0 # hours - 60 * 60
        else:
            time = time * 86400.0 # days - 24 * 60 * 60
        return(time)

    def name(self):
        return 'geodesicpointdecimate'

    def icon(self):
        return QIcon(os.path.dirname(__file__) + '/images/geodesicPointDecimate.svg')

    def displayName(self):
        return tr('Geodesic point decimate')

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
        file = os.path.dirname(__file__) + '/doc/GeodesicPointDecimateAlgorithm.help'
        if not os.path.exists(file):
            return ''
        with open(file) as helpf:
            help = helpf.read()
        return help

    def createInstance(self):
        return GeodesicPointDecimateAlgorithm()
