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
    QgsPointXY, QgsGeometry, QgsField, QgsPropertyDefinition,
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
# import traceback

SHAPE_TYPE = [tr("Polygon"), tr("Line")]

class CreateGearAlgorithm(QgsProcessingFeatureBasedAlgorithm):
    """
    Algorithm to create a star shape.
    """

    PrmShapeType = 'ShapeType'
    PrmGearTeeth = 'GearTeeth'
    PrmOuterRadius = 'OuterRadius'
    PrmInnerRadius = 'InnerRadius'
    PrmStartingAngle = 'StartingAngle'
    PrmUnitsOfMeasure = 'UnitsOfMeasure'
    PrmTeethPercent = 'TeethPercent'
    PrmSlotPercent = 'SlotPercent'

    def createInstance(self):
        return CreateGearAlgorithm()

    def name(self):
        return 'creategear'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'images/gear.png'))

    def displayName(self):
        return tr('Create gear')

    def group(self):
        return tr('Geodesic shapes')

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
        param = QgsProcessingParameterNumber(
            self.PrmGearTeeth,
            tr('Number of teeth'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=6,
            minValue=3,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmGearTeeth,
            tr('Number of teeth'),
            QgsPropertyDefinition.Integer))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmTeethPercent,
            tr('Teeth width (percent)'),
            QgsProcessingParameterNumber.Double,
            defaultValue=40.0,
            minValue=0,
            maxValue=100,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmTeethPercent,
            tr('Teeth width (percent)'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmSlotPercent,
            tr('Slot width (percent)'),
            QgsProcessingParameterNumber.Double,
            defaultValue=40.0,
            minValue=0,
            maxValue=100,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmSlotPercent,
            tr('Slot width (percent)'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=20.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmOuterRadius,
            tr('Outer radius'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsProcessingParameterNumber.Double,
            defaultValue=14.0,
            minValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmInnerRadius,
            tr('Inner radius'),
            QgsPropertyDefinition.Double))
        param.setDynamicLayerParameterName('INPUT')
        self.addParameter(param)

        param = QgsProcessingParameterNumber(
            self.PrmStartingAngle,
            tr('Starting angle'),
            QgsProcessingParameterNumber.Double,
            defaultValue=0,
            optional=False)
        param.setIsDynamic(True)
        param.setDynamicPropertyDefinition(QgsPropertyDefinition(
            self.PrmStartingAngle,
            tr('Starting angle'),
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

    def prepareAlgorithm(self, parameters, context, feedback):
        self.shape_type = self.parameterAsInt(parameters, self.PrmShapeType, context)
        self.outer_radius = self.parameterAsDouble(parameters, self.PrmOuterRadius, context)
        self.outer_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmOuterRadius)
        if self.outer_radius_dyn:
            self.outer_radius_property = parameters[self.PrmOuterRadius]
        self.inner_radius = self.parameterAsDouble(parameters, self.PrmInnerRadius, context)
        self.inner_radius_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmInnerRadius)
        if self.inner_radius_dyn:
            self.inner_radius_property = parameters[self.PrmInnerRadius]
        self.start_angle = self.parameterAsDouble(parameters, self.PrmStartingAngle, context)
        self.start_angle_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmStartingAngle)
        if self.start_angle_dyn:
            self.start_angle_property = parameters[self.PrmStartingAngle]
        self.num_teeth = self.parameterAsInt(parameters, self.PrmGearTeeth, context)
        if self.num_teeth < 3:
            feedback.reportError('There must be at least 3 teeth for a gear')
            return False
        self.num_teeth_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmGearTeeth)
        if self.num_teeth_dyn:
            self.num_teeth_property = parameters[self.PrmGearTeeth]

        self.teeth_percent = self.parameterAsDouble(parameters, self.PrmTeethPercent, context)
        self.teeth_percent_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmTeethPercent)
        if self.teeth_percent_dyn:
            self.teeth_percent_property = parameters[self.PrmTeethPercent]
        
        self.slot_percent = self.parameterAsDouble(parameters, self.PrmSlotPercent, context)
        self.slot_percent_dyn = QgsProcessingParameters.isDynamic(parameters, self.PrmSlotPercent)
        if self.slot_percent_dyn:
            self.slot_percent_property = parameters[self.PrmSlotPercent]
        
        units = self.parameterAsInt(parameters, self.PrmUnitsOfMeasure, context)

        self.measureFactor = conversionToMeters(units)
        self.inner_radius_converted = self.inner_radius * self.measureFactor
        self.outer_radius_converted = self.outer_radius * self.measureFactor

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

            if self.outer_radius_dyn:
                oradius, e = self.outer_radius_property.valueAsDouble(context.expressionContext(), self.outer_radius)
                if not e or oradius < 0:
                    self.num_bad += 1
                    return []
                oradius *= self.measureFactor
            else:
                oradius = self.outer_radius_converted
            if self.inner_radius_dyn:
                iradius, e = self.inner_radius_property.valueAsDouble(context.expressionContext(), self.inner_radius)
                if not e or iradius < 0:
                    self.num_bad += 1
                    return []
                iradius *= self.measureFactor
            else:
                iradius = self.inner_radius_converted
            if self.start_angle_dyn:
                sangle, e = self.start_angle_property.valueAsDouble(context.expressionContext(), self.start_angle)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                sangle = self.start_angle
            if self.teeth_percent_dyn:
                teeth_percent, e = self.teeth_percent_property.valueAsDouble(context.expressionContext(), self.teeth_percent)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                teeth_percent = self.teeth_percent
            if self.slot_percent_dyn:
                slot_percent, e = self.slot_percent_property.valueAsDouble(context.expressionContext(), self.slot_percent)
                if not e:
                    self.num_bad += 1
                    return []
            else:
                slot_percent = self.slot_percent
            if self.num_teeth_dyn:
                num_teeth, e = self.num_teeth_property.valueAsInt(context.expressionContext(), self.num_teeth)
                if not e or num_teeth < 3:
                    self.num_bad += 1
                    return []
            else:
                num_teeth = self.num_teeth
            half = (360.0 / num_teeth) / 2
            teeth_half = (360.0 / num_teeth) * teeth_percent / 200
            slot_half = (360.0 / num_teeth) * slot_percent / 200
            
            i = 0
            while i < num_teeth:
                angle = (i * 360.0 / num_teeth) + sangle
                g = geod.Direct(pt.y(), pt.x(), angle - teeth_half, oradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                g = geod.Direct(pt.y(), pt.x(), angle + teeth_half, oradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += half
                g = geod.Direct(pt.y(), pt.x(), angle - slot_half, iradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                g = geod.Direct(pt.y(), pt.x(), angle + slot_half, iradius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                i += 1

            makeIdlCrossingsPositive(pts)
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.toSinkCrs:
                for x, ptout in enumerate(pts):
                    pts[x] = self.toSinkCrs.transform(ptout)
            pts.append(pts[0])
            if self.shape_type == 0:
                feature.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                feature.setGeometry(QgsGeometry.fromPolylineXY(pts))
        except Exception:
            self.num_bad += 1
            return []
        return [feature]

    def postProcessAlgorithm(self, context, feedback):
        if self.num_bad:
            feedback.pushInfo(tr("{} out of {} features had invalid parameters and were ignored.".format(self.num_bad, self.total_features)))
        return {}
