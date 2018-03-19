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
import datetime
import pprint
import urllib

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class IngestCollectorPlugin(HookBaseClass):
    """
    Collector that operates on the current set of ingestion files. Should
    inherit from the basic collector hook.
    """

    def _resolve_work_path_template(self, properties, path):
        """
        Resolve work_path_template from the properties.
        The signature uses properties, so that it can resolve the template even if the item object hasn't been created.

        :param properties: properties that have/will be used to build item object.
        :param path: path to be used to get the templates, using template_from_path,
         in this class we use os.path.basename of the path.
        :return: Name of the template.
        """


        # using file name for resolving templates
        path = os.path.basename(path)

        work_path_template = super(IngestCollectorPlugin, self)._resolve_work_path_template(properties, path)
        return work_path_template

    def _get_item_context_from_path(self, parent_item, properties, path):
        """Updates the context of the item from the work_path_template/template, if needed.

        :param properties: properties of the item.
        :param path: path to build the context from, in this class we use os.path.basename of the path.
        """

        # using file name for resolving templates and context
        path = os.path.basename(path)

        item_context = super(IngestCollectorPlugin, self)._get_item_context_from_path(parent_item, properties, path)
        return item_context

    def _resolve_item_fields(self, item):
        """
        Helper method used to get fields that might not normally be defined in the context.
        Intended to be overridden by DCC-specific subclasses.
        """
        publisher = self.parent
        if item.properties["is_sequence"]:
            path = item.properties["sequence_paths"][0]
        else:
            path = item.properties["path"]

        fields = {}

        # this should be defined and correct by now!
        # Since we resolve this field too, while context change of the item.
        work_path_template = item.properties.get("work_path_template")

        if work_path_template:
            work_tmpl = publisher.get_template_by_name(work_path_template)

            tmpl_fields = work_tmpl.validate_and_get_fields(os.path.basename(path))

            if tmpl_fields:
                self.logger.info(
                    "Parsed path using template '%s' for item: %s" % (work_tmpl.name, item.name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Info",
                            "tooltip": "Show more info",
                            "text": "Path parsed by template '%s': %s\nResulting fields:\n%s" %
                            (work_path_template, path, pprint.pformat(tmpl_fields))
                        }
                    }
                )
                fields.update(tmpl_fields)
            else:
                self.logger.warning(
                    "Path does not match template for item: %s" % (item.name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Info",
                            "tooltip": "Show more info",
                            "text": "Path cannot be parsed by template '%s': %s" %
                            (work_path_template, path)
                        }
                    }
                )

        # If not already populated, first attempt to get the width and height
        if "width" not in fields or "height" not in fields:
            # If image, use OIIO to introspect file and get WxH
            try:
                from OpenImageIO import ImageInput
                fh = ImageInput.open(str(path))
                if fh:
                    try:
                        spec = fh.spec()
                        fields["width"] = spec.width
                        fields["height"] = spec.height
                    except Exception as e:
                        self.logger.error(
                            "Error getting resolution for item: %s" % (item.name,),
                            extra={
                                "action_show_more_info": {
                                    "label": "Show Info",
                                    "tooltip": "Show more info",
                                    "text": "Error reading file: %s\n  ==> %s" % (path, str(e))
                                }
                            }
                        )
                    finally:
                        fh.close()
            except ImportError as e:
                self.logger.error(str(e))

        # If item has version in file name, use it, otherwise, recurse up item hierarchy
        # Note: this intentionally overwrites any value found in the work file
        fields["version"] = self._get_version_number_r(item)

        # Get the file extension if not already defined
        if "extension" not in fields:
            file_info = publisher.util.get_file_path_components(path)
            fields["extension"] = file_info["extension"]

        # Force use of %d format
        if item.properties["is_sequence"]:
            fields["SEQ"] = "FORMAT: %d"

        # use %V - full view printout as default for the eye field
        fields["eye"] = "%V"

        # add in date values for YYYY, MM, DD
        today = datetime.date.today()
        fields["YYYY"] = today.year
        fields["MM"] = today.month
        fields["DD"] = today.day

        item.description = "Created by shotgun_ingest on %s" % str(today)

        # Try to set the name field if not defined
        if "name" not in fields:
            # First attempt to get it from the parent item
            name_field = self._get_name_field_r(item.parent)
            if name_field:
                fields["name"] = name_field

            # Else attempt to use a santized task name
            elif item.context.task:
                name_field = item.context.task["name"]
                fields["name"] = urllib.quote(name_field.replace(" ", "_").lower(), safe='')

        return fields
