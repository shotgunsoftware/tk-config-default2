# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class DDSettings(HookBaseClass):
    def get_resolution(self):
        """
        Returns the resolution that should be used when rendering the quicktime.

        :returns: tuple with (width, height)
        """
        return 1920, 1080

    def setup_quicktime_node(self, write_node):
        """
        Allows modifying settings for Quicktime generation.

        :param write_node: The nuke write node used to generate the quicktime that is being uploaded.
        """
        write_node["file_type"].setValue("mov")
        write_node["mov64_format"].setValue("default")
        write_node["mov64_codec"].setValue("jpeg")
        write_node["mov64_write_timecode"].setValue(True)
        write_node["mov64_bitrate"].setValue(400000)
        write_node["mov64_bitrate_tolerance"].setValue(28000)
        write_node["mov64_quality_min"].setValue(1)
        write_node["mov64_quality_max"].setValue(2)
