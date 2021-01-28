# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import os
import sys

if sys.version_info.major == 2:
    ModuleNotFoundError = ImportError
elif sys.version_info.major == 3:
    basestring = str

import json
from collections import OrderedDict

# Required when UnrealWriter is called from pmt-core, since an UE plugin
# has not the same structure as a Python module
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# With this we can import the module outside of unreal for applications like
# pmt_dump
try:
    import unreal
    from client_config import (
        SEQUENCER_CONFIG,
        CLIENT_CONFIG_PATH,
        override_default_config,
    )
    from scene_asset import SceneAsset
    from sequence_story import SequenceStory
    from ue_logging import log
except ModuleNotFoundError or ImportError as e:
    pass


class UEWriter(object):
    """Takes a PMT Project to write it in UE"""

    def __init__(self, input):
        """
        :param input: the source PMT project
        :type input: Project (PMTEntity), dict or str (path to a json file)
        """
        if isinstance(input, basestring):
            if not os.path.exists(input):
                raise IOError(
                    "File " + input + " could not be found"
                )  # Replace with FileNotFoundError if Py3
            json_file = open(input, "r")
            self.data = json.load(json_file)
            json_file.close()
        elif isinstance(input, dict):
            self.data = input
        else:  # consider it is a PMTEntity project
            self.data = input.to_pmt_dict()

        # Load client configuration if one is provided in the plugin's Resources folder
        config_filepath = unreal.Paths.combine(
            [unreal.Paths.project_plugins_dir(), CLIENT_CONFIG_PATH]
        )

        if config_filepath:
            override_default_config(config_filepath)

    def write(self, headless_mode=False):
        """Creates a Master LevelSequence in UE and populates it with shots and assets from the PMT Project."""
        # Parse the JSON to determine the sequences and tracks that need generating
        sequence_name = SEQUENCER_CONFIG.get(
            "MASTER_SEQUENCE", self.data.get("name", "Master_Sequence")
        )
        sequence_name.replace(" ", "_")

        script_components = self.data["children"]

        shots = {}
        assets = {}
        for component in script_components:
            name = component["name"]
            if component["type"] == "Sequence":
                shots[name] = component["assets"]
            elif component["type"] == "Asset":
                scene_asset = SceneAsset(
                    name, component["asset_type"], component["children"]
                )
                assets[name] = scene_asset

        # Sort shots by name
        shots = OrderedDict(sorted(shots.items(), key=lambda shot: shot[0]))

        # TODO: Display list of actions to be executed to user for approval
        response_ok = (
            unreal.UnrealWriterPythonAPI.display_sequencer_actions_dialog(
                sequence_name
            )
            if not headless_mode
            else True
        )

        if response_ok:
            log("Assembling Sequences for {}".format(sequence_name))

            master_sequence = SequenceStory(sequence_name)
            master_sequence.populate_master_sequence(shots, assets)

            # Save created Level Sequences
            unreal.EditorAssetLibrary.save_directory(
                SEQUENCER_CONFIG["SEQUENCE_DIR"]
            )
        else:
            log("Sequence assembly cancelled")


def assemble_sequence():
    """
    Callback function to open a file dialog and allow users to load a script breakdown JSON file and assemble
    a sequence through the Unreal Editor UI.
    """
    # Present file dialog for user to choose a JSON file
    picked_files = unreal.UnrealWriterPythonAPI.open_file_dialog(
        dialog_title="Select a PMT project file",
        file_types="JSON Source File|*.json",
    )

    if picked_files:
        log("Selected JSON file path: " + picked_files[0])
        do_assemble_sequence(picked_files[0], headless_mode=False)
    else:
        raise ValueError(
            "You need to select a PMT project file. Please start again"
        )


def do_assemble_sequence(file_path, headless_mode=True):
    """
    Assemble a sequence in the Unreal Sequence Editor using the structure provided by a client's JSON file.

    :param project_filepath: path to the json file containing the project's data in imgspc format
    :type project_filepath: str
    :param config_filepath: path to the Shotgun config file, containing the parameters of the target Shotgun server
    :type config_filepath: str
    :param headless_mode: flag indicating whether to supress Editor dialogs during sequence assembly
    :type config_filepath: bool
    """

    if not file_path:
        raise ValueError("No data provided to assemble a sequence.")

    ue_writer = UEWriter(file_path)
    ue_writer.write(headless_mode)
