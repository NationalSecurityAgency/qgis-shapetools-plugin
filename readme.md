# QGIS Shape Tools Plugin

***Shape Tools*** is a collection of geodesic tools that are installed in the Vector menu, on the toolbar, or in the Processing Toolbox. Geodesic is the shortest path between two points on the Earth, a spheroid, or an ellipsoid. 

* ![Create shapes](images/shapes.png) **Create shapes** processes a point vector layer to create ellipses, lines of bearing, pie wedges, donuts, arc wedges, polygons, stars, ellipse roses, hypocyloids, polyfoils, epicyloids, and hearts based on the table's fields and parameters from the dialog box. All use geodesic math to calculate the shapes. 
* ![XY to Line](images/xyline.png) **XY to Line** uses pairs of coordinates from each layer's records to create geodesic lines in between. The input can be a point vector layer or a table layer that contains pairs of coordinates.
* ![Geodesic line break](images/idlbreak.png) **Geodesic line break at -180,180** breaks lines at the International Date Line at -180,180 degrees longitude for a more pleasing visual look.
* ![Geodesic densifier](images/geodesicDensifier.png) **Geodesic densifier** densifies a line or polygon vector layer by adding geodesic points in between each line segment whenever the distance between vertices exceeds a certain threshold. This creates a geodesic path that gives it a nice smooth curved appearance. If the vector layer is a line, it can also draw a geodesic line just between the beginning and ending points.
* ![Geodesic line decimate](images/geodesicLineDecimate.png) **Geodesic line decimate** removes vertices in a line that who's geodesic distance is less than a certain value.
* ![Geodesic point decimate](images/geodesicPointDecimate.png) **Geodesic point decimate** removes points in a point layer who's geodesic distance is less than a certain value or who's time difference between points is less than a certain value.
* ![Geodesic measure tool](images/measure.png) **Geodesic measure tool** provides geodesic line measuring, similar to that implemented in Google Earth.
* ![Geodesic measurement layer](images/measureLine.png) **Geodesic measurement layer** converts a polygon or line layer a new layer with all geometries measured and labeled.
* ![Geodesic transfomations tool](images/transformShape.png) **Geodesic transformations** can geodesically scale, rotate, and translate points, lines and polygons. Each vector feature retains their relative dimensions no matter what the projection is.
* ![Geodesic flip and rotate](images/flip.png) **Geodesic flip & rotate tools** provide the following geodesic vector transformations: Flip horizontally, flip vertically, rotate by 180 degrees, rotate clockwise by 90 degrees, and rotate counter clockwise by 90 degrees.
* ![Azimuth, distance digitizer](images/dazdigitize.png) **Azimuth, distance digitizer** creates a new point at a certain azimuth/bearing and distance or creates a geodesic line from the point clicked to a point in the azimuth direction located at a distance.
* ![Azimuth distance sequence digitizer](images/linedigitize.png) **Azimuth distance sequence digitizer** digitizes a sequence of azimuth/bearing, distance pairs to create a series of points, a line, or a polygon.

## Contents

