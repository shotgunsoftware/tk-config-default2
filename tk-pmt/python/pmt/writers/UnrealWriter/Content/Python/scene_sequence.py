# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import sys

if sys.version_info.major == 2:
    ModuleNotFoundError = ImportError

try:
    import unreal
except ModuleNotFoundError or ImportError as e:
    pass

from asset_importer import import_published_file
from client_config import SEQUENCER_CONFIG
from ue_logging import log
from scene_asset import SceneAsset

CHARACTER_SPAWN_RADIUS = 100
DEFAULT_CAMERA_POSITION = unreal.Vector(-500, 0, 540)
DEFAULT_CAMERA_ROTATOR = unreal.Rotator(0, -40, 0)


class SceneSequence:
    """Represents a shot sequence for a given scene"""

    def __init__(self, template_kwargs, start_frame, end_frame):
        """
        :param template_kwargs: dict containing all pair of key-values required
            to fill the sequence template names and paths as defined in client_config
        """
        try:
            self._name = SEQUENCER_CONFIG["SEQUENCE_NAME"].format(
                **template_kwargs
            )
            self._directory = SEQUENCER_CONFIG["SEQUENCE_PATH"].format(
                **template_kwargs
            )
        except KeyError as err:
            raise RuntimeError(
                "Missing key to determine sequence path and name: {}".format(
                    err.message
                )
            )

        self._template_kwargs = template_kwargs

        self._start_frame = start_frame
        self._end_frame = end_frame
        self._subscenes = {}

        self.characters = []

        self._create_scene_sequence()

    def _create_scene_sequence(self):
        log("Creating shot: {} at {}".format(self._name, self._directory))

        self._shot_sequence = (
            unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                self._name,
                self._directory,
                unreal.LevelSequence,
                unreal.LevelSequenceFactoryNew(),
            )
        )

        # Add a camera cut track
        log("Adding camera cut and main cinecamera actor.")
        camera_cut_track = self._shot_sequence.add_master_track(
            unreal.MovieSceneCameraCutTrack
        )
        # Set the frame rate
        frame_rate = float(SEQUENCER_CONFIG["FRAME_RATE"])
        # Sequencer has two frame rates:
        # - There's the FPS which is the display rate
        # - and there is the tick interval, which determines the sub frame timing
        tick_resolution = self._shot_sequence.get_tick_resolution()
        tick_rate = (
            float(tick_resolution.numerator) / tick_resolution.denominator
        )
        duration = float(self._end_frame - self._start_frame) / frame_rate
        self._shot_sequence.set_display_rate(unreal.FrameRate(frame_rate))
        self._shot_sequence.set_playback_end(self._end_frame)
        self._shot_sequence.set_work_range_end(duration)

        camera_cut_section = camera_cut_track.add_section()
        # Time range relative to shot, not sequence
        camera_cut_section.set_range(0, self._end_frame - self._start_frame)
        camera_cut_section.set_pre_roll_frames(
            tick_rate / frame_rate * SEQUENCER_CONFIG["PRE_ROLL_FRAMES"]
        )

        # Add a binding for the camera
        cine_camera = unreal.EditorLevelLibrary.spawn_actor_from_class(
            unreal.CineCameraActor,
            DEFAULT_CAMERA_POSITION,
            DEFAULT_CAMERA_ROTATOR,
        )
        camera_binding = self._shot_sequence.add_spawnable_from_instance(
            cine_camera
        )
        unreal.EditorLevelLibrary().destroy_actor(cine_camera)
        # Can have a custom display name for camera actor section
        if SEQUENCER_CONFIG.get("CAMERA_DISPLAY_NAME"):
            camera_binding.set_display_name(
                SEQUENCER_CONFIG["CAMERA_DISPLAY_NAME"]
            )

        # Add the binding to the camera cut
        camera_binding_id = self._shot_sequence.make_binding_id(
            camera_binding, unreal.MovieSceneObjectBindingSpace.LOCAL
        )
        camera_cut_section.set_camera_binding_id(camera_binding_id)

        # Add a subscene track per department
        subscene_track = self._shot_sequence.add_master_track(
            unreal.MovieSceneSubTrack
        )

        template_kwargs = self._template_kwargs
        # Do not create subscene tracks if no key `SUBSCENE_TRACKS` in the config
        for department in SEQUENCER_CONFIG.get("SUBSCENE_TRACKS", []):
            template_kwargs["department"] = department
            try:
                subtrack_name = SEQUENCER_CONFIG["SUBSEQUENCE_NAME"].format(
                    **template_kwargs
                )
                subtrack_dir = SEQUENCER_CONFIG["SUBSEQUENCE_PATH"].format(
                    **template_kwargs
                )
            except KeyError as err:
                raise RuntimeError(
                    "Missing key to determine subsequence path and name: {}".format(
                        err.message
                    )
                )

            sub_sequence = (
                unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                    subtrack_name,
                    subtrack_dir,
                    unreal.LevelSequence,
                    unreal.LevelSequenceFactoryNew(),
                )
            )
            sub_sequence.set_display_rate(unreal.FrameRate(frame_rate))
            sub_sequence.set_playback_end(self._end_frame)
            unreal.UnrealWriterPythonAPI.add_sequence_to_subtrack(
                subscene_track, sub_sequence
            )
            self._subscenes[department] = sub_sequence

            # Save the created asset
            unreal.EditorAssetLibrary.save_directory(subtrack_dir)

        self._shot_sequence.set_view_range_start(0)
        self._shot_sequence.set_view_range_end(duration)

        for subscene_track_section in subscene_track.get_sections():
            subscene_track_section.set_pre_roll_frames(
                tick_rate / frame_rate * SEQUENCER_CONFIG["PRE_ROLL_FRAMES"]
            )

        # Save the created asset
        unreal.EditorAssetLibrary.save_directory(self._directory)

    @property
    def shot_sequence(self):
        """Get the level sequence associated with this scene, if it exists. Otherwise create one."""
        if not self._shot_sequence:
            self._create_scene_sequence()

        return self._shot_sequence

    def populate_scene_sequence(self):
        # Add character bindings to the Animation subscene track if it exists, otherwise the shot level sequence.
        parent_sequence = self._subscenes.get("anim", self.shot_sequence)

        # Using the Screenwriter's character pin to represent a default dummy actor
        character_asset = unreal.load_asset(
            SEQUENCER_CONFIG["DUMMY_ACTOR_ASSET"]
        )

        character_index = 0
        character_count = len(self.characters)
        for char_asset in self.characters:

            # If a published FBX exists for the asset, import and load
            if char_asset.children:
                imported_assets_paths = import_published_file(
                    char_asset.children, "Modeling", ".fbx"
                )
                if imported_assets_paths:
                    character_asset = unreal.load_asset(
                        imported_assets_paths[0]
                    )

            # Create a pin for each character and add it to the sequence as a spawnable
            rotation = unreal.Rotator(
                0, 0, 360 / character_count * character_index
            )
            position = rotation.get_forward_vector() * CHARACTER_SPAWN_RADIUS

            # Spawning character pins along the circumference of a circle
            character = unreal.EditorLevelLibrary.spawn_actor_from_object(
                character_asset, position, rotation
            )
            char_name = char_asset.name
            character.set_actor_label(char_name)

            log(
                "Adding character actor {} to shot {}.".format(
                    char_name, self._name
                )
            )
            character_binding = parent_sequence.add_spawnable_from_instance(
                character
            )
            unreal.EditorLevelLibrary().destroy_actor(character)

            log("Adding animation track to character: {}".format(char_name))
            character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
            character_index = character_index + 1