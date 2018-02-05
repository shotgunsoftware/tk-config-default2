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
import glob
import pprint
import traceback
import urllib

import sgtk
from sgtk import TankError

HookBaseClass = sgtk.get_hook_baseclass()


class ConformWorkFilesPlugin(HookBaseClass):
    """
    Plugin for copying work file(s) to match a template path.

    This plugin is typically configured to act upon files that are dragged and
    dropped into the publisher UI. It can also be used as a base class for
    other file-based publish plugins as it contains standard operations for
    validating and copying work files.

    Once attached to a publish item, the plugin will key off of properties that
    are set on the item. These properties can be set via the collector or
    by subclasses prior to calling methods on this class.

    The only property that is required for the plugin to operate is the ``path``
    property. All of the properties and settings understood by the plugin are
    documented below:

        Item properties
        -------------

        path - The path to the file to be published.

        sequence_paths - If set, implies the "path" property represents a
            sequence of files (typically using a frame identifier such as %04d).
            This property should be a list of files on disk matching the "path".
            If a work template is provided, and corresponds to the listed
            frames, fields will be extracted and applied to the publish template
            (if set) and copied to that publish location.

        is_sequence - A boolean defining whether or not this item is a sequence of files.

        Task settings
        -------------------

        work_path_template - If set in the plugin settings dictionary, used to
            determine where "path" should be copied.

    This plugin will also set the following properties on the item which may be 
    useful for child items.

        work_file_path - Calculated by the plugin as the fully resolved output path.

    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
        # look for icon one level up from this hook's folder in "icons" folder
        return self.parent.expand_path("{self}/hooks/icons/version_up.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Conform Work File(s)"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return ""

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
        schema = super(ConformWorkFilesPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"] = ["file.*"]
        schema["Item Type Settings"]["values"]["items"] = {
            "work_path_template": {
                "type": "template",
                "description": "",
                "fields": ["context", "*"],
                "allows_empty": True,
            },
        }
        return schema


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

        # Run the parent acceptance method
        accept_data = super(ConformWorkFilesPlugin, self).accept(task_settings, item)
        if not accept_data.get("accepted"):
            return accept_data

        path = item.properties.get("path")
        if not path:
            accept_data["accepted"] = False
            return accept_data

        # Get work_path_template from the accept_data
        work_path_template = task_settings.get("work_path_template")

        # Call sub method for comparing the item's path with the work_path_template
        # to see if this plugin should be accepted.
        accept_data["accepted"] = self._accept_work_path(item, work_path_template)

        # return the accepted info
        return accept_data


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to copy.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """
        path = item.properties["path"]
        publisher = self.parent

        # ---- ensure that input work file(s) exist on disk to be copied

        if item.properties["is_sequence"]:
            if not item.properties["sequence_paths"]:
                self.logger.warning("File sequence does not exist for item: %s" % item.name)
                return False
        else:
            if not os.path.exists(path):
                self.logger.warning("File does not exist for item: %s" % item.name)
                return False

        # ---- validate the settings required to publish

        attr_list = ("work_file_path",)
        for attr in attr_list:
            try:
                method = getattr(self, "_get_%s" % attr)
                item.properties[attr] = method(item, task_settings)
            except Exception:
                self.logger.error(
                    "Unable to determine '%s' for item: %s" % (attr, item.name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )
                return False

        # ---- check if the path is already conformed

        work_file_path = item.properties["work_file_path"]
        if path == work_file_path:
            return True

        # ---- ensure the destination work file(s) don't already exist on disk

        conflict_info = None
        if item.properties["is_sequence"]:
            seq_pattern = publisher.util.get_path_for_frame(work_file_path, "*")
            seq_files = [f for f in glob.iglob(seq_pattern) if os.path.isfile(f)]

            if seq_files:
                conflict_info = (
                    "The following files already exist!<br>"
                    "<pre>%s</pre>" % (pprint.pformat(seq_files),)
                )
        else:
            if os.path.exists(work_file_path):
                conflict_info = (
                    "The following file already exists!<br>"
                    "<pre>%s</pre>" % (work_file_path,)
                )

        if conflict_info:
            self.logger.error(
                "Work file(s) for item '%s' already exists on disk." %
                    (item.name,),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show the conflicting published files",
                        "text": conflict_info
                    }
                }
            )
            return False

        self.logger.info(
            "Work file(s) for item '%s' will be conformed." %
                (item.name,),
            extra={
                "action_show_more_info": {
                    "label": "Show Info",
                    "tooltip": "Show more info",
                    "text": "%s\n  ==> %s" % (path, work_file_path)
                }
            }
        )

        return True


    def publish(self, task_settings, item):
        """
        Executes the publish logic for the given item and task_settings.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # Skip publish if the work_file_path matches the input path
        work_file_path = item.properties["work_file_path"]
        if item.properties["path"] == work_file_path:
            self.logger.info("Work file(s) already conformed. Skipping")
            return

        # Copy work files to new location
        processed_files = self._copy_files(work_file_path, item)

        # Update path attrs to reflect new location
        if item.properties["is_sequence"]:
            item.properties["path"] = publisher.util.get_frame_sequence_path(processed_files[0])
            item.properties["sequence_paths"] = processed_files
        else:
            item.properties["path"] = processed_files[0]

        self.logger.info("Work file(s) for item '%s' copied succesfully!" % item.name)


    def finalize(self, task_settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the task_settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        pass


    ############################################################################
    # protected methods

    def _accept_work_path(self, item, work_path_template):
        """
        Compares the item's path with the input work_path_template. If the template
        is not defined or the template and the path match, we do not accept. If the
        path and the template do not match, then we accept the plugin.
        """
        path = item.properties["path"]
        publisher = self.parent

        if not work_path_template:
            self.logger.error("No work_path_template defined for item: '%s'" % item.name)
            return False

        tmpl = publisher.get_template_by_name(work_path_template)
        if not tmpl:
            # this template was not found in the template config!
            raise TankError("The Template '%s' does not exist!" % work_path_template)

        # If path doesn't match this template, then we should accept this plugin
        if not tmpl.validate(path):
            return True

        return False


    def _get_work_file_path(self, item, task_settings):
        """
        Get a work file path for the supplied item.

        :param item: The item to determine the work file path for

        :return: A string representing the output path to supply when
            registering a work file for the supplied item

        Extracts the work file path via the configured work_path_template.
        """
        publisher = self.parent
        fields = {}

        work_path_template = task_settings.get("work_path_template")
        if not work_path_template:
            self.logger.info("work_path_template not defined. Skipping conform.")
            return item.properties["path"]

        work_tmpl = publisher.get_template_by_name(work_path_template)
        if not work_tmpl:
            # this template was not found in the template config!
            raise TankError("The Template '%s' does not exist!" % work_path_template)

        # First get the fields from the context
        try:
            fields = item.context.as_template_fields(work_tmpl, validate=True)
        except TankError, e:
            self.logger.debug(
                "Unable to get context fields from work_path_template.")

        # Add in any additional fields from the item
        fields.update(self._resolve_item_fields(item, task_settings))

        missing_keys = work_tmpl.missing_keys(fields, True)
        if missing_keys:
            raise TankError(
                "Cannot resolve work_path_template (%s). Missing keys: %s" %
                        (work_path_template, pprint.pformat(missing_keys))
            )

        # Get the work_file_path
        return work_tmpl.apply_fields(fields)


    def _get_version_number_r(self, item):
        """
        Recurse up item hierarchy to determine version number
        """
        publisher = self.parent
        path = item.properties.get("path")

        if not path:
            if not item.is_root():
                version = self._get_version_number_r(item.parent)
            else:
                version = 1
        else:
            version = publisher.util.get_version_number(path)
            if not version:
                if not item.is_root():
                    version = self._get_version_number_r(item.parent)
                else:
                    version = 1
        return version


    def _resolve_item_fields(self, item, task_settings):
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

        # TODO: If image, use OIIO to introspect file and get WxH
        try:
            from OpenImageIO import ImageInput
            fh = ImageInput.open(path)
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
        fields["version"] = self._get_version_number_r(item)

        # Force use of %d format
        fields["SEQ"] = "FORMAT: %d"

        # use %V - full view printout as default for the eye field
        fields["eye"] = "%V"

        # add in date values for YYYY, MM, DD
        today = datetime.date.today()
        fields["YYYY"] = today.year
        fields["MM"] = today.month
        fields["DD"] = today.day

        # Set the item name equal to the task name if defined
        if item.context.task:
            fields["name"] = urllib.quote(item.context.task["name"].replace(" ", "_").lower(), safe='')            

        return fields
