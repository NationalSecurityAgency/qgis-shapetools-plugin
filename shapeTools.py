from qgis.PyQt.QtCore import QUrl, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolButton
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsWkbTypes, QgsProcessingAlgorithm, QgsApplication
import processing

from .settings import SettingsWidget
from .geodesicMeasureTool import GeodesicMeasureTool
from .azDigitizer import AzDigitizerTool
from .lineDigitizer import LineDigitizerTool

import os.path
import webbrowser
from .provider import ShapeToolsProvider
from .geodesicFlip import flipLayer

def tr(string):
    return QCoreApplication.translate('Processing', string)

class ShapeTools(object):
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settingsDialog = None
        self.xyLineDialog = None
        self.geodesicDensifyDialog = None
        self.azDigitizerTool = None
        self.lineDigitizerTool = None
        self.previousLayer = None
        self.toolbar = self.iface.addToolBar('Shape Tools Toolbar')
        self.toolbar.setObjectName('ShapeToolsToolbar')
        self.provider = ShapeToolsProvider()

    def initGui(self):
        self.azDigitizerTool = AzDigitizerTool(self.iface)
        self.lineDigitizerTool = LineDigitizerTool(self.iface)
        
        # Initialize the create shape menu items
        menu = QMenu()
        # Initialize Create Arc Wedge tool
        icon = QIcon(os.path.dirname(__file__) + '/images/arc.png')
        self.createArcAction = menu.addAction(icon, tr('Create arc wedge'), self.createArc)
        self.createArcAction.setObjectName('stCreateArcWedge')
        icon = QIcon(os.path.dirname(__file__) + '/images/donut.png')
        self.createDonutAction = menu.addAction(icon, tr('Create donut'), self.createDonut)
        self.createDonutAction.setObjectName('stCreateDonut')
        icon = QIcon(os.path.dirname(__file__) + '/images/ellipse.png')
        self.createEllipseAction = menu.addAction(icon, tr('Create ellipse'), self.createEllipse)
        self.createEllipseAction.setObjectName('stCreateEllipse')
        icon = QIcon(os.path.dirname(__file__) + '/images/rose.png')
        self.createEllipseRoseAction = menu.addAction(icon, tr('Create ellipse rose'), self.createEllipseRose)
        self.createEllipseRoseAction.setObjectName('stCreateEllipseRose')
        icon = QIcon(os.path.dirname(__file__) + '/images/epicycloid.png')
        self.createEpicycloidAction = menu.addAction(icon, tr('Create epicycloid'), self.createEpicycloid)
        self.createEpicycloidAction.setObjectName('stCreateEpicycloid')
        icon = QIcon(os.path.dirname(__file__) + '/images/heart.png')
        self.createHeartAction = menu.addAction(icon, tr('Create heart'), self.createHeart)
        self.createHeartAction.setObjectName('stCreateHeart')
        icon = QIcon(os.path.dirname(__file__) + '/images/hypocycloid.png')
        self.createHypocycloidAction = menu.addAction(icon, tr('Create hypocycloid'), self.createHypocycloid)
        self.createHypocycloidAction.setObjectName('stCreateHypocycloid')
        icon = QIcon(os.path.dirname(__file__) + '/images/line.png')
        self.createLOBAction = menu.addAction(icon, tr('Create line of bearing'), self.createLOB)
        self.createLOBAction.setObjectName('stCreateLineOfBearing')
        icon = QIcon(os.path.dirname(__file__) + '/images/pie.png')
        self.createPieAction = menu.addAction(icon, tr('Create pie wedge'), self.createPie)
        self.createPieAction.setObjectName('stCreatePie')
        icon = QIcon(os.path.dirname(__file__) + '/images/polyfoil.png')
        self.createPolyfoilAction = menu.addAction(icon, tr('Create polyfoil'), self.createPolyfoil)
        self.createPolyfoilAction.setObjectName('stCreatePolyfoil')
        icon = QIcon(os.path.dirname(__file__) + '/images/polygon.png')
        self.createPolygonAction = menu.addAction(icon, tr('Create polygon'), self.createPolygon)
        self.createPolygonAction.setObjectName('stCreatePolygon')
        icon = QIcon(os.path.dirname(__file__) + '/images/star.png')
        self.createStarAction = menu.addAction(icon, tr('Create star'), self.createStar)
        self.createStarAction.setObjectName('stCreateStar')
        # Add the shape creation tools to the menu
        icon = QIcon(os.path.dirname(__file__) + '/images/shapes.png')
        self.createShapesAction = QAction(icon, tr('Create shapes'), self.iface.mainWindow())
        self.createShapesAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.createShapesAction)
        # Add the shape creation tools to the toolbar
        self.createShapeButton = QToolButton()
        self.createShapeButton.setMenu(menu)
        self.createShapeButton.setDefaultAction(self.createDonutAction)
        self.createShapeButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.createShapeButton.triggered.connect(self.createShapeTriggered)
        self.createShapeToolbar = self.toolbar.addWidget(self.createShapeButton)
        
        # Initialize the XY to Line menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/xyline.png')
        self.xyLineAction = QAction(icon, tr('XY to Line'), self.iface.mainWindow())
        self.xyLineAction.setObjectName('stXYtoLine')        
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)
        
        # Initialize the Geodesic Densifier menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/geodesicDensifier.png')
        self.geodesicDensifyAction = QAction(icon, tr('Geodesic shape densifier'), self.iface.mainWindow())
        self.geodesicDensifyAction.setObjectName('stGeodesicDensifier')        
        self.geodesicDensifyAction.triggered.connect(self.geodesicDensifyTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.toolbar.addAction(self.geodesicDensifyAction)
        
        # Initialize the Geodesic line break menu item
        icon = QIcon(os.path.dirname(__file__) + '/images/idlbreak.png')
        self.geodesicLineBreakAction = QAction(icon, tr('Geodesic line break at -180,180'), self.iface.mainWindow())
        self.geodesicLineBreakAction.setObjectName('stGeodesicLineBreak')        
        self.geodesicLineBreakAction.triggered.connect(self.geodesicLineBreakTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicLineBreakAction)
        self.toolbar.addAction(self.geodesicLineBreakAction)
        
        # Initialize Geodesic Measure Tool
        self.geodesicMeasureTool = GeodesicMeasureTool(self.iface, self.iface.mainWindow())
        icon = QIcon(os.path.dirname(__file__) + '/images/measure.png')
        self.measureAction = QAction(icon, tr('Geodesic measure tool'), self.iface.mainWindow())
        self.measureAction.setObjectName('stGeodesicMeasureTool')        
        self.measureAction.triggered.connect(self.measureTool)
        self.measureAction.setCheckable(True)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureAction)
        self.toolbar.addAction(self.measureAction)
        
        # Initialize Geodesic Measurement layer
        icon = QIcon(os.path.dirname(__file__) + '/images/measureLine.png')
        self.measureLayerAction = QAction(icon, tr('Geodesic measurement layer'), self.iface.mainWindow())
        self.measureLayerAction.setObjectName('stGeodesicLineBreak')        
        self.measureLayerAction.triggered.connect(self.measureLayerTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureLayerAction)
        self.toolbar.addAction(self.measureLayerAction)
        
        menu = QMenu()
        # Initialize Geodesic transformation tool
        icon = QIcon(os.path.dirname(__file__) + '/images/transformShape.png')
        self.transformationsAction = menu.addAction(icon, tr('Geodesic transformations'), self.transformTool)
        self.transformationsAction.setObjectName('stGeodesicTransformations')
        
        icon = QIcon(os.path.dirname(__file__) + '/images/flip.png')
        self.flipRotateAction = menu.addAction(icon, tr('Geodesic flip and rotate'), self.flipRotateTool)
        self.flipRotateAction.setObjectName('stGeodesicFlipRotate')
        
        icon = QIcon(os.path.dirname(__file__) + '/images/flipHorizontal.png')
        self.flipHorizontalAction = menu.addAction(icon, tr('Flip horizontal'), self.flipHorizontalTool)
        self.flipHorizontalAction.setObjectName('stGeodesicFlipHorizontal')
        self.flipHorizontalAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/flipVertical.png')
        self.flipVerticalAction = menu.addAction(icon, tr('Flip vertical'), self.flipVerticalTool)
        self.flipVerticalAction.setObjectName('stGeodesicFlipVertical')
        self.flipVerticalAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotate180.png')
        self.rotate180Action = menu.addAction(icon, tr('Rotate 180\xb0'), self.rotate180Tool)
        self.rotate180Action.setObjectName('stGeodesicRotate180')
        self.rotate180Action.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotatecw.png')
        self.rotate90CWAction = menu.addAction(icon, tr('Rotate 90\xb0 CW'), self.rotate90CWTool)
        self.rotate90CWAction.setObjectName('stGeodesicRotate90CW')
        self.rotate90CWAction.setEnabled(False)
        icon = QIcon(os.path.dirname(__file__) + '/images/rotateccw.png')
        self.rotate90CCWAction = menu.addAction(icon, tr('Rotate 90\xb0 CCW'), self.rotate90CCWTool)
        self.rotate90CCWAction.setObjectName('stGeodesicRotate90CCW')
        self.rotate90CCWAction.setEnabled(False)
        self.transformsAction = QAction(icon, tr('Geodesic Transforms'), self.iface.mainWindow())
        self.transformsAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.transformsAction)
        
        self.transformationButton = QToolButton()
        self.transformationButton.setMenu(menu)
        self.transformationButton.setDefaultAction(self.transformationsAction)
        self.transformationButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.transformationButton.triggered.connect(self.toolButtonTriggered)
        self.tranformToolbar = self.toolbar.addWidget(self.transformationButton)
        
        # Initialize the Azimuth Distance Digitize function
        icon = QIcon(os.path.dirname(__file__) + '/images/dazdigitize.png')
        self.digitizeAction = QAction(icon, tr('Azimuth distance digitizer'), self.iface.mainWindow())
        self.digitizeAction.setObjectName('stAzDistanceDigitizer')        
        self.digitizeAction.triggered.connect(self.setShowAzDigitizerTool)
        self.digitizeAction.setCheckable(True)
        self.digitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.digitizeAction)
        self.toolbar.addAction(self.digitizeAction)
        
        # Initialize the multi point azimuth Digitize function
        icon = QIcon(os.path.dirname(__file__) + '/images/linedigitize.png')
        self.lineDigitizeAction = QAction(icon, tr('Azimuth distance sequence digitizer'), self.iface.mainWindow())
        self.lineDigitizeAction.setObjectName('stLineDigitizer')        
        self.lineDigitizeAction.triggered.connect(self.setShowLineDigitizeTool)
        self.lineDigitizeAction.setCheckable(True)
        self.lineDigitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.lineDigitizeAction)
        self.toolbar.addAction(self.lineDigitizeAction)
        
        # Settings
        icon = QIcon(os.path.dirname(__file__) + '/images/settings.png')
        self.settingsAction = QAction(icon, tr('Settings'), self.iface.mainWindow())
        self.settingsAction.setObjectName('shapeToolsSettings')        
        self.settingsAction.triggered.connect(self.settings)
        self.iface.addPluginToVectorMenu('Shape Tools', self.settingsAction)
        
        # Help
        icon = QIcon(os.path.dirname(__file__) + '/images/help.png')
        self.helpAction = QAction(icon, tr('Shape Tools help'), self.iface.mainWindow())
        self.helpAction.setObjectName('shapeToolsHelp')        
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu('Shape Tools', self.helpAction)
        
        self.iface.currentLayerChanged.connect(self.currentLayerChanged)
        self.canvas.mapToolSet.connect(self.unsetTool)
        self.enableTools()
        
        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)
        
    def unsetTool(self, tool):
        try:
            if not isinstance(tool, GeodesicMeasureTool):
                self.measureAction.setChecked(False)
                self.geodesicMeasureTool.closeDialog()
            if not isinstance(tool, AzDigitizerTool):
                self.digitizeAction.setChecked(False)
            if not isinstance(tool, LineDigitizerTool):
                self.lineDigitizeAction.setChecked(False)
        except:
            pass

    def unload(self):
        self.canvas.unsetMapTool(self.azDigitizerTool)
        self.canvas.unsetMapTool(self.lineDigitizerTool)
        
        # remove from menu
        self.iface.removePluginVectorMenu('Shape Tools', self.createShapesAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicLineBreakAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.measureAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.measureLayerAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.transformsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.digitizeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.lineDigitizeAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.settingsAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.helpAction)
        # Remove from toolbar
        self.iface.removeToolBarIcon(self.createShapeToolbar)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.geodesicDensifyAction)
        self.iface.removeToolBarIcon(self.geodesicLineBreakAction)
        self.iface.removeToolBarIcon(self.measureAction)
        self.iface.removeToolBarIcon(self.measureLayerAction)
        self.iface.removeToolBarIcon(self.transformationsAction)
        self.iface.removeToolBarIcon(self.digitizeAction)
        self.iface.removeToolBarIcon(self.lineDigitizeAction)
        self.iface.removeToolBarIcon(self.tranformToolbar)
        self.azDigitizerTool = None
        self.lineDigitizerTool = None
        # remove the toolbar
        del self.toolbar

        QgsApplication.processingRegistry().removeProvider(self.provider)
    
    def toolButtonTriggered(self, action):
        self.transformationButton.setDefaultAction(action)
    
    def createShapeTriggered(self, action):
        self.createShapeButton.setDefaultAction(action)
        
    def setShowAzDigitizerTool(self):
        self.digitizeAction.setChecked(True)
        self.canvas.setMapTool(self.azDigitizerTool)
        
    def setShowLineDigitizeTool(self):
        self.lineDigitizeAction.setChecked(True)
        self.canvas.setMapTool(self.lineDigitizerTool)
        
    def xyLineTool(self):
        results = processing.execAlgorithmDialog('shapetools:xy2line', {})
        
    def geodesicDensifyTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesicdensifier', {})
        
    def geodesicLineBreakTool(self):
        results = processing.execAlgorithmDialog('shapetools:linebreak', {})
        
    def measureTool(self):
        self.measureAction.setChecked(True)
        self.canvas.setMapTool(self.geodesicMeasureTool)
        
    def createArc(sefl):
        results = processing.execAlgorithmDialog('shapetools:createarc', {})
        
    def createDonut(sefl):
        results = processing.execAlgorithmDialog('shapetools:createdonut', {})
        
    def createEllipse(sefl):
        results = processing.execAlgorithmDialog('shapetools:createellipse', {})
        
    def createEllipseRose(sefl):
        results = processing.execAlgorithmDialog('shapetools:createrose', {})
        
    def createEpicycloid(sefl):
        results = processing.execAlgorithmDialog('shapetools:createepicycloid', {})
        
    def createHeart(sefl):
        results = processing.execAlgorithmDialog('shapetools:createheart', {})
        
    def createHypocycloid(sefl):
        results = processing.execAlgorithmDialog('shapetools:createhypocycloid', {})
        
    def createLOB(sefl):
        results = processing.execAlgorithmDialog('shapetools:createlob', {})
        
    def createPie(sefl):
        results = processing.execAlgorithmDialog('shapetools:createpie', {})
        
    def createPolyfoil(sefl):
        results = processing.execAlgorithmDialog('shapetools:createpolyfoil', {})
        
    def createPolygon(sefl):
        results = processing.execAlgorithmDialog('shapetools:createpolygon', {})
        
    def createStar(sefl):
        results = processing.execAlgorithmDialog('shapetools:createstar', {})
        
    def measureLayerTool(self):
        results = processing.execAlgorithmDialog('shapetools:measurelayer', {})
        
    def transformTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesictransformations', {})
        
    def flipRotateTool(self):
        results = processing.execAlgorithmDialog('shapetools:geodesicflip', {})
        
    def flipHorizontalTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 0)
        
    def flipVerticalTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 1)
        
    def rotate180Tool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 2)
        
    def rotate90CWTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 3)
        
    def rotate90CCWTool(self):
        layer = self.iface.activeLayer()
        flipLayer(self.iface, layer, 4)
        
    def settings(self):
        if self.settingsDialog is None:
            self.settingsDialog = SettingsWidget(self.iface, self.iface.mainWindow())
        self.settingsDialog.show()
    
    def help(self):
        '''Display a help page'''
        url = QUrl.fromLocalFile(os.path.dirname(__file__) + '/index.html').toString()
        webbrowser.open(url, new=2)
        
    def currentLayerChanged(self):
        layer = self.iface.activeLayer()
        if self.previousLayer != None:
            try:
                self.previousLayer.editingStarted.disconnect(self.layerEditingChanged)
            except:
                pass
            try:
                self.previousLayer.editingStopped.disconnect(self.layerEditingChanged)
            except:
                pass
        self.previousLayer = None
        if layer != None:
            if isinstance(layer, QgsVectorLayer):
                layer.editingStarted.connect(self.layerEditingChanged)
                layer.editingStopped.connect(self.layerEditingChanged)
                self.previousLayer = layer
        self.enableTools()

    def layerEditingChanged(self):
        self.enableTools()

    def enableTools(self):
        self.digitizeAction.setEnabled(False)
        self.lineDigitizeAction.setEnabled(False)
        self.flipHorizontalAction.setEnabled(False)
        self.flipVerticalAction.setEnabled(False)
        self.rotate180Action.setEnabled(False)
        self.rotate90CWAction.setEnabled(False)
        self.rotate90CCWAction.setEnabled(False)
        layer = self.iface.activeLayer()
        
        if not layer or not layer.isValid() or (layer.type() != QgsMapLayer.VectorLayer) or not layer.isEditable():
            return
        wkbtype = layer.wkbType()
        geomtype = QgsWkbTypes.geometryType(wkbtype)
        self.lineDigitizeAction.setEnabled(True)
        if geomtype == QgsWkbTypes.PointGeometry or geomtype == QgsWkbTypes.LineGeometry:
            self.digitizeAction.setEnabled(True)
        if geomtype == QgsWkbTypes.LineGeometry or geomtype == QgsWkbTypes.PolygonGeometry :
            self.flipHorizontalAction.setEnabled(True)
            self.flipVerticalAction.setEnabled(True)
            self.rotate180Action.setEnabled(True)
            self.rotate90CWAction.setEnabled(True)
            self.rotate90CCWAction.setEnabled(True)

