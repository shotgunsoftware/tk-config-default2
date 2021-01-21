# Copyright 2018 Epic Games, Inc. 

# Setup the asset in the turntable level for rendering

import unreal
import os
import sys

def main(argv):
    # Import the FBX into Unreal using the unreal_importer script
    current_folder = os.path.dirname( __file__ )
    
    if current_folder not in sys.path:
        sys.path.append(current_folder)

    import unreal_importer

    unreal_importer.main(argv[0:2])

    fbx_file_path = argv[0]
    content_browser_path = argv[1]
    turntable_map_path = argv[2]

    # Load the turntable map where to instantiate the imported asset
    world = unreal.EditorLoadingAndSavingUtils.load_map(turntable_map_path)
    
    if not world:
        return

    # Find the turntable actor, which is used in the turntable sequence that rotates it 360 degrees
    turntable_actor = None
    level_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for level_actor in level_actors:
        if level_actor.get_actor_label() == "turntable":
            turntable_actor = level_actor
            break
            
    if not turntable_actor:
        return
        
    # Destroy any actors attached to the turntable (attached for a previous render)
    for attached_actor in turntable_actor.get_attached_actors():
        unreal.EditorLevelLibrary.destroy_actor(attached_actor)
        
    # Derive the imported asset path from the given FBX filename and content browser path
    fbx_filename = os.path.basename(fbx_file_path)
    asset_name = os.path.splitext(fbx_filename)[0]
    asset_path_to_load =  content_browser_path + asset_name
    
    # Load the asset to spawn it at origin
    asset = unreal.EditorAssetLibrary.load_asset(asset_path_to_load)
    if not asset:
        return
        
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(asset, unreal.Vector(0, 0, 0))
    
    # Scale the actor to fit the frame, which is dependent on the settings of the camera used in the turntable sequence
    # The scale values are based on a volume that fits safely in the frustum of the camera and account for the frame ratio
    # and must be tweaked if the camera settings change
    origin, bounds = actor.get_actor_bounds(True)
    scale_x = 250 / min(bounds.x, bounds.y)
    scale_y = 300 / max(bounds.x, bounds.y)
    scale_z = 200 / bounds.z
    scale = min(scale_x, scale_y, scale_z)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    
    # Offset the actor location so that it rotates around its center
    origin = origin * scale
    actor.set_actor_location(unreal.Vector(-origin.x, -origin.y, -origin.z), False, True)
    
    # Attach the newly spawned actor to the turntable
    actor.attach_to_actor(turntable_actor, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)

    unreal.EditorLevelLibrary.save_current_level()
    
if __name__ == "__main__":
    # Script arguments must be, in order:
    # Path to FBX to import
    # Unreal content browser path where to store the imported asset
    # Unreal content browser path to the turntable map to duplicate and where to spawn the asset
    argv = []

    if 'UNREAL_SG_FBX_OUTPUT_PATH' in os.environ:
        argv.append(os.environ['UNREAL_SG_FBX_OUTPUT_PATH'])

    if 'UNREAL_SG_CONTENT_BROWSER_PATH' in os.environ:
        argv.append(os.environ['UNREAL_SG_CONTENT_BROWSER_PATH'])

    if 'UNREAL_SG_MAP_PATH' in os.environ:
        argv.append(os.environ['UNREAL_SG_MAP_PATH'])

    if len(argv) == 3:
        main(argv)
