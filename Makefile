PLUGINNAME = shapetools
PY_FILES = shapeTools.py __init__.py LatLon.py vector2Shape.py xyToLine.py settings.py geodesicDensify.py geodesicMeasureTool.py provider.py
EXTRAS = metadata.txt

deploy:
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/images
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf images $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf ui $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf doc $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf ext-libs $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf helphead.html $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/index.html
	python -m markdown -x markdown.extensions.headerid readme.md >> $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/index.html
	echo '</body>' >> $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/index.html
