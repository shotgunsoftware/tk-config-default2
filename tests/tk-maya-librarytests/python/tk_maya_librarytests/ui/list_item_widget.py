# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\devs\TESTS\tk-maya-librarytests\resources\list_item_widget.ui'
#
# Created: Mon May 04 15:06:04 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_ListItemWidget(object):
    def setupUi(self, ListItemWidget):
        ListItemWidget.setObjectName("ListItemWidget")
        ListItemWidget.resize(366, 109)
        self.horizontalLayout_3 = QtGui.QHBoxLayout(ListItemWidget)
        self.horizontalLayout_3.setSpacing(1)
        self.horizontalLayout_3.setContentsMargins(8, 4, 8, 4)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.box = QtGui.QFrame(ListItemWidget)
        self.box.setStyleSheet("#box { border-width: 2px;\n"
"           border-radius: 4px;\n"
"           border-color: rgb(48, 167, 227);\n"
"           border-style: solid;\n"
"}")
        self.box.setFrameShape(QtGui.QFrame.NoFrame)
        self.box.setObjectName("box")
        self.horizontalLayout = QtGui.QHBoxLayout(self.box)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.data_layout = QtGui.QFormLayout()
        self.data_layout.setObjectName("data_layout")
        self.project_label = QtGui.QLabel(self.box)
        self.project_label.setStyleSheet("font-weight: bold;\n"
"color: rgb(41, 128, 185);")
        self.project_label.setObjectName("project_label")
        self.data_layout.setWidget(0, QtGui.QFormLayout.LabelRole, self.project_label)
        self.project = QtGui.QLabel(self.box)
        self.project.setText("")
        self.project.setObjectName("project")
        self.data_layout.setWidget(0, QtGui.QFormLayout.FieldRole, self.project)
        self.path_label = QtGui.QLabel(self.box)
        self.path_label.setStyleSheet("font-weight: bold;\n"
"color: rgb(41, 128, 185);")
        self.path_label.setObjectName("path_label")
        self.data_layout.setWidget(1, QtGui.QFormLayout.LabelRole, self.path_label)
        self.path = QtGui.QLabel(self.box)
        self.path.setText("")
        self.path.setObjectName("path")
        self.data_layout.setWidget(1, QtGui.QFormLayout.FieldRole, self.path)
        self.horizontalLayout.addLayout(self.data_layout)
        self.horizontalLayout_3.addWidget(self.box)

        self.retranslateUi(ListItemWidget)
        QtCore.QMetaObject.connectSlotsByName(ListItemWidget)

    def retranslateUi(self, ListItemWidget):
        ListItemWidget.setWindowTitle(QtGui.QApplication.translate("ListItemWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.project_label.setText(QtGui.QApplication.translate("ListItemWidget", "Project", None, QtGui.QApplication.UnicodeUTF8))
        self.path_label.setText(QtGui.QApplication.translate("ListItemWidget", "Path", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
