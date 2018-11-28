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
import hou

HookBaseClass = sgtk.get_hook_baseclass()

class CustomHoudiniActions(HookBaseClass):

    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.

        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.

        The hook should return at least one action for each item passed in via the
        actions parameter.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        Because you are operating on a particular publish, you may tailor the output
        (caption, tooltip etc) to contain custom information suitable for this publish.

        The ui_area parameter is a string and indicates where the publish is to be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one action "instance" for
        an action! You can for example do scene introspection - if the action passed in
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than
        one object is returned for an action, use the params key to pass additional
        data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        # get the existing action instances
        action_instances = super(CustomHoudiniActions, self).generate_actions(sg_publish_data, actions, ui_area)

        if "image_plane" in actions:
            action_instances.append({
                "name": "image_plane",
                "params": None,
                "caption": "Create Camera Image Plane",
                "description": "Creates image plane for the selected camera or adds a new camera node with image plane set."
            })

        return action_instances

    ##############################################################################################################

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """

        # call the actions from super
        super(CustomHoudiniActions, self).execute_action(name, params, sg_publish_data)

        if name == "image_plane":
            self._create_image_plane(sg_publish_data)

    ##############################################################################################################
    def _import(self, path, sg_publish_data):
        """Import the supplied path as a geo/alembic sop.

        :param str path: The path to the file to import.
        :param dict sg_publish_data: The publish data for the supplied path.

        """

        app = self.parent

        name = sg_publish_data.get("name")
        path = self.get_publish_path(sg_publish_data)
        parent_module = sys.modules[HookBaseClass.__module__]

        # houdini doesn't like UNC paths.
        path = path.replace("\\", "/")

        obj_context = parent_module._get_current_context("/obj")

        published_file_type = sg_publish_data["published_file_type"].get("name")
        if published_file_type == "Model File" or published_file_type == "Model Sequence":
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
            try:
                alembic_node = obj_context.createNode("alembicarchive", name)
            except hou.OperationFailed:
                # failed to create the node in this context, create at top-level
                obj_context = hou.node("/obj")
                alembic_node = obj_context.createNode("alembicarchive", name)
            alembic_node.parm("fileName").set(path)
            alembic_node.parm("buildHierarchy").pressButton()
            node = alembic_node

        node_name = hou.nodeType(node.path()).name()
        app.log_debug(
            "Creating %s node: %s\n  path: '%s' " %
            (node_name, node.path(), path)
        )

        parent_module._show_node(node)

    ##############################################################################################################

    def _create_image_plane(self, sg_publish_data):
        """
        Adds an image plane for the selected camera or create a new camera node

        :param sg_publish_data: Shotgun data dictionary with all the standard
            publish fields.
        """

        app = self.parent

        name = sg_publish_data.get("name")
        path = self.get_publish_path(sg_publish_data)
        parent_module = sys.modules[HookBaseClass.__module__]

        # houdini doesn't like UNC paths.
        path = path.replace("\\", "/")

        obj_context = parent_module._get_current_context("/obj")

        selected_nodes = hou.selectedNodes()
        if selected_nodes:
            node_type = hou.nodeType(selected_nodes[0].path()).name()
            if len(selected_nodes) > 1:
                hou.ui.displayMessage("Please select only one camera node.")
            elif node_type != "cam":
                hou.ui.displayMessage("Please select a camera node.")
            else:
                camera_node = selected_nodes[0]
                camera_node.parm("vm_background").set(path)
                node_name = hou.nodeType(camera_node.path()).name()
                app.log_debug(
                    "Adding background image to %s node: %s\n  path: '%s' " %
                    (node_name, camera_node.path(), path)
                )
        else:
            try:
                camera_node = obj_context.createNode("cam", name)
            except hou.OperationFailed:
                obj_context = hou.node("/obj")
                camera_node = obj_context.createNode("cam", name)
            camera_node.parm("vm_background").set(path)

            node_name = hou.nodeType(camera_node.path()).name()
            app.log_debug(
                "Creating %s node: %s\n  path: '%s' " %
                (node_name, camera_node.path(), path)
            )

            parent_module._show_node(camera_node)