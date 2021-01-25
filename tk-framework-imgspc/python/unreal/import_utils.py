import os
import re
import functools

import sgtk
import unreal

from .. import globals as imgspc_globals


def get_tk(func):
    """
    Decorator function to get a `tk` instance (`tank.api.Tank`)

    :param func: function to decorate
    """
    @functools.wraps(func)
    def wrapper_get_tk(*args, **kwargs):
        if not kwargs.get("tk"):
            current_engine = sgtk.platform.current_engine()
            tk = current_engine.sgtk
            kwargs.update({"tk": tk})
        return func(*args, **kwargs)
    return wrapper_get_tk


@get_tk
def import_to_content_browser(path, sg_publish_data, tk=None):
    """
    Import the asset into the Unreal Content Browser.

    :param path: Path to file.
    :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
    """

    unreal.log("File to import: {}".format(path))

    if not os.path.exists(path):
        raise Exception(f"File not found on disk - '{path}'")

    destination_path, destination_name = get_destination_path_and_name(sg_publish_data, tk=tk)

    asset_path = import_fbx_asset(path, destination_path, destination_name)

    if asset_path:
        set_asset_metadata(asset_path, sg_publish_data, tk=tk)

        # Focus the Unreal Content Browser on the imported asset
        asset_paths = []
        asset_paths.append(asset_path)
        unreal.EditorAssetLibrary.sync_browser_to_objects(asset_paths)


@get_tk
def get_destination_path_and_name(sg_publish_data, tk=None):
    """
    Get the destination path and name from the publish data and the templates

    :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
    :return destination_path that matches a template and destination_name from asset or published file
    """
    # Get the publish context to determine the template to use
    context = tk.context_from_entity_dictionary(sg_publish_data)

    # Get the destination templates based on the context
    # Assets and Shots supported by default
    # Other entities fall back to Project
    if context.entity is None:
        destination_template = tk.templates["unreal_loader_project_path"]
        destination_name_template = tk.templates["unreal_loader_project_name"]
    elif context.entity["type"] == "Asset":
        destination_template = tk.templates["unreal_loader_asset_path"]
        destination_name_template = tk.templates["unreal_loader_asset_name"]
    elif context.entity["type"] == "Shot":
        destination_template = tk.templates["unreal_loader_shot_path"]
        destination_name_template = tk.templates["unreal_loader_shot_name"]
    else:
        destination_template = tk.templates["unreal_loader_project_path"]
        destination_name_template = tk.templates["unreal_loader_project_name"]

    # Get the name field from the Publish Data
    name = sg_publish_data["name"]
    name = os.path.splitext(name)[0]

    # Query the fields needed for the destination template from the context
    fields = context.as_template_fields(destination_template)

    # Add the name field from the publish data
    fields["name"] = name

    # Get destination path by applying fields to destination template
    # Fall back to the root level if unsuccessful
    try:
        destination_path = destination_template.apply_fields(fields)
    except Exception:
        destination_path = "/Game/Assets/"

    # Query the fields needed for the name template from the context
    name_fields = context.as_template_fields(destination_name_template)

    # Add the name field from the publish data
    name_fields["name"] = name

    # Get destination name by applying fields to the name template
    # Fall back to the filename if unsuccessful
    try:
        destination_name = destination_name_template.apply_fields(name_fields)
    except Exception:
        destination_name = _sanitize_name(sg_publish_data["code"])

    return destination_path, destination_name


@get_tk
def set_asset_metadata(asset_path, sg_publish_data, tk=None):
    """
    Set needed metadata on the given asset
    """
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)

    if not asset:
        return

    engine = sgtk.platform.current_engine()

    # Add a metadata tag for "created_by"
    if "created_by" in sg_publish_data:
        createdby_dict = sg_publish_data["created_by"]
        name = ""
        if "name" in createdby_dict:
            name = createdby_dict["name"]
        elif "id" in createdby_dict:
            name = createdby_dict["id"]

        tag = engine.get_metadata_tag("created_by")
        unreal.EditorAssetLibrary.set_metadata_tag(asset, tag, name)

    # Add a metadata tag for the Shotgun URL
    # Construct the PublishedFile URL from the publish data type and id since
    # the context of a PublishedFile is the Project context
    shotgun_site = tk.shotgun_url
    type = sg_publish_data["type"]
    id = sg_publish_data["id"]
    url = shotgun_site + "/detail/" + type + "/" + str(id)

    """
    # Get the URL from the context (Asset, Task, Project)
    # The context of the publish data is usually the Task (or Project if there's no task)
    # But try to be more specific by using the context of the linked entity (Asset)
    entity_dict = sg_publish_data["entity"]
    context = self.sgtk.context_from_entity_dictionary(entity_dict)
    url = context.shotgun_url

    if entity_dict["type"] == "Project":
        # As a last resort, construct the PublishedFile URL from the publish data type and id since
        # the context of a PublishedFile is the Project context
        shotgun_site = self.sgtk.shotgun_url
        type = sg_publish_data["type"]
        id = sg_publish_data["id"]
        url = shotgun_site + "/detail/" + type + "/" + str(id)
    """

    tag = engine.get_metadata_tag("url")
    unreal.EditorAssetLibrary.set_metadata_tag(asset, tag, url)

    publish_path = sg_publish_data.get("path", {}).get("local_path", asset_path)
    source_path_tag = engine.get_metadata_tag(imgspc_globals.SOURCE_PATH_TAG)
    unreal.EditorAssetLibrary.set_metadata_tag(asset, source_path_tag, publish_path)

    unreal.EditorAssetLibrary.save_loaded_asset(asset)


"""
Functions to import FBX into Unreal
"""

def _sanitize_name(name):
    # Remove the default Shotgun versioning number if found (of the form '.v001')
    name_no_version = re.sub(r'.v[0-9]{3}', '', name)

    # Replace any remaining '.' with '_' since they are not allowed in Unreal asset names
    return name_no_version.replace('.', '_')


def import_fbx_asset(input_path, destination_path, destination_name):
    """
    Import an FBX into Unreal Content Browser

    :param input_path: The fbx file to import
    :param destination_path: The Content Browser path where the asset will be placed
    :param destination_name: The asset name to use; if None, will use the filename without extension
    """
    tasks = []
    tasks.append(generate_fbx_import_task(input_path, destination_path, destination_name))

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    first_imported_object = None

    for task in tasks:
        unreal.log("Import Task for: {}".format(task.filename))
        for object_path in task.imported_object_paths:
            unreal.log("Imported object: {}".format(object_path))
            if not first_imported_object:
                first_imported_object = object_path

    return first_imported_object


def generate_fbx_import_task(filename, destination_path, destination_name=None, replace_existing=True,
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
    # task.options.static_mesh_import_data.combine_meshes = True

    task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    if as_skeletal:
        task.options.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH

    return task
