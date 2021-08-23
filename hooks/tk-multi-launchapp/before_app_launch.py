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
# FIXME put this in environment PATH, Engineering? Can it walk up to the config folder and find it?
import os
import sys
# sys.path.append('C:\Users\shilmarsdottir\DEV\Pipeline\ssvfx_sg')
sys.path.append(os.path.normpath("//10.80.8.252/VFX_Pipeline/Pipeline/ssvfx_sg"))

from ss_config.hooks.tk_multi_launchapp.before_app_launch import SsBeforeAppLaunch


class BeforeAppLaunch(SsBeforeAppLaunch):
    """
    Hook to set up the system prior to app launch.
    set's up the environment variables for Nuke, Maya, Houdini and 3DsMax
    """
    pass
