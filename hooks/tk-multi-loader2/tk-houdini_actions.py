# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type. 
"""
import os
import re
import sgtk
import sys

HookBaseClass = sgtk.get_hook_baseclass()

class CustomHoudiniActions(HookBaseClass):

    ##############################################################################################################
    def _import(self, path, sg_publish_data):
        """Import the supplied path as a geo/alembic sop.

        :param str path: The path to the file to import.
        :param dict sg_publish_data: The publish data for the supplied path.

        """

        import hou
        app = self.parent

        name = sg_publish_data.get("name")
        path = self.get_publish_path(sg_publish_data)
        parent_module = sys.modules[HookBaseClass.__module__]

        # houdini doesn't like UNC paths.
        path = path.replace("\\", "/")

        obj_context = parent_module._get_current_context("/obj")

        try:
            geo_node = obj_context.createNode("geo", name)
        except hou.OperationFailed:
            # failed to create the node in this context, create at top-level
            obj_context = hou.node("/obj")
            geo_node = obj_context.createNode("geo", name)

        app.log_debug("Created geo node: %s" % (geo_node.path(),))

        # delete the default nodes created in the geo
        for child in geo_node.children():
            child.destroy()

        published_file_type = sg_publish_data["published_file_type"].get("name")
        if published_file_type == "Model File" or published_file_type == "Model Sequence":
            file_sop = geo_node.createNode("file", name)
            # replace any %0#d format string with the corresponding houdini frame
            # env variable. example %04d => $F4
            frame_pattern = re.compile("(%0(\d)d)")
            frame_match = re.search(frame_pattern, path)
            if frame_match:
                full_frame_spec = frame_match.group(1)
                padding = frame_match.group(2)
                path = path.replace(full_frame_spec, "$F%s" % (padding,))
            file_sop.parm("file").set(path)
            node = file_sop
        else:
            alembic_sop = geo_node.createNode("alembic", name)
            alembic_sop.parm("fileName").set(path)
            node = alembic_sop

        node_name = hou.nodeType(node.path()).name()
        app.log_debug(
            "Creating %s node: %s\n  path: '%s' " %
            (node_name, node.path(), path)
        )
        node.parm("reload").pressButton()

        parent_module._show_node(node)

    ##############################################################################################################
