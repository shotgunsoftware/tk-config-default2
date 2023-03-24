# Copyright (c) 2023 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.
import os

import alias_api
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class AliasActions(HookBaseClass):
    """Custom ShotGrid Actions for Alias"""

    def generate_actions(self, sg_data, actions, ui_area):
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

        :param sg_data: ShotGrid data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        action_instances = super(AliasActions, self).generate_actions(sg_data, actions, ui_area)

        if "import_tape" in actions:
            action_instances.append(
                {
                    "name": "import_tape",
                    "params": None,
                    "caption": "Import Tape from VRED",
                    "description": "Import a Tape exported from VRED as FBX"
                }
            )

        return action_instances

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: ShotGrid data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """

        if name == "import_tape":
            self._import_file_from_note(sg_data)

        else:
            super(AliasActions, self).execute_action(name, params, sg_data)

    def _import_file_from_note(self, sg_data):
        """Read the node data to get the FBX file to import, then import it"""

        for note_link in sg_data["note_links"]:

            if note_link["type"] != "PublishedFile":
                continue

            if not note_link["name"].endswith(".fbx"):
                continue

            sg_publish = self.parent.shotgun.find_one(
                "PublishedFile",
                [["id", "is", note_link["id"]]],
                ["path"]
            )
            if not os.path.exists(sg_publish["path"]["local_path"]):
                return

            alias_api.import_file(sg_publish["path"]["local_path"])
