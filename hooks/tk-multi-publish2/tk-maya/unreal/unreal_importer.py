# Copyright 2018 Epic Games, Inc. 

import unreal
import os
import sys

"""
Functions to import FBX into Unreal
"""

def _sanitize_name(name):
    # Remove the default Shotgun versioning number if found (of the form '.v001')
    name_no_version = re.sub(r'.v[0-9]{3}', '', name)
    
    # Replace any remaining '.' with '_' since they are not allowed in Unreal asset names
    return name_no_version.replace('.', '_')

def _generate_fbx_import_task(filename, destination_path, destination_name=None, replace_existing=True,
                             automated=True, save=True, materials=True,
                             textures=True, as_skeletal=False):
    """
    Create and configure an Unreal AssetImportTask

    :param filename: The fbx file to import
    :param destination_path: The Content Browser path where the asset will be placed
    :return the configured AssetImportTask
    """
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = destination_path
    
    # By default, destination_name is the filename without the extension
    if destination_name is not None:
        task.destination_name = destination_name
        
    task.replace_existing = replace_existing
    task.automated = automated
    task.save = save

    task.options = unreal.FbxImportUI()
    task.options.import_materials = materials
    task.options.import_textures = textures
    task.options.import_as_skeletal = as_skeletal
    
    task.options.static_mesh_import_data.combine_meshes = True

    task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    if as_skeletal:
        task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH

    return task

def main(argv):
    tasks = []
    tasks.append(_generate_fbx_import_task(*argv))
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)

if __name__ == "__main__":
    # Script arguments must be, in order:
    # Path to FBX to import
    # Unreal content browser path where to store the imported asset
    main(sys.argv[1:])
