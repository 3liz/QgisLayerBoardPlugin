# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerBoard
                                 A QGIS plugin
 This plugin displays tables with all the project layers and lets the user change some properties directly. I also aims to be a board showing usefull information on all layers, and export this information as CSV or PDF
                              -------------------
        begin                : 2015-05-21
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Michaël DOUCHIN / 3liz
        email                : info@3liz.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMessageBar, QgsGenericProjectionSelector

from functools import partial

# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from layer_board_dialog import LayerBoardDialog
import os.path
import datetime


class LayerBoard:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'LayerBoard_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Create the dialog (after translation) and keep reference
        self.dlg = LayerBoardDialog()

        # Layers attribute that can be shown and optionally changed in the plugin
        self.layersTable =  {
            'generic': {
                'attributes': [
                    {'key': 'id', 'editable': False },
                    {'key': 'name', 'editable': True, 'type': 'string'},
                    {'key': 'crs', 'editable': False, 'type': 'crs'},
                    {'key': 'maxScale', 'editable': True, 'type': 'integer'},
                    {'key': 'minScale', 'editable': True, 'type': 'integer'},
                    {'key': 'extent', 'editable': False},
                    {'key': 'title', 'editable': True, 'type': 'string'},
                    {'key': 'abstract', 'editable': True, 'type': 'string'},
                    {'key': 'uri', 'editable': False}
                ]
            },
            'vector': {
                'tableWidget': self.dlg.vectorLayers,
                'attributes': [
                    {'key': 'featureCount', 'editable': False}
                ],
                'commitButton': self.dlg.btCommitVectorChanges,
                'discardButton': self.dlg.btDiscardVectorChanges
            },
            'raster': {
                'tableWidget': self.dlg.rasterLayers,
                'attributes': [
                    {'key': 'width', 'editable': False},
                    {'key': 'height', 'editable': False},
                    {'key': 'rasterUnitsPerPixelX', 'editable': False},
                    {'key': 'rasterUnitsPerPixelY', 'editable': False}
                ],
                'commitButton': self.dlg.btCommitRasterChanges,
                'discardButton': self.dlg.btDiscardRasterChanges
            }
        }

        # Attributes for a specific layer type
        self.layersAttributes = {}

        # Changed data for each layer type
        self.layerBoardChangedData = {}

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Layer Board')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LayerBoard')
        self.toolbar.setObjectName(u'LayerBoard')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LayerBoard', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/LayerBoard/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Layer properties board'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # slots/signals
        ###############

        # Projection selector
        self.dlg.btDefineProjection.clicked.connect( self.chooseProjection )

        # Right pannel buttons to apply property on several layers
        self.applyMultipleLayersButtons = {
            "crs" : {
                "button" : self.dlg.btApplyCrs,
                "input" : self.dlg.inCrs
            },
            "maxScale" : {
                "button" : self.dlg.btApplyMaxScale,
                "input" : self.dlg.inMaxScale
            },
            "minScale" : {
                "button" : self.dlg.btApplyMinScale,
                "input" : self.dlg.inMinScale
            }
        }
        for key, item in self.applyMultipleLayersButtons.items():
            control = item['button']
            slot = partial( self.applyPropertyOnSelectedLayers, key )
            control.clicked.connect(slot)

        # Apply/Discard changes made on the table
        for layerType, item in self.layersTable.items():
            if 'commitButton' in item:
                control = item['commitButton']
                slot = partial( self.commitLayersChanges, layerType )
                control.clicked.connect(slot)
            if 'discardButton' in item:
                control = item['discardButton']
                slot = partial( self.discardLayersChanges, layerType )
                control.clicked.connect(slot)

        # Log
        self.dlg.btClearLog.clicked.connect( self.clearLog )


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Layer Board'),
                action)
            self.iface.removeToolBarIcon(action)

        # remove the toolbar
        del self.toolbar

    def clearLog(self):
        '''
        Clear the log
        '''
        self.dlg.txtLog.clear()

    def updateLog(self, msg):
        '''
        Update the log
        '''
        t = self.dlg.txtLog
        t.ensureCursorVisible()
        prefix = '<span style="font-weight:normal;">'
        suffix = '</span>'
        t.append( '%s %s %s' % (prefix, msg, suffix) )
        c = t.textCursor()
        c.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        t.setTextCursor(c)
        qApp.processEvents()


    def populateLayerTable( self, layerType ):
        """
        Fill the table for a given layer type
        """
        # Get parameters for the widget
        lt = self.layersTable[layerType]
        table = lt['tableWidget']

        # Reset layerBoardChangedData
        self.layerBoardChangedData[ layerType ] = {}

        # disconnect itemChanged signal
        try: table.itemChanged.disconnect()
        except Exception: pass

        attributes = self.layersTable['generic']['attributes'] + lt['attributes']
        self.layersAttributes[ layerType ] = attributes

        # empty previous content
        for row in range(table.rowCount()):
            table.removeRow(row)
        table.setRowCount(0)

        # create columns and header row
        columns = [ a['key'] for a in attributes ]
        colCount = len( columns )
        table.setColumnCount( colCount )
        table.setHorizontalHeaderLabels( tuple( columns ) )

        # load content from project layers
        lr = QgsMapLayerRegistry.instance()
        for lid in lr.mapLayers():
            layer = lr.mapLayer( lid )

            if layerType == 'vector' and layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layerType == 'raster' and layer.type() != QgsMapLayer.RasterLayer:
                continue

            # Add layer in the layerBoardChangedData
            self.layerBoardChangedData[ layerType ][ lid ] = {}

            # Set row and column count
            twRowCount = table.rowCount()
            # add a new line
            table.setRowCount( twRowCount + 1 )
            table.setColumnCount( colCount )
            i=0

            # get information
            for attr in attributes:
                newItem = QTableWidgetItem( )

                # Is editable or not
                if( attr['editable'] ):
                    newItem.setFlags( Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled )
                else:
                    newItem.setFlags( Qt.ItemIsSelectable  )

                # Item value
                value = self.getLayerProperty( layer, attr['key'] )
                newItem.setData( Qt.EditRole, value )

                # Add item
                table.setItem(twRowCount, i, newItem)
                i+=1


        # Launch slot on item changed slot
        slot = partial( self.onItemChanged, layerType )
        table.itemChanged.connect( slot )


    def getLayerProperty( self, layer, prop ):
        """
        Get a layer property
        """

        if prop == 'id':
            return layer.id()

        if prop == 'name':
            return layer.name()

        elif prop == 'title':
            return layer.title()

        elif prop == 'abstract':
            return layer.abstract()

        elif prop == 'crs':
            return layer.crs().authid()

        elif prop == 'extent':
            return layer.extent().toString(2)

        elif prop == 'uri':
            return layer.dataProvider().dataSourceUri().split('|')[0]

        elif prop == 'maxScale':
            return int( layer.maximumScale() )

        elif prop == 'minScale':
            return int( layer.minimumScale() )

        # vector
        elif prop == 'featureCount':
            return layer.featureCount()

        # raster
        elif prop == 'width':
            return int( layer.width() )

        elif prop == 'height':
            return int( layer.height() )

        elif prop == 'rasterUnitsPerPixelX':
            return int( layer.rasterUnitsPerPixelX() )

        elif prop == 'rasterUnitsPerPixelY':
            return int( layer.rasterUnitsPerPixelY() )

        else:
            return None


    def onItemChanged( self, layerType, item ):
        '''
        Get data when table item content has changed
        And store it for future use
        '''

        # Get table
        if layerType == 'vector':
            table = self.dlg.vectorLayers
        elif layerType == 'raster':
            table = self.dlg.rasterLayers
        else:
            return

        # Get row and column
        row = item.row()
        col = item.column()

        # Unselect row and item
        table.clearSelection()

        # Get layer
        layerId = table.item( row, 0 ).data( Qt.EditRole )
        lr = QgsMapLayerRegistry.instance()
        layer = lr.mapLayer( layerId )
        if not layer:
            return

        # Get changed property
        prop = self.layersAttributes[layerType][col]['key']
        data = table.item( row, col ).data( Qt.EditRole )

        # Store data in global property
        self.layerBoardChangedData[ layerType ][ layerId ][ prop ] = data

        # Change cell background
        table.item( row, col ).setBackground( Qt.yellow );


    def setLayerProperty( self, layerType, layers, prop, data ):
        '''
        Set properties for a list of layers
        '''

        for layer in layers:

            if not layer:
                continue

            if prop == 'name':
                layer.setLayerName( str(data) )

            elif prop == 'title':
                layer.setTitle( data )

            elif prop == 'abstract':
                layer.setAbstract( data )

            elif prop == 'maxScale':
                layer.toggleScaleBasedVisibility( True )
                layer.setMaximumScale( float(data) )
                layer.triggerRepaint()

            elif prop == 'minScale':
                layer.toggleScaleBasedVisibility( True )
                layer.setMinimumScale( float(data) )
                layer.triggerRepaint()

            elif prop == 'crs':
                qcrs = QgsCoordinateReferenceSystem()
                qcrs.createFromOgcWmsCrs( data )
                if qcrs:
                    layer.setCrs(qcrs)
                    layer.triggerRepaint()

            else:
                continue

        # Refresh table
        self.populateLayerTable( layerType )


    def applyPropertyOnSelectedLayers(self, key):
        '''
        Apply changes on selected layers
        for the clicked button key
        '''

        # Value
        widget = self.applyMultipleLayersButtons[key]['input']
        value = unicode( widget.text() )
        if not value:
            return

        # Get active table
        tab = self.dlg.tabWidget.currentIndex()
        if tab == 0:
            table = self.dlg.vectorLayers
            layerType = 'vector'
        elif tab == 1:
            table = self.dlg.rasterLayers
            layerType = 'raster'
        else:
            return

        # Get selected lines
        sm = table.selectionModel()
        lines = sm.selectedRows()
        if not lines:
            return

        # Get column for the key
        col = next(index for (index, d) in enumerate(self.layersAttributes[ layerType ]) if d['key'] == key)
        if not col:
            return

        # Modify values for each line
        for index in lines:
            row = index.row()
            item = table.item( row, col )
            item.setData( Qt.EditRole, value )


    def commitLayersChanges(self, layerType='vector'):
        '''
        Commit all the changes made by the user
        visible via the different background color
        i.e. apply properties on layers
        '''
        lr = QgsMapLayerRegistry.instance()
        self.updateLog( '' )
        self.updateLog( '###############' )
        self.updateLog( datetime.datetime.now().strftime("%Y-%m-%d %H:%M") )
        self.updateLog( self.tr( u'Layer type: ' ) +  layerType )
        self.updateLog( '###############' )

        # Get all layers which have changes
        for layerId, layerData in self.layerBoardChangedData[layerType].items():
            # Some layers have an empty changed dictionnary
            if not layerData:
                continue

            # Get QGIS layer
            layer = lr.mapLayer( layerId )
            if not layer:
                # Reset layer data
                self.layerBoardChangedData[ layerType ][ layerId ] = {}
                continue

            # Log
            self.updateLog( '' )
            self.updateLog( '<b>%s</b> ( %s ):' % ( layer.name(), layerId ) )

            # Get all properties to commit with value
            for prop, data in layerData.items():
                if data:
                    self.setLayerProperty( layerType, [layer], prop, data )
                    self.updateLog( '* %s -> %s' % ( prop, data ) )

        # Repopulate table
        self.populateLayerTable( layerType )

    def discardLayersChanges(self, layerType='vector'):
        '''
        Repopulate the table, which also reinitialize the layerBoardChangedData
        '''
        # Repopulate table
        self.populateLayerTable( layerType )


    def chooseProjection(self):
        '''
        Let the user choose a SCR
        '''

        # crs Dialog parameters
        header = u"Choose CRS"
        sentence = u""
        projSelector = QgsGenericProjectionSelector( self.dlg )
        projSelector.setMessage( "<h2>%s</h2>%s" % (header.encode('UTF8'), sentence.encode('UTF8')) )

        if projSelector.exec_():
            self.crs = QgsCoordinateReferenceSystem( projSelector.selectedCrsId(), QgsCoordinateReferenceSystem.InternalCrsId )
            if len( projSelector.selectedAuthId() ) == 0:
                QMessageBox.information(
                    self,
                    self.tr(u'Layer Board'),
                    self.tr(u"No spatial reference system has been chosen")
                )
                return
            else:
                self.dlg.inCrs.clear()
                self.dlg.inCrs.setText( self.crs.authid() )

        else:
            return

    def run(self):
        """Run method that performs all the real work"""

        # Popuplate the layers table
        self.populateLayerTable( 'vector')
        self.populateLayerTable( 'raster')


        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()


        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
