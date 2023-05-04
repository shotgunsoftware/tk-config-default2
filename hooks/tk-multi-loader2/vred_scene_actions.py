# Copyright (c) 2023 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import json
import os

import sgtk


HookBaseClass = sgtk.get_hook_baseclass()


class VredActions(HookBaseClass):
    """Hook that loads defines all the available actions, broken down by publish type."""

    MATERIAL_GROUP_NAME = "ShotGrid Materials"

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

        :param sg_publish_data: ShotGrid data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        action_instances = []
        try:
            # call base class first
            action_instances += HookBaseClass.generate_actions(
                self, sg_publish_data, actions, ui_area
            )
        except AttributeError:
            # base class doesn't have the method, so ignore and continue
            pass

        if "import_metadata" in actions:
            action_instances.append(
                {
                    "name": "import_metadata",
                    "params": None,
                    "caption": "Import VRED Metadata",
                    "description": "This will import the VRED Metadata and update the Scene Graph accordingly.",
                }
            )

        if "import_material" in actions:
            action_instances.append(
                {
                    "name": "import_material",
                    "params": None,
                    "caption": "Import VRED Material",
                    "description": "This will import the OSB file as VRED Material.",
                }
            )

        return action_instances

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: ShotGrid data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """

        path = self.get_publish_path(sg_publish_data)

        if name == "import_metadata":
            self.import_metadata(path)
        elif name == "import_material":
            self.import_material(path)
        else:
            super(VredActions, self).execute_action(name, params, sg_publish_data)

    def import_metadata(self, path):
        """Import the VRED metadata and update the scene graph accordingly"""

        if not os.path.isfile(path):
            return

        with open(path, "r+") as fp:
            metadata = json.load(fp)
            for node_name, node_metadata in metadata.items():
                node = vrNodeService.findNode(node_name)
                if not node:
                    continue
                metadata = vrMetadataService.getMetadata(node)
                object_set = metadata.getObjectSet()
                for key, value in node_metadata.items():
                    object_set.setValue(key, value)

    def import_material(self, path):
        """Import the OSB file as VRED Material"""

        if not os.path.isfile(path):
            return

        # find the material group node and if it doesn't exist, create it
        group_node = vrNodeService.findNode(self.MATERIAL_GROUP_NAME, root=vrMaterialService.getMaterialRoot())
        if not group_node.isValid():
            group_node = vrMaterialService.createMaterialGroup()
            group_node.setName(self.MATERIAL_GROUP_NAME)

        # load the OSB file
        material = vrMaterialService.loadMaterials([path])[0]

        # move the material to the right group
        material_node = vrMaterialService.findMaterialNode(material)
        group_node.children.append(material_node)