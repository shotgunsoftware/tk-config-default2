# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import os
import tempfile

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopActions(HookBaseClass):
    """
    Photoshop Shotgun Panel Actions that apply to all DCCs
    """

    def generate_actions(self, sg_data, actions, ui_area):
        """
        Returns a list of action instances for a particular object.
        The data returned from this hook will be used to populate the
        actions menu.

        The mapping between Shotgun objects and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the app
        has already established *which* actions are appropriate for this object.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        The ui_area parameter is a string and indicates where the item is to be shown.

        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.

        :param sg_data: Shotgun data dictionary with a set of standard fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption, group and description
        """

        action_instances = []

        try:
            # call base class first
            action_instances += HookBaseClass.generate_actions(
                self, sg_data, actions, ui_area
            )
        except AttributeError as e:
            # base class doesn't have the method, so ignore and continue
            pass

        if "import_note_attachments" in actions:
            action_instances.append(
                {
                    "name": "import_note_attachments",
                    "params": None,
                    "caption": "Import Note attachment(s) as layer(s)",
                    "description": "This will create a new layer for each image attached to the note.",
                }
            )

        return action_instances

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: Shotgun data dictionary
        :returns: No return value expected.
        """

        if name == "import_note_attachments":
            self._import_note_attachments_as_layer(sg_data)

        else:
            try:
                HookBaseClass.execute_action(self, name, params, sg_data)
            except AttributeError as e:
                # base class doesn't have the method, so ignore and continue
                pass

    def _import_note_attachments_as_layer(self, sg_data):
        """"""
        engine = sgtk.platform.current_engine()
        current_doc = engine.adobe.get_active_document()

        tmp_folder = tempfile.mkdtemp(prefix="sgtk_notes")

        sg_note = self.parent.shotgun.find_one(
            "Note", [["id", "is", sg_data["id"]]], ["attachments"]
        )

        # download all the attachments on disk
        for a in sg_note["attachments"]:
            if a["name"].endswith(".png"):
                tmp_path = os.path.join(tmp_folder, a["name"])
                self.parent.shotgun.download_attachment(a, tmp_path)
                engine.adobe.add_as_layer(current_doc, tmp_path)
