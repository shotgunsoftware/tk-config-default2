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
import nuke

import sgtk

from sgtk import TankError
from sgtk.platform.qt import QtGui

HookClass = sgtk.get_hook_baseclass()

from dd.runtime import api

api.load("preferences")
import preferences

SHOW_FORMAT_NAME = 'SHOW_FORMAT'

class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
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
        # We need to see which mode of Nuke we're in. If this is Hiero or
        # Nuke Studio, then we have a separate scene operation routine to
        # use. We're checking that the "hiero_enabled" attribute exists
        # to ensure that this works properly with pre-v0.4.x versions of
        # the tk-nuke engine. If that one attribute exists, then we can be
        # confident that the "studio_enabled" attribute is also available,
        # so there's no need to check that.
        #
        # If there is ever a situation where Hiero- or Nuke Studio-specific
        # logic is required that doesn't also apply to the other, then this
        # conditional could be broken up between hiero_enabled and
        # studio_enabled cases that call through to Nuke Studio and Hiero
        # specific methods.
        engine = self.parent.engine
        if hasattr(engine, "hiero_enabled") and (engine.hiero_enabled or engine.studio_enabled):
            return self._scene_operation_hiero_nukestudio(
                operation,
                file_path,
                context,
                parent_action,
                file_version,
                read_only,
                **kwargs
            )

        # If we didn't hit the Hiero or Nuke Studio case above, we can
        # continue with the typical Nuke scene operation logic.
        if file_path:
            file_path = file_path.replace("/", os.path.sep)

        fields = context.as_template_fields()
        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)

        elif operation == "open":
            # open the specified script
            self.set_show_preferences(fields)
            nuke.scriptOpen(file_path)
            self.set_ocio_context(fields)

            # reset any write node render paths:
            if self._reset_write_node_render_paths():
                # something changed so make sure to save the script again:
                nuke.scriptSave()

        elif operation == "save":
            # save the current script:
            nuke.scriptSave()

        elif operation == "save_as":
            old_path = nuke.root()["name"].value()
            try:
                # rename script:
                nuke.root()["name"].setValue(file_path)

                # reset all write nodes:
                self._reset_write_node_render_paths()

                # save script:
                nuke.scriptSaveAs(file_path, -1)
            except Exception, e:
                # something went wrong so reset to old path:
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s", e)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your script?",
                                                 "Your script has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()

            # now clear the script:
            nuke.scriptClear()
            if parent_action == "new_file":
                self.set_show_preferences(fields)
                self.sync_frame_range()

            return True

    def sync_frame_range(self):
        engine = self.parent.engine
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
            pixel_aspect_ratio = show_prefs["show_settings"]["resolution"].get("pixel_aspect_ratio")

            if not pixel_aspect_ratio:
                format_string = "{0} {1} {2}".format(show_prefs["show_settings"]["resolution"]["width"],
                                                     show_prefs["show_settings"]["resolution"]["height"],
                                                     SHOW_FORMAT_NAME)
            else:
                format_string = "{0} {1} {2} {3}".format(show_prefs["show_settings"]["resolution"]["width"],
                                                         show_prefs["show_settings"]["resolution"]["height"],
                                                         pixel_aspect_ratio,
                                                         SHOW_FORMAT_NAME)

            formats = nuke.formats()
            for nuke_format in formats:
                if nuke_format.name() == SHOW_FORMAT_NAME:
                    nuke_format.setName('')
            nuke.addFormat(format_string)
            nuke.root().knob('format').setValue(SHOW_FORMAT_NAME)
        except KeyError as ke:
            self.parent.logger.warning("Unable to find {} in show preferences. "
                                       "Not setting root format.".format(ke))

        try:
            nuke.root().knob('fps').setValue(show_prefs["show_settings"]["fps"])
        except KeyError as ke:
            self.parent.logger.warning("Unable to find {} in show preferences. "
                                       "Not setting fps.".format(ke))

    def set_ocio_context(self, fields):
        """
        Set OCIO context for current OCIODisplay node
        """
        sequence = fields.get("Sequence")
        shot = fields.get("Shot")

        ocio_display_node = nuke.ViewerProcess.node()
        if ocio_display_node:
            ocio_display_node["key1"].setValue("DD_SEQ")
            ocio_display_node["value1"].setValue(sequence)
            ocio_display_node["key2"].setValue("DD_SHOT")
            ocio_display_node["value2"].setValue(shot)


    def _get_current_hiero_project(self):
        """
        Returns the current project based on where in the UI the user clicked
        """
        import hiero

        # get the menu selection from hiero engine
        selection = self.parent.engine.get_menu_selection()

        if len(selection) != 1:
            raise TankError("Please select a single Project!")

        if not isinstance(selection[0], hiero.core.Bin):
            raise TankError("Please select a Hiero Project!")

        project = selection[0].project()
        if project is None:
            # apparently bins can be without projects (child bins I think)
            raise TankError("Please select a Hiero Project!")

        return project

    def _reset_write_node_render_paths(self):
        """
        Use the tk-nuke-writenode app interface to find and reset
        the render path of any Shotgun Write nodes in the current script
        """
        write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            return False

        # only need to forceably reset the write node render paths if the app version
        # is less than or equal to v0.1.11
        from distutils.version import LooseVersion
        if (write_node_app.version == "Undefined"
                or LooseVersion(write_node_app.version) > LooseVersion("v0.1.11")):
            return False

        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)

        return len(write_nodes) > 0

    def _scene_operation_hiero_nukestudio(
            self, operation, file_path, context, parent_action, file_version, read_only, **kwargs
    ):
        """
        Scene operation logic for Hiero and Nuke Studio modes of Nuke.

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
        import hiero

        if operation == "current_path":
            # return the current script path
            project = self._get_current_hiero_project()
            curr_path = project.path().replace("/", os.path.sep)
            return curr_path

        elif operation == "open":
            # Manually fire the kBeforeProjectLoad event in order to work around a bug in Hiero.
            # The Foundry has logged this bug as:
            #   Bug 40413 - Python API - kBeforeProjectLoad event type is not triggered
            #   when calling hiero.core.openProject() (only triggered through UI)
            # It exists in all versions of Hiero through (at least) v1.9v1b12.
            #
            # Once this bug is fixed, a version check will need to be added here in order to
            # prevent accidentally firing this event twice. The following commented-out code
            # is just an example, and will need to be updated when the bug is fixed to catch the
            # correct versions.
            # if (hiero.core.env['VersionMajor'] < 1 or
            #     hiero.core.env['VersionMajor'] == 1 and hiero.core.env['VersionMinor'] < 10:
            hiero.core.events.sendEvent("kBeforeProjectLoad", None)

            # open the specified script
            hiero.core.openProject(file_path.replace(os.path.sep, "/"))

        elif operation == "save":
            # save the current script:
            project = self._get_current_hiero_project()
            project.save()

        elif operation == "save_as":
            project = self._get_current_hiero_project()
            project.saveAs(file_path.replace(os.path.sep, "/"))

            # ensure the save menus are displayed correctly
            _update_save_menu_items(project)

        elif operation == "reset":
            # do nothing and indicate scene was reset to empty
            return True

        elif operation == "prepare_new":
            # add a new project to hiero
            hiero.core.newProject()


def _update_save_menu_items(project):
    """
    There's a bug in Hiero when using `project.saveAs()` whereby the file menu
    text is not updated. This is a workaround for that to find the menu
    QActions and update them manually to match what Hiero should display.
    """

    import hiero

    project_path = project.path()

    # get the basename of the path without the extension
    file_base = os.path.splitext(os.path.basename(project_path))[0]

    save_action = hiero.ui.findMenuAction('foundry.project.save')
    save_action.setText("Save Project (%s)" % (file_base,))

    save_as_action = hiero.ui.findMenuAction('foundry.project.saveas')
    save_as_action.setText("Save Project As (%s)..." % (file_base,))
