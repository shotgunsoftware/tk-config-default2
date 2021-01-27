# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import unreal

ASSET_DIR = "/Game/Assets/"


def import_published_file(asset_data, task_type, file_type):
    """Import the FBX file published against the asset's Modeling task in Shotgun."""
    asset_path = ""
    current_version = 0

    for task in asset_data:
        # Collect files published against the asset's Modeling task
        if task["name"] == task_type:

            for child in task["children"]:
                # Currently only importing FBX assets
                if (
                    child["type"] == "PublishedFile"
                    and child["file_type"] == file_type
                ):
                    # Record the current asset version
                    if child["version"] > current_version:
                        current_version = child["version"]
                        asset_path = child["path"]

    # Import the asset with the most recent version
    if asset_path:
        object_paths = _import_asset(asset_path, ASSET_DIR)
        return object_paths


def _import_asset(asset_path, destination, headless_mode=True):
    if asset_path is None or destination is None:
        raise ValueError("Cannot import asset, given invalid arguments")

    if unreal.Paths.file_exists(asset_path):

        task = unreal.AssetImportTask()
        task.filename = asset_path
        task.destination_path = destination
        task.automated = headless_mode
        task.replace_existing = False
        task.save = True

        task.options = unreal.FbxImportUI()
        task.options.import_materials = True
        task.options.import_textures = True
        task.options.import_as_skeletal = True

        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        return task.imported_object_paths
    else:
        unreal.log_warning(
            "Unable to import, asset not found at path: {}".format(asset_path)
        )
