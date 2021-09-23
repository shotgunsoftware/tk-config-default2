# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import mari
import os
import sgtk
import tempfile
import uuid

HookBaseClass = sgtk.get_hook_baseclass()


class MariSessionCollector(HookBaseClass):
    """
    Collector that operates on the mari session. Should inherit from the basic
    collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

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

        # grab any base class settings
        collector_settings = super(MariSessionCollector, self).settings or {}

            # settings specific to this collector
        mari_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                               "correspond to a template defined in "
                               "templates.yml. If configured, is made available"
                               "to publish plugins via the collected item's "
                               "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(mari_session_settings)
        # return base class settings as there are is no Work Template at the moment for Mari
        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Mari and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        if not mari.projects.current():
            self.logger.warning(
                "You must be in an open Mari project. No items collected!"
            )
            return

        publisher = self.parent

        icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "mari_channel.png"
        )

        layers_icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "mari_layer.png"
        )

        layer_icon_path = os.path.join(
            self.disk_location, os.pardir, "icons", "texture.png"
        )

        layers_item = None
        thumbnail = self._extract_mari_thumbnail()
        # Look for all layers for all channels on all geometry.  Create items for both
        # the flattened channel as well as the individual layers
        for geo in mari.geo.list():
            geo_name = geo.name()

            for channel in geo.channelList():
                channel_name = channel.name()

                # find all collected layers:
                collected_layers = self._find_layers_r(channel.layerList())
                if not collected_layers:
                    # no layers to publish!
                    self.logger.warning(
                        "Channel '%s' has no layers. The channel will not be collected"
                        % channel_name
                    )
                    continue

                # add item for whole flattened channel:
                item_name = "%s, %s" % (geo.name(), channel.name())
                channel_item = parent_item.create_item(
                    "mari.texture", "Channel", item_name
                )
                channel_item.thumbnail_enabled = True
                channel_item.set_icon_from_path(icon_path)
                channel_item.properties["mari_geo_name"] = geo_name
                channel_item.properties["mari_channel_name"] = channel_name
                channel_item.set_thumbnail_from_path(thumbnail)

                if len(collected_layers) > 0 and layers_item is None:
                    layers_item = channel_item.create_item(
                        "mari.layers",
                        "Unflattened layers for the channel",
                        "Texture Channel Layers",
                    )
                    layers_item.set_icon_from_path(layers_icon_path)

                # add item for each collected layer:
                found_layer_names = set()
                for layer in collected_layers:

                    # for now, duplicate layer names aren't allowed!
                    layer_name = layer.name()
                    if layer_name in found_layer_names:
                        # we might want to handle this one day...
                        self.logger.warning(
                            "Duplicate layer name found: %s. Layer will not be exported"
                            % layer_name
                        )
                        pass
                    found_layer_names.add(layer_name)

                    item_name = "%s, %s (%s)" % (geo.name(), channel.name(), layer_name)
                    layer_item = layers_item.create_item(
                        "mari.texture", "Layer", item_name
                    )
                    layer_item.thumbnail_enabled = True
                    layer_item.set_icon_from_path(layer_icon_path)
                    layer_item.properties["mari_geo_name"] = geo_name
                    layer_item.properties["mari_channel_name"] = channel_name
                    layer_item.properties["mari_layer_name"] = layer_name
                    layer_item.set_thumbnail_from_path(thumbnail)

    def _find_layers_r(self, layers):
        """
        Find all layers within the specified list of layers.  This will return
        all layers that are either paintable or procedural and traverse any layer groups
        to find all grouped layers to be collected
        :param layers:  The list of layers to inspect
        :returns:       A list of all collected layers
        """
        collected_layers = []
        for layer in layers:
            # Note, only paintable or procedural layers are exportable from Mari - all
            # other layer types are only used within Mari.
            if layer.isPaintableLayer() or layer.isProceduralLayer():
                # these are the only types of layers that can be collected
                collected_layers.append(layer)
            elif layer.isGroupLayer():
                # recurse over all layers in the group looking for exportable layers:
                grouped_layers = self._find_layers_r(layer.layerStack().layerList())
                collected_layers.extend(grouped_layers or [])

        return collected_layers

    def _extract_mari_thumbnail(self):
        """
        Render a thumbnail for the current canvas in Mari

        :returns:   The path to the thumbnail on disk
        """
        if not mari.projects.current():
            return

        canvas = mari.canvases.current()
        if not canvas:
            return

        # calculate the maximum size to capture:
        MAX_THUMB_SIZE = 512
        sz = canvas.size()
        thumb_width = sz.width()
        thumb_height = sz.height()
        max_sz = max(thumb_width, sz.height())

        if max_sz > MAX_THUMB_SIZE:
            scale = min(float(MAX_THUMB_SIZE) / float(max_sz), 1.0)
            thumb_width = max(min(int(thumb_width * scale), thumb_width), 1)
            thumb_height = max(min(int(thumb_height * scale), thumb_height), 1)

        # disable the HUD:
        hud_enabled = canvas.getDisplayProperty("HUD/RenderHud")
        if hud_enabled:
            # Note - this doesn't seem to work when capturing an image!
            canvas.setDisplayProperty("HUD/RenderHud", False)

        # render the thumbnail:
        thumb = None
        try:
            thumb = self._capture(canvas, thumb_width, thumb_height)
        except Exception:
            pass

        # reset the HUD
        if hud_enabled:
            canvas.setDisplayProperty("HUD/RenderHud", True)

        if thumb:
            # save the thumbnail
            jpg_thumb_path = os.path.join(
                tempfile.gettempdir(), "sgtk_thumb_%s.jpg" % uuid.uuid4().hex
            )
            thumb.save(jpg_thumb_path)
        else:
            jpg_thumb_path = None

        return jpg_thumb_path

    def _capture(self, canvas, thumb_width, thumb_height):
        """
        Generate a screenshot from the given canvas.
        """
        thumb = None

        # The capture method was introduced to deprecate captureImage in 4.6,
        # so use it if available. We could have use the inspect module here to
        # differentiate between the signatures with and without arguments
        # for capture, but the module can't read the parameters from C Python
        # methods.

        # In Mari 4.6.4+ we can capture with width and height passed in
        try:
            return canvas.capture(thumb_width, thumb_height)
        except Exception:
            pass
        else:
            return thumb

        # In some earlier versions, we need to call scale after capture
        try:
            image = canvas.capture()
            if image:
                image = image.scaled(thumb_width, thumb_height)
            return image
        except Exception:
            pass

        # Finally in older versions of Mari, capture is not even an option, so call
        # captureImage
        return canvas.captureImage(thumb_width, thumb_height)
