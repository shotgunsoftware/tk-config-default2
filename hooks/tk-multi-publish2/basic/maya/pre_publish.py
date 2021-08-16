# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from maya import cmds
from PySide2.QtWidgets import QMessageBox

HookBaseClass = sgtk.get_hook_baseclass()


class PrePublishHook(HookBaseClass):
    """
    This hook defines logic to be executed before showing the publish
    dialog. There may be conditions that need to be checked before allowing
    the user to proceed to publishing.
    """

    def validate(self):
        """
        Returns True if the user can proceed to publish. Override thsi hook
        method to execute any custom validation steps.
        """

        # engine = sgtk.platform.current_engine()

        # Check for the right scene stuff
        # TODO move this part to a checker module
        # Check for the unknown reference nodes
        for ref_node in cmds.ls(type='reference'):
            try:
                cmds.referenceQuery(ref_node, filename=True)
            except Exception as e:
                cmds.lockNode(ref_node, lock=False)
                cmds.delete(ref_node)

        message = None
        selection = cmds.ls(assemblies=True, selection=True, long=True)
        if not selection:
            message = 'Please, select a geometry group to export to Alembic.'
        elif len(selection) > 1:
            message = 'Please, select only one geometry group to export to Alembic.'
        if message:
            QMessageBox.warning(None, 'Export to Alembic', message)
            return False

        return True
