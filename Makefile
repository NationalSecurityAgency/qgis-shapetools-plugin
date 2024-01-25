PLUGINNAME = shapetools
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = __init__.py azDigitizer.py compass.py createArc.py createCircle.py createDonut.py createEllipse.py createEpicycloid.py createGear.py createHeart.py createHypocycloid.py createLob.py createPie.py createPointsAlongLob.py createPolyfoil.py createPolygon.py createRadialLines.py createRings.py createRose.py createStar.py geodesicDensify.py geodesicFlip.py geodesicLayerMeasure.py geodesicLineDecimate.py geodesicMeasureTool.py geodesicPointDecimate.py geodesicTransformation.py idlbreakline.py interactiveConcentricRings.py interactiveCreateDonut.py lineDigitizer.py provider.py settings.py shapeTools.py shapeToolsProcessing.py stFunctions.py utils.py xyToLine.py
EXTRAS = metadata.txt icon.png LICENSE

deploy:
	mkdir -p $(PLUGINS)
	mkdir -p $(PLUGINS)/images
	mkdir -p $(PLUGINS)/i18n
	cp -vf i18n/shapeTools_zh.qm $(PLUGINS)/i18n
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
	cp -vrf images $(PLUGINS)
	cp -vrf ui $(PLUGINS)
	cp -vrf doc $(PLUGINS)
	cp -vrf ext-libs $(PLUGINS)
	cp -vf helphead.html index.html
	python -m markdown -x extra readme.md >> index.html
	echo '</body>' >> index.html
	cp -vf index.html $(PLUGINS)/index.html
