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
# geographiclib was added to QGIS around QGIS 3.12
try:
    import geographiclib
except Exception:
    import os
    import site
    site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/ext-libs'))

def classFactory(iface):
    if iface:
        from .shapeTools import ShapeTools
        return ShapeTools(iface)
    else:
        # This is used when the plugin is loaded from the command line command qgis_process
        from .shapeToolsProcessing import ShapeTools
        return ShapeTools()
