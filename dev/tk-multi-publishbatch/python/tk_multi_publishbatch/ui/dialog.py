# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Y:\SGTK\configs\automotive\nio\SG-Config-Dev-2\customization\apps\tk-multi-publishprogress\resources\dialog.ui'
#
# Created: Thu Apr 15 15:57:29 2021
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(400, 458)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.log_box = QtGui.QTextEdit(Dialog)
        self.log_box.setReadOnly(True)
        self.log_box.setObjectName("log_box")
        self.verticalLayout.addWidget(self.log_box)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.progress_status_icon = QtGui.QLabel(Dialog)
        self.progress_status_icon.setMinimumSize(QtCore.QSize(20, 20))
        self.progress_status_icon.setMaximumSize(QtCore.QSize(20, 20))
        self.progress_status_icon.setText("")
        self.progress_status_icon.setPixmap(QtGui.QPixmap(":/tk-multi-progress/publish_in_progress.png"))
        self.progress_status_icon.setScaledContents(True)
        self.progress_status_icon.setObjectName("progress_status_icon")
        self.horizontalLayout.addWidget(self.progress_status_icon)
        self.progress_message = QtGui.QLabel(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progress_message.sizePolicy().hasHeightForWidth())
        self.progress_message.setSizePolicy(sizePolicy)
        self.progress_message.setObjectName("progress_message")
        self.horizontalLayout.addWidget(self.progress_message)
        self.close_button = QtGui.QPushButton(Dialog)
        self.close_button.setObjectName("close_button")
        self.horizontalLayout.addWidget(self.close_button)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Dialog", None, QtGui.QApplication.UnicodeUTF8))
        self.progress_message.setText(QtGui.QApplication.translate("Dialog", "Publish in progress...", None, QtGui.QApplication.UnicodeUTF8))
        self.close_button.setText(QtGui.QApplication.translate("Dialog", "Close", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
