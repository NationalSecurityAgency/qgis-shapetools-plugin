import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import *
from qgis.gui import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from LatLon import LatLon



FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'vector2Shape.ui'))

DISTANCE_MEASURE=["Kilometers","Meters","Nautical Miles","Miles","Feet"]
class Vector2ShapeWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent, settings):
        super(Vector2ShapeWidget, self).__init__(parent)
        self.setupUi(self)
        self.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mMapLayerComboBox.layerChanged.connect(self.findFields)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.iface = iface
        self.settings = settings
        self.unitOfAxisComboBox.addItems(DISTANCE_MEASURE)
        self.unitOfDistanceComboBox.addItems(DISTANCE_MEASURE)
        self.distUnitsPolyComboBox.addItems(DISTANCE_MEASURE)
        self.unitsStarComboBox.addItems(DISTANCE_MEASURE)
        self.polygonLayer = None
        self.geod = Geodesic.WGS84

    def apply(self):
        '''process the data'''
        tab = self.tabWidget.currentIndex()
        layer = self.mMapLayerComboBox.currentLayer()
        outname = self.layerNameLineEdit.text()
        if not layer:
            self.showErrorMessage("No valid layer to process")
            return
        
        # We need to make sure all the points in the layer are transformed to EPSG:4326
        layerCRS = layer.crs()
        epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        self.transform = QgsCoordinateTransform(layerCRS, epsg4326)
        
        if tab == 0: # Ellipse
            self.processEllipse(layer, outname,
                self.semiMajorComboBox.currentIndex()-1,
                self.semiMinorComboBox.currentIndex()-1,
                self.orientationComboBox.currentIndex()-1,
                self.unitOfAxisComboBox.currentIndex(),
                self.defSemiMajorSpinBox.value(),
                self.defSemiMinorSpinBox.value(),
                self.defOrientationSpinBox.value())
        elif tab == 1: # LOB
            self.processLOB(layer, outname,
                self.bearingComboBox.currentIndex()-1,
                self.distanceComboBox.currentIndex()-1,
                self.unitOfDistanceComboBox.currentIndex(),
                self.defaultBearingSpinBox.value(),
                self.defaultDistanceSpinBox.value())
        elif tab == 2: # Polygon
            try:
                distance = float(self.distPolyLineEdit.text())
            except:
                self.showErrorMessage("Invalid Distance. Fix and try again")
                return
            self.processPoly(layer, outname,
                self.sidesPolyComboBox.currentIndex()-1, #number of sides column
                self.anglePolyComboBox.currentIndex()-1, #starting angle column
                self.distPolyComboBox.currentIndex()-1, # distance column
                self.sidesPolySpinBox.value(), # default sides
                self.anglePolySpinBox.value(), # default starting angle
                distance,
                self.distUnitsPolyComboBox.currentIndex())
        elif tab == 3: # Star
            self.processStar(layer, outname,
                self.starPointsSpinBox.value(),
                self.starStartAngleSpinBox.value(),
                self.innerStarRadiusSpinBox.value(),
                self.outerStarRadiusSpinBox.value(),
                self.unitsStarComboBox.currentIndex())
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(Vector2ShapeWidget, self).showEvent(event)
        self.findFields()
        
    def findFields(self):
        if not self.isVisible():
            return
        layer = self.mMapLayerComboBox.currentLayer()
        if not layer:
            self.clearLayerFields()
        else:
            header = [u"[ Use Default ]"]
            fields = layer.pendingFields()
            for field in fields.toList():
                # force it to be lower case - makes matching easier
                name = field.name()
                header.append(name)
            self.configureLayerFields(header)

    def configureLayerFields(self, header):
        if not self.settings.guessNames:
            self.clearLayerFields()
        self.semiMajorComboBox.addItems(header)
        self.semiMinorComboBox.addItems(header)
        self.orientationComboBox.addItems(header)
        
        self.bearingComboBox.addItems(header)
        self.distanceComboBox.addItems(header)
        
        self.sidesPolyComboBox.addItems(header)
        self.anglePolyComboBox.addItems(header)
        self.distPolyComboBox.addItems(header)
        
        if not self.settings.guessNames:
            return
        
        orientcol = semimajorcol = semiminorcol = -1
        bearingcol = distancecol = -1
        for x, item in enumerate(header):
            # Skip the first entry
            if x == 0:
                continue
            lcitem = item.lower()
            if lcitem.startswith('orient'):
                orientcol = x
            elif bool(re.match('semi.*maj', lcitem)):
                semimajorcol = x
            elif bool(re.match('semi.*min', lcitem)):
                semiminorcol = x
            elif bool(re.search('bearing', lcitem)):
                bearingcol = x
            elif bool(re.match('dist', lcitem)):
                distancecol = x
                
        if orientcol != -1:
            self.orientationComboBox.setCurrentIndex(orientcol)
        if semimajorcol != -1:
            self.semiMajorComboBox.setCurrentIndex(semimajorcol)
        if semiminorcol != -1:
            self.semiMinorComboBox.setCurrentIndex(semiminorcol)
        if bearingcol != -1:
            self.bearingComboBox.setCurrentIndex(bearingcol)
        if distancecol != -1:
            self.distanceComboBox.setCurrentIndex(distancecol)
        
    def clearLayerFields(self):
        self.semiMajorComboBox.clear()
        self.semiMinorComboBox.clear()
        self.orientationComboBox.clear()
        self.bearingComboBox.clear()
        self.distanceComboBox.clear()
        self.sidesPolyComboBox.clear()
        self.anglePolyComboBox.clear()
        self.distPolyComboBox.clear()
            
    def showErrorMessage(self, message):
        self.iface.messageBar().pushMessage("", message, level=QgsMessageBar.WARNING, duration=3)
        
    def processEllipse(self, layer, outname, semimajorcol, semiminorcol, orientcol, unitOfMeasure, defSemiMajor, defSemiMinor, defOrientation):
        measureFactor = 1.0
        # The ellipse calculation is done in Nautical Miles. This converts
        # the semi-major and minor axis to nautical miles
        if unitOfMeasure == 2: # Nautical Miles
            measureFactor = 1.0
        elif unitOfMeasure == 0: # Kilometers
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Meters, QGis.NauticalMiles)*1000.0
        elif unitOfMeasure == 1: # Meters
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Meters, QGis.NauticalMiles)
        elif unitOfMeasure == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.NauticalMiles)*5280.0
        elif unitOfMeasure == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.NauticalMiles)
        
        fields = layer.pendingFields()
        
        self.polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = self.polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        self.polygonLayer.updateFields()
        
        iter = layer.getFeatures()
        num_features = 0
        num_good = 0
        for feature in iter:
            num_features += 1
            try:
                if semimajorcol != -1:
                    semi_major = float(feature[semimajorcol])
                else:
                    semi_major = defSemiMajor
                if semiminorcol != -1:
                    semi_minor = float(feature[semiminorcol])
                else:
                    semi_minor = defSemiMinor
                if orientcol != -1:
                    orient = float(feature[orientcol])
                else:
                    orient = defOrientation
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                geom = LatLon.getEllipseCoords(pt.y(), pt.x(), semi_major*measureFactor,
                    semi_minor*measureFactor, orient)
                featureout = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolygon([geom]))
                featureout.setAttributes(feature.attributes())
                ppolygon.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                pass
        self.polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(self.polygonLayer)
        self.iface.messageBar().pushMessage("", "{} Ellipses created from {} records".format(num_good, num_features), level=QgsMessageBar.INFO, duration=3)
        
    def processLOB(self, layer, outname, bearingcol, distcol, unitOfDist, defaultBearing, defaultDist):
        '''Process each layer point and create a new line layer with the associated bearings'''
        if unitOfDist == 2: # Nautical Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.NauticalMiles, QGis.Meters)
        elif unitOfDist == 0: # Kilometers
            measureFactor = 1000.0
        elif unitOfDist == 1: # Meters
            measureFactor = 1.0
        elif unitOfDist == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)*5280.0
        elif unitOfDist == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)
            
        defaultDist *= measureFactor
        seglen = self.settings.maxSegLength*1000.0 # Needs to be in meters
        
        fields = layer.pendingFields()
        
        self.lineLayer = QgsVectorLayer("LineString?crs=epsg:4326", outname, "memory")
        pline = self.lineLayer.dataProvider()
        pline.addAttributes(fields)
        self.lineLayer.updateFields()
        
        iter = layer.getFeatures()
        num_features = 0
        num_good = 0
        for feature in iter:
            num_features += 1
            try:
                if bearingcol != -1:
                    bearing = float(feature[bearingcol])
                else:
                    bearing = defaultBearing
                if distcol != -1:
                    distance = float(feature[distcol])*measureFactor
                else:
                    distance = defaultDist
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                l = self.geod.Line(pt.y(), pt.x(), bearing)
                n = int(math.ceil(distance / seglen))
                if n > self.settings.maxSegments:
                    n = self.settings.maxSegments
                pts = [pt]
                for i in range(1,n+1):
                    s = min(seglen * i, distance)
                    g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                    pts.append( QgsPoint(g['lon2'], g['lat2']) )
                #pts = LatLon.getLineCoords(pt.y(), pt.x(), bearing, distance, 256, 2000)
                featureout  = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolyline(pts))
                featureout.setAttributes(feature.attributes())
                pline.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                pass
        self.lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(self.lineLayer)
        self.iface.messageBar().pushMessage("", "{} lines of bearing created from {} records".format(num_good, num_features), level=QgsMessageBar.INFO, duration=3)
        
    def processPoly(self, layer, outname, sidescol, anglecol, distcol, sides, angle, defaultDist, unitOfDist):
        if unitOfDist == 2: # Nautical Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.NauticalMiles, QGis.Meters)
        elif unitOfDist == 0: # Kilometers
            measureFactor = 1000.0
        elif unitOfDist == 1: # Meters
            measureFactor = 1.0
        elif unitOfDist == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)*5280.0
        elif unitOfDist == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)
            
        defaultDist *= measureFactor
 
        fields = layer.pendingFields()
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        for feature in iter:
            try:
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                if sidescol != -1:
                    s = int(feature[sidescol])
                else:
                    s = sides
                if anglecol != -1:
                    startangle = float(feature[anglecol])
                else:
                    startangle = angle
                if distcol != -1:
                    d = float(feature[distcol])*measureFactor
                else:
                    d = defaultDist
                pts = []
                i = s
                while i >= 0:
                    a = (i * 360.0 / s)+startangle
                    i -= 1
                    g = self.geod.Direct(pt.y(), pt.x(), a, d, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPoint(g['lon2'], g['lat2']))
                    #lat2, lon2 = LatLon.destinationPointVincenty(pt.y(), pt.x(), a, d)
                    #pts.append(QgsPoint(lon2, lat2))
                    
                featureout = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
                featureout.setAttributes(feature.attributes())
                ppolygon.addFeatures([featureout])
            except:
                pass
                
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)

    def processStar(self, layer, outname, numPoints, startAngle, innerRadius, outerRadius, unitOfDist):
        if unitOfDist == 2: # Nautical Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.NauticalMiles, QGis.Meters)
        elif unitOfDist == 0: # Kilometers
            measureFactor = 1000.0
        elif unitOfDist == 1: # Meters
            measureFactor = 1.0
        elif unitOfDist == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)*5280.0
        elif unitOfDist == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)
            
        innerRadius *= measureFactor
        outerRadius *= measureFactor

        fields = layer.pendingFields()
        
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        half = (360.0 / numPoints) / 2.0
        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            i = numPoints
            while i >= 0:
                i -= 1
                angle = (i * 360.0 / numPoints) + startAngle
                g = self.geod.Direct(pt.y(), pt.x(), angle, outerRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                #lat2, lon2 = LatLon.destinationPointVincenty(pt.y(), pt.x(), angle, outerRadius)
                #pts.append(QgsPoint(lon2, lat2))
                g = self.geod.Direct(pt.y(), pt.x(), angle-half, innerRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                #lat2, lon2 = LatLon.destinationPointVincenty(pt.y(), pt.x(), angle-half, innerRadius)
                #pts.append(QgsPoint(lon2, lat2))
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)
        
    def accept(self):
        self.apply()
        self.close()