* [Create Shapes](#create-shapes)
* [XY to Line](#xy-to-line)
* [Geodesic Line Break](#geodesic-line-break)
* [Geodesic Densifier](#geodesic-densifier)
* [Geodesic Line Decimate](#geodesic-line-decimate)
* [Geodesic Point Decimate](#geodesic-point-decimate)
* [Geodesic Measure Tool](#geodesic-measure)
* [Geodesic Measurement Layer](#geodesic-measure-layer)
* [Geodesic Transformations](#geodesic-transformations)
* [Geodesic Flip and Rotate Tools](#geodesic-flip)
* [Azimuth, Distance Digitizer](#azimuth-distance)
* [Azimuth Distance Sequence Digitizer](#azimuth-distance-sequence)
* [Settings](#settings)

## <a name="create-shapes"></a> ![Create Shapes](images/shapes.png) Create Shapes

<div style="text-align:center"><img src="doc/examples.png" alt="Examples"></div>

All of these shapes can be accessed from the ShapeTools processing algorithms.

<div style="text-align:center"><img src="doc/processing-shapes.jpg" alt="Processing Shapes"></div>

They can also be accessed from the *Vector->Shape Tools->Create Shapes* menu.

<div style="text-align:center"><img src="doc/menu-shapes.jpg" alt="Create Shapes"></div>

Ellipses, lines of bearing, pie wedges, donuts, arc wedges, multi-sided polygons, stars, ellipse roses, hypocycloids, polyfoils, epicycloids, and hearts can be created from parameters in the layer data or from default parameters in the *Create Shapes* tool. Note that if the output layer uses a temporary layer, it will not be saved with the QGIS project. You need to manually save the layer or use the [Memory Layer Saver](http://plugins.qgis.org/plugins/MemoryLayerSaver/) plugin.

The following are details for creating each shape. All of the shapes are created centered about the point or from the point. Common elements are:

* **Input point layer** - Select the desired points layer.
* **Output layer** - Select either ***[Create temporary layer]***, ***Save to file...***, ***Save to GeoPackage...***, or ***Save to PostGIS Table...***.
* **Shape Type** - Specify whether the shape should be drawn as a polygon or as a line.
* **Add input geometry fields to output table** - If checked, the input point geometry will be added to fields in the output shape table. By default these fields are named ***geom_x*** and ***geom_y***, but can be changed in **Settings**.

### Ellipse

<div style="text-align:center"><img src="doc/ellipse.jpg" alt="Ellipse"></div>

Select a point vector layer and an output layer or use the default temporary output layer. Then select the specific ellipse parameters. The semi-major axis of the ellipse runs along the orientation axis. The orientation the axis is measured in degrees in a clockwise direction from the north line. The units of measure for semi-major, and semi-minor lengths are defined by ***Radius units***.

If a field in the layer represents the semi-major axis, semi-minor axis, or orientation of axis, then the field can be selected and the data from the layer will be used, otherwise the default values will be used.

### Line of Bearing

**Bearing** is the angle measured in degrees, in a clockwise direction from the north line. A **line of bearing** is the line drawn from a starting point in the direction of the **bearing** or azimuth for the selected distance. The line of bearing uses geodesic math to find the shortest path and is accurate along the Earth's surface. 

### Pie Wedge

If **Azimuth mode** it is set to *Use beginning and ending azimuths*, then the pie wedge focal point starts at the point layer's geometry extending out to the specified radius. It starts at the **Starting azimuth** going in a clockwise direction to the **Ending azimuth**. If **Azimuth mode** is set to *Use center azimuth and width*, then a center azimuth is specified which becomes the center of the pie wedge with an arc length of **Azimuth width**. The pie wedge can either be defined from the point vector layer data fields or from the **Default** parameters. **Drawing segments** is the number of line segments that would be used to draw a full circle. A wedge will use a proportionally smaller number of segments. Making this larger will give smoother results, but will be slower rendering the shapes.

### Donut

Create a donut shape. The inner and outer radius is specified either as default values or from the attribute table. If the inner radius is 0 then a solid circle is drawn. **Number of drawing segments** defines how many line segments it uses to create the circle. A larger value will produce a smoother circle, but will take more time to draw.

### Arc wedge

In essence this takes a wedge of a donut shape. The parameters are similar to **Pie wedge** and **Donut**.

### Polygon

Create an N-sided polygon centered on the vector point. The vertices of the polygon lie on a circle of the default radius.

### Star

Create an N-pointed star with the outer vertices located on a circle defined by the outer radius. The inner vertices are located along the circle defined by the inner radius. One of the radius' can be negative which gives an interesting shape.

### Ellipse Rose

Create an N-petal rose. The distance from the center to the outer petals are defined by the radius.

### Hypocycloid

Create an N-pointed hypocycloid. A hypocycloid is defined as the curve traced by a point on the circumference of a circle that is rolling on the interior of another circle. The distance from the center to the outer cusps are defined by the radius.

### Polyfoil

Create an N-leafed polyfoil. The distance from the center to the outer leafs are defined by the radius.

### Epicycloid

Create an N-leafed epicycloid. The distance from the center to the outer edge is defined by the radius.

### Heart

Create a mathematical heart which fits within the circle defined by its radius.

## <a name="xy-to-line"></a> ![XY to Line](images/xyline.png) XY to Line
This creates geodesic, great circle, or simple lines based on starting and ending coordinates in each table record. One of the coordinates can be from a point layer geometry or both can come from the attribute table data where each record has a starting x-coordinate, starting y-coordinate, and an ending x-coordinate and ending y-coordinate.

<div style="text-align:center"><img src="doc/xytoline.jpg" alt="XY to Line"></div>

**Input Layer** - This can either be a point layer, a simple table, or any other vector data set that has two coordinates among its data fields. For example a CSV file containing starting and ending coordinates could be imported using ***Layer->Add Layer->Add Delimited Text Layer...*** located in the QGIS menu. From this dialog box the user can specify one of the coordinates for the layer's geometry or **No Geometry** can be used. Both types of layers will be visible to **XY to Line.**

**Output point layer** - Optional points layer that can be created in QGIS. It can contain the starting point, ending point, both points, or no points in which case it will not be created. 

**Output line layer** - Output line layer file that is created in QGIS.

**Input CRS for coordinates within the vector fields** - CRS of the input coordinates within the table data fields.

**Output layer CRS** - CRS of the output line and point layers.

**Line type** - 1) **Geodesic** creates a highly accurate shortest path between two points. 2) **Great Circle** creates a *Great Circle* arc between the two points. 3) **Simple Line** creates a non-geodesic straight line between the two points. 

**Starting point** - Specify whether to use the *Layer's point geometry* (not applicable for layers that don't have Point geometry) or to specify the **Starting X Field (lon)** and **Starting Y Field (lat)** from the layer's fields.

**Ending Point** - Specify whether to use the *Layer's geometry* (not applicable for layers that don't have Point geometry) or to specify the **Ending X Field (lon)** and **Ending Y Field (lat)** from the layer's fields.

**Show starting point** - If checked the output point layer will include an entry for the starting point if an **Output point layer** has been specified.

**Show ending point** - If checked the output point layer will include an entry for the ending point if an **Output point layer** has been specified.

**Break lines at -180, 180 boundary for better rendering** - Depending on the QGIS projection when lines cross the international date line, strange behavior may occur. Checking this box breaks the line at the -180, 180 boundary in a way that it displays properly.

This function can also be accessed from the **Processing Toolbox**.

<div style="text-align:center"><img src="doc/processing.jpg" alt="Processing Toolbox"></div>

## <a name="geodesic-line-break"></a> ![Geodesic Line Break at -180,180](images/idlbreak.png) Geodesic Line Break at -180,180

If you have ever created a geospatial masterpiece that has crossings across the International Date Line at a longitude of -180&deg;/180&deg; and it turned out like the image on the left, you are not alone.

<div style="text-align:center"><img src="doc/breaklines.jpg" alt="Break lines"></div>

**Geodesic line break** will break lines at the -180&deg;/180&deg; boundary along a geodesic path which is the shortest distance along the earth's surface between two points. The algorithm is very simple with just an input and output layer. The resulting output is shown in the above right side image. Depending on your data you may find it useful to also run the **Geodesic Densifier** on the data prior to this routine.

<div style="text-align:center"><img src="doc/geodesiclinebreak.jpg" alt="Geodesic Line Break"></div>

## <a name="geodesic-densifier"></a> ![Geodesic Densifier](images/geodesicDensifier.png) Geodesic Densifier

Densify a line or polygon vector layer by adding geodesic points in between individual line segments when its length is too great. This gives it a nice smooth curved appearance. For line vectors a geodesic line can be drawn between just the beginning and ending points.

<div style="text-align:center"><img src="doc/geodesicshape.jpg" alt="Geodesic Densifier"></div>

* **Input Layer** - Select an existing line or polygon layer.
* **Output Layer** - Specifies the output layer that will be created in QGIS.
* **Discard inner vertices (lines only)** - When this is checked only the beginning and ending points are used when drawing geodesic lines. This does not apply to polygons.
* **Maximum line segment length (in kilometers)** - This is the maximum length of a line segment before a new vertex is added along the geodesic path. This value defaults to the length specified in the **Settings** menu.

The following shows the before and after results of running this function on a polygon layer.

<div style="text-align:center"><img src="doc/geodesicpolygon.jpg" alt="Geodesic Polygon"></div>

This function can also be accessed from the **Processing Toolbox**.

<div style="text-align:center"><img src="doc/processing.jpg" alt="Processing Toolbox"></div>

## <a name="geodesic-line-decimate"></a> ![Geodesic Line Decimate](images/geodesicLineDecimate.png) Geodesic Line Decimate

This simplifies the geometry of a line layer by removing vertices who's distance to the previous vertex is less than the specified value. For each line, the geodesic distance is calculated between vertices and if the distance is less than the specified minimum distance then the vertex is deleted. This repeats until the distance threshold is exceeded. The only exception to this rule is if ***Preserve final vertex*** is selected in which case the final vertex is always saved.

<div style="text-align:center"><img src="doc/geodesiclinedecimate.jpg" alt="Geodesic line decimate"></div>

The following shows the before and after results of running this funciton on a line layer.

<div style="text-align:center"><img src="doc/geodesicdecimation.jpg" alt="Geodesic decimation"></div>

**Parameters**

* **Input layer** - Select an existing line layer.
* **Output layer** - Specifies the output layer that will be created.
* **Preserve final vertex** - If checked then the final vertex will not be discarded. If the distance between the previous saved vertex and the final vertex is less than the minimum distance then the next to the last saved vertex will be deleted or if there are only two vertices left, than the distance between the first and final vertex may be less than the minimum distance.
* **Decimation minimum distance beween vertices** - Sprecifies the minimum distance between vertices. Distances less than this are deleted.
* **Distance units** - Specifies the units of measure for the "Decimation minimum distance betwee vertices."

## <a name="geodesic-point-decimate"></a> ![Geodesic Point Decimate](images/geodesicPointDecimate.png) Geodesic Point Decimate
This reduces the number of points within a point vector layer by using geodesic distances mesurements between points and/or the time interval between points. This assumes that the points are ordered or that there is a property field that specifies the order of the points. Poiint can also be grouped together based on an attributed in the table in which case points from each grouping are processed separately.

**Parameters**

* **Input point layer** - Select an existing line layer.
* **Output layer** - Specifies the output layer that will be created.
* **Point order field** - This specifies a field that defines the order of the points to be processed. A time field can be used with GPS data to order the points by the time they were acquired.
* **Preserve final point** - If checked then the final point in each group will not be discarded.
* **Remove points that are less than the minimum distance** - Enables geodesic distance decimation.
    * **Minimum distance beween points** - Sprecifies the minimum distance between points. Distances less than this are targeted for deletion.
    * **Distance units** - Specifies the units of measure for the geodesic minimum distance.
* **Remove points by minimum time interval** - Enables time decimation.
    * **Time field** - Select a DateTime field to use for time decimation. If time is specified as a string then the field will need to be converted to a DateTime fields.
    * **Minimum time between points** - Points not meeting the minimum time difference are removed.
    * **Time units** - Specifies the time units of the above value. The units of time can be ***Seconds***, ***Minutes***, ***Hours***, and ***Days***.
* **When both decimate by distance and time are selected, preserve points if** - This specifies whether both distance and time requements must be met or only one or the other requirements are met.

## <a name="geodesic-measure"></a> ![Geodesic Measure Tool](images/measure.png) Geodesic Measure Tool

This provides the ability to measure distances using geodesic (shortest path) algorithms. The results returned are similar to those used by Google Earth and makes for a nice baseline of distances. It also includes the heading from the first point to the second and a heading from the second point to the first. The units are in degrees. The units of distance can be kilometers, meters, centimeters, miles, yards, feet, inches, and nautical miles. Simply click on the ***Geodesic Measure Tool*** icon and start clicking on the map. Notice that the ellipsoid used to calculate measurements is listed in the lower left-hand corner. By default this is set to ***WGS 84***, but it can be changed in the ***Settings*** menu. If snapping is enabled, then the ***Geodesic Measure Tool*** will snap to vector layer vertices and features when the mouse hovers over them.

While using the geodesic measure tool the user can quickly copy values of the last heading to, heading from, distance, and total distance onto the clipboard by typing one of the following keys:

* **1 or T** - Copies the most recent 'Heading to' value onto the clipboard.
* **2 or F** - Copies the most recent 'Heading from' value onto the clipboard.
* **3 or D** - Copies the most recent 'Distance' value onto the clipboard.
* **4 or A** - Copies the 'Total distance' value onto the clipboard.

The number of significant decimal digits of the value copied onto the clipboard is determined in the ***Settings***.

<div style="text-align:center"><img src="doc/geodesicmeasure.jpg" alt="Geodesic Measure Tool"></div>

The **Save to Layer** button will create a **Measurement** layer that contains the distance and by default the distance label will be displayed.

<div style="text-align:center"><img src="doc/geodesicmeasure2.jpg" alt="Geodesic Measure Tool"></div>

By right-mouse clicking on the **Measurement** layer and selecting **Open Attribute Table,** the following attributes are available for each measured line segment; label, value, units, heading_to, heading_from, and the total distance for all line segments.

<div style="text-align:center"><img src="doc/geodesicmeasure3.jpg" alt="Geodesic Measure Tool"></div>

By clicking on the ***Add measurement point*** icon ![Add measurement point](images/manualpoint.png), a new dialog windows is displayed were precise measurement points can be added. The coordinates can be in WGS 84 (EPSG:4326), the project CRS, or some other custom projection. In the drop down menus specify the projection and the coordinate order in which the coordinates are entered.

<div style="text-align:center"><img src="doc/geodesicmeasure4.jpg" alt="Add measurement point"></div>

## <a name="geodesic-measure-layer"></a> ![Geodesic Measurement Layer](images/linedigitize.png) Geodesic Measurement Layer

This take either a polygon or line layer and for each of the geometries calculates the geodesic distances of each feature. The user can choose whether each line segment is measured and output as a line measurement or whether the entire line/polygon geometry is measured. It outputs a new line layer of lines that contain attributes with all the measurements. If measuring individual line segments the attributes are a label, distance, units of measure, azimuth/bearing to the next point, and the total distance of the geometry. If measuring the entire geometry then the attributes are a label, distance, and units of measure. The input is either a line or polygon layer. Select whether you want to measure the entire line or polygon or each line segment within the line or polygon. **Distance units** can be kilometers, meters, centimeters, miles, yards, feet, inches, or nautical miles. **Use automatic styling** styles the QGIS layer with the label string in the attribute table and with the text and line colors found in **Settings**.

<div style="text-align:center"><img src="doc/measurement-layer.jpg" alt="Geodesic Measurement Layer"></div>

Here is an example of running this on a polygon. Notice how it not only measures the outer boundary, but it also measures the inner boundary as well.

<div style="text-align:center"><img src="doc/measure-polygon.jpg" alt="Measuring a polygon"></div>

Here is what the attributes table looks like.

<div style="text-align:center"><img src="doc/measurement-attributes.jpg" alt="Measurement Attributes"></div>

## <a name="geodesic-transformations"></a> ![Geodesic Transformations](images/transformShape.png) Geodesic Transformations Tool

This tool provides the ability to geodesically transform a shape. It supports scaling, rotation and translation. The size and geometry of each shape will be retained regardless of the projection. 

<div style="text-align:center"><img src="doc/geodesictransform.jpg" alt="Geodesic Transformations"></div>

* **Input vector layer** - Select an existing point, line, or polygon vector layer.
* **Selected features only** - Checking this box will cause the algorithm to only transform the selected features.
* **Rotation angle about the centroid** - Rotate the feature about its centroid. A positive angle rotates in a clockwise direction.
* **Scale factor about the centroid** - Scale the shape about its centroid. A scale factor of 1 retains its same size.
* **Translation distance** - Distance the shape will be moved along a geodesic path.
* **Translation azimuth** - Azimuth or direction the shape will be moved along a geodesic path.
* **Translation distance units** - Units of distance the shape will be move.
* **Output layer** - The output layer that will be created in QGIS.

## <a name="geodesic-flip"></a> ![Geodesic Flip and Rotate Tools](images/flip.png) Geodesic Flip and Rotate Tools
This is a collection of geodesic tools that transform vector features including the ability to flip horizontally, flip vertically, rotate by 180 degrees, rotate clockwise by 90 degrees, and rotate counter clockwise by 90 degrees. The first is a processing toolbox algorithm that allows the selection of one of these five transforms.

<div style="text-align:center"><img src="doc/fliptool.jpg" alt="Geodesic Flip and Rotate"></div>

* **Input vector layer** - Select an existing line, or polygon vector layer.
* **Transform function** - Choose the desired function: ***Flip Horizontal, Flip Vertical, Rotate 180&deg;, Rotate 90&deg; CW,*** or ***Rotate 90&deg; CCW***.
* **Output layer** - The output layer that will be created in QGIS.

The following geodesic tools work on an editable line or polygon vector layer. If a feature is selected, these functions only operate on that feature; otherwise, it operates on all features in the layer.

* ![Flip horizontal](images/flipHorizontal.png) **Flip horizontal** flips a vector feature horizontally about its centroid.
* ![Flip vertical](images/flipVertical.png) **Flip vertical** flips a vector feature vertically about its centroid.
* ![Rotate 180](images/rotate180.png) **Rotate 180&deg; ** rotates a vector feature by 180 degrees.
* ![Rotate 90 CW](images/rotatecw.png) **Rotate 90&deg; CW** rotates a vector feature by 90 degrees clockwise.
* ![Rotate 90 CCW](images/rotateccw.png) **Rotate 90&deg; CCW** rotates a vector feature by 90 degrees counter-clockwise.

## <a name="azimuth-distance"></a> ![Azimuth, Distance Digitizer](images/dazdigitize.png) Azimuth, Distance Digitizer

This tool works on point and line vector layers and is enabled when they are selected and in edit mode. In either case the following dialog box is displayed when the tool is enabled and a point on the map is clicked on. If snapping is enabled (*Project->Snapping Options...*), then when the cursor hovers close to an existing point or vertex, a bounding box around the point will be displayed. Clicking near the vertex will snap its location to be used by the ***Azimuth, Distance Digitizer*** as its starting point.

<div style="text-align:center"><img src="doc/azimuth-distance.jpg" alt="Azimuth, Distance Tool"></div>

Azimuth is in degrees and distance is in the selected *Distance units of measure*. The following is how it interacts on point and line layers. 

* **Point Vector Layer** - If an editable point vector layer is selected and the map is click on, the tool will create a point in the azimuth direction and at the specified distance. The point clicked on can be also included in the output layer.
* **Line Vector Layer** - If an editable line vector layer is selected and the map is click on, the tool will create a geodesic line from the clicked point along the azimuth and distance path.

## <a name="azimuth-distance-sequence"></a> ![Azimuth Distance Sequence Digitizer](images/dazdigitize.png) Azimuth Distance Sequence Digitizer

<div style="text-align:center"><img src="doc/az-sequence.jpg" alt="Azimuth, Distance Sequence Digitizer"></div>

This is similar to the **Azimuth, Distance Digitizer**, but it provides the ability to click on the map as a starting point and then give a series of bearings and distances in the order of 'bearing 1, distance 1, bearing 2, distance 2, ... bearing N, distance N' and it will create a path. This is useful in some survey work. If older surveying used magnetic north, it can be compensated for by the **Bearing / declination adjustment**. Magnetic declination changes over time, but the [NOAA Magnetic Field Calculator](https://www.ngdc.noaa.gov/geomag-web/#declination) provides an easy interface to estimate the magnetic north declination at a certain latitude, longitude and time, all the way back to 1590. West declination will be a negative number and east declination is a positive number. If a polygon layer is selected then the resulting shape automatically closes the polygon such that the beginning and ending points are the same. If a line layer is selected then you have the option of automatically adding a line segment from the last point in the sequence to the first point. If a point layer is selected, then only the nodes will be added to the layer. If snapping is enabled (*Project->Snapping Options...*), then when the cursor hovers close to an existing point or vertex, a bounding box around the point will be displayed. Clicking near the vertex will snap its location to be used by the ***Azimuth, Distance Sequence Digitizer*** as its starting point.

## <a name="settings"></a>Settings

The settings dialog box can be accessed from the Shape Tools menu *Vector->Shape Tools->Settings*. The following are the parameters that can be configured.

<div style="text-align:center"><img src="doc/settings.jpg" alt="Settings"></div>

* **Create Shapes default column names for input X,Y (Lat,Lon) geometry** - All of the different shapes have a check box called **Add input geometry fields to output table**. When checked, the input point geometry will be added to fields in the output shape table. By default these fields are named ***geom_x*** and ***geom_y***, but can be changed here. If the input layer has a field by the same name, then a number is appended to make it unique.
* **Geodesic Line Settings** - These settings are used when drawing geodesic and great circle lines.
    * **Maximum segment length before creating a new segment** - In order to draw a smooth curved line, multiple line segments are required. This defines how far to travel before a new line segment is created. This parameter is in kilometers. 
    * **Maximum number of segments per line** - This is the maximum number of line segments that will be created for any line even though the maximum segment length may be exceeded. This takes precedence.
* **Measure Tool Settings** - These are settings for the **Geodesic Measure Tool**.
    * **Azimuth Range** - The azimuth is displayed from **-180 to 180** degrees or from **0 to 360** degrees.
    * **Rubber band color** - Selects the rubber band line color used by the measure tool.
    * **Measurement layer color** - Vector line color when a measurement layer is created from the ***Geodesic measure tool*** or from the ***Geodesic measurement layer*** tool.
    * **Measurement layer text** - Color of the text when a measurement layer is created from the ***Geodesic measure tool*** or from the ***Geodesic measurement layer*** tool.
    * **Copy to clipboard significant digits** - This is the number of significant decimal digits that are copied onto the clipboard when the user is using the ***Geodesic measure tool*** and presses on one of the copy to clipboard keys.
* **Ellipsoid Used for Measurements** - Selects the ellipsoid used for calculating the geodesic distances within Shape Tools. By default this should normally be *WGS 84*
    * **Ellipsoid group** - Choose the default *WGS 84* setting or enable *System Ellipsoids* or *Historical Ellipsoids*.
    * **System Ellipsoids** - This is enabled if **Ellipsoid group** is set to *System Ellipsoids*.
    * **Historical Ellipsoids** - This is enabled if **Ellipsoid group** is set to *Historical Ellipsoids*. Additional historical ellipsoids can be selected.
