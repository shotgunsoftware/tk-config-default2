# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook
This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
import tank
import sgtk

class BeforeAppLaunch(tank.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(self, app_path, app_args, version, engine_name, **kwargs):

        if engine_name == "tk-nuke":
            # Get current project directory
            root_location = self.parent.tank.roots.get('primary')

            # Defining location of Nuke repository
            repo_location = '00_pipeline/nuke/repository'

            # Combining root_location and repo_location to make the path
            path = os.path.join(root_location,repo_location)

            # Appending NUKE_PATH environment to existing environment
            tank.util.append_path_to_env_var("NUKE_PATH", path)
