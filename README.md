Layer Board Plugin
==================

Description
-----------

This plugin helps to see and modify properties for vector and raster layers.

It shows the layers in a table sheet, and the user can directly modify some properties such as layer name, title, abstract, minimum and maximum scales. To do so, double-click on a cell and modify the value. The modified cells are then drawn in yellow, and you can apply or discard the changes via the button under the table.

Some properties can be changed on multiple layers at once, such as modifying spatial reference system and scale based visibility. To do so, select one or more layers in the vector or raster table, and use the right panel tools in the "Actions on Layers" tab, such as CRS or Max Scale, the click on the corresponding "Set" button.

Some actions can be performed on multiple layers at once:
* create a spatial index ( done only on vector layers)
* save current style as default : it creates a QML file beside the source file

The information visible in the "Vector layers" or "Raster layers" tabs can be exported to a "Comma Separated Values" (CSV) text file via the button in the tab "Export" of the right panel

When only one layers is selected, the tab "Layer style" in the right panel displays the current layers style, and you can change the style directly for the selected layer via the "Apply" button.
This is only available for vector layers.

IMPORTANT : the changes are made in the current project, and will be saved only if you save the project.

Authors
--------

Michaël Douchin ( 3liz )


Contributors
---------------

Enrico Ferreguti @enricofer

Licence
-----------

GPL V2
