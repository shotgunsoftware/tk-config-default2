# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.


from ss_config.hooks.tk_multi_publish2.houdini.collector import SsBasicSceneCollector


class BasicSceneCollector(SsBasicSceneCollector):
    """
    Collector that operates on the maya session. Should inherit from the basic
    collector hook.
    """
    pass
