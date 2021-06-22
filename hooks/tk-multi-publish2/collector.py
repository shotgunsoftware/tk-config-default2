# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import mimetypes
import os
import tempfile

import sgtk
from tank_vendor import six

HookBaseClass = sgtk.get_hook_baseclass()


class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.

    This collector hook is used to collect individual files that are browsed or
    dragged and dropped into the Publish2 UI. It can also be subclassed by other
    collectors responsible for creating items for a file to be published such as
    the current Maya session file.

    This plugin centralizes the logic for collecting a file, including
    determining how to display the file for publishing (based on the file
    extension).

    In addition to creating an item to publish, this hook will set the following
    properties on the item::

        path - The path to the file to publish. This could be a path
            representing a sequence of files (including a frame specifier).

        sequence_paths - If the item represents a collection of files, the
            plugin will populate this property with a list of files matching
            "path".

    """

    @property
    def common_file_info(self):
        """
        A dictionary of file type info that allows the basic collector to
        identify common production file types and associate them with a display
        name, item type, and config icon.

        The dictionary returned is of the form::

            {
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                ...
            }

        See the collector source to see the default values returned.

        Subclasses can override this property, get the default values via
        ``super``, then update the dictionary as necessary by
        adding/removing/modifying values.
        """

        if not hasattr(self, "_common_file_info"):

            self._common_file_info = {}

            published_file_types = self.parent.shotgun.find(
                "PublishedFileType",
                [],
                ["code", "image", "sg_item_type", "sg_extensions", "sg_templates"],
            )

            for pft in published_file_types:

                if pft["sg_item_type"] is None or pft["sg_extensions"] is None:
                    self.logger.debug(
                        "Skipping Published File Type {}: Missing information.".format(
                            pft["code"]
                        )
                    )
                    continue

                publish_templates = {}
                if pft["sg_templates"] is not None:
                    for x in pft["sg_templates"].strip("}{").split(","):
                        k, v = x.split(":")
                        publish_templates[k.strip()] = v.strip()

                self._common_file_info[pft["code"]] = {
                    "extensions": [
                        x.strip() for x in pft["sg_extensions"].strip("][").split(",")
                    ],
                    "item_type": pft["sg_item_type"],
                    "icon": self._get_icon_path_from_sg(pft),
                    "publish_templates": publish_templates,
                }

        return self._common_file_info

    def _get_icon_path_from_sg(self, sg_data):
        """"""

        icon_folder = os.path.join(tempfile.gettempdir(), "sgtk_pft_icons")

        # the icon has already been downloaded
        for f in os.listdir(icon_folder):
            if os.path.splitext(f)[0] == sg_data["code"]:
                return os.path.join(icon_folder, f)

        # the image doesn't exist on disk nor in SG
        if sg_data["image"] is None:
            return os.path.join(self.disk_location, "icons", "file.png")

        # be sure the icon folder exists on disk
        if not os.path.isdir(icon_folder):
            os.makedirs(icon_folder)

        # download the image form its url
        icon_path = os.path.join(icon_folder, sg_data["code"])
        thumb_source_url = six.moves.urllib.parse.urlunparse(
            (
                self.parent.shotgun.config.scheme,
                self.parent.shotgun.config.server,
                "/thumbnail/full/%s/%s"
                % (
                    six.moves.urllib.parse.quote(str(sg_data["type"])),
                    six.moves.urllib.parse.quote(str(sg_data["id"])),
                ),
                None,
                None,
                None,
            )
        )

        return sgtk.util.download_url(
            self.parent.shotgun, thumb_source_url, icon_path, True
        )

    def _collect_file(self, parent_item, path, frame_sequence=False):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :param frame_sequence: Treat the path as a part of a sequence
        :returns: The item that was created
        """
        file_item = super(BasicSceneCollector, self)._collect_file(
            parent_item, path, frame_sequence
        )
        file_item.properties.publish_type = file_item.type_display

        for display in self._common_file_info:
            if display == file_item.type_display:
                file_item.properties.publish_templates = self._common_file_info[
                    display
                ].get("publish_templates")

        return file_item
