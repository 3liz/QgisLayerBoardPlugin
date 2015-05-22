# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerBoard
                                 A QGIS plugin
 This plugin display a table with all the project layers and let you change some properties directly. I aims also to be a board showing usefull information on all layers, and export this information as CSV or PDF
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

        # Plugin properties
        self.layersTable =  {
            'generic': {
                'attributes': [
                    {'key': 'id', 'editable': False },
                    {'key': 'name', 'editable': True, 'type': 'string'},
                    {'key': 'srs', 'editable': False, 'type': 'srs'},
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
                ]
            },
            'raster': {
                'tableWidget': self.dlg.rasterLayers,
                'attributes': [
                    {'key': 'width', 'editable': False},
                    {'key': 'height', 'editable': False},
                    {'key': 'rasterUnitsPerPixelX', 'editable': False},
                    {'key': 'rasterUnitsPerPixelY', 'editable': False}
                ]
            }
        }
        self.layersAttributes = {}

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Layer Board')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'LayerBoard')
        self.toolbar.setObjectName(u'LayerBoard')

        # slots/signals
        self.dlg.btDefineProjection.clicked.connect( self.chooseProjection )

        self.applyButtons = {
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
        for key, item in self.applyButtons.items():
            control = item['button']
            slot = partial( self.applyChanges, key )
            control.clicked.connect(slot)


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

    def test( self, item ):
        print "test  %s %s" % ( item.row, item.col )


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Layer Board'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def populateLayerTable( self, layerType='vector'):
        """
        Fill the table
        """
        # Get parameters for the widget
        lt = self.layersTable[layerType]
        table = lt['tableWidget']

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

            twRowCount = table.rowCount()
            # add a new line
            table.setRowCount(twRowCount + 1)
            table.setColumnCount(colCount)
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


        # Layer board signal/slots
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

        elif prop == 'srs':
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
        Change the data for one edited cell
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

        # Get layer
        layerId = table.item( row, 0 ).data( Qt.EditRole )
        lr = QgsMapLayerRegistry.instance()
        layer = lr.mapLayer( layerId )

        # Get changed property
        prop = self.layersAttributes[layerType][col]['key']
        data = table.item( row, col ).data( Qt.EditRole )

        self.setLayerProperty( layerType, [layer], prop, data )


    def setLayerProperty( self, layerType, layers, prop, data ):
        '''
        Set properties for a list of layers
        '''

        for layer in layers:

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


    def applyChanges(self, key):
        '''
        Apply changes on selected layers
        for the clicked key
        '''
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


        # Get layers to change
        lr = QgsMapLayerRegistry.instance()
        layers = []
        for index in lines:
            row = index.row()
            lid = table.item( row, 0 ).data( Qt.EditRole )
            layer = lr.mapLayer( lid )
            if layer:
               layers.append( layer )

        # Apply changes
        widget = self.applyButtons[key]['input']
        self.setLayerProperty( layerType, layers, key, unicode( widget.text() ) )

        # Refresh table
        self.populateLayerTable( layerType )


    def chooseProjection(self):
        '''
        Let the user choose a SCR
        '''

        # SRS Dialog parameters
        header = u"Choose SRS"
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
