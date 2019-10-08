# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerBoardDialog
                                 A QGIS plugin
 This plugin displays a table with all the project layers and lets the user change some properties directly. It also aims to be a board showing usefull information on all layers, and export this information as CSV or PDF
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

from qgis.PyQt.QtWidgets import QDialog

from .qgis_plugin_tools.resources import load_ui

FORM_CLASS = load_ui('layer_board_dialog_base.ui')


class LayerBoardDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(LayerBoardDialog, self).__init__(parent)
        self.setupUi(self)
