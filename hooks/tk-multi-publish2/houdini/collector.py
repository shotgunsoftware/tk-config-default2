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


class DDHoudiniSessionCollector(HookBaseClass):

    def __init__(self, parent, **kwargs):
        """
        Construction
        """
        # call base init
        super(DDHoudiniSessionCollector, self).__init__(parent, **kwargs)

        self.houdini_sgtk_outputs[hou.ropNodeTypeCategory()]["geometry"] = "sopoutput"
        self.houdini_native_outputs[hou.ropNodeTypeCategory()]["geometry"] = "sopoutput"

    def collect_tk_geometrynodes(self, settings, parent_item):
        """
        Checks for an installed `tk-houdini-geometrynode` app. If installed, will
        search for instances of the node in the current session and create an
        item for each one with an output on disk.

        :param dict settings: Configured settings for this collector
        :param parent_item: The parent item for any write geo nodes collected
        """
        items = []

        publisher = self.parent
        engine = publisher.engine

        geometrynode_app = engine.apps.get("tk-houdini-geometrynode")
        if not geometrynode_app:
            self.logger.debug(
                "The tk-houdini-geometrynode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return items

        try:
            tk_geometry_nodes = geometrynode_app.get_nodes()
        except AttributeError:
            self.logger.warning(
                "Unable to query the session for tk-houdini-geometrynode "
                "instances. It looks like perhaps an older version of the "
                "app is in use which does not support querying the nodes. "
                "Consider updating the app to allow publishing their outputs."
            )
            return items

        for node in tk_geometry_nodes:

            out_path = geometrynode_app.get_output_path(node)

            if not os.path.exists(out_path):
                continue

            self.logger.info(
                "Processing sgtk_geometry node: %s" % (node.name(),))

            # allow the base class to collect and create the item. it
            # should know how to handle the output path
            item = self._collect_file(settings, parent_item, out_path)

            # the item has been created. update the display name to
            # include the node path to make it clear to the user how it
            # was collected within the current session.
            item.name = "%s (%s)" % (node.type().name(), node.name())

            # Store a reference to the originating node
            item.properties.node = node

            # Add item to the list
            items.append(item)

            self._geometry_nodes_collected = True

        return items
