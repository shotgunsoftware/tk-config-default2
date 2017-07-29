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
import hou
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# A dict of dicts organized by category, type and output file parm
_HOUDINI_OUTPUTS = {
    # rops
    hou.ropNodeTypeCategory(): {
        "alembic": "filename",    # alembic cache
        "comp": "copoutput",      # composite
        "ifd": "vm_picture",      # mantra render node
        "opengl": "picture",      # opengl render
        "wren": "wr_picture",     # wren wireframe
    },
}


class HoudiniSessionCollector(HookBaseClass):
    """
    Collector that operates on the houdini session
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current Houdini session and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """
        # create an item representing the current houdini session
        item = self.collect_current_houdini_session(parent_item)

        self.collect_node_outputs(item)

    def collect_current_houdini_session(self, parent_item):
        """
        Creates an item that represents the current houdini session.

        :param parent_item: Parent Item instance
        :returns: Item of type houdini.session
        """

        publisher = self.parent

        # get the path to the current file
        path = hou.hipFile.path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Houdini Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "houdini.session",
            "Houdini File",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "houdini.png"
        )
        session_item.set_icon_from_path(icon_path)

        self.logger.info("Collected current Houdini session")

        return session_item

    def collect_node_outputs(self, parent_item):
        """
        Creates items for known output nodes

        :param parent_item: Parent Item instance
        """

        for node_category in _HOUDINI_OUTPUTS:
            for node_type in _HOUDINI_OUTPUTS[node_category]:

                path_parm_name = _HOUDINI_OUTPUTS[node_category][node_type]

                # get all the nodes for the category and type
                nodes = hou.nodeType(node_category, node_type).instances()

                for node in nodes:

                    # get the evaluated path parm value
                    path = node.parm(path_parm_name).eval()

                    # ensure the output path exists
                    if not os.path.exists(path):
                        continue

                    self.logger.info(
                        "Processing %s node: %s" % (node_type, node.path()))

                    # allow the base class to collect and create the item. it
                    # should know how to handle the output path
                    item = super(HoudiniSessionCollector, self)._collect_file(
                        parent_item,
                        path,
                        frame_sequence=True
                    )

                    # the item has been created. update the display name to
                    # include the node path to make it clear to the user how it
                    # was collected within the current session.
                    item.name = "%s (%s)" % (item.name, node.path())
