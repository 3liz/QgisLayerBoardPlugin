# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerBoard
                                 A QGIS plugin
 This plugin display a table with all the project layers and let you change some properties directly. I aims also to be a board showing usefull information on all layers, and export this information as CSV or PDF
                             -------------------
        begin                : 2015-05-21
        copyright            : (C) 2015 by Michaël DOUCHIN / 3liz
        email                : info@3liz.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load LayerBoard class from file LayerBoard.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .layer_board import LayerBoard
    return LayerBoard(iface)
