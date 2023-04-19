# Copyright (c) 2023 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.
import os.path

import sgtk
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


class PublishVREDTapePlugin(HookBaseClass):
    """Plugin for exporting VRED Tape as FBX and publish it to SG"""

    @property
    def name(self):
        """One line display name describing the plugin"""
        return "Publish Tape to ShotGrid"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Export VRED Tape as FBX and publish it to ShotGrid"

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # inherit the settings from the base publish plugin
        base_settings = super(PublishVREDTapePlugin, self).settings or {}

        # settings specific to this class
        plugin_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
            },
            "Tape Node Path": {
                "type": "str",
                "default": "WorldRef",
                "description": ""
            }
        }

        # update the base settings
        base_settings.update(plugin_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["vred.session"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """
        return {"accepted": True, "checked": False}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        # check that we have a valid publish template
        publish_template_setting = settings.get("Publish Template")
        publish_template = self.parent.engine.get_template_by_name(
            publish_template_setting.value
        )
        if not publish_template:
            self.logger.error("Couldn't find a valid publish template to export the tape.")
            return False
        item.local_properties["publish_template"] = publish_template

        # check that we have something to export
        tape_node = self.get_tape_node(settings)
        if not tape_node:
            self.logger.error("Couldn't find tape node in the current scene")
            return False

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publish_template = item.get_property("publish_template")
        template_fields = item.context.as_template_fields(publish_template)

        # get the file name from the node path
        path_components = settings["Tape Node Path"].value.split("/")
        template_fields["name"] = path_components[-1]

        # now it's time to get the version number
        existing_files = self.parent.sgtk.paths_from_template(
            publish_template,
            template_fields,
            skip_keys=["version"]
        )
        template_fields["version"] = max(
            [publish_template.get_fields(p).get("version") for p in existing_files],
            default=0
        ) + 1
        publish_path = publish_template.apply_fields(template_fields)
        item.local_properties["publish_path"] = publish_path
        item.local_properties["path"] = publish_path

        # export the tape as FBX
        self.export_tape_as_fbx(settings, item)

        # publish the tape file to ShotGrid
        super(PublishVREDTapePlugin, self).publish(settings, item)

        # move the sg_data property to local_property to be able to access it later in the finalize method
        item.local_properties["sg_publish_data"] = item.get_property("sg_publish_data")

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # create a note to warn people that a new file has been published
        data = {
            "subject": "VRED VR Taping Note",
            "sg_status_list": "opn",
            "content": "A new tape file has been published",
            "project": item.context.project,
            "note_links": [item.context.entity, item.get_property("sg_publish_data")],
            "tasks": [item.context.task],
            "addressings_to": [item.context.user],
        }

        # find the tasks the note should be linked to (current task + downstream task)
        sg_downstream_task = self.parent.shotgun.find_one(
            "Task",
            [["downstream_tasks", "is", item.context.task]],
            ["task_assignees"]
        )
        if sg_downstream_task:
            data["tasks"] += [sg_downstream_task]
            data["addressings_to"] += sg_downstream_task["task_assignees"]

        self.parent.shotgun.create("Note", data)

    def get_tape_node(self, settings):
        """Check for the Tape node in the VRED scene"""
        node_path = settings.get("Tape Node Path").value
        return self.parent.engine.vredpy.vrScenegraph.findNodePath(node_path)

    def export_tape_as_fbx(self, settings, item):
        """Export the tape as FBX"""
        tape_node = self.get_tape_node(settings)
        path = item.get_property("publish_path")
        export_folder = os.path.dirname(path)
        ensure_folder_exists(export_folder)
        self.parent.engine.vredpy.vrFileIO.saveGeometry(tape_node, path)
