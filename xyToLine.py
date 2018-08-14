import os
import re
import math
from geographiclib.geodesic import Geodesic

from qgis.core import (QgsVectorLayer,
    QgsCoordinateTransform, QgsPoint, QgsFeature, QgsGeometry, 
    QgsMapLayerRegistry, QGis)
from qgis.gui import QgsMessageBar, QgsMapLayerProxyModel

from PyQt4.QtGui import QDialog
from PyQt4 import uic

from .LatLon import LatLon
from .settings import settings, epsg4326

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/xyToLineDialog.ui'))

class XYToLineWidget(QDialog, FORM_CLASS):
    def __init__(self, iface, parent):
        super(XYToLineWidget, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.inputMapLayerComboBox.setFilters(QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.NoGeometry)
        self.inputMapLayerComboBox.layerChanged.connect(self.layerChanged)
        self.inputQgsProjectionSelectionWidget.setCrs(epsg4326)
        self.outputQgsProjectionSelectionWidget.setCrs(epsg4326)
        self.lineTypeComboBox.addItems(['Geodesic','Great Circle','Simple Line'])
        self.geod = Geodesic.WGS84
        
    def accept(self):
        layer = self.inputMapLayerComboBox.currentLayer()
        if not layer:
            self.iface.messageBar().pushMessage("", "No Valid Layer", level=QgsMessageBar.WARNING, duration=4)
        pointname = self.pointsNameLineEdit.text()
        linename = self.lineNameLineEdit.text()
        startXcol = self.startXFieldComboBox.currentIndex() # Returns -1 if none selected
        startYcol = self.startYFieldComboBox.currentIndex()
        endXcol = self.endXFieldComboBox.currentIndex()
        endYcol = self.endYFieldComboBox.currentIndex()
        startUseGeom = self.startCheckBox.isChecked()
        endUseGeom = self.endCheckBox.isChecked()
        inCRS = self.inputQgsProjectionSelectionWidget.crs()
        outCRS = self.outputQgsProjectionSelectionWidget.crs()
        lineType = self.lineTypeComboBox.currentIndex()
        showStart = self.showStartCheckBox.isChecked()
        showEnd = self.showEndCheckBox.isChecked()
        dateLine = self.breakLinesCheckBox.isChecked()
        
        if dateLine and lineType <= 1:
            isMultiPart = True
        else:
            isMultiPart = False
        
        if (startUseGeom == False) and (startXcol == -1 or startYcol == -1):
            self.iface.messageBar().pushMessage("", "Must specify valid starting point columns", level=QgsMessageBar.WARNING, duration=4)
            return
        if (endUseGeom == False) and (endXcol == -1 or endYcol == -1):
            self.iface.messageBar().pushMessage("", "Must specify valid ending point columns", level=QgsMessageBar.WARNING, duration=4)
            return
        
        # Get the field names for the input layer. The will be copied to the output layers
        fields = layer.pendingFields()
        
        # Create the points and line output layers
        if isMultiPart:
            lineLayer = QgsVectorLayer("MultiLineString?crs={}".format(outCRS.authid()), linename, "memory")
        else:
            lineLayer = QgsVectorLayer("LineString?crs={}".format(outCRS.authid()), linename, "memory")
        pline = lineLayer.dataProvider()
        pline.addAttributes(fields)
        lineLayer.updateFields()
        
        if showStart or showEnd:
            pointLayer = QgsVectorLayer("Point?crs={}".format(outCRS.authid()), pointname, "memory")
            ppoint = pointLayer.dataProvider()
            ppoint.addAttributes(fields)
            pointLayer.updateFields()
        
        if inCRS != epsg4326:
            transto4326 = QgsCoordinateTransform(inCRS, epsg4326)
        if outCRS != epsg4326:
            transfrom4326 = QgsCoordinateTransform(epsg4326, outCRS)
        
        iter = layer.getFeatures()
        num_features = 0
        num_bad = 0
        maxseglen = settings.maxSegLength*1000.0
        maxSegments = settings.maxSegments
        for feature in iter:
            num_features += 1
            try:
                if startUseGeom == True:
                    ptStart = feature.geometry().asPoint()
                else:
                    ptStart = QgsPoint(float(feature[startXcol]), float(feature[startYcol]))
                if endUseGeom == True:
                    ptEnd = feature.geometry().asPoint()
                else:
                    ptEnd = QgsPoint(float(feature[endXcol]), float(feature[endYcol]))
                # If the input is not 4326 we need to convert it to that and then back to the output CRS
                if inCRS != epsg4326: # Convert to 4326
                    ptStart = transto4326.transform(ptStart)
                    ptEnd = transto4326.transform(ptEnd)
                # Create a new Line Feature
                fline = QgsFeature()
                pts = [ptStart]
                if lineType == 0: # Geodesic
                    l = self.geod.InverseLine(ptStart.y(), ptStart.x(), ptEnd.y(), ptEnd.x())
                    if l.s13 > maxseglen:
                        n = int(math.ceil(l.s13 / maxseglen))
                        if n > maxSegments:
                            n = maxSegments
                        seglen = l.s13 / n
                        for i in range(1,n+1):
                            s = seglen * i
                            g = l.Position(s, Geodesic.LATITUDE | Geodesic.LONGITUDE)
                            pts.append( QgsPoint(g['lon2'], g['lat2']) )
                    else: # The line segment is too short so it is from ptStart to ptEnd
                        pts.append(ptEnd)
                elif lineType == 1: # Great Circle
                    pts = LatLon.getPointsOnLine(ptStart.y(), ptStart.x(),
                        ptEnd.y(), ptEnd.x(),
                        settings.maxSegLength*1000.0, # Put it in meters
                        settings.maxSegments+1)
                else: # Simple line
                    pts.append(ptEnd)
                    
                if isMultiPart:
                    outseg = self.checkCrossings(pts)
                    if outCRS != epsg4326: # Convert each point to the output CRS
                        for y in range(len(outseg)):
                            for x, pt in enumerate(outseg[y]):
                                outseg[y][x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromMultiPolyline(outseg))
                else:
                    if outCRS != epsg4326: # Convert each point to the output CRS
                        for x, pt in enumerate(pts):
                            pts[x] = transfrom4326.transform(pt)
                    fline.setGeometry(QgsGeometry.fromPolyline(pts))
                if outCRS != epsg4326: # Convert each point to the output CRS
                    ptStart = transfrom4326.transform(ptStart)
                    ptEnd = transfrom4326.transform(ptEnd)
                
                fline.setAttributes(feature.attributes())
                pline.addFeatures([fline])
                # Add two point features
                if showStart:
                    fpoint = QgsFeature()
                    fpoint.setGeometry(QgsGeometry.fromPoint(ptStart))
                    fpoint.setAttributes(feature.attributes())
                    ppoint.addFeatures([fpoint])
                if showEnd:
                    fpoint = QgsFeature()
                    fpoint.setGeometry(QgsGeometry.fromPoint(ptEnd))
                    fpoint.setAttributes(feature.attributes())
                    ppoint.addFeatures([fpoint])
            except:
                num_bad += 1
                pass
                
        lineLayer.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(lineLayer)
        if showStart or showEnd:
            pointLayer.updateExtents()
            QgsMapLayerRegistry.instance().addMapLayer(pointLayer)
        if num_bad != 0:
            self.iface.messageBar().pushMessage("", "{} out of {} features failed".format(num_bad, num_features), level=QgsMessageBar.WARNING, duration=3)
       
        self.close()
    
    def checkCrossings(self, pts):
        outseg = []
        ptlen = len(pts)
        pts2 = [pts[0]]
        for i in range(1,ptlen):
            if pts[i-1].x() < -130 and pts[i].x() > 130: # We have crossed the date line going west
                ld = self.geod.Inverse(pts[i-1].y(), pts[i-1].x(), pts[i].y(), pts[i].x())
                try:
                    (intrlat, intrlon) = intersection_point(-89,-180, 0, pts[i-1].y(), pts[i-1].x(), ld['azi1'])
                    ptnew = QgsPoint(-180, intrlat)
                    pts2.append(ptnew)
                    outseg.append(pts2)
                    ptnew = QgsPoint(180, intrlat)
                    pts2 = [ptnew]
                except:
                    pts2.append(pts[i])
            if pts[i-1].x() > 130 and pts[i].x() < -130: # We have crossed the date line going east
                ld = self.geod.Inverse(pts[i-1].y(), pts[i-1].x(), pts[i].y(), pts[i].x())
                try:
                    (intrlat, intrlon) = intersection_point(-89,180, 0, pts[i-1].y(), pts[i-1].x(), ld['azi1'])
                    ptnew = QgsPoint(180, intrlat)
                    pts2.append(ptnew)
                    outseg.append(pts2)
                    ptnew = QgsPoint(-180, intrlat)
                    pts2 = [ptnew]
                except:
                    pts2.append(pts[i])
            else:
                pts2.append(pts[i])
        outseg.append(pts2)

        return(outseg)
        
    def layerChanged(self):
        if not self.isVisible():
            return
        layer = self.inputMapLayerComboBox.currentLayer()
        self.startXFieldComboBox.setLayer(layer)
        self.startYFieldComboBox.setLayer(layer)
        self.endXFieldComboBox.setLayer(layer)
        self.endYFieldComboBox.setLayer(layer)

        if not layer:
            return
            
        geomType = layer.geometryType()
        if geomType == QGis.Point:
            self.startCheckBox.setEnabled(True)
            self.endCheckBox.setEnabled(True)
        else:
            self.startCheckBox.setChecked(False)
            self.endCheckBox.setChecked(False)
            self.startCheckBox.setEnabled(False)
            self.endCheckBox.setEnabled(False)
        
        name = layer.name()
        self.pointsNameLineEdit.setText(name + " points")
        self.lineNameLineEdit.setText(name + " line")
        
    def showEvent(self, event):
        '''The dialog is being shown. We need to initialize it.'''
        super(XYToLineWidget, self).showEvent(event)
        self.layerChanged()


def intersection_point(lat1, lon1, bearing1, lat2, lon2, bearing2):
    o1 = math.radians(lat1)
    lam1 = math.radians(lon1)
    o2 = math.radians(lat2)
    lam2 = math.radians(lon2)
    bo_13 = math.radians(bearing1)
    bo_23 = math.radians(bearing2)
    
    diff_fo = o2 - o1
    diff_la = lam2 - lam1
    d12 = 2 * math.asin(math.sqrt(math.sin(diff_fo / 2) * math.sin(diff_fo / 2) + math.cos(o1) * math.cos(o2) * math.sin(diff_la / 2) * math.sin(diff_la / 2)))
    if d12 == 0: # intersection_not_found
        raise ValueError('Intersection not found')

    bo_1 = math.acos((math.sin(o2) - math.sin(o1) * math.cos(d12)) / (math.sin(d12) * math.cos(o1)))
    bo_2 = math.acos((math.sin(o1) - math.sin(o2) * math.cos(d12)) / (math.sin(d12) * math.cos(o2)))
    if math.sin(lam2 - lam1) > 0:
        bo_12 = bo_1
        bo_21 = 2 * math.pi - bo_2
    else:
        bo_12 = 2 * math.pi - bo_1
        bo_21 = bo_2
    a_1 = ((bo_13 - bo_12 + math.pi) % (2 * math.pi)) - math.pi
    a_2 = ((bo_21 - bo_23 + math.pi) % (2 * math.pi)) - math.pi
    if (math.sin(a_1) == 0) and (math.sin(a_2) == 0): # infinite intersections
        raise ValueError('Intersection not found')
    if math.sin(a_1) * math.sin(a_2) < 0: # ambiguous intersection
        raise ValueError('Intersection not found')

    a_3 = math.acos(-math.cos(a_1) * math.cos(a_2) + math.sin(a_1) * math.sin(a_2) * math.cos(d12))
    be_13 = math.atan2(math.sin(d12) * math.sin(a_1) * math.sin(a_2), math.cos(a_2) + math.cos(a_1) * math.cos(a_3))
    fo_3 = math.asin(math.sin(o1) * math.cos(be_13) + math.cos(o1) * math.sin(be_13) * math.cos(bo_13))
    diff_lam13 = math.atan2(math.sin(bo_13) * math.sin(be_13) * math.cos(o1), math.cos(be_13) - math.sin(o1) * math.sin(fo_3))
    la_3 = lam1 + diff_lam13

    return (math.degrees(fo_3), math.degrees(la_3))
