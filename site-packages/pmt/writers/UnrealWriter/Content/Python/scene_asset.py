# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import unreal

from client_config import SEQUENCER_CONFIG
from ue_logging import log

class SceneAsset(object):
    """Represents an asset created as part of a shot sequence"""

    def __init__(self, name, asset_type, children = []): 
        self.name = name.replace(" ", "_")
        self.asset_type = asset_type
        self.children = children
        self._create_asset_folder()

    def _create_asset_folder(self):

        for department, tasks in SEQUENCER_CONFIG['DEPARTMENT_TASK_MAPPINGS'].items():
            # Create a folder for each task type
            dept_folder = SEQUENCER_CONFIG['ASSET_PATH'].format(
                asset_type = self.asset_type,
                asset_name = self.name,
                department = department,
            )
            unreal.EditorAssetLibrary.make_directory(dept_folder)

            if tasks:
                # Create a folder for each subtask (e.g. Material under the Surfacing task)
                for task in tasks:
                    task_folder = unreal.Paths.combine([dept_folder, task])
                    unreal.EditorAssetLibrary.make_directory(task_folder)