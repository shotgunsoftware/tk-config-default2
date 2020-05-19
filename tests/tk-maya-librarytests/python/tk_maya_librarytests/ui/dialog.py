# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\devs\TESTS\tk-maya-librarytests\resources\dialog.ui'
#
# Created: Mon May 04 15:10:51 2020
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(542, 427)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.local_group = QtGui.QGroupBox(Dialog)
        self.local_group.setObjectName("local_group")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.local_group)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.verticalLayout.addWidget(self.local_group)
        self.external_group = QtGui.QGroupBox(Dialog)
        self.external_group.setObjectName("external_group")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.external_group)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.external_group)
        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setContentsMargins(-1, -1, 20, -1)
        self.button_layout.setObjectName("button_layout")
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.button_layout.addItem(spacerItem2)
        self.update_button = QtGui.QPushButton(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.update_button.sizePolicy().hasHeightForWidth())
        self.update_button.setSizePolicy(sizePolicy)
        self.update_button.setObjectName("update_button")
        self.button_layout.addWidget(self.update_button)
        self.verticalLayout.addLayout(self.button_layout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.local_group.setTitle(QtGui.QApplication.translate("Dialog", "Local References", None, QtGui.QApplication.UnicodeUTF8))
        self.external_group.setTitle(QtGui.QApplication.translate("Dialog", "External References", None, QtGui.QApplication.UnicodeUTF8))
        self.update_button.setText(QtGui.QApplication.translate("Dialog", "Update", None, QtGui.QApplication.UnicodeUTF8))

