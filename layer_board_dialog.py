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

import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'layer_board_dialog_base.ui'))


class LayerBoardDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(LayerBoardDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
