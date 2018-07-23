# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk
from sgtk.platform.qt import QtGui

from dd.runtime import api
api.load('frangetools')
import frangetools

HookBaseClass = sgtk.get_hook_baseclass()


class MayaPublishFilesDDIntegValidationPlugin(HookBaseClass):
    """
    Inherits from MayaPublishPlugin
    """

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        desc = super(MayaPublishFilesDDIntegValidationPlugin, self).description

        return desc + "<br><br>" + """
        Validation checks before a file is published.
        """

    def _build_dict(self, seq, key):
        """
        Creating a dictionary based on a key.

        :param seq: list of dictionaries
        :param key: dictionary key from which to create the dictionary
        :return: dict with information arranged based on that particular key
        """
        return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))

    def _framerange_of_sequence(self, item):
        """
        Since users have the option to render only a subset of frames,
        adding validation to check if the full frame range is being published.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        lss_path = item.properties['path']
        lss_data = frangetools.getSequence(lss_path)

        info_by_path = self._build_dict(lss_data, key="path")
        missing_frames = info_by_path.get(lss_path)['missing_frames']

        if missing_frames:
            self.logger.error("Incomplete playblast! All the frames are not the playblast.")
            return False
        else:
            # If there are no missing frames, checking if the start and end frames match with playblast settings.
            # This is being directly checked with playblast settings in the scene since
            # _sync_frame_range_with_shotgun() will ensure playblast frame range is synced with shotgun
            import pymel.core as pm
            playback_start = pm.playbackOptions(q=True, minTime=True)
            playback_end = pm.playbackOptions(q=True, maxTime=True)
            collected_playblast_firstframe = info_by_path.get(lss_path)['frame_range'][0]
            collected_playblast_lastframe = info_by_path.get(lss_path)['frame_range'][1]
            if (collected_playblast_firstframe != playback_start) or (collected_playblast_lastframe != playback_end):
                self.logger.error("Incomplete playblast! All the frames are not in the playblast.")
                return False
        return True


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        status = True
        
        # Checks for the scene file, i.e if the item is not a sequence or a cache file
        if item.properties['is_sequence']:
            sequences = self._framerange_of_sequence(item)
            status = sequences and status

        if not status:
            return status

        return super(MayaPublishFilesDDIntegValidationPlugin, self).validate(task_settings, item)
