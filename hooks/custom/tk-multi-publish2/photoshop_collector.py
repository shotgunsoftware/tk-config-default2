# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCSceneCollector(HookBaseClass):
    """
    Collector that operates on the current photoshop document. Should inherit
    from the basic collector hook.
    """

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the open documents in Photoshop and creates publish items
        parented under the supplied item.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        super(PhotoshopCCSceneCollector, self).process_current_session(
            settings, parent_item
        )

        # get all the document items and add them a new item
        for item in parent_item.children:
            if item.type_spec == "photoshop.document":
                img_item = item.create_item(
                    "photoshop.document.image", "Export", "All Session Export"
                )
                img_item.thumbnail_enabled = False
