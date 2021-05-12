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
import re
import sgtk
from sgtk import TankError
from sgtk.util.filesystem import ensure_folder_exists
import shutil
import traceback

HookBaseClass = sgtk.get_hook_baseclass()


class StandalonePublishPlugin(HookBaseClass):
    """
    Plugin for publishing files from the Standalone Publisher.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

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
        base_settings = super(StandalonePublishPlugin, self).settings or {}

        standalone_publish_settings = {
            "Publish Templates": {
                "type": "dict",
                "default": None,
                "description": "Templates paths for published work files. Should correspond to templates defined in"
                               "templates.yml. The key of the dictionary is the Publish File Type we want to associate"
                               "to the template. The value of the dictionary is also a dictionary where the key is the"
                               "entity type we want to define the template for and the value is the template itself.",
            },
            "Default Publish Templates": {
                "type": "dict",
                "default": None,
                "description": "Templates paths for published work files. Should correspond to templates defined in"
                               "templates.yml. The key of the dictionary is the entity type we want to associate"
                               "to the template. The value is the template itself.",
            }
        }

        base_settings.update(standalone_publish_settings)

        return base_settings

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

        if item.type_spec == "file.alias.translation":
            return {"accepted": False}

        return super(StandalonePublishPlugin, self).accept(settings, item)

    def get_publish_path(self, settings, item):
        """
        Get a publish path for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish path for

        :return: A string representing the output path to supply when
            registering a publish for the supplied item

        Extracts the publish path via the configured work and publish templates
        if possible.
        """

        # publish type explicitly set or defined on the item
        publish_path = item.get_property("publish_path")
        if publish_path:
            return publish_path

        publish_template = self.get_publish_template(settings, item)
        if publish_template:

            # first, try to get the template fields from the selected context
            # if no folder has been created on disk, this logic will fail as the cache will be empty. We have to
            # find another solution to get the template keys from the current context
            try:
                fields = item.context.as_template_fields(publish_template, validate=True)
            except TankError:
                ctx_entity = item.context.task or item.context.entity or item.context.project
                self.parent.sgtk.create_filesystem_structure(ctx_entity["type"], ctx_entity["id"])
                fields = item.context.as_template_fields(publish_template, validate=True)

            # try to fill all the missing keys
            missing_keys = publish_template.missing_keys(fields)
            if missing_keys:
                self._extend_fields(settings, item, fields, missing_keys)

            if missing_keys:
                self.logger.warning("Not enough keys to apply publish fields (%s) "
                                    "to publish template (%s)" % (fields, publish_template))
                return

            # be sure to have the right name to find the version number
            original_name = fields.get("name")
            if "sequence_paths" in item.properties and "name" in fields:
                fields["name"] = fields["name"].split(".")[0]

            # try to find the suitable version number now that we have a "first" publish path
            while True:
                publish_path = publish_template.apply_fields(fields)
                if "version" not in fields or not os.path.exists(publish_path):
                    item.properties["publish_version"] = fields["version"]
                    break
                fields["version"] += 1

            # restore the sequence name if needed
            if "sequence_paths" in item.properties and "name" in fields:
                fields["name"] = original_name

            # add the seq token
            if "sequence_paths" in item.properties:
                file_name, file_extension = os.path.splitext(publish_path)
                seq_token = self.__get_seq_token(os.path.basename(item.properties.path))
                if seq_token:
                    publish_path = file_name + "." + seq_token + file_extension

        item.properties["publish_path"] = publish_path

        return publish_path

    def get_publish_template(self, settings, item):
        """
        Get a publish template for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A template representing the publish path of the item or
            None if no template could be identified.
        """
        publish_template = super(StandalonePublishPlugin, self).get_publish_template(settings, item)

        if publish_template:
            return publish_template

        # first, try to determine if a template has been defined for the item publish type
        publish_template = self.__get_template_by_publish_type(settings, item)
        if publish_template:
            return publish_template

        # if no template has been found, try to get the default one
        publish_template = self.__get_default_template(settings, item)

        return publish_template

    def get_publish_version(self, settings, item):
        """
        Get the publish version for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish version for

        Extracts the publish version via the configured work template if
        possible. Will fall back to using the path info hook.
        """

        publish_version = item.get_property("publish_version")
        if publish_version:
            return publish_version

        # fall back to the template/path_info logic
        publisher = self.parent
        path = item.properties.path

        self.logger.debug("Using path info hook to determine publish version.")
        publish_version = publisher.util.get_version_number(path)
        if publish_version is None:
            publish_version = 1

        return publish_version

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

        publish_template = self.get_publish_template(settings, item)
        if not publish_template:
            self.logger.debug(
                "No publish template set on the item. "
                "Skipping copying file to publish location."
            )
            return

        # ---- get a list of files to be copied

        # by default, the path that was collected for publishing
        work_files = [item.properties.path]

        # if this is a sequence, get the attached files
        if "sequence_paths" in item.properties:
            work_files = item.properties.get("sequence_paths", [])
            if not work_files:
                self.logger.warning(
                    "Sequence publish without a list of files. Publishing "
                    "the sequence path in place: %s" % (item.properties.path,)
                )
                return

        # ---- copy the work files to the publish location

        for work_file in work_files:

            publish_file = self.get_publish_path(settings, item)

            # copy the file
            try:
                publish_folder = os.path.dirname(publish_file)
                ensure_folder_exists(publish_folder)
                shutil.copyfile(work_file, publish_file)
            except Exception:
                raise Exception(
                    "Failed to copy work file from '%s' to '%s'.\n%s" %
                    (work_file, publish_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to publish file '%s'." %
                (work_file, publish_file)
            )

    def _extend_fields(self, settings, item, fields, missing_keys):
        """
        Add missing fields to match the publish template.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish path for
        :param fields: Templates fields extracted from the context
        :param missing_keys: List of missing fields keys

        :return:
        """

        publish_name = self.get_publish_name(settings, item)
        name, file_extension = os.path.splitext(publish_name)
        file_extension = file_extension[1:]

        if "version" in missing_keys:
            fields["version"] = self.get_publish_version(settings, item)
            missing_keys.remove("version")

        if "name" in missing_keys:
            fields["name"] = name
            missing_keys.remove("name")

        if "extension" in missing_keys:
            fields["extension"] = file_extension
            missing_keys.remove("extension")

    def __get_template_by_publish_type(self, settings, item):
        """
        :return:
        """

        publish_templates = settings.get("Publish Templates").value
        if not publish_templates:
            return

        publish_type = self.get_publish_type(settings, item)
        templates_by_type = publish_templates.get(publish_type)
        if not templates_by_type:
            return

        return self.__get_template_by_entity_type(item, templates_by_type)

    def __get_default_template(self, settings, item):
        """
        :param settings:
        :param item:
        :return:
        """

        publish_templates = settings.get("Default Publish Templates").value
        if not publish_templates:
            return

        return self.__get_template_by_entity_type(item, publish_templates)

    def __get_template_by_entity_type(self, item, publish_templates):
        """
        :return:
        """

        shotgun_globals = self.parent.frameworks["tk-framework-shotgunutils"].import_module("shotgun_globals")

        if not item.context.entity:
            return
        entity_type = item.context.entity["type"]

        # check if a template can be found using the entity type or entity display name
        entity_type_list = [
            entity_type,
            entity_type.lower(),
            shotgun_globals.get_type_display_name(entity_type),
            shotgun_globals.get_type_display_name(entity_type).lower()
        ]

        for e in entity_type_list:
            publish_template = publish_templates.get(e)
            if publish_template:
                return self.parent.engine.get_template_by_name(publish_template)

        return None

    @staticmethod
    def __get_seq_token(file_name):
        """
        :param file_name:
        :return:
        """
        seg_regex = r"(.+)%0(\d+)d(.+)"
        matched = re.match(seg_regex, os.path.basename(file_name))
        if matched:
            return "%0{}d".format(matched.group(2))
