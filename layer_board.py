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
from __future__ import absolute_import

import csv
import datetime
import os.path
import re
import sys
from builtins import next
from builtins import range
from builtins import str
from functools import partial

from qgis.PyQt.QtCore import (
    QCoreApplication, QSettings, QTranslator, qVersion, Qt
)
from qgis.PyQt.QtGui import QIcon, QTextCursor
from qgis.PyQt.QtWidgets import (
    QAction,
    QTableWidgetItem,
    QLabel,
    QMessageBox,
    QFileDialog,
    QApplication,
)
from qgis.PyQt.QtXml import QDomDocument, QDomElement
from qgis.core import (
    QgsProject,
    QgsMapLayer,
    QgsCoordinateReferenceSystem,
    QgsVectorDataProvider,
    QgsVectorLayer,
    Qgis,
    QgsStyle,
)
from qgis.gui import QgsProjectionSelectionTreeWidget, QgsRendererPropertiesDialog

from .layer_board_dialog import LayerBoardDialog
from .tools import resources_path


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
            '{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LayerBoardDialog()

        # Layers attribute that can be shown and optionally changed in the plugin
        self.layersTable = {
            'generic': {
                'attributes': [
                    {'key': 'id', 'label': self.tr('Id'), 'editable': False},
                    {'key': 'name', 'label': self.tr('Name'), 'editable': True, 'type': 'string'},
                    {'key': 'crs', 'label': self.tr('CRS'), 'editable': False, 'type': 'crs'},
                    {'key': 'maxScale', 'label': self.tr('Max scale'), 'editable': True, 'type': 'integer'},
                    {'key': 'minScale', 'label': self.tr('Min scale'), 'editable': True, 'type': 'integer'},
                    {'key': 'extent', 'label': self.tr('Extent'), 'editable': False},
                    {'key': 'title', 'label': self.tr('Title'), 'editable': True, 'type': 'string'},
                    {'key': 'abstract', 'label': self.tr('Abstract'), 'editable': True, 'type': 'string'},
                    {'key': 'shortname', 'label': self.tr('Short name'), 'editable': True, 'type': 'string'},
                    {'key': 'ghost', 'label': self.tr('Ghost ?'), 'editable': False, 'type': 'string'}
                ]
            },
            'vector': {
                'tableWidget': self.dlg.vectorLayers,
                'attributes': [
                    {'key': 'labelsEnabled', 'label': self.tr('Labels on'), 'editable': False},
                    {'key': 'featureCount', 'label': self.tr('Features count'), 'editable': False},
                    {'key': 'source|uri', 'label': self.tr('Datasource URI'), 'editable': True},
                    {'key': 'encoding', 'label': self.tr('Encoding'), 'editable': True},
                    {'key': 'styles_in_db', 'label': self.tr('Styles in DB'), 'editable': False, 'type': 'string'},
                ],
                'commitButton': self.dlg.btCommitVectorChanges,
                'discardButton': self.dlg.btDiscardVectorChanges
            },
            'raster': {
                'tableWidget': self.dlg.rasterLayers,
                'attributes': [
                    {'key': 'width', 'label': self.tr('Width'), 'editable': False},
                    {'key': 'height', 'label': self.tr('Height'), 'editable': False},
                    {'key': 'rasterUnitsPerPixelX', 'label': self.tr('Units per pixel (X)'), 'editable': False},
                    {'key': 'rasterUnitsPerPixelY', 'label': self.tr('Units per pixel (Y)'), 'editable': False},
                    {'key': 'uri', 'label': self.tr('URI'), 'editable': False}
                ],
                'commitButton': self.dlg.btCommitRasterChanges,
                'discardButton': self.dlg.btDiscardRasterChanges
            }
        }

        # Attributes for a specific layer type
        self.layersAttributes = {}

        # Changed data for each layer type
        self.layerBoardChangedData = {}

        # Data contained in the table widget after it has been filled
        self.layerBoardData = {}

        # CSV default options
        self.csvDelimiter = ','
        self.csvQuotechar = '"'
        self.csvQuoting = csv.QUOTE_ALL

        # Keep record of style widget
        self.styleWidget = None
        self.styleLayer = None

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr('&Layer Board')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar('LayerBoard')
        self.toolbar.setObjectName('LayerBoard')

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

        icon_path = resources_path('icons', 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr('Layer board'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # slots/signals
        ###############

        # Projection selector
        self.dlg.btDefineProjection.clicked.connect(self.chooseProjection)

        # Right pannel buttons to apply property on several layers
        self.applyMultipleLayersButtons = {
            "crs": {
                "button": self.dlg.btApplyCrs,
                "input": self.dlg.inCrs
            },
            "maxScale": {
                "button": self.dlg.btApplyMaxScale,
                "input": self.dlg.inMaxScale
            },
            "minScale": {
                "button": self.dlg.btApplyMinScale,
                "input": self.dlg.inMinScale
            },
            "encoding": {
                "button": self.dlg.btApplyEncoding,
                "input": self.dlg.inEncodingList
            }
        }
        for key, item in list(self.applyMultipleLayersButtons.items()):
            control = item['button']
            slot = partial(self.applyPropertyOnSelectedLayers, key)
            control.clicked.connect(slot)

        # Apply/Discard changes made on the table
        for layerType, item in list(self.layersTable.items()):
            # Commit button
            if 'commitButton' in item:
                control = item['commitButton']
                slot = partial(self.commitLayersChanges, layerType)
                control.clicked.connect(slot)
            # Discard button
            if 'discardButton' in item:
                control = item['discardButton']
                slot = partial(self.discardLayersChanges, layerType)
                control.clicked.connect(slot)

        # Right pannel buttons to perform actions on multiple layers
        self.applyMultipleLayersActions = {
            "saveStyleAsDefault": {
                "button": self.dlg.btSaveStyleAsDefault
            },
            "createSpatialIndex": {
                "button": self.dlg.btCreateSpatialIndex
            },
            "removeLayer": {
                "button": self.dlg.btRemoveLayer
            }
        }
        for key, item in list(self.applyMultipleLayersActions.items()):
            control = item['button']
            slot = partial(self.performActionOnSelectedLayers, key)
            control.clicked.connect(slot)

        # Global actions
        self.dlg.btRemoveGhostLayers.clicked.connect(self.removeGhostLayers)

        # Actions when row selection changes
        for layerType, item in list(self.layersTable.items()):
            # Style widget
            if layerType in ('vector', 'raster'):
                slot = partial(self.setSelectedLayerStyleWidget, layerType)
                table = item['tableWidget']
                sm = table.selectionModel()
                sm.selectionChanged.connect(slot)

        # Actions when layer tab is changed
        self.dlg.tabWidget.currentChanged.connect(self.onTabChanged)

        # Log
        self.dlg.btClearLog.clicked.connect(self.clearLog)

        # Export
        self.dlg.btExportCsv.clicked.connect(self.exportToCsv)

        # Apply style
        self.dlg.btApplyStyle.clicked.connect(self.applyStyle)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&Layer Board'),
                action)
            self.iface.removeToolBarIcon(action)

        # remove the toolbar
        del self.toolbar

    def clearLog(self):
        """
        Clear the log
        """
        self.dlg.txtLog.clear()

    def updateLog(self, msg):
        """
        Update the log
        """
        t = self.dlg.txtLog
        t.ensureCursorVisible()
        prefix = '<span style="font-weight:normal;">'
        suffix = '</span>'
        t.append('%s %s %s' % (prefix, msg, suffix))
        c = t.textCursor()
        c.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        t.setTextCursor(c)
        QCoreApplication.processEvents()

    def populateLayerTable(self, layerType):
        """
        Fill the table for a given layer type
        """
        # Get parameters for the widget
        lt = self.layersTable[layerType]
        table = lt['tableWidget']

        # Reset layerBoardChangedData
        self.layerBoardChangedData[layerType] = {}

        # disconnect itemChanged signal
        try:
            table.itemChanged.disconnect()
        except Exception:
            pass

        attributes = self.layersTable['generic']['attributes'] + lt['attributes']
        self.layersAttributes[layerType] = attributes

        self.layerBoardData[layerType] = []
        headerData = [a['key'] for a in attributes]
        self.layerBoardData[layerType].append(headerData)

        # empty previous content
        for row in range(table.rowCount()):
            table.removeRow(row)
        table.setRowCount(0)
        table.setColumnCount(0)

        # create columns and header row
        columns = [a['key'] for a in attributes]
        columnsLabels = [a['label'] for a in attributes]
        colCount = len(columns)
        table.setColumnCount(colCount)
        table.setHorizontalHeaderLabels(tuple(columnsLabels))

        # load content from project layers
        lr = QgsProject().instance()
        for lid in lr.mapLayers():
            layer = lr.mapLayer(lid)

            if layerType == 'vector' and layer.type() != QgsMapLayer.VectorLayer:
                continue
            if layerType == 'raster' and layer.type() != QgsMapLayer.RasterLayer:
                continue

            # Add layer in the layerBoardChangedData
            self.layerBoardChangedData[layerType][lid] = {}
            lineData = []

            # Set row and column count
            twRowCount = table.rowCount()
            # add a new line
            table.setRowCount(twRowCount + 1)
            table.setColumnCount(colCount)
            i = 0

            # get information
            for attr in attributes:
                newItem = QTableWidgetItem()
                newItem.setToolTip(layer.name())

                # Is editable or not
                if (attr['editable']):
                    newItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                else:
                    newItem.setFlags(Qt.ItemIsSelectable)

                # Item value
                value = self.getLayerProperty(layer, attr['key'])
                newItem.setData(Qt.EditRole, value)

                # Add cell data to lineData
                # encode it in the file system encoding, only if needed
                if hasattr(value, 'encode'):
                    value = value.encode(sys.getfilesystemencoding())
                lineData.append(value)

                # Add item
                table.setItem(twRowCount, i, newItem)
                i += 1

            # Add data to layerBoardData
            self.layerBoardData[layerType].append(lineData)

        # Launch slot on item changed slot
        slot = partial(self.onItemChanged, layerType)
        table.itemChanged.connect(slot)

    def getLayerProperty(self, layer, prop):
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

        elif prop == 'shortname':
            return layer.shortName()

        elif prop == 'ghost':
            # TODO QGIS 3, check ghost layers
            # isGhost = str( layer not in self.iface.legendInterface().layers() )
            return str(False)

        elif prop == 'crs':
            return layer.crs().authid()

        elif prop == 'extent':
            return layer.extent().toString(2)

        elif prop == 'maxScale':
            try:
                return int(layer.maximumScale())
            except:
                return 100000000

        elif prop == 'minScale':
            try:
                return int(layer.minimumScale())
            except:
                return 0

        # vector
        elif prop == 'labelsEnabled':
            le = False
            if hasattr(layer, 'labelsEnabled'):
                le = layer.labelsEnabled()
            else:
                le = layer.hasLabelsEnabled()
            return le

        elif prop == 'featureCount':
            return layer.featureCount()

        elif prop == 'source|uri':
            return layer.dataProvider().name() + "|" + layer.dataProvider().dataSourceUri().split('|')[0]

        elif prop == 'encoding':
            enc = None
            if hasattr(layer.dataProvider(), 'encoding'):
                enc = layer.dataProvider().encoding()
            return enc

        elif prop == 'styles_in_db':
            nb, _, _, _, _ = layer.listStylesInDatabase()
            if nb < 0:
                # If the table layer_styles doesn't exist, it returns -1 because the query failed
                nb = 0
            return nb

        # raster
        elif prop == 'width':
            return int(layer.width())

        elif prop == 'height':
            return int(layer.height())

        elif prop == 'rasterUnitsPerPixelX':
            return int(layer.rasterUnitsPerPixelX())

        elif prop == 'rasterUnitsPerPixelY':
            return int(layer.rasterUnitsPerPixelY())

        elif prop == 'uri':
            return layer.dataProvider().dataSourceUri().split('|')[0]

        else:
            return None

    def onItemChanged(self, layerType, item):
        """
        Get data when table item content has changed
        And store it for future use
        """

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
        layerId = table.item(row, 0).data(Qt.EditRole)
        lr = QgsProject().instance()
        layer = lr.mapLayer(layerId)
        if not layer:
            return

        # Get changed property
        prop = self.layersAttributes[layerType][col]['key']
        data = table.item(row, col).data(Qt.EditRole)

        # test if new datasource prop is valid otherwise restore previous data
        if prop == 'source|uri' and not self.newDatasourceIsValid(layer, data):
            table.itemChanged.disconnect()
            item.setData(Qt.EditRole, self.getLayerProperty(layer, 'source|uri'))
            slot = partial(self.onItemChanged, layerType)
            table.itemChanged.connect(slot)
            return

        # Check encoding and revert if problem
        if prop == 'encoding' and data not in layer.dataProvider().availableEncodings():
            table.itemChanged.disconnect()
            item.setData(Qt.EditRole, self.getLayerProperty(layer, 'encoding'))
            slot = partial(self.onItemChanged, layerType)
            table.itemChanged.connect(slot)
            return

        #  Check shortname and modify to remove unwanted chars
        if prop == 'shortname':
            table.itemChanged.disconnect()
            newshortname = re.sub('[^A-Za-z0-9\.-]', '_', data)
            item.setData(Qt.EditRole, newshortname)
            slot = partial(self.onItemChanged, layerType)
            table.itemChanged.connect(slot)

        # Store data in global property
        self.layerBoardChangedData[layerType][layerId][prop] = data

        # Change cell background
        table.item(row, col).setBackground(Qt.yellow)

    def setLayerProperty(self, layerType, layers, prop, data):
        """
        Set properties for a list of layers
        """

        for layer in layers:

            if not layer:
                continue

            if prop == 'name':
                layer.setLayerName(str(data))

            elif prop == 'title':
                layer.setTitle(data)

            elif prop == 'abstract':
                layer.setAbstract(data)

            elif prop == 'shortname':
                newshortname = re.sub('[^A-Za-z0-9\.-]', '_', data)
                layer.setShortName(newshortname)

            elif prop == 'maxScale':
                layer.toggleScaleBasedVisibility(True)
                layer.setMaximumScale(float(data))
                layer.triggerRepaint()

            elif prop == 'minScale':
                layer.toggleScaleBasedVisibility(True)
                layer.setMinimumScale(float(data))
                layer.triggerRepaint()

            elif prop == 'crs':
                qcrs = QgsCoordinateReferenceSystem()
                qcrs.createFromOgcWmsCrs(data)
                if qcrs:
                    layer.setCrs(qcrs)
                    layer.triggerRepaint()

            elif prop == 'source|uri':
                self.setDataSource(layer, data)

            elif prop == 'encoding' and data in layer.dataProvider().availableEncodings():
                layer.setProviderEncoding(data)

            else:
                continue

        # Refresh table
        self.populateLayerTable(layerType)

    def getActiveLayerType(self):
        """
        Get the visible layer type table
        """
        layerType = None
        tab = self.dlg.tabWidget.currentIndex()
        if tab == 0:
            table = self.dlg.vectorLayers
            layerType = 'vector'
        elif tab == 1:
            table = self.dlg.rasterLayers
            layerType = 'raster'

        return layerType

    def applyPropertyOnSelectedLayers(self, key):
        """
        Apply changes on selected layers
        for the clicked button key
        """

        # Value
        value = None
        widget = self.applyMultipleLayersButtons[key]['input']
        if hasattr(widget, 'text'):
            value = str(widget.text())
        elif hasattr(widget, 'currentText'):
            value = str(widget.currentText())
        if not value:
            return

        # Get active table
        layerType = self.getActiveLayerType()
        if not layerType:
            return
        lt = self.layersTable[layerType]
        table = lt['tableWidget']

        # Get selected lines
        sm = table.selectionModel()
        lines = sm.selectedRows()
        if not lines:
            return

        # Get column for the key
        col = next(index for (index, d) in enumerate(self.layersAttributes[layerType]) if d['key'] == key)
        if not col:
            return

        # Modify values for each line
        for index in lines:
            row = index.row()
            item = table.item(row, col)
            item.setData(Qt.EditRole, value)

    def performActionOnSelectedLayers(self, key):
        """
        Perform actions on selected layers
        for the clicked button key
        """
        # Get active table
        layerType = self.getActiveLayerType()
        if not layerType:
            return
        lt = self.layersTable[layerType]
        table = lt['tableWidget']

        # Get selected lines
        sm = table.selectionModel()
        lines = sm.selectedRows()
        if not lines:
            return

        p = QgsProject.instance()

        # Loop through layers and perform action
        lr = QgsProject.instance()
        for index in lines:
            row = index.row()
            layerId = table.item(row, 0).data(Qt.EditRole)
            layer = lr.mapLayer(layerId)
            if not layer:
                continue

            # Apply action if compatible

            # Save style as default
            if key == 'saveStyleAsDefault':
                # saveDefaultStyle() does not work in all QGIS 2 versions for postgres layers
                if layer.providerType() == 'postgres':
                    layer.saveStyleToDatabase(layer.name(), '', True, None, '')
                else:
                    layer.saveDefaultStyle()

            # Create spatial index
            if key == 'createSpatialIndex' and layer.type() == 0:
                provider = layer.dataProvider()
                if provider.capabilities() and QgsVectorDataProvider.CreateSpatialIndex:
                    if not provider.createSpatialIndex():
                        continue

            # Remove layer from project
            if key == 'removeLayer':
                lr.removeMapLayer(layer.id())
                # Remove line
                table.removeRow(row)
                # Set the dirty flag
                p.setDirty(True)

    def commitLayersChanges(self, layerType='vector'):
        """
        Commit all the changes made by the user
        visible via the different background color
        i.e. apply properties on layers
        """
        lr = QgsProject.instance()
        self.updateLog('')
        self.updateLog('###############')
        self.updateLog(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.updateLog(self.tr('Layer type: ') + layerType)
        self.updateLog('###############')

        # Get all layers which have changes
        for layerId, layerData in list(self.layerBoardChangedData[layerType].items()):

            # Some layers have an empty changed dictionnary
            if not layerData:
                continue

            # Get QGIS layer
            layer = lr.mapLayer(layerId)
            if not layer:
                # Reset layer data
                self.layerBoardChangedData[layerType][layerId] = {}
                continue

            # Log
            self.updateLog('')
            self.updateLog('<b>%s</b> ( %s ):' % (layer.name(), layerId))

            # Get all properties to commit with value
            for prop, data in list(layerData.items()):
                if data or data == '':
                    self.setLayerProperty(layerType, [layer], prop, data)
                    self.updateLog('* %s -> %s' % (prop, data))

        # Flag the project as dirty
        p = QgsProject.instance()
        p.setDirty(True)

        # Repopulate table
        self.populateLayerTable(layerType)

    def discardLayersChanges(self, layerType='vector'):
        """
        Repopulate the table, which also reinitialize the layerBoardChangedData
        """
        # Repopulate table
        self.populateLayerTable(layerType)

    def setDataSource(self, layer, newSourceUri):
        """
        Method to apply a new datasource to a vector Layer
        """
        newDS, newUri = self.splitSource(newSourceUri)
        newDatasourceType = newDS or layer.dataProvider().name()

        # read layer definition
        XMLDocument = QDomDocument("style")
        XMLMapLayers = QDomElement()
        XMLMapLayers = XMLDocument.createElement("maplayers")
        XMLMapLayer = QDomElement()
        XMLMapLayer = XMLDocument.createElement("maplayer")
        layer.writeLayerXML(XMLMapLayer, XMLDocument)

        # apply layer definition
        XMLMapLayer.firstChildElement("datasource").firstChild().setNodeValue(newUri)
        XMLMapLayer.firstChildElement("provider").firstChild().setNodeValue(newDatasourceType)
        XMLMapLayers.appendChild(XMLMapLayer)
        XMLDocument.appendChild(XMLMapLayers)
        layer.readLayerXML(XMLMapLayer)
        layer.reload()
        self.iface.actionDraw().trigger()
        self.iface.mapCanvas().refresh()

    def splitSource(self, source):
        """
        Split QGIS datasource into meaningfull components
        """
        if "|" in source:
            datasourceType = source.split("|")[0]
            uri = source.split("|")[1].replace('\\', '/')
        else:
            datasourceType = None
            uri = source.replace('\\', '/')
        return (datasourceType, uri)

    def newDatasourceIsValid(self, layer, newDS):
        """
        Probe new datasource to prevent layer issues
        """
        ds, uri = self.splitSource(newDS)
        if not ds:
            # if datasource type is not specified uri is probed with current one
            ds = layer.dataProvider().name()
        nlayer = QgsVectorLayer(uri, "probe", ds)
        if not nlayer.isValid():
            self.iface.messageBar().pushMessage("Error", "incorrect source|uri string: " + newDS, level=Qgis.Critical, duration=4)
            self.updateLog("\nERROR: incorrect source|uri string: " + newDS)
            return None
        if nlayer.geometryType() != layer.geometryType():
            self.iface.messageBar().pushMessage("Error", "geometry type mismatch on new datasource: " + newDS, level=Qgis.Critical, duration=4)
            self.updateLog("\nERROR: geometry type mismatch on new datasource: " + newDS)
            return None
        return True

    def chooseProjection(self):
        """
        Let the user choose a SCR
        """
        # crs Dialog parameters
        header = "Choose CRS"
        sentence = ""
        projSelector = QgsProjectionSelectionTreeWidget(self.dlg)
        projSelector.setMessage("<h2>%s</h2>%s" % (header.encode('UTF8'), sentence.encode('UTF8')))

        if projSelector.exec_():
            self.crs = QgsCoordinateReferenceSystem(projSelector.selectedCrsId(), QgsCoordinateReferenceSystem.InternalCrsId)
            if len(projSelector.selectedAuthId()) == 0:
                QMessageBox.information(
                    self,
                    self.tr('Layer Board'),
                    self.tr("No spatial reference system has been chosen")
                )
                return
            else:
                self.dlg.inCrs.clear()
                self.dlg.inCrs.setText(self.crs.authid())

        else:
            return

    ###########
    # STYLE
    ###########

    def setSelectedLayerStyleWidget(self, layerType, selected, unselected):
        """
        Get selected layer and display the corresponding style widget
        in the right panel
        """
        lt = self.layersTable[layerType]
        table = lt['tableWidget']
        sm = table.selectionModel()
        lines = sm.selectedRows()
        showStyle = True

        # Empty label widget if style must not been displayed
        w = QLabel()
        w.setText('')
        layer = None

        # Refresh Style tab
        if len(lines) != 1:
            showStyle = False

        if showStyle:
            row = lines[0].row()

            # Get layer
            layerId = table.item(row, 0).data(Qt.EditRole)
            lr = QgsProject.instance()
            layer = lr.mapLayer(layerId)
            if not layer:
                showStyle = False
            else:
                self.styleLayer = layer

        if showStyle and layer:
            # Choose widget depending on layer
            if layer.type() == 0 and layer.geometryType() not in [3, 4]:
                w = QgsRendererPropertiesDialog(layer, QgsStyle.defaultStyle(), True)

        # Make the widget visible
        self.styleWidget = w
        self.styleLayer = layer
        self.dlg.styleScrollArea.setWidget(w)

    def applyStyle(self):
        """
        Apply the style changed in the Style tab to the selected layer
        """
        # Do nothing if no widget or layer
        w = self.styleWidget
        layer = self.styleLayer
        if not w or not layer or not hasattr(w, 'apply'):
            return

        # Apply the new renderer to the layer
        w.apply()
        if hasattr(layer, "setCacheImage"):
            layer.setCacheImage(None)
        layer.triggerRepaint()

    ############
    # EXPORT
    ############
    def exportToCsv(self, layerType):
        """
        Exports the layers information to CSV

        """

        # Cancel if not path given
        path, __, __ = QFileDialog.getSaveFileName(self.dlg, QApplication.translate("LayerBoard", "Choose the path where the data must be saved."), '', 'CSV(*.csv)')
        if not path:
            msg = QApplication.translate("LayerBoard", "No destination file chose. Export canceled.")
            status = 'info'
            return msg, status

        # Get active table
        layerType = self.getActiveLayerType()
        if not layerType:
            return

        # Get layer data
        data = self.layerBoardData[layerType]

        # Write data into CSV file
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            with open(path, 'wb') as csvfile:
                writer = csv.writer(
                    csvfile, delimiter=self.csvDelimiter, quotechar=self.csvQuotechar, quoting=self.csvQuoting
                )
                writer.writerows(data)
            msg = QApplication.translate("LayerBoard", "The layers information table has been successfully exported.")
            status = 'info'
        except OSError as e:
            msg = QApplication.translate("LayerBoard", "An error occured during layer export." + str(e.error))
            status = 'critical'
        finally:
            QApplication.restoreOverrideCursor()

        return msg, status

    #################
    # GLOBAL ACTIONS
    #################

    def removeGhostLayers(self):
        """
        Remove all ghost layers from project
        """

        # Check if the layer is in the map registry but not in the legend
        lr = QgsProject.instance()
        li = self.iface.legendInterface()
        for lname, layer in list(lr.mapLayers().items()):
            if not layer in li.layers():
                lr.removeMapLayer(layer.id())

        # Set the dirty flag
        p = QgsProject.instance()
        p.setDirty(True)

        # Repopulate layers table
        self.populateLayerTable('vector')
        self.populateLayerTable('raster')

    #####
    # OTHER
    #####
    def populateAvailableEncodingList(self):
        """
        Fill in the encoding list combobox
        """
        cb = self.dlg.inEncodingList
        # empty combobox
        cb.clear()

        # add empty item
        cb.addItem('---', -1)

        # Get list of avalaible encodings
        vl = QgsVectorLayer("Point?crs=epsg:4326", "temp", "memory")
        enclist = vl.dataProvider().availableEncodings()
        del vl

        # Add encoding items
        for enc in enclist:
            cb.addItem(enc)

    def onTabChanged(self):
        """
        Perform some actions when tab is changed
        """
        layerType = self.getActiveLayerType()

        # Toggle activation of encoding tools
        isEnabled = layerType == 'vector'
        self.dlg.encodingLabel.setEnabled(isEnabled)
        self.dlg.inEncodingList.setEnabled(isEnabled)
        self.dlg.btApplyEncoding.setEnabled(isEnabled)

        # Toggle create spatial index button
        self.dlg.btCreateSpatialIndex.setEnabled(isEnabled)

    #######
    # RUN
    #######
    def run(self):
        """Run method that performs all the real work"""

        # Popuplate the layers table
        self.populateLayerTable('vector')
        self.populateLayerTable('raster')

        # Populate the encoding list
        self.populateAvailableEncodingList()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
