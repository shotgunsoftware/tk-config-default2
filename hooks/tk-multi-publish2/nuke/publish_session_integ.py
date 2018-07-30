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
import nuke
import sgtk


HookBaseClass = sgtk.get_hook_baseclass()


class NukePublishSessionDDIntegValidationPlugin(HookBaseClass):
    """
    Inherits from NukePublishSessionPlugin
    """

    def _bbsize(self, item):
        """
        Checks for oversized bounding box for shotgun write nodes.

        :param item: Item to process
        :return:True if all the write nodes have bounding boxes within limits
        """
        node = item.properties['node']

        bb = node.bbox()  # write node bbox
        bb_height = bb.h()  # bbox height
        bb_width = bb.w()  # bbox width

        node_h = node.height()  # write node height
        node_w = node.width()  # write node width
        tolerance_h = (bb_height - node_h) / node_h * 100
        tolerance_w = (bb_width - node_w) / node_w * 100

        # Check if the size if over 5%(tolerance limit)
        if tolerance_h > 5 or tolerance_w > 5:
            self.logger.error(
                "Bounding Box resolution over the tolerance limit for write node.")
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
        # Segregating the checks, specifically for write nodes and for general nuke script
        if item.properties.get("node"):
            status = self._bbsize(item) and status

        if not status:
            return status

        return super(NukePublishSessionDDIntegValidationPlugin, self).validate(task_settings, item)

