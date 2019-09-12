Changelog
===========

Version 0.9.0:

* Port the plugin to QGIS 3

Version 0.8.0:

* [BUGFIX] Fix saving default style for PostgreSQL layers
* [BUGFIX] Allow to erase a value when erasing a cell content (ex: abstract = '')
* [BUGFIX] Refresh the table correctly when a column order has been set
* Add compiled translation files: french now available


Version 0.7:

* [BUGFIX] layer's minScale can be float infinity
* Add the number of styles and tooltip
* Add layer shortname property
* Add label status for vector layers && translate table headers
* Add French translation
* Create the translation and translate to French


Version 0.5:

* Add the property 'Encoding' for vector layers
* Add a button to remove selected layers
* Add a button to remove all ghost layers ( layers which are in the project XML file, but not in the legend )

Version 0.4: Added 2 main features:

* Perform actions on multiple layers : save as default style and create spatial index
* New style tab which allows to see and change style for vector layers

Version 0.3.1

* CSV export - Handle non ascii characters by encoding CSV data to file system encoding
* CSV export - prevent error when canceling the export and no filename given
* Modify vector datasource - Prevent crash due to inverted variables assignment.

Version 0.3

* Vector datasources change support thanks to @enricofer
* Button to export visible table to Comma Separated Values (CSV)

Version 0.2

* The changes are not applied automatically on layers any more. They are just highlited in the table
* Two buttons for each table can be used to discard or apply changes on layers
* A new "Log" tab has been added and shows the changes made during the session. Content can be manually copied.
