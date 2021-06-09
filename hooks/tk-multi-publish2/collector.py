# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import glob
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaSessionCollector(HookBaseClass):
    """
    Collector that operates on the maya session. Should inherit from the basic
    collector hook.

    RA overriding this to also include FBX for Alias
    """

    def collect_current_maya_session(self, settings, parent_item):
        """
        Creates an item that represents the current maya session.
        :param parent_item: Parent Item instance
        :returns: Item of type maya.session
        """

        publisher = self.parent

        # get the path to the current file
        path = cmds.file(query=True, sn=True)

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Maya Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "maya.session",
            "Maya Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            "icons",
            "maya.png"
        )
        session_item.set_icon_from_path(icon_path)

        # Add an FBX export item as child of the session item
        filename = os.path.splitext(display_name)[0]
        fbx_display_name = filename + ".fbx"
        fbx_item = session_item.create_item(
            "maya.fbx",
            "FBX Export",
            fbx_display_name
        )
        
        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            "icons",
            "fbx.png"
        )

        fbx_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = cmds.workspace(q=True, rootDirectory=True)
        session_item.properties["project_root"] = project_root

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            self.logger.debug("Work template defined for Maya collection.")

        self.logger.info("Collected current Maya scene")

        return session_item
