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
import os
import shutil

import sgtk
from sgtk.platform.qt import QtGui, QtCore, tankqdialog
from tank_vendor import six

from .ui.dialog import Ui_Dialog
from .log_handler import QtHandler

task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
BackgroundTaskManager = task_manager.BackgroundTaskManager

shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)


class AppDialog(QtGui.QWidget):
    def __init__(self, parent=None, tree_file=None):
        """
        :param parent: The parent QWidget for this control
        """

        QtGui.QWidget.__init__(self, parent)

        self._pending_requests = []

        self._app = sgtk.platform.current_bundle()
        self._tree_file = tree_file

        # create a single instance of the task manager that manages all
        # asynchronous work/tasks
        self._bg_task_manager = BackgroundTaskManager(self, max_threads=8)
        self._bg_task_manager.start_processing()
        self._bg_task_manager.task_completed.connect(self._on_background_task_completed)
        self._bg_task_manager.task_failed.connect(self._on_background_task_failed)
        # shotgun_globals.register_bg_task_manager(self._bg_task_manager)

        # now load in the UI that was created in the UI designer
        self._ui = Ui_Dialog()
        self._ui.setupUi(self)

        self._ui.close_button.setEnabled(False)
        self._ui.close_button.clicked.connect(self.close)

        # -----------------------------------------------------------------
        # log management
        log_formatter = logging.Formatter("%(asctime)s :: %(levelname)s :: %(message)s")

        # QT Handler
        self.log_handler = QtHandler(self.log_message)
        self.log_handler.setFormatter(log_formatter)
        if sgtk.LogManager().global_debug:
            self.log_handler.setLevel(logging.DEBUG)
        else:
            self.log_handler.setLevel(logging.INFO)
        self._app.logger.addHandler(self.log_handler)

        # File Handler
        file_name = os.path.join(sgtk.LogManager().log_folder, "batch_publish.log")
        self.file_handler = sgtk.LogManager()._SafeRotatingFileHandler(
            file_name,
            maxBytes=1024 * 1024 * 5,
            backupCount=1,
            encoding="utf8" if six.PY3 else None,
        )
        self._app.logger.addHandler(self.file_handler)

        # -----------------------------------------------------------------

        # Launch the publish batch process
        if self._tree_file:
            task_id = self._bg_task_manager.add_task(self.run_publish_process)
            self._pending_requests.append(task_id)

    def closeEvent(self, event):
        """
        Overriden method triggered when the widget is closed.  Cleans up as much as possible
        to help the GC.

        :param event: Close event
        """

        # and shut down the task manager
        if self._bg_task_manager:
            self._bg_task_manager.task_completed.disconnect(
                self._on_background_task_completed
            )
            self._bg_task_manager.task_failed.disconnect(
                self._on_background_task_failed
            )
            # shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)
            self._bg_task_manager.shut_down()
            self._bg_task_manager = None

        # disconnect log handlers
        if self.log_handler in self._app.logger.handlers:
            self._app.logger.removeHandler(self.log_handler)
        if self.file_handler in self._app.logger.handlers:
            self._app.logger.removeHandler(self.file_handler)

        return QtGui.QWidget.closeEvent(self, event)

    def log_message(self, msg):
        """
        :param msg:
        :return:
        """
        self._ui.log_box.append(msg)

    def run_publish_process(self):
        """
        :return:
        """

        # check that the files we need to run the publish process exist on disk
        if not os.path.isfile(self._tree_file):
            self._app.logger.warning(
                "Couldn't find the publish tree file to start the publish process"
            )
            return

        current_engine = sgtk.platform.current_engine()
        self._publisher_app = current_engine.apps.get("tk-multi-publish2")
        if self._publisher_app:

            os.environ[
                "SGTK_BATCH_PUBLISH"
            ] = "True"  # Maya environment variables only accept strings...

            # disconnect the publish app progress handler
            # we need to do this otherwise all the calls to logger.info()/logger.debug()/... in the hooks will fail
            # because of the custom publish handler/extra attribute in the log methods
            self.__shut_down_publish_handler()

            try:
                self._app.logger.info("Launch publish process!")
                manager = self._publisher_app.create_publish_manager()
                manager.load(self._tree_file)
                manager.publish()
                manager.finalize()

            finally:
                os.environ["SGTK_BATCH_PUBLISH"] = "False"

    def _on_background_task_completed(self, uid, group_id, result):
        """
        Slot triggered when the background manager has finished doing some task. The only task we're asking the manager
        to do is to find the latest published file associated to the current item.

        :param uid:      Unique id associated with the task
        :param group_id: The group the task is associated with
        :param result:   The data returned by the task
        """
        if uid not in self._pending_requests:
            return
        self._pending_requests.remove(uid)
        self._ui.progress_message.setText("Publish process completed!")
        self._ui.progress_status_icon.setPixmap(
            QtGui.QPixmap(":/tk-multi-progress/publish_complete.png")
        )
        shutil.rmtree(os.path.dirname(self._tree_file))
        self._ui.close_button.setEnabled(True)

    def _on_background_task_failed(self, uid, group_id, msg, stack_trace):
        """
        Slot triggered when the background manager fails to do some task.

        :param uid:         Unique id associated with the task
        :param group_id:    The group the task is associated with
        :param msg:         Short error message
        :param stack_trace: Full error traceback
        """
        if uid in self._pending_requests:
            self._pending_requests.remove(uid)
        self._app.logger.error("Failed to execute publish process %s: %s" % (uid, msg))
        self._app.logger.error(stack_trace)
        self._app.logger.error("Publish tree file path: {}".format(self._tree_file))
        self._ui.progress_message.setText("Publish process failed!")
        self._ui.progress_status_icon.setPixmap(
            QtGui.QPixmap(":/tk-multi-progress/publish_failed.png")
        )
        self._ui.close_button.setEnabled(True)

    def __shut_down_publish_handler(self):
        """"""

        tk_multi_publish2 = self._publisher_app.import_module("tk_multi_publish2")

        publisher_widget = None
        for widget in QtGui.QApplication.allWidgets():
            if isinstance(widget, tankqdialog.TankQDialog):
                if widget._widget:
                    child_widget = widget._widget
                    while child_widget:
                        if (
                            isinstance(child_widget, tk_multi_publish2.dialog.AppDialog)
                            and hasattr(child_widget, "_bundle")
                            and child_widget._bundle == self._publisher_app
                        ):
                            publisher_widget = child_widget
                            break
                        child_widget = child_widget.parent()

        publisher_widget._progress_handler.shut_down()
