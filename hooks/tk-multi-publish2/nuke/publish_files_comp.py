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
import itertools
from dd.runtime import api
api.load("frangetools")
import frangetools

HookBaseClass = sgtk.get_hook_baseclass()


class NukePublishFilesDDCompValidationPlugin(HookBaseClass):
    """
    Inherits from NukePublishFilesPlugin
    """
    def _build_dict(self, seq, key):
        """
        Creating a dictionary based on a key.

        :param seq: list of dictionaries
        :param key: dictionary key from which to create the dictionary
        :return: dict with information for that particular key
        """
        return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))


    def _framerange_to_be_published(self, item):
        """
        Since users have the option to render only a subset of frames,
        adding validation to check if the full frame range is being published.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        lss_path = item.properties['path']
        lss_data = frangetools.getSequence(lss_path)

        # Since lss_data will be a list of dictionaries,
        # building a dictionary from key value for the ease of fetching data.
        info_by_path = self._build_dict(lss_data, key="path")
        missing_frames = info_by_path.get(lss_path)['missing_frames']
        root = nuke.Root()

        # If there are no missing frames, then checking if the first and last frames match with root first and last
        # Checking with root because _sync_frame_range() will ensure root is up to date with shotgun
        if missing_frames:
            self.logger.error("Renders Mismatch! Incomplete renders on disk.")
            return False
        else:
            first_rendered_frame = info_by_path.get(lss_path)['frame_range'][0]
            last_rendered_frame = info_by_path.get(lss_path)['frame_range'][1]
            if (first_rendered_frame != root.firstFrame()) or (last_rendered_frame != root.lastFrame()):
                self.logger.error("Renders Mismatch! Incomplete renders on disk.")
                return False
            elif (first_rendered_frame > root.firstFrame()) or (last_rendered_frame > root.lastFrame()):
                self.logger.error("Renders Mismatch! Extra renders on disk.")
                return False
            return True


    def _sync_frame_range(self, item):
        """
        Checks whether frame range is in sync with shotgun.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        context = item.context
        entity = context.entity

        # checking entity validity since it can be invalid/empty in case of Project Level item
        if entity:
            frame_range_app = self.parent.engine.apps.get("tk-multi-setframerange")
            if not frame_range_app:
                # return valid for asset/sequence entities
                self.logger.warning("Unable to find tk-multi-setframerange app. "
                                    "Not validating frame range.")
                return True

            sg_entity_type = entity["type"]
            sg_filters = [["id", "is", entity["id"]]]
            in_field = frame_range_app.get_setting("sg_in_frame_field")
            out_field = frame_range_app.get_setting("sg_out_frame_field")
            fields = [in_field, out_field]

            # get the field information from shotgun based on Shot
            # sg_cut_in and sg_cut_out info will be on Shot entity, so skip in case this info is not present
            data = self.sgtk.shotgun.find_one(sg_entity_type, filters=sg_filters, fields=fields)
            if in_field not in data or out_field not in data:
                return True
            elif data[in_field] is None or data[out_field] is None:
                return True

            # compare if the frame range set at root level is same as the shotgun cut_in, cut_out
            root = nuke.Root()
            if root.firstFrame() != data[in_field] or root.lastFrame() != data[out_field]:
                self.logger.error("Frame range not synced with Shotgun.")
                return False
            return True
        return True

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
        if item.type != 'file.nuke':
            status = self._bbsize(item) and status
            status = self._framerange_to_be_published(item) and status
            if item.properties['node']['tank_channel'].value() == 'main':
                status = self._sync_frame_range(item) and status

        if not status:
            return status

        return super(NukePublishFilesDDCompValidationPlugin, self).validate(task_settings, item)

