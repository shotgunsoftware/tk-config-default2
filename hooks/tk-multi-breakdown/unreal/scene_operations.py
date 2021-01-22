# Copyright (c) 2013 Shotgun Software Inc.
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
from sgtk import Hook
from tank.hook import create_hook_instance

import unreal


class BreakdownSceneOperations(Hook):
    """
    Breakdown operations for Unreal.

    The updating part of this implementation relies on the importing
    functionnalities of the tk-multi-loader2.unreal's Hook.
    """

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.

        Toolkit will scan the list of items, see if any of the objects matches
        any templates and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """
        refs = []
        # Parse Unreal Editor Assets
        # Call _build_scene_item_dict method on each asset to build the scene_item_dict (node, type, path)
        # The _build_scene_item_dict method can be overriden by derived hooks.
        for asset_path in unreal.EditorAssetLibrary.list_assets("/Game/"):
            scene_item_dict = self._build_scene_item_dict(asset_path)
            if not scene_item_dict:
                continue
            refs.append(scene_item_dict)

        return refs


    def _build_scene_item_dict(self, asset_path: str):
        """
        If the UAsset at `asset_path` has the tag `SOURCE_PATH_TAG` defined in
        `tk-framework-imgspc`, build the scene item dict that will be used
        by the `tk-multi-breakdown` app to determine if there is a more recent
        version available.

        If the studio's workflow is not compatible with the use of tags, this
        method should be overriden in derived Hooks to provide its own logic.

        :param asset_path: Path of the UAsset to check
        :returns: scene item dict or None
        """
        imgspc_fw = self.load_framework("tk-framework-imgspc")
        imgspc_globals = imgspc_fw.import_module("globals")
        engine = sgtk.platform.current_engine()
        source_path_tag = engine.get_metadata_tag(imgspc_globals.SOURCE_PATH_TAG)

        asset = unreal.load_asset(asset_path)
        sgtk_path = unreal.EditorAssetLibrary.get_metadata_tag(
            asset, source_path_tag
        )
        if not sgtk_path:
            self.logger.debug("Asset `{}` does not have the tag `{}`".format(
                asset.get_path_name(), source_path_tag
            ))
            return None

        scene_item_dict = {
            "node": asset.get_path_name(),
            "type": str(type(asset)),
            # Must be a path linked ot a template with a {version} key
            # (see tk-multi-breakdown/python/tk_multi_breakdown/breakdown.py)
            "path": sgtk_path,
        }

        return scene_item_dict


    def update(self, items):
        """
        Perform replacements given a number of scene items passed from the app.

        The method relies on `tk-multi-loader2.unreal` `action_mappings` hook:
        the update is an import replacing the older version. This way, this
        `update` method can update all the types the loader can load, and will
        also apply the same metadata.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        The items parameter is a list of dictionaries on the same form as was
        generated by the scan_scene hook above. The path key now holds
        the that each node should be updated *to* rather than the current path.
        """
        engine = sgtk.platform.current_engine()

        # tk-unreal from github releases
        tk_unreal_actions = os.path.join(
            engine.disk_location,
            "hooks", "tk-multi-loader2", "tk-unreal_actions.py",
        )

        # Build the hook, with tk-unreal's hook as a parent
        tk_imgspc_actions_hook = create_hook_instance(
            [
                tk_unreal_actions,
                # resolve path to this config
                engine._TankBundle__resolve_hook_expression(
                    None,
                    "{config}/tk-multi-loader2/unreal/tk-unreal_sgtk_actions.py"
                )[0]
            ],
            self,
        )
        tk_imgspc_actions_hook.parent.engine = engine

        for item in items:

            asset_to_update = unreal.load_asset(item["node"])
            if not asset_to_update:
                self.logger.warning(f"Could not load asset {asset_to_update}.")
                continue

            asset_path = unreal.Paths.get_path(asset_to_update.get_path_name())
            asset_name = asset_to_update.get_name()
            new_source_file_path = item["path"]

            publishes = sgtk.util.find_publish(
                self.sgtk,
                [new_source_file_path],
                fields=[
                    "path",
                    "name",
                    "created_by",
                    "version_number",
                    "published_file_type",
                ]
            )
            if not publishes.get(new_source_file_path):
                self.logger.warning(
                    f"No PublishedFile found in Shotgun for path `{new_source_file_path}`"
                )
                continue

            sg_publish_data = publishes[new_source_file_path]

            tk_imgspc_actions_hook._import_to_content_browser(
                new_source_file_path,
                sg_publish_data,
            )
