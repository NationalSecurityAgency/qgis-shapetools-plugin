import os
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsPoint, QgsFeature, QgsGeometry, QgsField, QgsFields,
    QgsProject, QgsWkbTypes, QgsCoordinateTransform)
    
from qgis.core import (QgsProcessing,
    QgsFeatureSink,
    QgsProcessingAlgorithm,
    QgsProcessingParameterExtent,
    QgsProcessingParameterPoint,
    QgsProcessingParameterCrs,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QVariant, QUrl

from .settings import settings, epsg4326, geod
from .utils import tr, conversionToMeters, DISTANCE_LABELS

GRID_TYPE=[tr("Point"),tr("Line"),tr("Rectangle (Polygon)")]
GRID_ORIGIN=[tr("Bottom Left"), tr("Top Left"), tr("Top Right"), tr("Bottom Right")]
PRIMARY_AXIS=[tr("Y (Latitude)"), tr("X (Longitude)")]

class GeodesicGridAlgorithm(QgsProcessingAlgorithm):
    """
    Algorithm to create a donut shape.
    """

    PrmOutputLayer = 'OutputLayer'
    PrmGridType = 'GridType'
    PrmGridExtent = 'GridExtent'
    PrmGridStartingPoint = 'GridStartingPoint'
    PrmGridSpacingX = 'GridSpacingX'
    PrmGridSpacingY = 'GridSpacingY'
    PrmGridWidth = 'GridWidth'
    PrmGridHeight = 'GridHeight'
    PrmGridOrigin = 'GridOrigin'
    PrmGridMeasurementUnits = 'GridMeasurementUnits'
    PrmGridCrs = 'GridCrs'
    PrmPrimaryAxis = 'PrimaryAxis'

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterExtent(
                self.PrmGridExtent,
                tr('Either select this grid extent or the starting point below'),
                optional=True)
        )
        self.addParameter(
            QgsProcessingParameterPoint(
                self.PrmGridStartingPoint,
                tr('Grid starting point (uses grid width & height)'),
                optional=True)
        )
        self.addParameter(QgsProcessingParameterCrs(
            self.PrmGridCrs,
            tr('Grid CRS'),
            'ProjectCrs',
            optional=False))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmGridType,
                tr('Grid type'),
                options=GRID_TYPE,
                defaultValue=1,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmGridOrigin,
                tr('Grid origin'),
                options=GRID_ORIGIN,
                defaultValue=0,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmPrimaryAxis,
                tr('Primary axis'),
                options=PRIMARY_AXIS,
                defaultValue=1,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmGridWidth,
                tr('Grid width (Not used when selecting the grid extent)'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=4,
                minValue=1,
                optional=False)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmGridHeight,
                tr('Grid height (Not used when selecting the grid extent)'),
                QgsProcessingParameterNumber.Integer,
                defaultValue=4,
                minValue=1,
                optional=False)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmGridSpacingX,
                tr('Horizontal spacing'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10,
                optional=False)
            )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PrmGridSpacingY,
                tr('Vertical spacing'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10,
                optional=False)
            )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PrmGridMeasurementUnits,
                tr('Grid units of measure'),
                options=DISTANCE_LABELS,
                defaultValue=1,
                optional=False)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.PrmOutputLayer,
                tr('Output layer'))
            )
    
    def processAlgorithm(self, parameters, context, feedback):
        extent          = self.parameterAsExtent(parameters, self.PrmGridExtent, context)
        extent_crs      = self.parameterAsExtentCrs(parameters, self.PrmGridExtent, context)
        start_point_def = self.parameterAsPoint(parameters, self.PrmGridStartingPoint, context)
        start_point_crs = self.parameterAsPointCrs(parameters, self.PrmGridStartingPoint, context)
        output_crs      = self.parameterAsCrs(parameters, self.PrmGridCrs, context)
        grid_type       = self.parameterAsInt(parameters, self.PrmGridType, context)
        primary_axis    = self.parameterAsInt(parameters, self.PrmPrimaryAxis, context)
        grid_origin     = self.parameterAsInt(parameters, self.PrmGridOrigin, context)
        grid_width      = self.parameterAsInt(parameters, self.PrmGridWidth, context)
        grid_height     = self.parameterAsInt(parameters, self.PrmGridHeight, context)
        spacing_x       = self.parameterAsDouble(parameters, self.PrmGridSpacingX, context)
        spacing_y       = self.parameterAsDouble(parameters, self.PrmGridSpacingY, context)
        units           = self.parameterAsInt(parameters, self.PrmGridMeasurementUnits, context)
        
        measureFactor = conversionToMeters(units)

        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('xindex', QVariant.Int))
        fields.append(QgsField('yindex', QVariant.Int))
        fields.append(QgsField('xdist', QVariant.Double))
        fields.append(QgsField('ydist', QVariant.Double))
        ''' FIELDS
            POINT
            id
            xindex
            yindex
            xdist
            ydist
            x
            y
            
            LINE & POLYGON
            id
            xindex
            yindex
            xdist
            ydist
            xstart
            ystart
            xend
            yend
        '''
        
        if grid_type == 0: # point
            fields.append(QgsField('x', QVariant.Double))
            fields.append(QgsField('y', QVariant.Double))
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Point, output_crs)
        elif grid_type == 1: # line
            fields.append(QgsField('xstart', QVariant.Double))
            fields.append(QgsField('ystart', QVariant.Double))
            fields.append(QgsField('xend', QVariant.Double))
            fields.append(QgsField('yend', QVariant.Double))
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fields,
                QgsWkbTypes.LineString, output_crs)
        else: # polygon
            fields.append(QgsField('xstart', QVariant.Double))
            fields.append(QgsField('ystart', QVariant.Double))
            fields.append(QgsField('xend', QVariant.Double))
            fields.append(QgsField('yend', QVariant.Double))
            (sink, dest_id) = self.parameterAsSink(parameters,
                self.PrmOutputLayer, context, fields,
                QgsWkbTypes.Polygon, output_crs)
                
        # Calculate the grid size
        if not extent.isNull():
            if grid_origin == 0: # Bottom left
                
            
           
        feedback.pushInfo("extent {}".format(extent.isNull()))
        feedback.pushInfo("start_point {}".format(start_point))
        return {self.PrmOutputLayer: dest_id}
        
    def name(self):
        return 'geodesicgrid'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__),'images/grid.png'))
    
    def displayName(self):
        return tr('Create gedesic grid')
    
    def group(self):
        return tr('Geodesic vector creation')
        
    def groupId(self):
        return 'vectorcreation'
        
    def helpUrl(self):
        file = os.path.dirname(__file__)+'/index.html'
        if not os.path.exists(file):
            return ''
        return QUrl.fromLocalFile(file).toString(QUrl.FullyEncoded)
        
    def createInstance(self):
        return GeodesicGridAlgorithm()

