PLUGINNAME = shapetools
PY_FILES = shapeTools.py __init__.py LatLon.py vector2Shape.py xyToLine.py
EXTRAS = metadata.txt
UI_FILES = vector2Shape.ui xyToLineDialog.ui

default: compile

compile: $(UI_FILES)

%.py : %.qrc
	pyrcc4 -o $@ $<

deploy: compile
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	mkdir -p $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)/images
	cp -vf $(PY_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)
	cp -vrf images $(HOME)/.qgis2/python/plugins/$(PLUGINNAME)

