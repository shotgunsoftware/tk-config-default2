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
from sgtk.util.filesystem import ensure_folder_exists
import vrController
import vrFileIO

HookBaseClass = sgtk.get_hook_baseclass()


class PublishVREDMetadataPlugin(HookBaseClass):

    @property
    def name(self):
        """One line display name describing the plugin"""
        return "Publish CMF Metadata to ShotGrid"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Export the VRED metadata as JSON file and publish it to ShotGrid."

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
        base_settings = super(PublishVREDMetadataPlugin, self).settings or {}

        # settings specific to this class
        plugin_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            },
            "Root Node Name": {
                "type": "str",
                "default": None,
                "description": "Name of the root node we want to get the metadata from it and its children."
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

        # make sure we run a version of VRED that supports metadata
        if float(vrController.getVredVersion()) < 15.2:
            self.logger.debug("Skipping the plugin: this version of VRED doesn't support metadata.")
            return {"accepted": False}

        # check that we have at least one metadata in the scene
        has_metadata = self.get_vred_metadata(settings, check=True)
        if not has_metadata:
            self.logger.debug("Skipping the plugin: can't find any metadata in the current scene.")
            return {"accepted": False}

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

        # be sure the "Publish to ShotGrid" publish plugin is also selected
        root_item = self.__get_root_item(item)
        is_plugin_checked = False
        for d in root_item.descendants:
            for t in d.tasks:
                if t.name == "Publish to ShotGrid" and t.checked:
                    is_plugin_checked = True
        if not is_plugin_checked:
            self.logger.error(
                'Please, check the "Publish to ShotGrid" publish plugin to be able to export the VRED metadata'
            )
            return False

        # check that we have a valid publish template
        publish_template_setting = settings.get("Publish Template")
        publish_template = self.parent.engine.get_template_by_name(
            publish_template_setting.value
        )
        if not publish_template:
            self.logger.error("Couldn't find a valid publish template to export the tape.")
            return False
        item.local_properties["publish_template"] = publish_template

        # ensure the session has been saved
        path = vrFileIO.getFileIOFilePath()
        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The VRED session has not been saved."
            self.logger.error(
                error_msg, extra=sgtk.platform.current_engine().open_save_as_dialog
            )
            raise Exception(error_msg)

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the publish "mode" stored inside of the root item properties
        bg_processing = item.parent.properties.get("bg_processing", False)
        in_bg_process = item.parent.properties.get("in_bg_process", False)

        if not bg_processing or (bg_processing and in_bg_process):

            publish_template = item.get_property("publish_template")

            # get the publish path of the current session and use it to retrieve some template fields
            session_publish_path = item.properties.sg_publish_data.get("path", {}).get("local_path")

            if not session_publish_path:
                self.logger.error("Couldn't find the publish path of the current session")
                return

            session_publish_template = self.sgtk.template_from_path(session_publish_path)
            template_fields = session_publish_template.get_fields(session_publish_path)

            publish_path = publish_template.apply_fields(template_fields)
            item.local_properties.publish_path = publish_path

            # ensure the publish folder exists
            publish_folder = os.path.dirname(publish_path)
            ensure_folder_exists(publish_folder)

            # get the metadata and export them as json file
            scene_metadata = self.get_vred_metadata(settings)
            with open(publish_path, "w+") as fp:
                json.dump(scene_metadata, fp)

            # finally, publish the scene
            item.local_properties.publish_type = "VRED Metadata"
            item.local_properties.publish_version = template_fields["version"]
            item.local_properties.publish_name = self.parent.util.get_publish_name(publish_path)
            item.local_properties.publish_dependencies = [session_publish_path]
            super(PublishVREDMetadataPlugin, self).publish(settings, item)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass

    def _copy_work_to_publish(self, settings, item):
        """
        This method handles copying work file path(s) to a designated publish
        location.

        This method requires a "work_template" and a "publish_template" be set
        on the supplied item.

        The method will handle copying the "path" property to the corresponding
        publish location assuming the path corresponds to the "work_template"
        and the fields extracted from the "work_template" are sufficient to
        satisfy the "publish_template".

        The method will not attempt to copy files if any of the above
        requirements are not met. If the requirements are met, the file will
        ensure the publish path folder exists and then copy the file to that
        location.

        If the item has "sequence_paths" set, it will attempt to copy all paths
        assuming they meet the required criteria with respect to the templates.

        """
        pass

    @staticmethod
    def get_vred_metadata(settings, check=False):
        """
        Get the VRED metadata of the root node and all its children.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param check: If check is True, stop as soon as we find the first metadata
        """

        scene_metadata = {}

        # get the root node
        node_name = settings.get("Root Node Name").value
        if not node_name:
            return {}
        root_node = vrNodeService.findNode(node_name)
        if not root_node:
            return {}

        def __rec_get_metadata(node):
            """Recursive function to get the metadata of a node and its children"""
            if vrMetadataService.hasMetadata(node):
                metadata = vrMetadataService.getMetadata(node)
                object_set = metadata.getObjectSet()
                entries = object_set.getEntries()
                node_metadata = {entry.getKey(): entry.getValue() for entry in entries}
                if node_metadata:
                    scene_metadata[node.getName()] = node_metadata
                if check:
                    return
            for child_node in node.getChildren():
                __rec_get_metadata(child_node)

        __rec_get_metadata(root_node)
        return scene_metadata

    def __get_root_item(self, item):
        """Recursively get the publish root item"""
        if item.is_root:
            return item
        else:
            return self.__get_root_item(item.parent)
