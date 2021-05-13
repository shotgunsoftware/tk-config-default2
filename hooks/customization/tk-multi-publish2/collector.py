# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import sgtk

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

        # inherit the settings from the base publish plugin
        base_file_info = super(BasicSceneCollector, self).common_file_info or {}

        icons_folders = [os.path.join(self.disk_location, "icons")]

        automotive_file_info = {
            "Wref File": {
                "extensions": ["wref"],
                "icon": self._get_icon_path("alias.png"),
                "item_type": "file.wref",
            },
            "Catpart File": {
                "extensions": ["CATPart"],
                "icon": self._get_icon_path("catia.png", icons_folders=icons_folders),
                "item_type": "file.catpart",
            },
            "Jt File": {
                "extensions": ["jt"],
                "icon": self._get_icon_path("jt.png", icons_folders=icons_folders),
                "item_type": "file.jt",
            },
            "Stp File": {
                "extensions": ["stp", "step"],
                "icon": self._get_icon_path("stp.png", icons_folders=icons_folders),
                "item_type": "file.stp",
            },
            "Igs File": {
                "extensions": ["igs", "iges"],
                "icon": self._get_icon_path("igs.png", icons_folders=icons_folders),
                "item_type": "file.stp",
            },
            "Office File": {
                "extensions": ["doc", "docx", "xls", "xlsx", "ppt", "pptx"],
                "icon": self._get_icon_path("office.png", icons_folders=icons_folders),
                "item_type": "file.office",
            },
            "OBJ File": {
                "extensions": ["obj"],
                "icon": self._get_icon_path("3d_model.png", icons_folders=icons_folders),
                "item_type": "file.obj",
            },
            "FBX File": {
                "extensions": ["fbx"],
                "icon": self._get_icon_path("fbx.png", icons_folders=icons_folders),
                "item_type": "file.fbx",
            },
        }
        # update the base settings
        base_file_info.update(automotive_file_info)

        return base_file_info

    def process_file(self, settings, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """

        current_item = super(BasicSceneCollector, self).process_file(settings, parent_item, path)

        if current_item.type_spec == "file.alias":

            # create the translation item
            translation_item = current_item.create_item(
                "file.alias.translation",
                "Alias Translations",
                "All Alias Translations"
            )
            translation_item.properties["path"] = path

        return current_item
