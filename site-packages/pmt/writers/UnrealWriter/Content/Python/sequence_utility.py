# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import sys

if sys.version_info.major == 2:
    ModuleNotFoundError = ImportError

try:
    import unreal
except ModuleNotFoundError or ImportError as e:
    pass

from client_config import (
    SEQUENCER_CONFIG,
    CLIENT_CONFIG_PATH,
    override_default_config,
)
from scene_sequence import SceneSequence
from scene_asset import SceneAsset


@unreal.uclass()
class ShotBrowserUtilityWrapper(unreal.ShotBrowserUtility):
    """Utility class for handling the creation of level sequence assets"""

    # Load client configuration if one is provided in the plugin's Resources folder
    config_filepath = unreal.Paths.combine(
        [unreal.Paths.engine_plugins_dir(), CLIENT_CONFIG_PATH]
    )
    if config_filepath:
        override_default_config(config_filepath)

    @unreal.ufunction(override=True)
    def create_sequence(self, shot_ID, characters, template_kwargs):
        """
        Create a sequence asset following the project structure and naming
        convention specified in the client configuration.
        """
        sequence = SceneSequence(
            template_kwargs, 0, SEQUENCER_CONFIG["SHOT_LENGTH"]
        )

        unreal.EditorAssetLibrary.set_metadata_tag(
            sequence.shot_sequence, "shot_browser.sg_shot_id", shot_ID
        )

        # Populate the level sequence with animation tracks for each
        # SG character asset linked to the shot
        if characters:
            for char_name in characters:
                scene_asset = SceneAsset(char_name, "character")
                sequence.characters.append(scene_asset)

            sequence.populate_scene_sequence()

            # Save character list to the sequence asset's metadata
            unreal.EditorAssetLibrary.set_metadata_tag(
                sequence.shot_sequence,
                "shot_browser.sg_shot_characters",
                ", ".join(characters),
            )