# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import os
import sgtk

from pyfbsdk import FBApplication

mb_app = FBApplication()

HookBaseClass = sgtk.get_hook_baseclass()


class MotionBuilderSessionCollector(HookBaseClass):
    """
    Collector that operates on the motion builder session. Should inherit from the basic
    collector hook.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Motion Builder and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # create an item representing the current motion builder session
        item = self.collect_current_motion_builder_session(parent_item)

    def collect_current_motion_builder_session(self, parent_item):
        """
        Creates an item that represents the current motion builder session.

        :param parent_item: Parent Item instance
        :returns: Item of type motionbuilder.session
        """

        publisher = self.parent

        # get the path to the current file
        path = mb_app.FBXFileName

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Motion Builder Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "motionbuilder.session",
            "Motion Builder Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "motionbuilder.png"
        )
        session_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = path
        session_item.properties["project_root"] = project_root

        self.logger.info("Collected current Motion Builder scene")

        return session_item

