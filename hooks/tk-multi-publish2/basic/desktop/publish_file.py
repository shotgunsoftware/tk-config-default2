# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os, sys
import re
import pprint
import traceback
import subprocess

import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()

try:
    if "SSVFX_PIPELINE" in os.environ.keys():
        pipeline_root =  os.environ["SSVFX_PIPELINE"]
    else:
        pipeline_root = "\\\\10.80.8.252\\VFX_Pipeline"
    
    image_magick = os.path.join(pipeline_root, "Pipeline\\external_scripts\\image_magick\\magick.exe")

except:
    pass

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

        publish_user - If set, will be supplied to SG as the publish user
            when registering the new publish. If not available, the publishing
            will fall back to the :meth:`tank.util.register_publish` logic.

        publish_fields - If set, will be passed to
            :meth:`tank.util.register_publish` as the ``sg_fields`` keyword
            argument. A dictionary of additional fields that should be used
            for the publish entity in Shotgun.

        publish_kwargs - If set, will be used to update the dictionary of kwargs
            passed to :meth:`tank.util.register_publish`. Because this
            dictionary updates the kwargs built from other ``property``
            and ``local_property`` values, any kwargs set in this property will
            supersede those values.

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

    ############################################################################
    # standard publish plugin properties

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            "icons",
            "publish.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish to Shotgun"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        Publishes the file to Shotgun. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the file's current
        path on disk. Other users will be able to access the published file via
        the <b><a href='%s'>Loader</a></b> so long as they have access to
        the file's location on disk.

        <h3>File versioning</h3>
        The <code>version</code> field of the resulting <b>Publish</b> in
        Shotgun will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        <br><br><i>NOTE: any amount of version number padding is supported.</i>

        <h3>Overwriting an existing publish</h3>
        A file can be published multiple times however only the most recent
        publish will be available to other users. Warnings will be provided
        during validation if there are previous publishes.
        """ % (loader_url,)

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
                    ["Alias File", "wire"],
                    ["Alembic Cache", "abc"],
                    ["3dsmax Scene", "max"],
                    ["NukeStudio Project", "hrox"],
                    ["Houdini Scene", "hip", "hipnc"],
                    ["Maya Scene", "ma", "mb"],
                    ["Motion Builder FBX", "fbx"],
                    ["Nuke Script", "nk"],
                    ["Photoshop Image", "psd", "psb"],
                    ["VRED Scene", "vpb", "vpe", "osb"],
                    ["Rendered Image", "dpx", "exr"],
                    ["Texture", "tiff", "tx", "tga", "dds"],
                    ["Image", "jpeg", "jpg", "png"],
                    ["Movie", "mov", "mp4"],
                    ["PDF", "pdf"],         
                ],
                "description": (
                    "List of file types to include. Each entry in the list "
                    "is a list in which the first entry is the Shotgun "
                    "published file type and subsequent entries are file "
                    "extensions that should be associated."
                )
            },
        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["file.*"]

    ############################################################################
    # standard publish plugin methods

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

        path = item.properties.path
        accept = {"accepted": True}

        # check pipeline step to determine if it should be checked/unchecked
        if item.properties.sg_publish_to_shotgun:
            accept.update({'checked': True})
            # log the accepted file and display a button to reveal it in the fs
            self.logger.info(
                "File publisher plugin accepted: %s" % (path,),
                extra={
                    "action_show_folder": {
                        "path": path
                    }
                }
            )
            
        else:
            accept.update({'checked': False})
            accept.update({'enabled': False})
            accept.update({'visible': False})
            accept = {"accepted": False}

        try:
            if item.properties['template_file']:
                if item.properties['template_file'].name == "maya_shot_outsource_work_file":
                    self.logger.warning(item.properties['template_file'])
                    accept = {"accepted": False}
        except:
            pass
        # return the accepted info
        return accept

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        self.review_process = None
        if not item.context.task:
            raise Exception("Need task info!")

        path = item.properties.get("path")
        if not item.properties.get("step"):

            self.review_process = publisher.shotgun.find_one("Step", 
                [['id', 'is', item.context.step['id']]], 
                item.properties["step_fields"])
        else:
            self.review_process = item.properties.get("step")
            
        # We allow the information to be pre-populated by the collector or a
        # base class plugin. They may have more information than is available
        # here such as custom type or template settings.
        publish_path = self.get_publish_path(settings, item)
        publish_name = self.get_publish_name(settings, item)
        if re.search(r".abc$", publish_name):
            publish_name = re.sub(r".abc$", "", publish_name)
            item.properties['publish_name'] = publish_name
        self.logger.warning(publish_name)
        self.logger.info("Review process: %s" % (self.review_process['sg_review_process_type']))

        # ---- check for conflicting publishes of this path with a status

        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.
        publishes = publisher.util.get_conflicting_publishes(
            item.context,
            publish_path,
            publish_name,
            filters=["sg_status_list", "is_not", "omt"]
        )

        if publishes:

            self.logger.warning(
                "Conflicting publishes: %s" % (pprint.pformat(publishes),))

            publish_template = self.get_publish_template(settings, item)

            if "work_template" in item.properties or publish_template:

                # templates are in play and there is already a publish in SG
                # for this file path. We will raise here to prevent this from
                # happening.
                error_msg = (
                    "Can not validate file path. There is already a publish in "
                    "Shotgun that matches this path. Please uncheck this "
                    "plugin or save the file to a different path."
                )
                self.logger.error(error_msg)
                raise Exception(error_msg)

            else:
                conflict_info = (
                    "If you continue, these conflicting publishes will no "
                    "longer be available to other users via the loader:<br>"
                    "<pre>%s</pre>" % (pprint.pformat(publishes),)
                )
                self.logger.warning(
                    "Found %s conflicting publishes in Shotgun" % (len(publishes),),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Conflicts",
                            "tooltip": "Show conflicting publishes in Shotgun",
                            "text": conflict_info
                        }
                    }
                )
                return False
        if item.properties.get("workfile_template"):
            publish_path = item.properties.get("workfile_template")
        else:
            publish_path = path
        self.logger.info("A Publish will be created in Shotgun and linked to:")
        self.logger.info("  %s" % (path,))

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # ---- determine the information required to publish

        # We allow the information to be pre-populated by the collector or a
        # base class plugin. They may have more information than is available
        # here such as custom type or template settings.

        publish_name = self.get_publish_name(settings, item)
        publish_version = self.get_publish_version(settings, item)
        publish_path = self.get_publish_path(settings, item)
        publish_dependencies_paths = self.get_publish_dependencies(settings, item)
        publish_user = self.get_publish_user(settings, item)
        publish_type = self.get_publish_type(settings, item)
        publish_thumbnail = self.get_publish_thumbnail(item)
        # Test if there is sufficient info for thumbnail
        if publish_thumbnail:
            self.logger.debug("Found first frame for thumbnail:")
            self.logger.debug(publish_thumbnail)
        else:
            self.logger.debug("No thumbnail file given.")

        self.logger.debug("Publish name: %s" % (publish_name,))
        # if the parent item has a publish path, include it in the list of
        # dependencies
        publish_dependencies_ids = []        
        if "sg_publish_path" in item.parent.properties:
            publish_dependencies_ids.append(item.parent.properties.sg_publish_path)

        # Copy outsource file into production
        if item.properties.get("workfile_template"):
            self._copy_work_to_workfiles(item.properties.path, item.properties.get("workfile_template"))

        # arguments for publish registration
        self.logger.info("Registering publish...")

        # If there was a Version created with this item - add to Publish field
        version = item.properties.get("sg_version_data")
        if version:
            publish_status = "lwv"
            self.logger.info("Found associated Version: %s" %(item.properties.sg_version_data['code']))
        else:
            publish_status = "cmpt"
            self.logger.debug("No associated Version found. PublishedFile will have no linked Version.")

        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "path": publish_path,
            "name": publish_name,
            "comment": item.description,
            "version_number": publish_version,
        }
        item.properties.publish_fields = {
            "sg_fields": {"sg_status_list": publish_status,}
            }

        item.properties.publish_kwargs = {
            "version_entity": version,
            "thumbnail_path": publish_thumbnail, 
            "created_by": publish_user,
            "published_file_type": publish_type,
            "dependency_paths": publish_dependencies_paths,
            "dependency_ids": publish_dependencies_ids,
            }
            

        # catch-all for any extra kwargs that should be passed to register_publish.
        publish_kwargs = self.get_publish_kwargs(settings, item)
        publish_fields = self.get_publish_fields(settings, item)
        
        # add extra kwargs
        publish_data.update(publish_kwargs)
        publish_data.update(publish_fields)

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
        

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties.sg_publish_data = sgtk.util.register_publish(**publish_data)
        self.logger.info("Publish registered!")
        self.logger.debug(
            "Shotgun Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Shotgun Publish Data",
                    "tooltip": "Show the complete Shotgun Publish Entity dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(item.properties.sg_publish_data),)
                }
            }
        )

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # get the data for the publish that was just created in SG
        publish_data = item.properties.sg_publish_data

        # ensure conflicting publishes have their status cleared
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data)

        self.logger.info(
            "Cleared the status of all previous, conflicting publishes")

        path = item.properties.path
        self.logger.info(
            "Publish created for file: %s" % (path,),
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Publish",
                    "tooltip": "Open the Publish in Shotgun.",
                    "entity": publish_data
                }
            }
        )

    def get_publish_template(self, settings, item):
        """
        Get a publish template for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A template representing the publish path of the item or
            None if no template could be identified.
        """

        return item.get_property("publish_template")

    def get_publish_type(self, settings, item):
        """
        Get a publish type for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish type for

        :return: A publish type or None if one could not be found.
        """

        # publish type explicitly set or defined on the item
        publish_type = item.get_property("publish_type")
        item.properties.publish_thumb = None
        if publish_type: 
            return publish_type

        # fall back to the path info hook logic
        publisher = self.parent
        path = item.properties.path

        # get the publish path components
        path_info = publisher.util.get_file_path_components(path)
        # determine the publish type
        extension = path_info["extension"]

        # ensure lowercase and no dot
        if extension:
            extension = extension.lstrip(".").lower()

            for type_def in settings["File Types"].value:

                publish_type = type_def[0]
                file_extensions = type_def[1:]

                if extension in file_extensions:
                    # found a matching type in settings. use it!
                    if (publish_type == "Rendered Image" and
                    self.review_process['sg_department'] == "3D"):
                        publish_type = "3D Render"
                        publish_thumb = None
                        try:
                            if self.review_process['entity_type'] == "Shot":
                                publish_thumb_jpeg = publisher.engine.get_template_by_name("maya_shot_render_thumb_jpeg")
                            elif self.review_process['entity_type'] == "Asset":
                                publish_thumb_jpeg = publisher.engine.get_template_by_name("maya_asset_render_thumb_jpeg")
                            publish_thumb = publish_thumb_jpeg.apply_fields(item.properties.fields)
                        except:
                            pass
                        
                        if publish_thumb:
                            publish_thumb_dir = os.path.dirname(publish_thumb)
                            self.logger.debug("Converted thumb output: %s" % (publish_thumb))
                            self.logger.debug("Converted thumb directory: %s" % (publish_thumb_dir))
                            if not os.path.exists(publish_thumb_dir):
                                os.makedirs(publish_thumb_dir)
                            if os.path.exists(image_magick):
                                if subprocess.call("%s convert -background none -alpha off %s %s" % (image_magick, self.get_publish_thumbnail(item), publish_thumb)) == 0:
                                    self.logger.info("Successfully converted thumbnail.")
                                    item.properties.thumbnail_path = publish_thumb

                    return publish_type

        if extension:
            # publish type is based on extension
            publish_type = "%s File" % extension.capitalize()
        else:
            # no extension, assume it is a folder
            publish_type = "Folder"
        
        return publish_type

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

        work_template = item.properties.get("work_template")
        publish_template = self.get_publish_template(settings, item)

        work_fields = []
        publish_path = None

        # We need both work and publish template to be defined for template
        # support to be enabled.
        if work_template and publish_template:
            if work_template.validate(path):
                work_fields = work_template.get_fields(path)

            missing_keys = publish_template.missing_keys(work_fields)

            if missing_keys:
                self.logger.warning(
                    "Not enough keys to apply work fields (%s) to "
                    "publish template (%s)" % (work_fields, publish_template))
            else:
                publish_path = publish_template.apply_fields(work_fields)
                self.logger.debug(
                    "Used publish template to determine the publish path: %s" %
                    (publish_path,)
                )
        else:
            self.logger.debug("publish_template: %s" % publish_template)
            self.logger.debug("work_template: %s" % work_template)

        if not publish_path:
            publish_path = path
            self.logger.debug(
                "Could not validate a publish template. Publishing in place.")

        return publish_path

    def get_publish_version(self, settings, item):
        """
        Get the publish version for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish version for

        Extracts the publish version via the configured work template if
        possible. Will fall back to using the path info hook.
        """

        # publish version explicitly set or defined on the item
        publish_version = item.get_property("publish_version")
        if publish_version:
            return publish_version

        # fall back to the template/path_info logic
        publisher = self.parent
        path = item.properties.path

        work_template = item.properties.get("work_template")
        work_fields = None
        publish_version = None

        if work_template:
            if work_template.validate(path):
                self.logger.debug(
                    "Work file template configured and matches file.")
                work_fields = work_template.get_fields(path)

        if work_fields:
            # if version number is one of the fields, use it to populate the
            # publish information
            if "version" in work_fields:
                publish_version = work_fields.get("version")
                self.logger.debug(
                    "Retrieved version number via work file template.")

        else:
            self.logger.debug(
                "Using path info hook to determine publish version.")
            publish_version = publisher.util.get_version_number(path)
            if publish_version is None:
                publish_version = 1

        return publish_version

    def get_publish_thumbnail(self, item):
         
        thumbnail_path = None

        thumbnail_path = item.get_property("thumbnail_path")

        return thumbnail_path

    def get_publish_name(self, settings, item):
        """
        Get the publish name for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish name for

        Uses the path info hook to retrieve the publish name.
        """

        # publish name explicitly set or defined on the item
        publish_name = item.get_property("publish_name")
        if publish_name:
            self.logger.info("Got publish name from item: %s" %(publish_name,))
            return publish_name

        self.logger.info("Could not get publish name from item. Using path info...")
        # fall back to the path_info logic
        publisher = self.parent
        path = item.properties.path
        
        if "sequence_paths" in item.properties:
            # generate the name from one of the actual files in the sequence
            name_path = item.properties.sequence_paths[0]
            is_sequence = True
        else:
            name_path = path
            is_sequence = False

        return publisher.util.get_publish_name(
            name_path,
            sequence=is_sequence
        )

    def get_publish_dependencies(self, settings, item):
        """
        Get publish dependencies for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A list of file paths representing the dependencies to store in
            SG for this publish
        """

        # local properties first
        dependencies = item.local_properties.get("publish_dependencies")

        # have to check against `None` here since `[]` is valid and may have
        # been explicitly set on the item
        if dependencies is None:
            # get from the global item properties.
            dependencies = item.properties.get("publish_dependencies")

        if dependencies is None:
            # not set globally or locally on the item. make it []
            dependencies = []

        return dependencies

    def get_publish_user(self, settings, item):
        """
        Get the user that will be associated with this publish.

        If publish_user is not defined as a ``property`` or ``local_property``,
        this method will return ``None``.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A user entity dictionary or ``None`` if not defined.
        """
        return item.get_property("publish_user", default_value=None)

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
        return item.get_property("publish_fields", default_value={})

    def get_publish_kwargs(self, settings, item):
        """
        Get kwargs that should be passed to :meth:`tank.util.register_publish`.
        These kwargs will be used to update the kwarg dictionary that is passed
        when calling :meth:`tank.util.register_publish`, meaning that any value
        set here will supersede a value already retrieved from another
        ``property`` or ``local_property``.

        If publish_kwargs is not defined as a ``property`` or
        ``local_property``, this method will return an empty dictionary.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A dictionary of kwargs to be passed to
                 :meth:`tank.util.register_publish`.
        """
        return item.get_property("publish_kwargs", default_value={})

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
                copy_file(work_file, publish_file)
            except Exception:
                raise Exception(
                    "Failed to copy work file from '%s' to '%s'.\n%s" %
                    (work_file, publish_file, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to publish file '%s'." %
                (work_file, publish_file)
            )

    def _copy_work_to_workfiles(self, source, destination):

            # copy the file
            try:
                destination_folder = os.path.dirname(destination)
                ensure_folder_exists(destination_folder)
                copy_file(source, destination)
            except Exception:
                raise Exception(
                    "Failed to copy outsource file from '%s' to '%s'.\n%s" %
                    (source, destination, traceback.format_exc())
                )

            self.logger.debug(
                "Copied work file '%s' to work file '%s'." %
                (source, destination)
            )                

    def _get_next_version_info(self, path, item):
        """
        Return the next version of the supplied path.

        If templates are configured, use template logic. Otherwise, fall back to
        the zero configuration, path_info hook logic.

        :param str path: A path with a version number.
        :param item: The current item being published

        :return: A tuple of the form::

            # the first item is the supplied path with the version bumped by 1
            # the second item is the new version number
            (next_version_path, version)
        """

        if not path:
            self.logger.debug("Path is None. Can not determine version info.")
            return None, None

        publisher = self.parent

        # if the item has a known work file template, see if the path
        # matches. if not, warn the user and provide a way to save the file to
        # a different path
        work_template = item.properties.get("work_template")
        work_fields = None

        if work_template:
            if work_template.validate(path):
                work_fields = work_template.get_fields(path)

        # if we have template and fields, use them to determine the version info
        if work_fields and "version" in work_fields:

            # template matched. bump version number and re-apply to the template
            work_fields["version"] += 1
            next_version_path = work_template.apply_fields(work_fields)
            version = work_fields["version"]

        # fall back to the "zero config" logic
        else:
            next_version_path = publisher.util.get_next_version_path(path)
            cur_version = publisher.util.get_version_number(path)
            if cur_version is not None:
                version = cur_version + 1
            else:
                version = None

        return next_version_path, version

    def _save_to_next_version(self, path, item, save_callback):
        """
        Save the supplied path to the next version on disk.

        :param path: The current path with a version number
        :param item: The current item being published
        :param save_callback: A callback to use to save the file

        Relies on the _get_next_version_info() method to retrieve the next
        available version on disk. If a version can not be detected in the path,
        the method does nothing.

        If the next version path already exists, logs a warning and does
        nothing.

        This method is typically used by subclasses that bump the current
        working/session file after publishing.
        """

        (next_version_path, version) = self._get_next_version_info(path, item)

        if version is None:
            self.logger.debug(
                "No version number detected in the publish path. "
                "Skipping the bump file version step."
            )
            return None

        self.logger.info("Incrementing file version number...")

        # nothing to do if the next version path can't be determined or if it
        # already exists.
        if not next_version_path:
            self.logger.warning("Could not determine the next version path.")
            return None
        elif os.path.exists(next_version_path):
            self.logger.warning(
                "The next version of the path already exists",
                extra={
                    "action_show_folder": {
                        "path": next_version_path
                    }
                }
            )
            return None

        # save the file to the new path
        save_callback(next_version_path)
        self.logger.info("File saved as: %s" % (next_version_path,))

        return next_version_path
