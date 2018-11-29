# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import hou

import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtGui
from dd.runtime import api
api.load("preferences")
import preferences

HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the current scene
    """
    def execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """

        fields = context.as_template_fields()

        if operation == "current_path":
            return str(hou.hipFile.name())
        elif operation == "open":
            # give houdini forward slashes
            file_path = file_path.replace(os.path.sep, '/')
            hou.hipFile.load(file_path.encode("utf-8"))
            self.set_show_preferences(fields)
        elif operation == "save":
            hou.hipFile.save()
        elif operation == "save_as":
            # give houdini forward slashes
            file_path = file_path.replace(os.path.sep, '/')
            hou.hipFile.save(str(file_path.encode("utf-8")))
        elif operation == "reset":
            hou.hipFile.clear()
            if parent_action == "new_file":
                self.set_show_preferences(fields)
                self.sync_frame_range()
            return True

    def sync_frame_range(self):
        # using sgtk.platform.current_engine() instead of self.parent.engine because
        # context_change_allowed is False for houdini and tk-multi-workfiles app being in middle of execution
        # continues with the same instance even upon context change giving different environment and engine contexts
        engine = sgtk.platform.current_engine()
        if engine.context.entity is None:
            # tk-multi-setframerange needs a context entity to work
            warning_message = "Your current context does not have an entity " \
                              "(e.g. a current Shot, current Asset etc). \nNot syncing frame range."
            self.parent.logger.warning(warning_message)
            QtGui.QMessageBox.warning(None, "Context has no entity", warning_message)
            return

        try:
            # get app
            frame_range_app = engine.apps["tk-multi-setframerange"]
        except KeyError as ke:
            error_message = "Unable to find {} in {} at this time. " \
                            "Not syncing frame range automatically.".format(ke, engine.name)
            # assume it is sequence/asset entity and do not give a pop-up warning
            self.parent.logger.warning(error_message)
        else:
            try:
                frame_range_app.run_app()
            except TankError as te:
                warning_message = "{}. Not syncing frame range.".format(te)
                self.parent.logger.warning(warning_message)
                QtGui.QMessageBox.warning(None, "Entity has no in/out frame", warning_message)

    def set_show_preferences(self, fields):
        show_prefs = preferences.Preferences(pref_file_name="show_preferences.yaml",
                                             role=fields.get("Step"),
                                             seq_override=fields.get("Sequence"),
                                             shot_override=fields.get("Shot"))
        try:
            hou.setFps(show_prefs["show_settings"]["fps"])
        except KeyError as ke:
            warning_message = "Unable to find {} in show preferences. " \
                              "Not setting fps.".format(ke)
            self.parent.logger.warning(warning_message)
            QtGui.QMessageBox.warning(None, "FPS not set", warning_message)