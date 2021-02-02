# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import sys

if sys.version_info.major == 2:
    ModuleNotFoundError = ImportError

try:
    import unreal
except ModuleNotFoundError or ImportError as e:
    pass

from client_config import SEQUENCER_CONFIG
from scene_sequence import SceneSequence
from ue_logging import log


class SequenceStory:
    """Manages the master level sequence for an episodic or film production"""

    def __init__(self, name):
        self._name = name
        self._create_master_sequence()

    def _create_master_sequence(self):
        log("Creating Master Sequence: {}".format(self._name))

        self._master_sequence = (
            unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                self._name,
                SEQUENCER_CONFIG["SEQUENCE_DIR"],
                unreal.LevelSequence,
                unreal.LevelSequenceFactoryNew(),
            )
        )
        frame_rate = float(SEQUENCER_CONFIG["FRAME_RATE"])
        self._master_sequence.set_display_rate(unreal.FrameRate(frame_rate))
        self._master_shot_track = self._master_sequence.add_master_track(
            unreal.MovieSceneCinematicShotTrack
        )

    def populate_master_sequence(self, shots, assets):
        """
        Populate the master sequence with the shots and character assets assigned to each scene.
        """
        if not self._master_sequence or not self._master_shot_track:
            raise ValueError(
                "The sequence {} either does not exist or is misconfigured.".format(
                    self._name
                )
            )

        start_frame = 0
        end_frame = SEQUENCER_CONFIG["SHOT_LENGTH"]
        episode_name = SEQUENCER_CONFIG["DEFAULT_EPISODE_NAME"]
        sequence_name = SEQUENCER_CONFIG["DEFAULT_SEQUENCE_NAME"]
        shot_type = SEQUENCER_CONFIG["DEFAULT_SHOT_TYPE"]

        with unreal.ScopedSlowTask(
            len(shots), "Generating shot sequences"
        ) as slow_task:
            slow_task.make_dialog(True)

            for shot_name, shot_assets in shots.items():
                # If user pressed Cancel in the UI
                if slow_task.should_cancel():
                    break
                else:
                    # Advance the progress bar by one frame
                    slow_task.enter_progress_frame(
                        1, "Generating level sequence: {}".format(shot_name)
                    )

                template_kwargs = {
                    "project": self._name,
                    "episode": episode_name,
                    "sequence": sequence_name,
                    "shot": shot_name,
                    "shot_type": shot_type,
                }
                # Create a subsequence for each shot
                subsequence = SceneSequence(
                    template_kwargs, start_frame, end_frame
                )

                # Populate the shot sequence
                for asset_name in shot_assets:
                    scene_asset = assets.get(asset_name)
                    if scene_asset and scene_asset.asset_type == "character":
                        subsequence.characters.append(scene_asset)

                subsequence.populate_scene_sequence()

                # Add a subsection for this shot in the master sequence
                subsequence_section = self._master_shot_track.add_section()
                subsequence_section.set_sequence(subsequence.shot_sequence)
                subsequence_section.set_range(start_frame, end_frame)

                start_frame = end_frame + 1
                end_frame = start_frame + SEQUENCER_CONFIG["SHOT_LENGTH"]
