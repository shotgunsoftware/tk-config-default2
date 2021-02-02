# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import json
import os

import unreal

from ue_logging import log

CLIENT_CONFIG_PATH = "UnrealWriter/Resources/client_config.json"

# This defines a default configuration for the Unreal sequencer
# which can be overridden with a JSON file.
SEQUENCER_CONFIG = {
    "MASTER_SEQUENCE": "S1E1",
    # TODO: This is currently referenced in the PMT, should be removed and for the Writer to simply use "SEQUENCE_PATH"
    "SEQUENCE_DIR": "/Game/shots/",
    # Shots
    "SEQUENCE_PATH": "/Game/shots/{shot}/",
    "SEQUENCE_NAME": "S1E1_{shot}",
    "SUBSCENE_TRACKS": ["anim", "lighting", "environment", "FX"],
    "SUBSEQUENCE_PATH": "/Game/shots/{shot}/{department}",
    "SUBSEQUENCE_NAME": "S1E1_{shot}_{department}",
    "SHOT_LENGTH": 30,
    # Assets
    "ASSET_PATH": "/Game/assets/{asset_type}/{asset_name}/{department}",
    "DEPARTMENT_TASK_MAPPINGS": {
        "rig": [],
        "model": [],
        "surface": ["texture", "material"],
    },
    "DUMMY_ACTOR_ASSET": "/UnrealWriter/Assets/Character.Character",
    "FRAME_RATE": 24,
    "PRE_ROLL_FRAMES": 24,
    # Custom Camera Actor
    "CAMERA_ACTOR_CLASS": unreal.CineCameraActor,
    "DEFAULT_EPISODE_NAME": "S01E01",
    "DEFAULT_SEQUENCE_NAME": "S01E01_0010",
    "DEFAULT_SHOT_TYPE": "shot",
}


def override_default_config(client_config_path):
    """
    Overrides the default settings for sequence assembly using a JSON file with the client's custom config.
    """
    if not os.path.exists(client_config_path):
        log(
            "Client config at path {} not found, using defaults instead.".format(
                client_config_path
            )
        )
        return

    log("Loading client configuration {}".format(client_config_path))
    with open(client_config_path, "r") as json_file:
        data = json.load(json_file)

    SEQUENCER_CONFIG.update(data)
