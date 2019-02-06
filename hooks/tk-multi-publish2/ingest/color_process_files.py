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
import copy
import glob
import pprint
import traceback

import sgtk
from sgtk import TankError


HookBaseClass = sgtk.get_hook_baseclass()


class ColorProcessFilesPlugin(HookBaseClass):
    """
    Inherits from IngestFilesPlugin
    """

    def __init__(self, parent, **kwargs):
        """
        Construction
        """
        # call base init
        super(ColorProcessFilesPlugin, self).__init__(parent, **kwargs)

        # cache the color process files app, which is an instance of review submission app.
        self.__color_process_files_app = self.parent.engine.apps.get("tk-multi-colorprocessfiles")

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        schema = super(ColorProcessFilesPlugin, self).settings_schema

        ingest_schema = {
            "publish_file_identifiers": {
                "type": "dict",
                "values": {
                    "type": "template",
                    "description": "",
                    "fields": ["context", "version", "[output]", "[name]", "*"],
                },
                "default_value": {"2K": "{env_name}_2k_image", "Proxy": "{env_name}_proxy_image"},
                "description": (
                    "Dictionary of Identifier to Publish Path "
                    "This identifier will be added to publish name and publish type for creating PublishedFile entity."
                )
            },
        }

        # add tags also to publish files
        schema["Item Type Settings"]["values"]["items"].update(ingest_schema)

        # make sure this plugin only accepts render sequences.
        schema["Item Type Filters"]["default_value"] = ["file.*.sequence"]

        return schema

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """
        Ingests the file to the location specified by the publish_path_template for this item and
        creates a <b>PublishedFile</b> entity in Shotgun, which will include a
        reference to the file's published path on disk.

        After the <b>PublishedFile</b> is created successfully, a <b>Plate/Asset</b> entity is also created.
        The <b>PublishedFile</b> is then linked to it's corresponding <b>Plate/Asset</b> entity for other users to use.
        Once the ingestion is complete these files can be accessed using the Loader window within each DCC.
        """

    def accept(self, task_settings, item):
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

        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        accept_data = super(ColorProcessFilesPlugin, self).accept(task_settings, item)

        # this plugin shouldn't accept CDL files! Ever!
        if item.type == "file.cdl":
            accept_data["accepted"] = False

        return accept_data

    def register_publish(self, task_settings, item, path_to_publish):

        publisher = self.parent
        sg_publish_data = None

        publish_identifiers = item.properties.resolved_identifiers

        # Get item properties populated by validate method
        publish_name = item.properties.publish_name
        publish_path = item.properties.publish_path
        publish_type = item.properties.publish_type
        publish_version = item.properties.publish_version

        # modify the properties of the publish as per the identifier
        # for eg. Proxy identifier will lead to Rendered Image Proxy Publish type
        if path_to_publish in publish_identifiers.keys() and publish_identifiers[path_to_publish]:
            publish_name = "%s_%s" % (publish_name, publish_identifiers[path_to_publish])
            # override the publish path with the identifier
            publish_path = path_to_publish
            publish_type = "%s %s" % (publish_type, publish_identifiers[path_to_publish])

        # Get any upstream dependency paths
        dependency_paths = item.properties.get("publish_dependencies", [])

        # If the parent item has publish data, include those ids in the
        # list of dependencies as well
        dependency_ids = []
        if "sg_publish_data_list" in item.parent.properties:
            [dependency_ids.append(sg_publish_data["id"]) for sg_publish_data in item.parent.properties["sg_publish_data_list"]]

        # get any additional_publish_fields that have been defined
        sg_fields = {}
        additional_fields = task_settings.get("additional_publish_fields").value or {}
        for template_key, sg_field in additional_fields.iteritems():
            if template_key in item.properties.fields:
                sg_fields[sg_field] = item.properties.fields[template_key]

        # 769: update sg_path_to_source field
        sg_fields["sg_path_to_source"] = item.properties.path

        # arguments for publish registration
        self.logger.info("Registering publish for %s..." % publish_path)
        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": publish_path,
            "name": publish_name,
            "version_number": publish_version,
            "thumbnail_path": item.get_thumbnail_as_path() or "",
            "published_file_type": publish_type,
            "dependency_ids": dependency_ids,
            "dependency_paths": dependency_paths,
            "sg_fields": sg_fields
        }

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),)
                }
            }
        )

        # try to freeze file permissions
        if item.properties.is_sequence:
            seq_pattern = publisher.util.get_path_for_frame(publish_path, "*")
            published_files = [f for f in glob.iglob(seq_pattern) if os.path.isfile(f)]
        else:
            published_files = [publish_path]

        for published_file in published_files:
            try:
                sgtk.util.filesystem.freeze_permissions(published_file)
            except OSError:
                self.logger.warning(
                    "Unable to make file '{}' read-only.".format(published_file),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )

            try:
                sgtk.util.filesystem.seal_file(published_file)
            except Exception as e:
                # primary function is to copy. Do not raise exception if sealing fails.
                self.logger.warning("File '%s' could not be sealed, skipping: %s" % (published_file, e))
                self.logger.warning(traceback.format_exc())

        exception = None
        # create the publish and stash it in the item properties for other
        # plugins to use.
        try:
            sg_publish_data = sgtk.util.register_publish(**publish_data)

            self.logger.info("Publish registered for %s" % publish_path)
        except Exception as e:
            exception = e
            self.logger.error(
                "Couldn't register Publish for %s" % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": traceback.format_exc()
                    }
                }
            )

        if not sg_publish_data:
            self.undo(task_settings, item)
        else:
            if "sg_publish_data_list" not in item.properties:
                item.properties.sg_publish_data_list = []

            # add the publish data to item properties
            item.properties.sg_publish_data_list.append(sg_publish_data)

        if exception:
            raise exception

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        # this has to run first so that item properties are populated.
        # Properties are used to find a linked entity.
        status = super(ColorProcessFilesPlugin, self).validate(task_settings, item)

        if status:

            resolved_identifiers = {item.properties.publish_path: None}

            # First copy the item's fields
            fields = copy.copy(item.properties.fields)

            # Update with the fields from the context
            fields.update(item.context.as_template_fields())

            # set review_submission app's env/context based on item (ingest)
            self.__color_process_files_app.change_context(item.context)

            extra_write_node_mapping = self.__color_process_files_app.resolve_extra_write_nodes(fields)

            # potential processed paths
            processed_paths = extra_write_node_mapping.values()

            # resolve the templates to figure out what they are before we start publishing
            for identifier, template in task_settings.get("publish_file_identifiers").value.iteritems():
                resolved_template = self._get_resolved_path(task_settings, item, template)
                # these paths should never be the same as publish path
                if resolved_template and resolved_template != item.properties.publish_path:
                    resolved_identifiers[resolved_template] = identifier

            diff_list = list(set(processed_paths) - set(resolved_identifiers.keys()))

            # review submit hook should return exact amount of paths for which the color processing hook is configured.
            if diff_list:
                error_message = "Processed paths: %s\nResolved identifiers: %s\nDon't match.\nDifferences: %s" % \
                                ('\n'.join(processed_paths), '\n'.join(resolved_identifiers), '\n'.join(diff_list))
                self.logger.error(
                    "Can't Publish %s! Review Submission plugin not setup." % item.name,
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": error_message
                        }
                    }
                )

                # review submit and color processing profile doesn't match.
                status = False

            else:
                for publish_path, identifier in resolved_identifiers.iteritems():
                    if identifier:
                        publish_name = "%s_%s" % (item.properties.publish_name, resolved_identifiers[publish_path])
                        publish_type = "%s %s" % (item.properties.publish_type, resolved_identifiers[publish_path])
                        self.logger.info(
                            "A Publish will be created for item '%s'." %
                            (item.name,),
                            extra={
                                "action_show_more_info": {
                                    "label": "Show Info",
                                    "tooltip": "Show more info",
                                    "text": "Publish Name: %s" % (publish_name,) + "\n" +
                                            "Linked Entity Name: %s" % (item.properties.publish_linked_entity_name,) + "\n" +
                                            "Publish Path: %s" % (publish_path,) + "\n" +
                                            "Publish Type: %s" % (publish_type,)
                                }
                            }
                        )
                item.properties.resolved_identifiers = resolved_identifiers

        return status

    def create_published_files(self, task_settings, item):
        """
        Publishes the files for the given item and task_settings.
        This can call super or implement it's own.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # run the review submission to publish the processed files.
        publisher = self.parent

        first_frame, last_frame = self._get_frame_range(item)
        first_frame = int(first_frame)
        last_frame = int(last_frame)

        sg_publish_data_list = []

        # First copy the item's fields
        fields = copy.copy(item.properties.fields)

        # Update with the fields from the context
        fields.update(item.context.as_template_fields())

        self.logger.info("Processing the frames...")
        # run the render hook
        pre_processed_paths = self.__color_process_files_app.render(item.properties.path, fields, first_frame,
                                                                    last_frame,
                                                                    sg_publish_data_list, item.context.task,
                                                                    item.description, item.get_thumbnail_as_path(),
                                                                    self._progress_cb, colorspace=None)

        # add these paths to item properties
        item.properties.pre_processed_paths = pre_processed_paths

        resolved_identifiers = item.properties.resolved_identifiers

        # validate the renders, so that we have identifiers for all the paths that came out of the render.
        diff_list = list(set(pre_processed_paths) - set(resolved_identifiers.keys()))

        # review submit hook should return exact amount of paths for which the color processing hook is configured.
        if diff_list:
            error_message = "Processed paths: %s\nResolved identifiers: %s\nDon't match.\nDifferences: %s" % \
                            ('\n'.join(pre_processed_paths), '\n'.join(resolved_identifiers), '\n'.join(diff_list))
            self.logger.error(
                "Can't Publish %s! Review Submission plugin not setup correctly." % item.name,
                extra={
                    "action_show_more_info": {
                        "label": "Show Error Log",
                        "tooltip": "Show the error log",
                        "text": error_message
                    }
                }
            )

            # delete the rendered files
            self.undo(task_settings, item)
        else:
            # register publishes
            for processed_path in item.properties.pre_processed_paths:
                self.register_publish(task_settings, item, processed_path)

    def undo(self, task_settings, item):
        """
        Execute the undo method. This method will
        delete the linked_entity entity that got created due to the publish.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        publisher = self.parent

        pre_processed_paths = item.properties.get("pre_processed_paths")

        if pre_processed_paths:
            self.logger.info("Cleaning up rendered files for %s..." % item.name,
                             extra={
                                 "action_show_more_info": {
                                     "label": "Show Error Log",
                                     "tooltip": "Show the error log",
                                     "text": "Rendered frames:\n%s" % '\n'.join(pre_processed_paths)
                                 }
                             }
                             )
            for processed_path in pre_processed_paths:
                publisher.util.delete_files(processed_path, item)

        sg_publish_data_list = item.properties.get("sg_publish_data_list")

        if sg_publish_data_list:
            for publish_data in sg_publish_data_list:
                try:
                    self.sgtk.shotgun.delete(publish_data["type"], publish_data["id"])
                    self.logger.info("Cleaning up published file...",
                                     extra={
                                         "action_show_more_info": {
                                             "label": "Publish Data",
                                             "tooltip": "Show the publish data.",
                                             "text": "%s" % publish_data
                                         }
                                     }
                                     )
                except Exception:
                    self.logger.error(
                        "Failed to delete PublishedFile Entity for %s" % item.name,
                        extra={
                            "action_show_more_info": {
                                "label": "Show Error Log",
                                "tooltip": "Show the error log",
                                "text": traceback.format_exc()
                            }
                        }
                    )
            # pop the sg_publish_data_list too
            item.properties.pop("sg_publish_data_list")

    def _progress_cb(self, msg=None, stage=None):
        """
        """
        # if stage matches a task then we want to include
        # the task details at the start of the message:
        if msg is not None:
            try:
                item_name = stage["item"]["name"]
                output_name = stage["output"]["name"]

                # update message to include task info:
                self.logger.info("%s - %s: %s" % (output_name, item_name, msg))
            except:
                pass

    def _get_movie_path(self, task_settings, item):
        """
        Returns the path of the movie that's supposed to be output of review submit.
        """

        # Make sure we don't overwrite the item's fields
        fields = copy.copy(item.properties.fields)
        # Update with the fields from the context
        fields.update(item.context.as_template_fields())

        # Movie output width and height
        width = self.__color_process_files_app.get_setting("movie_width")
        height = self.__color_process_files_app.get_setting("movie_height")
        fields["width"] = width
        fields["height"] = height

        # Get an output path for the movie.
        output_path_template = self.__color_process_files_app.get_template("movie_path_template")
        output_path = output_path_template.apply_fields(fields)

        return output_path

    def _get_resolved_path(self, task_settings, item, template_name):
        """
        Get a publish path for the supplied item.

        :param item: The item to determine the publish type for

        :return: A string representing the output path to supply when
            registering a publish for the supplied item

        Extracts the publish path via the configured publish templates
        if possible.
        """

        publisher = self.parent

        # Start with the item's fields
        fields = copy.copy(item.properties.get("fields", {}))

        path_template = template_name
        resolved_path = None

        # If a template is defined, get the publish path from it
        if path_template:

            path_tmpl = publisher.get_template_by_name(path_template)
            if not path_tmpl:
                # this template was not found in the template config!
                raise TankError("The Template '%s' does not exist!" % path_template)

            # First get the fields from the context
            try:
                fields.update(item.context.as_template_fields(path_tmpl))
            except TankError, e:
                self.logger.debug(
                    "Unable to get context fields for %s." % path_template)

            missing_keys = path_tmpl.missing_keys(fields, True)
            if missing_keys:
                raise TankError(
                    "Cannot resolve template (%s). Missing keys: %s" %
                            (path_template, pprint.pformat(missing_keys))
                )

            # Apply fields to path_template to get publish path
            resolved_path = path_tmpl.apply_fields(fields)
            self.logger.debug(
                "Used %s to determine the publish path: %s" %
                (path_template, resolved_path,)
            )

        return resolved_path
