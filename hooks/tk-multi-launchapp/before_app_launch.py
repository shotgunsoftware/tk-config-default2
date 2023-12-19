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
import sys

roots = [os.getenv('SSVFX_PIPELINE_DEV'), os.getenv('SSVFX_PIPELINE'), "//ssvfx_pipeline/pipeline_repo"]
for root_path in roots:
    if not root_path:
        continue
    sg_path = os.path.join(root_path, 'master', 'ssvfx_sg')
    if os.path.exists(sg_path):
        sys.path.append(os.path.normpath(sg_path))
        break

from ss_config.hooks.tk_multi_launchapp.before_app_launch import SsBeforeAppLaunch


class BeforeAppLaunch(SsBeforeAppLaunch):
    """
    Hook to set up the system prior to app launch.
    set's up the environment variables for Nuke, Maya, Houdini and 3DsMax
    """
    pass
