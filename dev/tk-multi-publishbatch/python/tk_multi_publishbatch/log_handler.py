# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import logging

from sgtk.platform.qt import QtGui, QtCore


class Signaller(QtCore.QObject):
    """"""

    signal = QtCore.Signal(str, logging.LogRecord)


class QtHandler(logging.Handler):
    """
    Custom handler to be able to log messages to a GUI
    """

    def __init__(self, slotfunc, *args, **kwargs):
        """
        Class constructor
        :param slotfunc: Function to execute when a log message is emitted
        """
        super(QtHandler, self).__init__(*args, **kwargs)
        self.signaller = Signaller()
        self.signaller.signal.connect(slotfunc)

    def emit(self, record):
        s = self.format(record)
        self.signaller.signal.emit(s, record)
