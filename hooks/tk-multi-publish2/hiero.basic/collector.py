# Copyright (c) 2017 Shotgun Software Inc.
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

HookBaseClass = sgtk.get_hook_baseclass()

class HieroSessionCollector(HookBaseClass):
    """
    Collector that operates on the current Hiero session. Should
    inherit from the basic collector hook.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Hiero and parents a
        subtree of items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        publisher = self.parent
        engine = publisher.engine

        if hasattr(engine, "hiero_enabled") and engine.hiero_enabled:
            # running hiero
            self.collect_current_hiero_session(parent_item)

            # since we're in NS, any additional collected outputs will be
            # parented under the root item
            session_item = parent_item

    def collect_current_hiero_session(self, parent_item):
        """
        Analyzes the current session open in Hiero and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # import here since the hooks are imported into nuke and nukestudio.
        # hiero module is only available in later versions of nuke
        import hiero.core
        import hiero.ui

        # go ahead and build the path to the icon for use by any projects
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "hiero.png"
        )

        active_project = None
        active_sequence = hiero.ui.activeSequence()
        if active_sequence:
            active_project = active_sequence.project()

        for project in hiero.core.projects():

            # create the session item for the publish hierarchy
            session_item = parent_item.create_item(
                "nukestudio.project",
                "NukeStudio Project",
                project.name()
            )
            session_item.set_icon_from_path(icon_path)

            # add the project object to the properties so that the publish
            # plugins know which open project to associate with this item
            session_item.properties["project"] = project

            self.logger.info(
                "Collected Hiero project: %s" % (project.name(),))

            # enable the active project and expand it. other projects are
            # collapsed and disabled.
            if active_project and active_project.guid() == project.guid():
                session_item.expanded = True
                session_item.checked = True
            elif active_project:
                # there is an active project, but this isn't it. collapse and
                # disable this item
                session_item.expanded = False
                session_item.checked = False

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    root_name = nuke.root().name()
    return None if root_name == "Root" else root_name
