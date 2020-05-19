# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk.platform.qt import QtCore, QtGui
from .ui.list_item_widget import Ui_ListItemWidget


class ListItemWidget(QtGui.QWidget):
    """
    Widget that is used to display entries in all the item listings.
    This widget goes together with the list item delegate and is always
    manufactured by the list item delegate.
    """

    def __init__(self, parent=None):
        """
        Constructor

        :param parent: QT parent object
        """
        QtGui.QWidget.__init__(self, parent)

    #     # make sure this widget isn't shown
    #     self.setVisible(False)
    #
        # set up the UI
        self.ui = Ui_ListItemWidget()
        self.ui.setupUi(self)

    #     # keep predefined classes for each state of the widget
    #
    #     # style when the widget is selected
    #     self._css_selected = """
    #         #box { border-width: 2px;
    #                border-radius: 4px;
    #                border-color: rgb(48, 167, 227);
    #                border-style: solid;
    #                background-color: rgba(48, 167, 227, 25%);
    #         }
    #         """
    #
    #     # style when the widget is passive (not selected)
    #     self._css_passive = """
    #         #box { border-width: 2px;
    #                border-radius: 4px;
    #                border-color: rgba(0, 0, 0, 0%);
    #                border-style: solid;
    #         }
    #         """
    #

    def set_path(self, path):
        self.ui.path.setText(path)

    def set_project(self, project):
        self.ui.project.setText(project)


    #
    # def set_selected(self, selected):
    #     """
    #     Adjust the style sheet to indicate selection or not
    #
    #     :param selected: True if selected, false if not
    #     """
    #     css = self._css_selected if selected else self._css_passive
    #     self.ui.box.setStyleSheet(css)
    #
    # def set_thumbnail(self, pixmap):
    #     """
    #     Set a thumbnail given the current pixmap.
    #     The pixmap must be 100x100 or it will appear squeezed
    #
    #     :param pixmap: pixmap object to use
    #     """
    #     self.ui.thumbnail.setPixmap(pixmap)
    #
    # def set_text(self, sg_data):
    #     """
    #     Populate the lines of text in the widget
    #
    #     :param body: Body text as string
    #     """
    #     self.ui.project.setText(sg_data.get("project", {}).get("name"))
    #     self.ui.asset_id.setText(str(sg_data.get("id", "")))
    #     self.ui.asset_name.setText(sg_data.get("code", ""))
    #
    # @staticmethod
    # def calculate_size():
    #     """
    #     Calculates and returns a suitable size for this widget.
    #
    #     :returns: Size of the widget
    #     """
    #     return QtCore.QSize(300, 102)


