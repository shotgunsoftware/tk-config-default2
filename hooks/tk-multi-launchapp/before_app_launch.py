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
sg_path = None
if os.getenv('SSVFX_PIPELINE_DEV') and os.path.exists(os.getenv('SSVFX_PIPELINE_DEV')):
    sg_path = os.path.join(os.getenv('SSVFX_PIPELINE_DEV'), 'Pipeline', 'ssvfx_sg')
    if os.path.exists(sg_path):
        sys.path.append(os.path.normpath(sg_path))
        print('adding ssvfx_sg from dev: %s' % sg_path)
    else:
        sg_path = None
if sg_path is None:
    # FIXME put this in environment PATH, Engineering?
    sys.path.append(os.path.normpath("//10.80.8.252/VFX_Pipeline/Pipeline/ssvfx_sg"))

from ss_config.hooks.tk_multi_launchapp.before_app_launch import SsBeforeAppLaunch

class BeforeAppLaunch(SsBeforeAppLaunch):
    """
    Hook to set up the system prior to app launch.
    set's up the environment variables for Nuke, Maya, Houdini and 3DsMax
    """
    pass
