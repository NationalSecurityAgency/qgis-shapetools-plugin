PLUGINNAME = shapetools
PY_FILES = shapeTools.py __init__.py LatLon.py ellipse.py quickPoints.py quicklob.py
EXTRAS = metadata.txt
IMAGES=ellipse.png points.png lob.png 
UI_FILES = ellipseDialog.ui pointsDialog.ui lobDialog.ui
RESOURCE_FILES = resources.py

default: compile

compile: $(UI_FILES) $(RESOURCE_FILES)

%.py : %.qrc
	pyrcc4 -o $@ $<

deploy: compile
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/images
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(RESOURCE_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf images $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)

clean:
	rm $(RESOURCE_FILES)

