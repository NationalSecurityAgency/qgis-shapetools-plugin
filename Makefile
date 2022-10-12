PLUGINNAME = shapetools
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = shapeTools.py __init__.py xyToLine.py settings.py geodesicDensify.py geodesicPointDecimate.py geodesicLineDecimate.py geodesicLayerMeasure.py geodesicMeasureTool.py azDigitizer.py lineDigitizer.py geodesicFlip.py provider.py createDonut.py createGear.py createLob.py createPointsAlongLob.py createPolygon.py createPie.py createRadialLines.py createArc.py createStar.py createRose.py createHypocycloid.py createEpicycloid.py createPolyfoil.py createHeart.py utils.py idlbreakline.py createEllipse.py geodesicTransformation.py stFunctions.py
EXTRAS = metadata.txt icon.png

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
