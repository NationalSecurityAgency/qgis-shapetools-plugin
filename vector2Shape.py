import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsFeature,
    QgsCoordinateTransform, QgsVectorLayer, QgsPointXY, QgsFeature,
    QgsGeometry, QgsProject, QgsMapLayerProxyModel, Qgis, QgsUnitTypes)

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
import processing
#import traceback

from .LatLon import LatLon
from .settings import settings, epsg4326
from .utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/vector2Shape.ui'))

class Vector2ShapeWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(Vector2ShapeWidget, self).__init__(parent)
        self.setupUi(self)
        self.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mMapLayerComboBox.layerChanged.connect(self.findFields)
        self.buttonBox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)
        self.outputCRSComboBox.addItems([tr('Layer CRS'), tr('Project CRS'), tr('WGS 84')])
        self.shapeTypeComboBox.addItems([tr('Polygon'), tr('Line')])
        self.iface = iface
        self.unitOfAxisComboBox.addItems(DISTANCE_LABELS)
        self.unitOfDistanceComboBox.addItems(DISTANCE_LABELS)
        self.distUnitsPolyComboBox.addItems(DISTANCE_LABELS)
        self.unitsDonutComboBox.addItems(DISTANCE_LABELS)
        self.unitsStarComboBox.addItems(DISTANCE_LABELS)
        self.unitsRoseComboBox.addItems(DISTANCE_LABELS)
        self.unitsCyclodeComboBox.addItems(DISTANCE_LABELS)
        self.unitsFoilComboBox.addItems(DISTANCE_LABELS)
        self.unitsHeartComboBox.addItems(DISTANCE_LABELS)
        self.unitsEpicyclodeComboBox.addItems(DISTANCE_LABELS)
        self.pieUnitOfDistanceComboBox.addItems(DISTANCE_LABELS)
        self.pieAzimuthModeComboBox.addItems([tr('Use beginning end ending azimuths'),
            tr('Use center azimuth and width')])
        self.pieAzimuthModeComboBox.activated.connect(self.pieAzimuthModeChange)
        self.geod = Geodesic.WGS84
        icon = QIcon(os.path.dirname(__file__) + '/images/ellipse.png')
        self.tabWidget.setTabIcon(0, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/line.png')
        self.tabWidget.setTabIcon(1, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/pie.png')
        self.tabWidget.setTabIcon(2, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/donut.png')
        self.tabWidget.setTabIcon(3, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/polygon.png')
        self.tabWidget.setTabIcon(4, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/star.png')
        self.tabWidget.setTabIcon(5, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/rose.png')
        self.tabWidget.setTabIcon(6, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/hypocycloid.png')
        self.tabWidget.setTabIcon(7, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/polyfoil.png')
        self.tabWidget.setTabIcon(8, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/epicycloid.png')
        self.tabWidget.setTabIcon(9, icon)
        icon = QIcon(os.path.dirname(__file__) + '/images/heart.png')
        self.tabWidget.setTabIcon(10, icon)

    def apply(self):
        '''process the data'''
        tab = self.tabWidget.currentIndex()
        layer = self.mMapLayerComboBox.currentLayer()
        outname = self.layerNameLineEdit.text()
        if not layer:
            self.showErrorMessage(tr("No valid layer to process"))
            return
        
        # Apply any environment variable settings
        qset = QSettings()
        qset.setValue('/ShapeTools/DonutSegments', self.donutDrawingSegmentsSpinBox.value())
        qset.setValue('/ShapeTools/PieSegments', self.pieDrawingSegmentsSpinBox.value())
        qset.setValue('/ShapeTools/PieAzimuthMode', self.pieAzimuthModeComboBox.currentIndex())
        
        # We need to make sure all the points in the layer are transformed to EPSG:4326
        layerCRS = layer.crs()
        self.transform = QgsCoordinateTransform(layerCRS, epsg4326, QgsProject.instance())
        
        outCrsMode = self.outputCRSComboBox.currentIndex()
        self.outputCRS = epsg4326
        if outCrsMode == 0: # Layer CRS
            if layerCRS != epsg4326:
                self.outputCRS = layerCRS
                self.transformOut = QgsCoordinateTransform(epsg4326, layerCRS, QgsProject.instance())
        elif outCrsMode == 1: # Project CRS
            self.outputCRS = self.iface.mapCanvas().mapSettings().destinationCrs()
            if self.outputCRS != epsg4326:
                self.transformOut = QgsCoordinateTransform(epsg4326, self.outputCRS, QgsProject.instance())
        shapetype = self.shapeTypeComboBox.currentIndex()
        if tab == 0: # Ellipse
            self.processEllipse(layer, outname, shapetype,
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
            self.processPie(layer, outname, shapetype,
                self.pieAzimuthModeComboBox.currentIndex(),
                self.pieBearingStartComboBox.currentIndex()-1,
                self.pieBearingEndComboBox.currentIndex()-1,
                self.pieDistanceComboBox.currentIndex()-1,
                self.pieUnitOfDistanceComboBox.currentIndex(),
                self.pieBearingStartSpinBox.value(),
                self.pieBearingEndSpinBox.value(),
                self.pieDefaultDistanceSpinBox.value(),
                self.pieDrawingSegmentsSpinBox.value())
        elif tab == 3: # Donut
            self.processDonut(layer, outname, shapetype,
                self.donutInnerRadiusComboBox.currentIndex()-1,
                self.donutOuterRadiusComboBox.currentIndex()-1,
                self.donutInnerRadiusSpinBox.value(),
                self.donutOuterRadiusSpinBox.value(),
                self.unitsDonutComboBox.currentIndex(),
                self.donutDrawingSegmentsSpinBox.value())
        elif tab == 4: # Polygon
            try:
                distance = float(self.distPolyLineEdit.text())
            except:
                self.showErrorMessage(tr("Invalid Distance. Fix and try again"))
                return
            self.processPoly(layer, outname, shapetype,
                self.sidesPolyComboBox.currentIndex()-1, #number of sides column
                self.anglePolyComboBox.currentIndex()-1, #starting angle column
                self.distPolyComboBox.currentIndex()-1, # distance column
                self.sidesPolySpinBox.value(), # default sides
                self.anglePolySpinBox.value(), # default starting angle
                distance,
                self.distUnitsPolyComboBox.currentIndex())
        elif tab == 5: # Star
            self.processStar(layer, outname, shapetype,
                self.starPointsSpinBox.value(),
                self.starStartAngleSpinBox.value(),
                self.innerStarRadiusSpinBox.value(),
                self.outerStarRadiusSpinBox.value(),
                self.unitsStarComboBox.currentIndex())
        elif tab == 6: # Rose
            self.processRose(layer, outname, shapetype,
                self.roseAngleSpinBox.value(),
                self.rosePetalSpinBox.value(),
                self.roseRadiusSpinBox.value(),
                self.unitsRoseComboBox.currentIndex())
        elif tab == 7: # Cyclode
            self.processCyclode(layer, outname, shapetype,
                self.cyclodeAngleSpinBox.value(),
                self.cyclodeCuspsSpinBox.value(),
                self.cyclodeRadiusSpinBox.value(),
                self.unitsCyclodeComboBox.currentIndex())
        elif tab == 8: # Polyfoil
            self.processPolyfoil(layer, outname, shapetype,
                self.foilAngleSpinBox.value(),
                self.foilLobesSpinBox.value(),
                self.foilRadiusSpinBox.value(),
                self.unitsFoilComboBox.currentIndex())
        elif tab == 9: # Epicycloid
            self.processEpicycloid(layer, outname, shapetype,
                self.epicyclodeAngleSpinBox.value(),
                self.epicyclodeLobesSpinBox.value(),
                self.epicyclodeRadiusSpinBox.value(),
                self.unitsEpicyclodeComboBox.currentIndex())
        elif tab == 10: # Heart
            self.processHeart(layer, outname, shapetype,
                self.heartAngleSpinBox.value(),
                self.heartSizeSpinBox.value(),
                self.unitsHeartComboBox.currentIndex())
        
    def pieAzimuthModeChange(self):
        if int(self.pieAzimuthModeComboBox.currentIndex()) == 0:
            self.pieAngleField1Label.setText(tr('Starting azimuth field'))
            self.pieAngleField2Label.setText(tr('Ending azimuth field'))
            self.pieDefaultAngle1Label.setText(tr('Default starting azimuth'))
            self.pieDefaultAngle2Label.setText(tr('Default ending azimuth'))
        else:
            self.pieAngleField1Label.setText(tr('Center azimuth field'))
            self.pieAngleField2Label.setText(tr('Azimuth width field'))
            self.pieDefaultAngle1Label.setText(tr('Default center azimuth'))
            self.pieDefaultAngle2Label.setText(tr('Default azimuth width'))
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(Vector2ShapeWidget, self).showEvent(event)
        # read  environment variables required for setting up the dialog
        qset = QSettings()
        donutSegments = int(qset.value('/ShapeTools/DonutSegments', 36))
        pieSegments = int(qset.value('/ShapeTools/PieSegments', 36))
        pieAzimuthMode = int(qset.value('/ShapeTools/PieAzimuthMode', 0))
        self.donutDrawingSegmentsSpinBox.setValue(donutSegments)
        self.pieDrawingSegmentsSpinBox.setValue(pieSegments)
        self.pieAzimuthModeComboBox.setCurrentIndex(pieAzimuthMode)
        
        self.findFields()
        self.pieAzimuthModeChange()
        
    def findFields(self):
        if not self.isVisible():
            return
        layer = self.mMapLayerComboBox.currentLayer()
        self.clearLayerFields()
        try:
            if layer:
                header = [tr("[ Use Default ]")]
                fields = layer.fields()
                for field in fields.toList():
                    # force it to be lower case - makes matching easier
                    name = field.name()
                    header.append(name)
                self.configureLayerFields(header)
        except:
            pass

    def configureLayerFields(self, header):
        if not settings.guessNames:
            self.clearLayerFields()
        self.semiMajorComboBox.addItems(header)
        self.semiMinorComboBox.addItems(header)
        self.orientationComboBox.addItems(header)
        
        # Donut
        self.donutInnerRadiusComboBox.addItems(header)
        self.donutOuterRadiusComboBox.addItems(header)
        
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
        # Donut
        self.donutInnerRadiusComboBox.clear()
        self.donutOuterRadiusComboBox.clear()
        
        self.bearingComboBox.clear()
        self.distanceComboBox.clear()
        self.pieBearingStartComboBox.clear()
        self.pieBearingEndComboBox.clear()
        self.pieDistanceComboBox.clear()
        self.sidesPolyComboBox.clear()
        self.anglePolyComboBox.clear()
        self.distPolyComboBox.clear()
            
    def showErrorMessage(self, message):
        self.iface.messageBar().pushMessage("", message, level=Qgis.Warning, duration=3)
        
    def processEllipse(self, layer, outname, shapetype, semimajorcol, semiminorcol, orientcol, unitOfMeasure, defSemiMajor, defSemiMinor, defOrientation):
        measureFactor = 1.0
        # The ellipse calculation is done in Nautical Miles. This converts
        # the semi-major and minor axis to nautical miles
        if unitOfMeasure == 2: # Nautical Miles
            measureFactor = 1.0
        elif unitOfMeasure == 0: # Kilometers
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceKilometers, QgsUnitTypes.DistanceNauticalMiles)
        elif unitOfMeasure == 1: # Meters
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, QgsUnitTypes.DistanceNauticalMiles)
        elif unitOfMeasure == 3: # Miles
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMiles, QgsUnitTypes.DistanceNauticalMiles)
        elif unitOfMeasure == 4: # Yards
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceYards, QgsUnitTypes.DistanceNauticalMiles)
        elif unitOfMeasure == 5: # Feet
            measureFactor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceFeet, QgsUnitTypes.DistanceNauticalMiles)
        
        fields = layer.fields()
        
        if shapetype == 0:
            self.outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            self.outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = self.outLayer.dataProvider()
        dp.addAttributes(fields)
        self.outLayer.updateFields()
        
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
                pts = LatLon.getEllipseCoords(pt.y(), pt.x(), semi_major*measureFactor,
                    semi_minor*measureFactor, orient)
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if self.outputCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = self.transformOut.transform(ptout)
                        
                featureout = QgsFeature()
                featureout.setAttributes(feature.attributes())
                if shapetype == 0:
                    featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                else:
                    featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
                dp.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                #traceback.print_exc()
                pass
        self.outLayer.updateExtents()
        QgsProject.instance().addMapLayer(self.outLayer)
        self.iface.messageBar().pushMessage("", "{} Ellipses created from {} records".format(num_good, num_features), level=Qgis.Info, duration=3)
        
    def processLOB(self, layer, outname, bearingcol, distcol, unitOfDist, defaultBearing, defaultDist):
        '''Process each layer point and create a new line layer with the associated bearings'''
        measureFactor = conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
        maxseglen = settings.maxSegLength*1000.0 # Needs to be in meters
        maxSegments = settings.maxSegments
        
        fields = layer.fields()
        
        lineLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        pline = lineLayer.dataProvider()
        pline.addAttributes(fields)
        lineLayer.updateFields()
        
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
                    pts.append( QgsPointXY(g['lon2'], g['lat2']) )
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if self.outputCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = self.transformOut.transform(ptout)
                            
                featureout  = QgsFeature()
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
                featureout.setAttributes(feature.attributes())
                pline.addFeatures([featureout])
                num_good += 1
            except:
                # Just skip any lines that are badly formed
                pass
        lineLayer.updateExtents()
        QgsProject.instance().addMapLayer(lineLayer)
        self.iface.messageBar().pushMessage("", "{} lines of bearing created from {} records".format(num_good, num_features), level=Qgis.Info, duration=3)
        
    def processPie(self, layer, outname, shapetype, azimuthMode, startanglecol, endanglecol, distcol, unitOfDist, startangle, endangle, defaultDist, segments):
        measureFactor = conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
        
        arcPtSpacing = 360.0 / segments
 
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                if azimuthMode == 1:
                    width = abs(eangle) / 2.0
                    eangle = sangle + width
                    sangle -= width
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
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    sangle += arcPtSpacing # add this number of degrees to the angle
                    
                g = self.geod.Direct(pt.y(), pt.x(), eangle, dist, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                pts.append(pt)
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if self.outputCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = self.transformOut.transform(ptout)
                        
                featureout = QgsFeature()
                if shapetype == 0:
                    featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                else:
                    featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
                featureout.setAttributes(feature.attributes())
                dp.addFeatures([featureout])
            except:
                pass
                
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processDonut(self, layer, outname, shapetype, innerCol, outerCol, defInnerRadius, defOuterRadius, units, segments):
        measureFactor = conversionToMeters(units)
            
        defInnerRadius *= measureFactor
        defOuterRadius *= measureFactor
        
        ptSpacing = 360.0 / segments
 
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("MultiLineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
        iter = layer.getFeatures()
        
        for feature in iter:
            try:
                ptsi = []
                ptso = []
                pt = feature.geometry().asPoint()
                # make sure the coordinates are in EPSG:4326
                pt = self.transform.transform(pt.x(), pt.y())
                lat = pt.y()
                lon = pt.x()
                angle = 0
                while angle < 360:
                    if innerCol == -1:
                        iRadius = defInnerRadius
                    else:
                        iRadius = float(feature[innerCol]) * measureFactor
                    if outerCol == -1:
                        oRadius = defOuterRadius
                    else:
                        oRadius = float(feature[outerCol]) * measureFactor
                    if iRadius != 0:
                        g = self.geod.Direct(lat, lon, angle, iRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                        ptsi.append(QgsPointXY(g['lon2'], g['lat2']))
                    g = self.geod.Direct(lat, lon, angle, oRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                    ptso.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += ptSpacing
                if iRadius != 0:
                    ptsi.append(ptsi[0])
                ptso.append(ptso[0])
                
                # If the Output crs is not 4326 transform the points to the proper crs
                if self.outputCRS != epsg4326:
                    if iRadius != 0:
                        for x, ptout in enumerate(ptsi):
                            ptsi[x] = self.transformOut.transform(ptout)
                    for x, ptout in enumerate(ptso):
                        ptso[x] = self.transformOut.transform(ptout)
                        
                featureout = QgsFeature()
                if shapetype == 0:
                    if iRadius == 0:
                        featureout.setGeometry(QgsGeometry.fromPolygonXY([ptso]))
                    else:
                        featureout.setGeometry(QgsGeometry.fromPolygonXY([ptso, ptsi]))
                else:
                    if iRadius == 0:
                        featureout.setGeometry(QgsGeometry.fromMultiPolylineXY([ptso]))
                    else:
                        featureout.setGeometry(QgsGeometry.fromMultiPolylineXY([ptso, ptsi]))
                featureout.setAttributes(feature.attributes())
                dp.addFeatures([featureout])
            except:
                pass
                
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)        
               
    def processPoly(self, layer, outname, shapetype, sidescol, anglecol, distcol, sides, angle, defaultDist, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        defaultDist *= measureFactor
 
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    
                # If the Output crs is not 4326 transform the points to the proper crs
                if self.outputCRS != epsg4326:
                    for x, ptout in enumerate(pts):
                        pts[x] = self.transformOut.transform(ptout)

                featureout = QgsFeature()
                if shapetype == 0:
                    featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                else:
                    featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
                featureout.setAttributes(feature.attributes())
                dp.addFeatures([featureout])
            except:
                pass
                
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processStar(self, layer, outname, shapetype, numPoints, startAngle, innerRadius, outerRadius, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        innerRadius *= measureFactor
        outerRadius *= measureFactor

        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                g = self.geod.Direct(pt.y(), pt.x(), angle-half, innerRadius, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processRose(self, layer, outname, shapetype, startAngle, k, radius, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                    pts.append(QgsPointXY(g['lon2'], g['lat2']))
                    angle += astep
                    index+=1
            # repeat the very first point to close the polygon
            pts.append(pts[0])
            
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processCyclode(self, layer, outname, shapetype, startAngle, cusps, radius, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / cusps
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += 0.5
                
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processEpicycloid(self, layer, outname, shapetype, startAngle, lobes, radius, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / (lobes + 2.0)
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += 0.5
                
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processPolyfoil(self, layer, outname, shapetype, startAngle, lobes, radius, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
            
        radius *= measureFactor
        r = radius / lobes
        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += 0.5
                
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)

    def processHeart(self, layer, outname, shapetype, startAngle, size, unitOfDist):
        measureFactor = conversionToMeters(unitOfDist)
        # The algorithm creates the heart on its side so this rotates
        # it so that it is upright.
        startAngle -= 90.0
            
        size *= measureFactor

        fields = layer.fields()
        
        if shapetype == 0:
            outLayer = QgsVectorLayer("Polygon?crs={}".format(self.outputCRS.authid()), outname, "memory")
        else:
            outLayer = QgsVectorLayer("LineString?crs={}".format(self.outputCRS.authid()), outname, "memory")
        dp = outLayer.dataProvider()
        dp.addAttributes(fields)
        outLayer.updateFields()
        
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
                pts.append(QgsPointXY(g['lon2'], g['lat2']))
                angle += 0.5
                
            # If the Output crs is not 4326 transform the points to the proper crs
            if self.outputCRS != epsg4326:
                for x, ptout in enumerate(pts):
                    pts[x] = self.transformOut.transform(ptout)
                    
            featureout = QgsFeature()
            if shapetype == 0:
                featureout.setGeometry(QgsGeometry.fromPolygonXY([pts]))
            else:
                featureout.setGeometry(QgsGeometry.fromPolylineXY(pts))
            featureout.setAttributes(feature.attributes())
            dp.addFeatures([featureout])
                    
        outLayer.updateExtents()
        QgsProject.instance().addMapLayer(outLayer)
        
    def accept(self):
        self.apply()
        self.close()
