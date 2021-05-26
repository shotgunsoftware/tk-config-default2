# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

import sgtk
import vrMaterialPtr

HookBaseClass = sgtk.get_hook_baseclass()


class VREDSceneCollector(HookBaseClass):
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

        super(VREDSceneCollector, self).process_current_session(settings, parent_item)

        # For each new material which are not already published, create an item
        for mat in vrMaterialPtr.getAllMaterials():
            material_name = mat.getName()
            if material_name in ["Environments", "Studio", "Shadow"]:
                self.logger.debug("Skipping default material...")
                continue
            if mat.isAsset():
                self.logger.debug("Material already published, skip it...")
                continue
            material_item = parent_item.create_item(
                "vred.material", "VRED Material", material_name
            )
            material_item.thumbnail_enabled = False
            material_item.context_change_allowed = False

            material_item.properties["material"] = mat

            # TODO: explore further to see if we can get the material preview
            material_item.set_icon_from_path(
                os.path.join(self.disk_location, "icons", "material.png")
            )
            # att = mat.fields().getAttachment("ImageAttachment")
            # img = vrFieldAccess(att).getFieldContainer("image")
