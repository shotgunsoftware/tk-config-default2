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
import maya.cmds as cmds

HookBaseClass = sgtk.get_hook_baseclass()


class ExtraBuildActions(HookBaseClass):

    ##############################################################################################################
    # public interface - to be overridden by deriving classes

    @staticmethod
    def get_references_from_path(path):
        return [
            ref for ref in cmds.ls(type="reference")
            if ref != "sharedReferenceNode"
               and cmds.referenceQuery(ref, filename=True, withoutCopyNumber=True) == path
        ]

    @staticmethod
    def duplicate_reference(ref_node, n):
        path = cmds.referenceQuery(
            ref_node,
            filename=True,
            withoutCopyNumber=True
        )

        for i in range(n):
            cmds.file(
                path,
                reference=True,
                namespace=f"duplicate_{i}"
            )

    def post_build_action(self, items):
        """
        This method is executed just after the files have been loaded into the current scene.

        :param items:  List of dictionaries where each item represents a loaded file. Each dictionary contains a
                       *sg_data* key to store the Shotgun data and an *action_name* refering to the name of the action
                       used to load the file.
        """

        # query for the AssetShotConnections to get how many assets are referenced in the current shot
        sg_asset_shot_connections = self.parent.shotgun.find(
            "AssetShotConnection",
            [
                ["shot", "is", self.parent.context.entity]
            ],
            ["sg_assets_number", "asset"]
        )
        connections_by_asset = {c["id"]: c["sg_assets_number"] for c in sg_asset_shot_connections}

        # duplicate the references
        for item in items:
            asset_id = item["sg_data"]["entity"]["id"]
            asset_number = connections_by_asset.get(asset_id, 1)
            if asset_number == 1:
                continue
            ref_path = item["sg_data"]["path"]["local_path"]
            ref_node = self.get_references_from_path(ref_path)
            self.duplicate_reference(ref_node, asset_number - 1)
