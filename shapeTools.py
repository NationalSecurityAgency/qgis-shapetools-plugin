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
from qgis.PyQt.QtCore import QUrl, QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolButton
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsWkbTypes, QgsApplication
import processing

from .settings import SettingsWidget
from .geodesicMeasureTool import GeodesicMeasureTool
from .azDigitizer import AzDigitizerTool
from .lineDigitizer import LineDigitizerTool

import os.path
import webbrowser
from .provider import ShapeToolsProvider
from .geodesicFlip import flipLayer
from .stFunctions import InitShapeToolsFunctions, UnloadShapeToolsFunctions

def tr(string):
    return QCoreApplication.translate('@default', string)

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
        self.provider = ShapeToolsProvider()
        # Initialize the plugin path directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        try:
            locale = QSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'shapeTools_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.azDigitizerTool = AzDigitizerTool(self.iface)
        self.lineDigitizerTool = LineDigitizerTool(self.iface)

        # Initialie the Shape Tools toolbar
        self.toolbar = self.iface.addToolBar('Shape Tools Toolbar')
        self.toolbar.setObjectName('ShapeToolsToolbar')
        self.toolbar.setToolTip('Shape Tools Toolbar')

        # Initialize the create shape menu items
        menu = QMenu()
        menu.setObjectName('stCreateShapes')
        # Initialize Create Arc Wedge tool
        icon = QIcon(self.plugin_dir + '/images/arc.png')
        self.createArcAction = menu.addAction(icon, tr('Create arc wedge'), self.createArc)
        self.createArcAction.setObjectName('stCreateArcWedge')

        icon = QIcon(self.plugin_dir + '/images/circle.png')
        self.createCircleAction = menu.addAction(icon, tr('Create circle'), self.createCircle)
        self.createCircleAction.setObjectName('stCreateCircle')

        icon = QIcon(self.plugin_dir + '/images/donut.png')
        self.createDonutAction = menu.addAction(icon, tr('Create donut'), self.createDonut)
        self.createDonutAction.setObjectName('stCreateDonut')

        icon = QIcon(self.plugin_dir + '/images/ellipse.png')
        self.createEllipseAction = menu.addAction(icon, tr('Create ellipse'), self.createEllipse)
        self.createEllipseAction.setObjectName('stCreateEllipse')

        icon = QIcon(self.plugin_dir + '/images/rose.png')
        self.createEllipseRoseAction = menu.addAction(icon, tr('Create ellipse rose'), self.createEllipseRose)
        self.createEllipseRoseAction.setObjectName('stCreateEllipseRose')

        icon = QIcon(self.plugin_dir + '/images/epicycloid.png')
        self.createEpicycloidAction = menu.addAction(icon, tr('Create epicycloid'), self.createEpicycloid)
        self.createEpicycloidAction.setObjectName('stCreateEpicycloid')

        icon = QIcon(self.plugin_dir + '/images/gear.png')
        self.createGearAction = menu.addAction(icon, tr('Create gear'), self.createGear)
        self.createGearAction.setObjectName('stCreateGear')

        icon = QIcon(self.plugin_dir + '/images/heart.png')
        self.createHeartAction = menu.addAction(icon, tr('Create heart'), self.createHeart)
        self.createHeartAction.setObjectName('stCreateHeart')

        icon = QIcon(self.plugin_dir + '/images/hypocycloid.png')
        self.createHypocycloidAction = menu.addAction(icon, tr('Create hypocycloid'), self.createHypocycloid)
        self.createHypocycloidAction.setObjectName('stCreateHypocycloid')

        icon = QIcon(self.plugin_dir + '/images/line.png')
        self.createLOBAction = menu.addAction(icon, tr('Create line of bearing'), self.createLOB)
        self.createLOBAction.setObjectName('stCreateLineOfBearing')

        icon = QIcon(self.plugin_dir + '/images/ptline.png')
        self.createPointLOBAction = menu.addAction(icon, tr('Create points along a bearing'), self.createPointLOB)
        self.createPointLOBAction.setObjectName('stCreatePointLineOfBearing')

        icon = QIcon(self.plugin_dir + '/images/pie.png')
        self.createPieAction = menu.addAction(icon, tr('Create pie wedge'), self.createPie)
        self.createPieAction.setObjectName('stCreatePie')

        icon = QIcon(self.plugin_dir + '/images/polyfoil.png')
        self.createPolyfoilAction = menu.addAction(icon, tr('Create polyfoil'), self.createPolyfoil)
        self.createPolyfoilAction.setObjectName('stCreatePolyfoil')

        icon = QIcon(self.plugin_dir + '/images/polygon.png')
        self.createPolygonAction = menu.addAction(icon, tr('Create polygon'), self.createPolygon)
        self.createPolygonAction.setObjectName('stCreatePolygon')

        icon = QIcon(self.plugin_dir + '/images/radialLines.png')
        self.createPolygonAction = menu.addAction(icon, tr('Create radial lines'), self.createRadialLines)
        self.createPolygonAction.setObjectName('stCreateRadialLines')

        icon = QIcon(self.plugin_dir + '/images/concentricrings.png')
        self.createRingsAction = menu.addAction(icon, tr('Create rings'), self.createRings)
        self.createRingsAction.setObjectName('stCreateRings')

        icon = QIcon(self.plugin_dir + '/images/star.png')
        self.createStarAction = menu.addAction(icon, tr('Create star'), self.createStar)
        self.createStarAction.setObjectName('stCreateStar')

        # Add the shape creation tools to the menu
        icon = QIcon(self.plugin_dir + '/images/shapes.png')
        self.createShapesAction = QAction(icon, tr('Create geodesic shapes'), self.iface.mainWindow())
        self.createShapesAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.createShapesAction)

        # Add the shape creation tools to the toolbar
        self.createShapeButton = QToolButton()
        self.createShapeButton.setMenu(menu)
        self.createShapeButton.setDefaultAction(self.createDonutAction)
        self.createShapeButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.createShapeButton.triggered.connect(self.createShapeTriggered)
        self.createShapeToolbar = self.toolbar.addWidget(self.createShapeButton)
        self.createShapeToolbar.setObjectName('stCreateShape')

        # Initialize the interactive shape menu items
        menu = QMenu()
        menu.setObjectName('stInteractiveShapes')
        # Initialize Interactive concentric rings
        icon = QIcon(self.plugin_dir + '/images/concentricrings.png')
        self.interactiveRingsAction = menu.addAction(icon, tr('Interactive concentric rings'), self.interactiveRings)
        self.interactiveRingsAction.setObjectName('stInteractiveRings')

        icon = QIcon(self.plugin_dir + '/images/donut.png')
        self.interactiveDonutAction = menu.addAction(icon, tr('Interactive donut'), self.interactiveDonut)
        self.interactiveDonutAction.setObjectName('stInteractiveDonut')

        # Add the interactive creation tools to the menu
        icon = QIcon(self.plugin_dir + '/images/concentricrings.png')
        self.interactiveShapesAction = QAction(icon, tr('Interactive geodesic shapes'), self.iface.mainWindow())
        self.interactiveShapesAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.interactiveShapesAction)

        # Add the interactive creation tools to the toolbar
        self.createInteractiveButton = QToolButton()
        self.createInteractiveButton.setMenu(menu)
        self.createInteractiveButton.setDefaultAction(self.interactiveRingsAction)
        self.createInteractiveButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.createInteractiveButton.triggered.connect(self.interactiveShapeTriggered)
        self.createInteractiveShapeToolbar = self.toolbar.addWidget(self.createInteractiveButton)
        self.createInteractiveShapeToolbar.setObjectName('stInteractiveShape')

        # Initialize the XY to Line menu item
        icon = QIcon(self.plugin_dir + '/images/xyline.svg')
        self.xyLineAction = QAction(icon, tr('XY to line'), self.iface.mainWindow())
        self.xyLineAction.setObjectName('stXYtoLine')
        self.xyLineAction.triggered.connect(self.xyLineTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.xyLineAction)
        self.toolbar.addAction(self.xyLineAction)

        # Initialize the Geodesic Densifier menu item
        icon = QIcon(self.plugin_dir + '/images/geodesicDensifier.svg')
        self.geodesicDensifyAction = QAction(icon, tr('Geodesic shape densifier'), self.iface.mainWindow())
        self.geodesicDensifyAction.setObjectName('stGeodesicDensifier')
        self.geodesicDensifyAction.triggered.connect(self.geodesicDensifyTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.toolbar.addAction(self.geodesicDensifyAction)
        
        # Initialize the Geodesic decimation menu items
        menu = QMenu()
        menu.setObjectName('stGeodesicDecimations')
        icon = QIcon(self.plugin_dir + '/images/geodesicLineDecimate.svg')
        self.lineDecimateAction = menu.addAction(icon, tr('Geodesic line decimate'), self.lineDecimateTool)
        self.lineDecimateAction.setObjectName('stGeodesicLineDecimate')
        icon = QIcon(self.plugin_dir + '/images/geodesicPointDecimate.svg')
        self.pointDecimateAction = menu.addAction(icon, tr('Geodesic point decimate'), self.pointDecimateTool)
        self.pointDecimateAction.setObjectName('stGeodesicPointDecimate')
        # Add the decimation tools to the menu
        icon = QIcon(self.plugin_dir + '/images/geodesicLineDecimate.svg')
        self.simplifyGeomAction = QAction(icon, tr('Geodesic geometry simplification'), self.iface.mainWindow())
        self.simplifyGeomAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.simplifyGeomAction)
        # Add the shape creation tools to the toolbar
        self.simplifyButton = QToolButton()
        self.simplifyButton.setMenu(menu)
        self.simplifyButton.setDefaultAction(self.lineDecimateAction)
        self.simplifyButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.simplifyButton.triggered.connect(self.simplifyTriggered)
        self.simplifyToolbar = self.toolbar.addWidget(self.simplifyButton)
        self.simplifyToolbar.setObjectName('stGeodesicSimplify')

        # Initialize the Geodesic line break menu item
        icon = QIcon(self.plugin_dir + '/images/idlbreak.svg')
        self.geodesicLineBreakAction = QAction(icon, tr('Geodesic line break at -180,180'), self.iface.mainWindow())
        self.geodesicLineBreakAction.setObjectName('stGeodesicLineBreak')
        self.geodesicLineBreakAction.triggered.connect(self.geodesicLineBreakTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.geodesicLineBreakAction)
        self.toolbar.addAction(self.geodesicLineBreakAction)

        # Initialize Geodesic Measure Tool
        self.geodesicMeasureTool = GeodesicMeasureTool(self, self.iface, self.iface.mainWindow())
        icon = QIcon(self.plugin_dir + '/images/measure.svg')
        self.measureAction = QAction(icon, tr('Geodesic measure tool'), self.iface.mainWindow())
        self.measureAction.setObjectName('stGeodesicMeasureTool')
        self.measureAction.triggered.connect(self.measureTool)
        self.measureAction.setCheckable(True)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureAction)
        self.toolbar.addAction(self.measureAction)

        # Initialize Geodesic Measurement layer
        icon = QIcon(self.plugin_dir + '/images/measureLine.svg')
        self.measureLayerAction = QAction(icon, tr('Geodesic measurement layer'), self.iface.mainWindow())
        self.measureLayerAction.setObjectName('stGeodesicLineBreak')
        self.measureLayerAction.triggered.connect(self.measureLayerTool)
        self.iface.addPluginToVectorMenu('Shape Tools', self.measureLayerAction)
        self.toolbar.addAction(self.measureLayerAction)

        menu = QMenu()
        menu.setObjectName('stGeodesicTransformationsMenu')
        # Initialize Geodesic transformation tool
        icon = QIcon(self.plugin_dir + '/images/transformShape.svg')
        self.transformationsAction = menu.addAction(icon, tr('Geodesic transformations'), self.transformTool)
        self.transformationsAction.setObjectName('stGeodesicTransformations')

        icon = QIcon(self.plugin_dir + '/images/flip.svg')
        self.flipRotateAction = menu.addAction(icon, tr('Geodesic flip and rotate'), self.flipRotateTool)
        self.flipRotateAction.setObjectName('stGeodesicFlipRotate')

        icon = QIcon(self.plugin_dir + '/images/flipHorizontal.svg')
        self.flipHorizontalAction = menu.addAction(icon, tr('Flip horizontal'), self.flipHorizontalTool)
        self.flipHorizontalAction.setObjectName('stGeodesicFlipHorizontal')
        self.flipHorizontalAction.setEnabled(False)
        icon = QIcon(self.plugin_dir + '/images/flipVertical.svg')
        self.flipVerticalAction = menu.addAction(icon, tr('Flip vertical'), self.flipVerticalTool)
        self.flipVerticalAction.setObjectName('stGeodesicFlipVertical')
        self.flipVerticalAction.setEnabled(False)
        icon = QIcon(self.plugin_dir + '/images/rotate180.svg')
        self.rotate180Action = menu.addAction(icon, tr('Rotate 180\xb0'), self.rotate180Tool)
        self.rotate180Action.setObjectName('stGeodesicRotate180')
        self.rotate180Action.setEnabled(False)
        icon = QIcon(self.plugin_dir + '/images/rotatecw.svg')
        self.rotate90CWAction = menu.addAction(icon, tr('Rotate 90\xb0 CW'), self.rotate90CWTool)
        self.rotate90CWAction.setObjectName('stGeodesicRotate90CW')
        self.rotate90CWAction.setEnabled(False)
        icon = QIcon(self.plugin_dir + '/images/rotateccw.svg')
        self.rotate90CCWAction = menu.addAction(icon, tr('Rotate 90\xb0 CCW'), self.rotate90CCWTool)
        self.rotate90CCWAction.setObjectName('stGeodesicRotate90CCW')
        self.rotate90CCWAction.setEnabled(False)
        self.transformsAction = QAction(icon, tr('Geodesic transforms'), self.iface.mainWindow())
        self.transformsAction.setMenu(menu)
        self.iface.addPluginToVectorMenu('Shape Tools', self.transformsAction)

        self.transformationButton = QToolButton()
        self.transformationButton.setMenu(menu)
        self.transformationButton.setDefaultAction(self.transformationsAction)
        self.transformationButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.transformationButton.triggered.connect(self.toolButtonTriggered)
        self.tranformToolbar = self.toolbar.addWidget(self.transformationButton)
        self.tranformToolbar.setObjectName('stGeodesicTransformation')

        # Initialize the Azimuth Distance Digitize function
        icon = QIcon(self.plugin_dir + '/images/dazdigitize.svg')
        self.digitizeAction = QAction(icon, tr('Azimuth distance digitizer'), self.iface.mainWindow())
        self.digitizeAction.setObjectName('stAzDistanceDigitizer')
        self.digitizeAction.triggered.connect(self.setShowAzDigitizerTool)
        self.digitizeAction.setCheckable(True)
        self.digitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.digitizeAction)
        self.toolbar.addAction(self.digitizeAction)

        # Initialize the multi point azimuth Digitize function
        icon = QIcon(self.plugin_dir + '/images/linedigitize.svg')
        self.lineDigitizeAction = QAction(icon, tr('Azimuth distance sequence digitizer'), self.iface.mainWindow())
        self.lineDigitizeAction.setObjectName('stLineDigitizer')
        self.lineDigitizeAction.triggered.connect(self.setShowLineDigitizeTool)
        self.lineDigitizeAction.setCheckable(True)
        self.lineDigitizeAction.setEnabled(False)
        self.iface.addPluginToVectorMenu(u'Shape Tools', self.lineDigitizeAction)
        self.toolbar.addAction(self.lineDigitizeAction)

        # Settings
        icon = QIcon(':/images/themes/default/mActionOptions.svg')
        self.settingsAction = QAction(icon, tr('Settings'), self.iface.mainWindow())
        self.settingsAction.setObjectName('shapeToolsSettings')
        self.settingsAction.triggered.connect(self.settings)
        self.iface.addPluginToVectorMenu('Shape Tools', self.settingsAction)

        # Help
        icon = QIcon(self.plugin_dir + '/images/help.svg')
        self.helpAction = QAction(icon, tr('Help'), self.iface.mainWindow())
        self.helpAction.setObjectName('shapeToolsHelp')
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToVectorMenu('Shape Tools', self.helpAction)

        self.iface.currentLayerChanged.connect(self.currentLayerChanged)
        self.canvas.mapToolSet.connect(self.unsetTool)
        self.enableTools()

        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)
        
        InitShapeToolsFunctions()

    def unsetTool(self, tool):
        try:
            if not isinstance(tool, GeodesicMeasureTool):
                self.measureAction.setChecked(False)
                self.geodesicMeasureTool.endInteractiveLine()
            if not isinstance(tool, AzDigitizerTool):
                self.digitizeAction.setChecked(False)
            if not isinstance(tool, LineDigitizerTool):
                self.lineDigitizeAction.setChecked(False)
        except Exception:
            pass

    def unload(self):
        self.canvas.unsetMapTool(self.azDigitizerTool)
        self.canvas.unsetMapTool(self.lineDigitizerTool)

        # remove from menu
        self.iface.removePluginVectorMenu('Shape Tools', self.createShapesAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.interactiveShapesAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.xyLineAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.geodesicDensifyAction)
        self.iface.removePluginVectorMenu('Shape Tools', self.simplifyGeomAction)
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
        self.iface.removeToolBarIcon(self.createInteractiveShapeToolbar)
        self.iface.removeToolBarIcon(self.xyLineAction)
        self.iface.removeToolBarIcon(self.geodesicDensifyAction)
        self.iface.removeToolBarIcon(self.simplifyToolbar)
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
        UnloadShapeToolsFunctions()

    def toolButtonTriggered(self, action):
        self.transformationButton.setDefaultAction(action)

    def createShapeTriggered(self, action):
        self.createShapeButton.setDefaultAction(action)

    def interactiveShapeTriggered(self, action):
        self.createInteractiveButton.setDefaultAction(action)

    def simplifyTriggered(self, action):
        self.simplifyButton.setDefaultAction(action)

    def setShowAzDigitizerTool(self):
        self.digitizeAction.setChecked(True)
        self.canvas.setMapTool(self.azDigitizerTool)

    def setShowLineDigitizeTool(self):
        self.lineDigitizeAction.setChecked(True)
        self.canvas.setMapTool(self.lineDigitizerTool)

    def xyLineTool(self):
        processing.execAlgorithmDialog('shapetools:xy2line', {})

    def geodesicDensifyTool(self):
        processing.execAlgorithmDialog('shapetools:geodesicdensifier', {})

    def pointDecimateTool(self):
        processing.execAlgorithmDialog('shapetools:geodesicpointdecimate', {})

    def lineDecimateTool(self):
        processing.execAlgorithmDialog('shapetools:geodesiclinedecimate', {})

    def geodesicLineBreakTool(self):
        processing.execAlgorithmDialog('shapetools:linebreak', {})

    def measureTool(self):
        self.measureAction.setChecked(True)
        self.canvas.setMapTool(self.geodesicMeasureTool)

    def createArc(self):
        processing.execAlgorithmDialog('shapetools:createarc', {})

    def createCircle(self):
        processing.execAlgorithmDialog('shapetools:createcircle', {})

    def createDonut(self):
        processing.execAlgorithmDialog('shapetools:createdonut', {})

    def createRings(self):
        processing.execAlgorithmDialog('shapetools:createrings', {})

    def createEllipse(self):
        processing.execAlgorithmDialog('shapetools:createellipse', {})

    def createEllipseRose(self):
        processing.execAlgorithmDialog('shapetools:createrose', {})

    def createEpicycloid(self):
        processing.execAlgorithmDialog('shapetools:createepicycloid', {})

    def createGear(self):
        processing.execAlgorithmDialog('shapetools:creategear', {})

    def createHeart(self):
        processing.execAlgorithmDialog('shapetools:createheart', {})

    def createHypocycloid(self):
        processing.execAlgorithmDialog('shapetools:createhypocycloid', {})

    def createLOB(self):
        processing.execAlgorithmDialog('shapetools:createlob', {})

    def createPointLOB(self):
        processing.execAlgorithmDialog('shapetools:createpointsalonglob', {})

    def createPie(self):
        processing.execAlgorithmDialog('shapetools:createpie', {})

    def createPolyfoil(self):
        processing.execAlgorithmDialog('shapetools:createpolyfoil', {})

    def createPolygon(self):
        processing.execAlgorithmDialog('shapetools:createpolygon', {})

    def createRadialLines(self):
        processing.execAlgorithmDialog('shapetools:createradiallines', {})

    def createStar(self):
        processing.execAlgorithmDialog('shapetools:createstar', {})

    def interactiveRings(self):
        processing.execAlgorithmDialog('shapetools:interactiverings', {})

    def interactiveDonut(self):
        processing.execAlgorithmDialog('shapetools:interactivedonut', {})

    def measureLayerTool(self):
        processing.execAlgorithmDialog('shapetools:measurelayer', {})

    def transformTool(self):
        processing.execAlgorithmDialog('shapetools:geodesictransformations', {})

    def flipRotateTool(self):
        processing.execAlgorithmDialog('shapetools:geodesicflip', {})

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
        url = QUrl.fromLocalFile(self.plugin_dir + '/index.html').toString()
        webbrowser.open(url, new=2)

    def currentLayerChanged(self):
        layer = self.iface.activeLayer()
        if self.previousLayer is not None:
            try:
                self.previousLayer.editingStarted.disconnect(self.layerEditingChanged)
            except Exception:
                pass
            try:
                self.previousLayer.editingStopped.disconnect(self.layerEditingChanged)
            except Exception:
                pass
        self.previousLayer = None
        if layer is not None:
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
        if geomtype == QgsWkbTypes.LineGeometry or geomtype == QgsWkbTypes.PolygonGeometry:
            self.flipHorizontalAction.setEnabled(True)
            self.flipVerticalAction.setEnabled(True)
            self.rotate180Action.setEnabled(True)
            self.rotate90CWAction.setEnabled(True)
            self.rotate90CCWAction.setEnabled(True)
