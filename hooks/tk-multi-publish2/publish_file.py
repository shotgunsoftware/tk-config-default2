# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import os
import shutil
import traceback

import sgtk
from sgtk import TankError
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


class StandalonePublishPlugin(HookBaseClass):
    """
    Plugin for publishing files from the standalone publisher.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{config}/tk-multi-publish2/publish_file.py"

    """

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

        # fall back to template/path logic
        path = item.properties.path

        publish_template = self.get_publish_template(settings, item)
        if publish_template:

            try:
                fields = item.context.as_template_fields(
                    publish_template, validate=True
                )
            except TankError:
                ctx_entity = (
                    item.context.task or item.context.entity or item.context.project
                )
                self.parent.sgtk.create_filesystem_structure(
                    ctx_entity["type"], ctx_entity["id"]
                )
                fields = item.context.as_template_fields(
                    publish_template, validate=True
                )

            # try to fill all the missing keys
            missing_keys = publish_template.missing_keys(fields)
            if missing_keys:
                self._extend_fields(settings, item, fields, missing_keys)

            if missing_keys:
                self.logger.warning(
                    "Not enough keys to apply publish fields (%s) "
                    "to publish template (%s)" % (fields, publish_template)
                )
                return

            # try to find the suitable version number now that we have a "first" publish path
            # TODO: replace with paths_from_template()
            while True:
                publish_path = publish_template.apply_fields(fields)
                if "version" not in fields or not os.path.exists(publish_path):
                    item.properties["publish_version"] = fields["version"]
                    break
                fields["version"] += 1

        if not publish_path:
            publish_path = path

        return publish_path

    def get_publish_template(self, settings, item):
        """
        Get a publish template for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A template representing the publish path of the item or
            None if no template could be identified.
        """

        publish_template = item.get_property("publish_template")
        if publish_template:
            return publish_template

        if not item.context.entity:
            return None

        publish_templates = item.get_property("publish_templates")
        if not publish_templates:
            return None

        template_name = publish_templates.get(item.context.entity["type"].lower())
        if not template_name:
            return None

        return self.parent.get_template_by_name(template_name)

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
                    "Failed to copy work file from '%s' to '%s'.\n%s"
                    % (work_file, publish_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to publish file '%s'."
                % (work_file, publish_file)
            )
