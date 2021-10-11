# Copyright (c) 2014 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
# ### OVERRIDDEN IN SSVFX_SG ###
from ss_config.hooks.tk_mari_projectmanager.get_project_creation_args import SsGetArgsHook


class GetArgsHook(SsGetArgsHook):
    """
    Hook used by the create Mari project app to get the arguments that should be used
    when creating a new project.
    """
    pass
