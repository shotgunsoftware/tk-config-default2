
# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

"""
Hook that loads defines all the available actions, broken down by publish type.
"""

import pprint
import os
import sgtk
import unreal
import re

HookBaseClass = sgtk.get_hook_baseclass()


class UnrealSgtkActions(HookBaseClass):

    def _set_asset_metadata(self, asset_path, sg_publish_data):
        """
        Set needed metadata on the given asset
        """
        super()._set_asset_metadata(asset_path, sg_publish_data)

        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if not asset:
            return

        engine = sgtk.platform.current_engine()

        imgspc_fw = self.load_framework("tk-framework-imgspc")
        imgspc_globals = imgspc_fw.import_module("globals")

        publish_path = sg_publish_data.get("path", {}).get("local_path", asset_path)
        source_path_tag = engine.get_metadata_tag(imgspc_globals.SOURCE_PATH_TAG)
        unreal.EditorAssetLibrary.set_metadata_tag(asset, source_path_tag, publish_path)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
