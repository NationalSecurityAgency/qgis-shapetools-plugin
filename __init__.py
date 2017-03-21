import sys 
import os 
import site

site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/ext-libs'))

def classFactory(iface):
    from .shapeTools import ShapeTools
    return ShapeTools(iface)
