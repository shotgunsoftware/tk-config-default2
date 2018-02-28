# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import datetime
import glob
import pprint
import urllib
import sgtk
from sgtk import TankError

from tank import context

HookBaseClass = sgtk.get_hook_baseclass()


class IngestCollectorPlugin(HookBaseClass):
    """
    Collector that operates on the current set of ingestion files. Should
    inherit from the basic collector hook.
    """

    def _add_file_item(self, settings, parent_item, path, is_sequence=False, seq_files=None):
        """
        Creates a file item

        :param dict settings: Configured settings for this collector
        :param parent_item: parent item instance
        :param path: Path to analyze
        :param is_sequence: Bool as to whether to treat the path as a part of a sequence
        :param seq_files: A list of files in the sequence

        :returns: The item that was created
        """
        publisher = self.parent

        # get info for the extension
        item_info = self._get_item_info(settings, path, is_sequence)

        icon_path = item_info["icon_path"]
        item_type = item_info["item_type"]
        type_display = item_info["type_display"]
        work_path_template = item_info["work_path_template"]

        display_name = publisher.util.get_publish_name(path)

        # Define the item's properties
        properties = {}

        # set the path and is_sequence properties for the plugins to use
        properties["path"] = path
        properties["is_sequence"] = is_sequence

        # If a sequence, add the sequence path
        if is_sequence:
            properties["sequence_paths"] = seq_files

        if work_path_template:
            properties["work_path_template"] = work_path_template

        # build the context of the item
        context = self._get_item_context_from_path(parent_item, properties, os.path.basename(path))

        # create and populate the item
        file_item = parent_item.create_item(
            item_type,
            type_display,
            display_name,
            collector=self.plugin,
            context=context,
            properties=properties
        )

        # resolve work_path_template for the item
        file_item.properties["work_path_template"] = self._resolve_work_path_template(file_item.properties,
                                                                                      os.path.basename(path))

        # Set the icon path
        file_item.set_icon_from_path(icon_path)

        # if the supplied path is an image, use the path as the thumbnail.
        if (item_type.startswith("file.image") or
            item_type.startswith("file.texture") or
            item_type.startswith("file.render")):

            if is_sequence:
                file_item.set_thumbnail_from_path(seq_files[0])
            else:
                file_item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False

        if is_sequence:
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            file_info = (
                "The following files were collected:<br>"
                "<pre>%s</pre>" % (pprint.pformat(seq_files),)
            )
        else:
            file_info = (
                "The following file was collected:<br>"
                "<pre>%s</pre>" % (path,)
            )

        self.logger.info(
            "Collected item: %s" % display_name,
            extra={
                "action_show_more_info": {
                    "label": "Show File(s)",
                    "tooltip": "Show the collected file(s)",
                    "text": file_info
                }
            }
        )

        return file_item

    def on_context_changed(self, settings, item):
        """
        Callback to update the item on context changes.

        :param dict settings: Configured settings for this collector
        :param item: The Item instance
        """

        path = item.properties["path"]
        is_sequence = item.properties["is_sequence"]

        item_info = self._get_item_info(settings, path, is_sequence)

        item.properties["work_path_template"] = self._resolve_work_path_template(item_info,
                                                                                 os.path.basename(path))

        # Set the item's fields property
        item.properties["fields"] = self._resolve_item_fields(item)


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
