PLUGINNAME = shapetools
PLUGINS = "$(HOME)"/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/$(PLUGINNAME)
PY_FILES = shapeTools.py __init__.py xyToLine.py settings.py geodesicDensify.py geodesicLayerMeasure.py geodesicMeasureTool.py azDigitizer.py lineDigitizer.py geodesicFlip.py provider.py createDonut.py createLob.py createPolygon.py createPie.py createArc.py createStar.py createRose.py createHypocycloid.py createEpicycloid.py createPolyfoil.py createHeart.py utils.py idlbreakline.py createEllipse.py geodesicTransformation.py
EXTRAS = metadata.txt

deploy:
	mkdir -p $(PLUGINS)
	mkdir -p $(PLUGINS)/images
	mkdir -p $(PLUGINS)/i18n
	cp -vf $(PY_FILES) $(PLUGINS)
	cp -vf $(EXTRAS) $(PLUGINS)
	cp -vrf images $(PLUGINS)
	cp -vrf ui $(PLUGINS)
	cp -vrf doc $(PLUGINS)
	cp -vrf ext-libs $(PLUGINS)
	cp -vf helphead.html $(PLUGINS)/index.html
	python -m markdown -x markdown.extensions.headerid readme.md >> $(PLUGINS)/index.html
	echo '</body>' >> $(PLUGINS)/index.html
