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
import sys
import nuke

import sgtk

from sgtk import TankError
from sgtk.platform.qt import QtGui
from tank.util import append_path_to_env_var
HookClass = sgtk.get_hook_baseclass()

logger = sgtk.platform.get_logger(__name__)

SG_DEV = "sg/tools/dev"
SG_PRIMARY = "sg/tools/primary"

if os.environ.get('PIPELINE_ROOT') and os.path.exists(os.environ['PIPELINE_ROOT']):
    sgtools_path = os.path.join(os.environ.get("PIPELINE_ROOT"), SG_PRIMARY)
    if os.environ.get("PIPELINE_DEV"):
        sgtools_path = os.path.join(os.environ.get("PIPELINE_ROOT"), SG_PRIMARY)
        # Check if there is a true value for this to
        # determine if user is a developer
        if os.environ.get("DEV_ROOT") and os.path.exists(os.environ.get("DEV_ROOT")):
            # DEV_ROOT is the root location of unique development work
            # This should be set by the developer on a local level
            sgtools_path = os.path.join(os.environ.get("DEV_ROOT"), SG_PRIMARY)

    if sgtools_path not in sys.path:
        sys.path.append(sgtools_path)

from sg_tools.utils.sg_utils import SGUtils

class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
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
        sgu = SGUtils(sgtk, engine, logger=logger)

        if hasattr(engine, "hiero_enabled") and (
            engine.hiero_enabled or engine.studio_enabled
        ):
            return self._scene_operation_hiero_nukestudio(
                operation,
                file_path,
                context,
                parent_action,
                file_version,
                read_only,
                **kwargs
            )

        logger.debug("Operation:{operation}".format(operation=operation))

        # If we didn't hit the Hiero or Nuke Studio case above, we can
        # continue with the typical Nuke scene operation logic.
        if file_path:
            file_path = file_path.replace("/", os.path.sep)

        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)

        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)

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

                # set frame range on intial save
                sgu.set_sg_frame_range(sgtk, context)

                # save script:
                nuke.scriptSaveAs(file_path, -1)
            except Exception as e:
                # something went wrong so reset to old path:
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s", e)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(
                    None,
                    "Save your script?",
                    "Your script has unsaved changes. Save before proceeding?",
                    QtGui.QMessageBox.Yes
                    | QtGui.QMessageBox.No
                    | QtGui.QMessageBox.Cancel,
                )

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()

            # now clear the script:
            nuke.scriptClear()
            return True

        elif operation == "prepare_new":
            logger.debug("Context:{context}".format(context=context))
            sgu.set_project_settings(context)

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

        if write_node_app.version == "Undefined" or LooseVersion(
            write_node_app.version
        ) > LooseVersion("v0.1.11"):
            return False

        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)

        return len(write_nodes) > 0

    def _scene_operation_hiero_nukestudio(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
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

    save_action = hiero.ui.findMenuAction("foundry.project.save")
    save_action.setText("Save Project (%s)" % (file_base,))

    save_as_action = hiero.ui.findMenuAction("foundry.project.saveas")
    save_as_action.setText("Save Project As (%s)..." % (file_base,))
