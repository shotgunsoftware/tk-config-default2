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
import shutil
import traceback

import sgtk
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


class BasicFilePublishPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun.

    This plugin is typically configured to act upon files that are dragged and
    dropped into the publisher UI. It can also be used as a base class for
    other file-based publish plugins as it contains standard operations for
    validating and registering publishes with Shotgun.

    Once attached to a publish item, the plugin will key off of properties that
    drive how the item is published.

    The ``path`` property, set on the item, is the only required property as it
    informs the plugin where the file to publish lives on disk.

    The following properties can be set on the item via the collector or by
    subclasses prior to calling methods on the base class::

        ``sequence_paths`` - If set in the item properties dictionary, implies
            the "path" property represents a sequence of files (typically using
            a frame identifier such as %04d). This property should be a list of
            files on disk matching the "path". If the ``work_template`` property
            is set, and corresponds to the listed frames, fields will be
            extracted and applied to the publish_template (if set) and copied to
            that publish location.

        ``work_template`` - If set in the item properties dictionary, this
            value is used to validate ``path`` and extract fields for further
            processing and contextual discovery. For example, if configured and
            a version key can be extracted, it will be used as the publish
            version to be registered in Shotgun.

    The following properties can also be set by a subclass of this plugin via
    :meth:`Item.properties` or :meth:`Item.local_properties`.

        publish_template - If set, used to determine where "path" should be
            copied prior to publishing. If not specified, "path" will be
            published in place.

        publish_type - If set, will be supplied to SG as the publish type when
            registering "path" as a new publish. If not set, will be determined
            via the plugin's "File Type" setting.

        publish_path - If set, will be supplied to SG as the publish path when
            registering the new publish. If not set, will be determined by the
            "published_file" property if available, falling back to publishing
            "path" in place.

        publish_name - If set, will be supplied to SG as the publish name when
            registering the new publish. If not available, will be determined
            by the "work_template" property if available, falling back to the
            ``path_info`` hook logic.

        publish_version - If set, will be supplied to SG as the publish version
            when registering the new publish. If not available, will be
            determined by the "work_template" property if available, falling
            back to the ``path_info`` hook logic.

        publish_dependencies - A list of files to include as dependencies when
            registering the publish. If the item's parent has been published,
            it's path will be appended to this list.

    NOTE: accessing these ``publish_*`` values on the item does not necessarily
    return the value used during publish execution. Use the corresponding
    ``get_publish_*`` methods which include fallback logic when no property is
    set. For example, if a ``work_template`` is used, the publish version and
    name might be extracted from the template fields in the fallback logic.

    This plugin will also set an ``sg_publish_data`` property on the item during
    the ``publish`` method which may be useful for child items.

        ``sg_publish_data`` - The dictionary of publish information returned
            from the tk-core register_publish method.

    NOTE: If you have multiple plugins acting on the same item, and you need to
    access or operate on the publish data, you can extract the
    ``sg_publish_data`` from the item after calling the base class ``publish``
    method in your plugin subclass.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.
        A dictionary on the following form::
            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }
        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        return {
            "File Types": {
                "type": "list",
                "default": [
                    ["Alias", "wire"],
                    ["Alembic Cache", "abc"],
                    ["3dsmax Scene", "max"],
                    ["NukeStudio Project", "hrox"],
                    ["Houdini Scene", "hip", "hipnc"],
                    ["Maya Scene", "ma", "mb"],
                    ["FBX Translation", "fbx"],
                    ["Nuke Script", "nk"],
                    ["Photoshop Image", "psd", "psb"],
                    ["VRED", "vpb", "vpe"],
                    ["Rendered Image", "dpx", "exr"],
                    ["Texture", "tiff", "tx", "tga", "dds"],
                    ["Image", "jpeg", "jpg", "png"],
                    ["Movie", "mov", "mp4"],
                    ["PDF", "pdf"],
                    ["IGS Translation", "igs"],
                    ["JT Translation", "jt"],
                    ["CATPart Translation", "CATPart", "catpart"],
                    ["STP Translation", "stp"],
                    ["STL Translation", "stl"],
                    ["WREF Translation", "wref"],
                    ["OSB", "osb"],
                    ["Office File", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]
                ],
                "description": (
                    "List of file types to include. Each entry in the list "
                    "is a list in which the first entry is the Shotgun "
                    "published file type and subsequent entries are file "
                    "extensions that should be associated."
                )
            },
        }

    def get_publish_fields(self, settings, item):
        """
        Get additional fields that should be used for the publish. This
        dictionary is passed on to :meth:`tank.util.register_publish` as the
        ``sg_fields`` keyword argument.
        If publish_fields is not defined as a ``property`` or
        ``local_property``, this method will return an empty dictionary.
        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for
        :return: A dictionary of field names and values for those fields.
        """
        if item.parent.properties.get("sg_status_list") is not None:
            return {"sg_status_list": item.parent.properties["sg_status_list"]}
        return item.get_property("publish_fields", default_value={})

        ############################################################################
        # protected methods

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

        # ---- ensure templates are available
        work_template = item.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "No work template set on the item. "
                "Skipping copy file to publish location."
            )
            return

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

            if not work_template.validate(work_file):
                self.logger.warning(
                    "Work file '%s' did not match work template '%s'. "
                    "Publishing in place." % (work_file, work_template)
                )
                return

            work_fields = work_template.get_fields(work_file)

            missing_keys = publish_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Work file '%s' missing keys required for the publish "
                    "template: %s" % (work_file, missing_keys)
                )
                return

            publish_file = publish_template.apply_fields(work_fields)

            # copy the file
            try:
                publish_folder = os.path.dirname(publish_file)
                ensure_folder_exists(publish_folder)
                shutil.copyfile(work_file, publish_file)
            except Exception as e:
                raise Exception(
                    "Failed to copy work file from '%s' to '%s'.\n%s" %
                    (work_file, publish_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to publish file '%s'." %
                (work_file, publish_file)
            )
