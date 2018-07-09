# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that controls various codec settings when submitting items for review
"""
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class CodecSettings(HookBaseClass):

    def get_quicktime_settings(self, **kwargs):
        """
        Allows modifying default codec settings for Quicktime generation.
        Returns a dictionary of settings to be used for the Write Node that generates
        the Quicktime in Nuke.
        """
        settings = {}
        settings["file_type"] = "mov"
        settings["mov64_format"] = "default"
        settings["mov64_codec"] = "jpeg"
        settings["mov64_write_timecode"] = True
        settings["mov64_bitrate"] = 400000
        settings["mov64_bitrate_tolerance"] = 28000
        settings["mov64_quality_min"] = 1
        settings["mov64_quality_max"] = 2

        return settings
