import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsFeature,
    QgsCoordinateTransform, QgsVectorLayer, QgsPoint, QgsFeature,
    QgsGeometry, QgsMapLayerRegistry, QGis)
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel

from PyQt4.QtGui import QIcon, QDialog, QDialogButtonBox
from PyQt4 import uic

from .LatLon import LatLon
from .settings import settings, epsg4326

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/vector2Shape.ui'))

DISTANCE_MEASURE=["Kilometers","Meters","Nautical Miles","Miles","Feet"]
class Vector2ShapeWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(Vector2ShapeWidget, self).__init__(parent)
        self.setupUi(self)
        self.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mMapLayerComboBox.layerChanged.connect(self.findFields)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.iface = iface
        self.unitOfAxisComboBox.addItems(DISTANCE_MEASURE)
        self.unitOfDistanceComboBox.addItems(DISTANCE_MEASURE)
        self.distUnitsPolyComboBox.addItems(DISTANCE_MEASURE)
        self.unitsStarComboBox.addItems(DISTANCE_MEASURE)
        self.unitsRoseComboBox.addItems(DISTANCE_MEASURE)
        self.unitsCyclodeComboBox.addItems(DISTANCE_MEASURE)
        self.unitsFoilComboBox.addItems(DISTANCE_MEASURE)
        self.unitsHeartComboBox.addItems(DISTANCE_MEASURE)
        self.unitsEpicyclodeComboBox.addItems(DISTANCE_MEASURE)
        self.pieUnitOfDistanceComboBox.addItems(DISTANCE_MEASURE)
        self.polygonLayer = None
        self.geod = Geodesic.WGS84
        icon = QIcon(os.path.dirname(__file__) + '/images/ellipse.png')
        self.tabWidget.setTabIcon(0, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/line.png')
        self.tabWidget.setTabIcon(1, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/pie.png')
        self.tabWidget.setTabIcon(2, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/polygon.png')
        self.tabWidget.setTabIcon(3, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/star.png')
        self.tabWidget.setTabIcon(4, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/rose.png')
        self.tabWidget.setTabIcon(5, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/hypocycloid.png')
        self.tabWidget.setTabIcon(6, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/polyfoil.png')
        self.tabWidget.setTabIcon(7, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/epicycloid.png')
        self.tabWidget.setTabIcon(8, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/heart.png')
        self.tabWidget.setTabIcon(9, icon)

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
        elif tab == 2: # Pie shape
            self.processPie(layer, outname,
                self.pieBearingStartComboBox.currentIndex()-1,
                self.pieBearingEndComboBox.currentIndex()-1,
                self.pieDistanceComboBox.currentIndex()-1,
                self.pieUnitOfDistanceComboBox.currentIndex(),
                self.pieBearingStartSpinBox.value(),
                self.pieBearingEndSpinBox.value(),
                self.pieDefaultDistanceSpinBox.value())
        elif tab == 3: # Polygon
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
        elif tab == 4: # Star
            self.processStar(layer, outname,
                self.starPointsSpinBox.value(),
                self.starStartAngleSpinBox.value(),
                self.innerStarRadiusSpinBox.value(),
                self.outerStarRadiusSpinBox.value(),
                self.unitsStarComboBox.currentIndex())
        elif tab == 5: # Rose
            self.processRose(layer, outname,
                self.roseAngleSpinBox.value(),
                self.rosePetalSpinBox.value(),
                self.roseRadiusSpinBox.value(),
                self.unitsRoseComboBox.currentIndex())
        elif tab == 6: # Cyclode
            self.processCyclode(layer, outname,
                self.cyclodeAngleSpinBox.value(),
                self.cyclodeCuspsSpinBox.value(),
                self.cyclodeRadiusSpinBox.value(),
                self.unitsCyclodeComboBox.currentIndex())
        elif tab == 7: # Polyfoil
            self.processPolyfoil(layer, outname,
                self.foilAngleSpinBox.value(),
                self.foilLobesSpinBox.value(),
                self.foilRadiusSpinBox.value(),
                self.unitsFoilComboBox.currentIndex())
        elif tab == 8: # Epicycloid
            self.processEpicycloid(layer, outname,
                self.epicyclodeAngleSpinBox.value(),
                self.epicyclodeLobesSpinBox.value(),
                self.epicyclodeRadiusSpinBox.value(),
                self.unitsEpicyclodeComboBox.currentIndex())
        elif tab == 9: # Heart
            self.processHeart(layer, outname,
                self.heartAngleSpinBox.value(),
                self.heartSizeSpinBox.value(),
                self.unitsHeartComboBox.currentIndex())
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(Vector2ShapeWidget, self).showEvent(event)
        self.findFields()
        
    def findFields(self):
        if not self.isVisible():
            return
        layer = self.mMapLayerComboBox.currentLayer()
        self.clearLayerFields()
        if layer:
            header = [u"[ Use Default ]"]
            fields = layer.pendingFields()
            for field in fields.toList():
                # force it to be lower case - makes matching easier
                name = field.name()
                header.append(name)
            self.configureLayerFields(header)

    def configureLayerFields(self, header):
        if not settings.guessNames:
            self.clearLayerFields()
        self.semiMajorComboBox.addItems(header)
        self.semiMinorComboBox.addItems(header)
        self.orientationComboBox.addItems(header)
        
        self.bearingComboBox.addItems(header)
        self.distanceComboBox.addItems(header)
        
        self.pieBearingStartComboBox.addItems(header)
        self.pieBearingEndComboBox.addItems(header)
        self.pieDistanceComboBox.addItems(header)
        
        self.sidesPolyComboBox.addItems(header)
        self.anglePolyComboBox.addItems(header)
        self.distPolyComboBox.addItems(header)
        
        if not settings.guessNames:
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
        self.pieBearingStartComboBox.clear()
        self.pieBearingEndComboBox.clear()
        self.pieDistanceComboBox.clear()
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
        measureFactor = self.conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
        maxseglen = settings.maxSegLength*1000.0 # Needs to be in meters
        maxSegments = settings.maxSegments
        
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
                pts = [pt]
                l = self.geod.Line(pt.y(), pt.x(), bearing)
                n = int(math.ceil(distance / maxseglen))
                if n > maxSegments:
                    n = maxSegments
                seglen = distance / n
                for i in range(1,n+1):
                    s = seglen * i
                    g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE | Geodesic.LONG_UNROLL)
                    pts.append( QgsPoint(g['lon2'], g['lat2']) )
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
        
    def processPie(self, layer, outname, startanglecol, endanglecol, distcol, unitOfDist, startangle, endangle, defaultDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
 
        fields = layer.pendingFields()
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()
        
        for feature in iter:
            try:
                pts = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                pts.append(pt)
                if startanglecol == -1:
                    sangle = startangle
                else:
                    sangle = float(feature[startanglecol])
                if endanglecol == -1:
                    eangle = endangle
                else:
                    eangle = float(feature[endanglecol])
                if distcol == -1:
                    dist = defaultDist
                else:
                    dist = float(feature[distcol]) * measureFactor
                    
                sangle = sangle % 360
                eangle = eangle % 360
                
                if sangle > eangle:
                    # We are crossing the 0 boundry so lets just subtract
                    # 360 from it.
                    sangle -= 360.0
                while sangle < eangle:
                    g = self.geod.Direct(pt.y(), pt.x(), sangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPoint(g['lon2'], g['lat2']))
                    sangle += 4 # add this number of degrees to the angle
                    
                g = self.geod.Direct(pt.y(), pt.x(), eangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                pts.append(pt)
                    
                featureout = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
                featureout.setAttributes(feature.attributes())
                ppolygon.addFeatures([featureout])
            except:
                pass
                
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)
                
    def processPoly(self, layer, outname, sidescol, anglecol, distcol, sides, angle, defaultDist, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
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
        measureFactor = self.conversionToMeters(unitOfDist)
            
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
            i = numPoints - 1
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

    def processRose(self, layer, outname, startAngle, k, radius, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        fields = layer.pendingFields()
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()
        dist=[]
        if k == 1:
            dist.append(0.0)
        step = 1
        angle = -90.0 + step
        while angle < 90.0:
            a = math.radians(angle)
            r = math.cos(a)
            dist.append(r)
            angle += step
        cnt = len(dist)

        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            arange = 360.0 / k
            angle = -arange / 2.0
            astep = arange / cnt
            for i in range(k):
                aoffset = arange * (k - 1)
                index = 0
                while index < cnt:
                    r = dist[index] * radius
                    g = self.geod.Direct(pt.y(), pt.x(), angle + aoffset, r, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    pts.append(QgsPoint(g['lon2'], g['lat2']))
                    angle += astep
                    index+=1
            # repeat the very first point to close the polygon
            pts.append(pts[0])
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)

    def processCyclode(self, layer, outname, startAngle, cusps, radius, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / cusps
        fields = layer.pendingFields()
        
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            angle = 0.0
            while angle <= 360.0:
                a = math.radians(angle)
                x = r * (cusps - 1.0)*math.cos(a) + r * math.cos((cusps - 1.0) * a)
                y = r * (cusps - 1.0)*math.sin(a) - r * math.sin((cusps - 1.0) * a)
                a2 = math.degrees(math.atan2(y,x))+startAngle
                dist = math.sqrt(x*x + y*y)
                g = self.geod.Direct(pt.y(), pt.x(), a2, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                angle += 0.5
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)

    def processEpicycloid(self, layer, outname, startAngle, lobes, radius, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / (lobes + 2.0)
        fields = layer.pendingFields()
        
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            angle = 0.0
            while angle <= 360.0:
                a = math.radians(angle)
                x = r * (lobes + 1.0)*math.cos(a) - r * math.cos((lobes + 1.0) * a)
                y = r * (lobes + 1.0)*math.sin(a) - r * math.sin((lobes + 1.0) * a)
                a2 = math.degrees(math.atan2(y,x))+startAngle
                dist = math.sqrt(x*x + y*y)
                g = self.geod.Direct(pt.y(), pt.x(), a2, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                angle += 0.5
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)

    def processPolyfoil(self, layer, outname, startAngle, lobes, radius, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / lobes
        fields = layer.pendingFields()
        
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            angle = 0.0
            while angle <= 360.0:
                a = math.radians(angle-startAngle)
                x = r * (lobes - 1.0)*math.cos(a) + r * math.cos((lobes - 1.0) * a)
                y = r * (lobes - 1.0)*math.sin(a) - r * math.sin((lobes - 1.0) * a)
                dist = math.sqrt(x*x + y*y)
                g = self.geod.Direct(pt.y(), pt.x(), angle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                angle += 0.5
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)

    def processHeart(self, layer, outname, startAngle, size, unitOfDist):
        measureFactor = self.conversionToMeters(unitOfDist)
        # The algorithm creates the heart on its side so this rotates
        # it so that it is upright.
        startAngle -= 90.0
            
        size *= measureFactor

        fields = layer.pendingFields()
        
        
        polygonLayer = QgsVectorLayer("Polygon?crs=epsg:4326", outname, "memory")
        ppolygon = polygonLayer.dataProvider()
        ppolygon.addAttributes(fields)
        polygonLayer.updateFields()
        
        iter = layer.getFeatures()

        for feature in iter:
            pts = []
            pt = feature.geometry().asPoint()
            # make sure the coordinates are in EPSG:4326
            pt = self.transform.transform(pt.x(), pt.y())
            angle = 0.0
            while angle <= 360.0:
                a = math.radians(angle)
                sina = math.sin(a)
                x = 16 * sina * sina * sina
                y = 13 * math.cos(a) - 5 * math.cos(2*a) - 2 * math.cos(3 * a)- math.cos(4*a)
                dist = math.sqrt(x*x + y*y) * size / 17.0
                a2 = math.degrees(math.atan2(y,x))+startAngle
                g = self.geod.Direct(pt.y(), pt.x(), a2, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPoint(g['lon2'], g['lat2']))
                angle += 0.5
            featureout = QgsFeature()
            featureout.setGeometry(QgsGeometry.fromPolygon([pts]))
            featureout.setAttributes(feature.attributes())
            ppolygon.addFeatures([featureout])
                    
        polygonLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(polygonLayer)
        
    def conversionToMeters(self, units):
        if units == 2: # Nautical Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.NauticalMiles, QGis.Meters)
        elif units == 0: # Kilometers
            measureFactor = 1000.0
        elif units == 1: # Meters
            measureFactor = 1.0
        elif units == 3: # Miles
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)*5280.0
        elif units == 4: # Feet
            measureFactor = QGis.fromUnitToUnitFactor(QGis.Feet, QGis.Meters)
        return measureFactor
        
    def accept(self):
        self.apply()
        self.close()
