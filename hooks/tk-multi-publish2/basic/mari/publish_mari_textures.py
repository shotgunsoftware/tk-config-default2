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
import json
import pprint
# import subprocess

import mari
import sgtk
import converter

HookBaseClass = sgtk.get_hook_baseclass()


class MariTexturesPublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open mari session.
    """

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(self.disk_location, os.pardir, "icons", "publish.png")

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Publish to ShotGrid"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        Publishes the file to ShotGrid. A <b>Publish</b> entry will be
        created in ShotGrid which will include a reference to the file's current
        path on disk. Other users will be able to access the published file via
        the <b><a href='%s'>Loader</a></b> so long as they have access to
        the file's location on disk.

        If the session has not been saved, validation will fail and a button
        will be provided in the logging output to save the file.

        <h3>File versioning</h3>
        If the filename contains a version number, the process will bump the
        file to the next version after publishing.

        The <code>version</code> field of the resulting <b>Publish</b> in
        ShotGrid will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        After publishing, if a version number is detected in the file, the file
        will automatically be saved to the next incremental version number.
        For example, <code>filename.v001.ext</code> will be published and copied
        to <code>filename.v002.ext</code>

        If the next incremental version of the file already exists on disk, the
        validation step will produce a warning, and a button will be provided in
        the logging output which will allow saving the session to the next
        available version number prior to publishing.

        <br><br><i>NOTE: any amount of version number padding is supported.</i>

        <h3>Overwriting an existing publish</h3>
        A file can be published multiple times however only the most recent
        publish will be available to other users. Warnings will be provided
        during validation if there are previous publishes.
        """ % (
            loader_url,
        )
        # TODO: add link to workflow docs

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
        return {
            "Publish Type": {
                "type": "shotgun_publish_type",
                "default": "UDIM Image",
                "description": "SG publish type to associate publishes with.",
            },
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                "correspond to a template defined in "
                "templates.yml.",
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
        return ["mari.texture"]

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

        # because a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        if settings.get("Publish Template").value:
            item.context_change_allowed = False
        
        checked = True
        layer = item.properties.get('mari_layer_name')
        if layer:
            checked = False

        return {"accepted": checked, "checked": checked}

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

        publisher = self.parent

        # populate the publish template on the item if found
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.engine.get_template_by_name(
            publish_template_setting.value
        )
        if publish_template:
            item.properties["publish_template"] = publish_template
        else:
            error_msg = "Validation failed. Publish template not found"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        geo_name = item.properties["mari_geo_name"]
        geo = mari.geo.find(geo_name)
        if not geo:
            error_msg = (
                "Failed to find geometry in the project! Validation failed." % geo_name
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)

        channel_name = item.properties["mari_channel_name"]
        channel = geo.findChannel(channel_name)
        if not channel:
            error_msg = (
                "Failed to find channel on geometry! Validation failed." % channel_name
            )
            self.logger.error(error_msg)
            raise Exception(error_msg)

        layer_name = item.properties.get("mari_layer_name")
        if layer_name:
            layer = channel.findLayer(layer_name)
            if not layer:
                error_msg = (
                    "Failed to find layer for channel: %s Validation failed."
                    % layer_name
                )
                self.logger.error(error_msg)
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

        # Currently there is no primary publish for Mari so just save the
        # current project to ensure nothing is lost if something goes wrong!
        proj = mari.projects.current()
        if proj:
            self.logger.info("Saving the current project...")
            proj.save()

        publisher = self.parent

        geo_name = item.properties["mari_geo_name"]
        geo = mari.geo.find(geo_name)
        channel_name = item.properties["mari_channel_name"]
        channel = geo.findChannel(channel_name)
        layer_name = item.properties.get("mari_layer_name")

        publish_template = item.properties["publish_template"]

        # Get fields from the current context
        fields = {}
        ctx_fields = self.parent.context.as_template_fields(publish_template)
        fields.update(ctx_fields)

        # For geo name, strip out the non-alphanumeric characters because Mari's
        # publish template filter does not allow non-alphanumeric characters in
        # the geo name.
        geo_name = re.sub(r"[\W_]+", "", geo_name)
        fields["name"] = geo_name

        fields["channel"] = channel_name
        fields["layer"] = layer_name
        fields["UDIM"] = "$UDIM"

        # get the publish name. This will ensure we get a
        # consistent name across version publishes of this file.
        if layer_name:
            publish_name = "%s, %s - %s" % (geo_name, channel_name, layer_name)
        else:
            publish_name = "%s, %s" % (geo_name, channel_name)

        existing_publishes = self._find_publishes(
            self.parent.context, publish_name, settings["Publish Type"].value
        )
        version = max([p["version_number"] for p in existing_publishes] or [0]) + 1

        fields["version"] = version

        publish_path = publish_template.apply_fields(fields).replace(' ', '_')

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(publish_path)

        self.logger.info("A Publish will be created in SG and linked to:")
        self.logger.info("  %s" % (path,))

        if layer_name:
            layer = channel.findLayer(layer_name)
            layer.exportImages(path)
        else:
            # publish the entire channel, flattened
            layers = channel.layerList()
            if len(layers) == 1:
                # only one layer so just publish it:
                # Note - this works around an issue that was reported (#27945) where flattening a channel
                # with only a single layer would cause Mari to crash - this bug was not reproducible by
                # us but happened 100% for the client!
                layer = layers[0]
                layer.exportImages(path)
            elif len(layers) > 1:
                # flatten layers in the channel and publish the flattened layer:
                # remember the current channel:
                current_channel = geo.currentChannel()
                duplicate_channel = None
                try:
                    # duplicate the channel so we don't operate on the original:
                    duplicate_channel = geo.createDuplicateChannel(channel)
                except RuntimeError as e:
                    self.logger.exception(e)
                if duplicate_channel:
                    try:
                        # flatten it into a single layer:
                        flattened_layer = duplicate_channel.flatten()
                        # export the images for it:
                        flattened_layer.exportImages(path)
                    finally:
                        # set the current channel back - not doing this will result in Mari crashing
                        # when the duplicated channel is removed!
                        geo.setCurrentChannel(current_channel)
                        # remove the duplicate channel, destroying the channel and the flattened layer:
                        geo.removeChannel(duplicate_channel, geo.DESTROY_ALL)
            else:
                self.logger.error(
                    "Channel '%s' doesn't appear to have any layers!" % channel.name()
                )

        # Export as Arnold TX files
        channel_exrs = list()
        self.logger.info("Converting exr to tx...")
        for patch in geo.patchList():
            uv_ind = patch.uvIndex() + 1001
            exr_path = path.replace('$UDIM', str(uv_ind).encode('utf-8'))
            if not os.path.isfile(exr_path):
                continue
            channel_exrs.append(exr_path)
        if channel_exrs:
            json_path = channel_exrs[0].rsplit('.', 2)[0] + '.json'
            json.dump(channel_exrs, open(json_path, 'w'), indent=4)
            converter.init_deadline_job(
                json_path=json_path,
                frames='1001-' + str(1000 + len(channel_exrs)))

        # arguments for publish registration
        self.logger.info("Registering publish...")
        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "comment": item.description,
            "path": path,
            "name": publish_name,
            "version_number": version,
            "thumbnail_path": item.get_thumbnail_as_path(),
            "published_file_type": settings["Publish Type"].value,
            "dependency_paths": [],
        }

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),),
                }
            },
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties["sg_publish_data"] = sgtk.util.register_publish(**publish_data)

        # inject the publish path such that children can refer to it when
        # updating dependency information
        item.properties["sg_publish_path"] = path

        self.logger.info("Publish registered!")

        # now that we've published. keep a handle on the path that was published
        item.properties["path"] = path

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # get the data for the publish that was just created in SG
        publish_data = item.properties["sg_publish_data"]

        # ensure conflicting publishes have their status cleared
        publisher.util.clear_status_for_conflicting_publishes(
            item.context, publish_data
        )

        self.logger.info("Cleared the status of all previous, conflicting publishes")

        path = item.properties["path"]
        self.logger.info(
            "Publish created for file: %s" % (path,),
            extra={
                "action_show_in_shotgun": {
                    "label": "Show Publish",
                    "tooltip": "Open the Publish in ShotGrid.",
                    "entity": publish_data,
                }
            },
        )

    def _find_publishes(self, ctx, publish_name, publish_type):
        """
        Given a context, publish name and type, find all publishes from Shotgun
        that match.

        :param ctx:             Context to use when looking for publishes
        :param publish_name:    The name of the publishes to look for
        :param publish_type:    The type of publishes to look for

        :returns:               A list of Shotgun publish records that match the search
                                criteria
        """
        publish_entity_type = sgtk.util.get_published_file_entity_type(self.parent.sgtk)
        if publish_entity_type == "PublishedFile":
            publish_type_field = "published_file_type.PublishedFileType.code"
        else:
            publish_type_field = "tank_type.TankType.code"

        # construct filters from the context:
        filters = [["project", "is", ctx.project]]
        if ctx.entity:
            filters.append(["entity", "is", ctx.entity])
        if ctx.task:
            filters.append(["task", "is", ctx.task])

        # add in name & type:
        if publish_name:
            filters.append(["name", "is", publish_name])
        if publish_type:
            filters.append([publish_type_field, "is", publish_type])

        # retrieve a list of all matching publishes from Shotgun:
        sg_publishes = []
        try:
            query_fields = ["version_number"]
            sg_publishes = self.parent.shotgun.find(
                publish_entity_type, filters, query_fields
            )
        except Exception as e:
            self.logger.error(
                "Failed to find publishes of type '%s', called '%s', for context %s: %s"
                % (publish_name, publish_type, ctx, e)
            )
        return sg_publishes
