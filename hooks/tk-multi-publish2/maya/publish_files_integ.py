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
from dd.runtime import api
api.load('frangetools')
import frangetools

HookBaseClass = sgtk.get_hook_baseclass()

GROUP_NODES = ['WORLDSCALE',
               'SET_TO_WORLD',
               'TRACK_GEO']

CAMERA_NAME = 'CAM'

DEFAULT_CAMERAS = ['persp',
                   'top',
                   'front',
                   'side']


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


    def _sync_frame_range_with_shotgun(self, item):
        """
        Checks whether frame range is in sync with shotgun.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        context = item.context
        entity = context.entity

        # checking entity validity
        if entity:

            frame_range_app = self.parent.engine.apps.get("tk-multi-setframerange")

            sg_entity_type = entity["type"]
            sg_filters = [["id", "is", entity["id"]]]
            in_field = frame_range_app.get_setting("sg_in_frame_field")
            out_field = frame_range_app.get_setting("sg_out_frame_field")
            fields = [in_field, out_field]

            # get the field information from shotgun based on Shot
            # sg_cut_in and sg_cut_out info will be on Shot entity, so skip in case this info is not present
            # or if the sg_head_in or sg_tail_out is empty, skip the check
            data = self.sgtk.shotgun.find_one(sg_entity_type, filters=sg_filters, fields=fields)
            if in_field not in data or out_field not in data:
                return True
            elif in_field is None or out_field is None:
                return True

            # Check if playback_start or animation_start is not in sync with shotgun
            # Similarly if animation_start or animation_start is not in sync with shotgun
            import pymel.core as pm
            playback_start = pm.playbackOptions(q=True, minTime=True)
            playback_end = pm.playbackOptions(q=True, maxTime=True)
            animation_start = pm.playbackOptions(q=True, animationStartTime=True)
            animation_end = pm.playbackOptions(q=True, animationEndTime=True)
            if playback_start != data[in_field] or playback_end != data[out_field]:
                self.logger.error("Frame range not synced with Shotgun.")
                return False
            if animation_start != data[in_field] or animation_end != data[out_field]:
                self.logger.error("Frame range not synced with Shotgun.")
                return False
            return True
        return True


    def _extra_nodes_outside_track_geo(self):
        """
        Check for nodes, apart from groups and camera lying outside of TRACK_GEO node
        :return: True if yes false otherwise
        """
        children = cmds.listRelatives('TRACK_GEO', c=True)
        # Subtracting group nodes, cameras and child nodes of TRACK_GEO from the list of dag nodes.
        # This is to get extra nodes present outside TRACK_GEO
        if children:
            extras = list(set(cmds.ls(tr=True, dag=True)) - set(GROUP_NODES) - set(cmds.listCameras()) - set(children))
        else:
            extras = list(set(cmds.ls(tr=True, dag=True)) - set(GROUP_NODES) - set(cmds.listCameras()))

        if extras:
            self.logger.error("Nodes present outside TRACK_GEO.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Show the extra nodes",
                                      "text": "Nodes outside TRACK_GEO:\n{}".format("\n".join(extras))
                                  }
                              }
                              )
            return False
        return True


    def _track_geo_locked_channels(self):
        """Check for locked channels for all nodes under the group TRACK_GEO.
            :param:
                nodes: list of nodes under TRACK_GEO
            :return: True if yes false otherwise
        """
        children = cmds.listRelatives('TRACK_GEO', c=True)
        if children:
            locked = ""
            for node in children:
                # For each node, list out attributes which are locked
                lock_per_node = cmds.listAttr(node, l=True)
                if lock_per_node:
                    locked += "\n" + node + "  --->  " + ", ".join(lock_per_node)
            # If there are locked channels, error message with node name and locked attribute name(s).
            if locked:
                self.logger.error("Locked channels detected.",
                                  extra={
                                      "action_show_more_info": {
                                          "label": "Show Info",
                                          "tooltip": "Show the node and locked channels",
                                          "text": "Locked channels:\n{}".format(locked)
                                      }
                                  }
                                  )
                return False
            return True
        return True


    def _track_geo_child_naming(self):
        """Checks if the name of nodes under TRACK_GEO are prefixed with 'integ_'.
            :param:
                track_geo: nodes under TRACK_GEO
            :return: True if yes false otherwise
        """
        # Nodes under TRACK_GEO group
        children = cmds.listRelatives('TRACK_GEO', c=True)
        error_names = ""
        # if there are nodes under TRACK_GEO, check for one without prefix "integ_"
        if children:
            for child in children:
                # If the name doesn't start with integ_ add node name to errorNames
                if child[:6] != "integ_":
                    error_names += "\n" + child
        if error_names:
            self.logger.error("Incorrect Naming! Node name should start with integ_.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Show the node with incorrect naming",
                                      "text": "Nodes with incorrect naming:\n{}".format(error_names)
                                  }
                              }
                              )
            return False
        return True


    def _check_hierarchy(self, group_nodes):
        """Checks the hierarchy of group nodes in the scene.
            :param:
                group_nodes: the list of nodes in the scene
            :return: True if yes false otherwise
        """
        for name in range(len(group_nodes) - 1):
            # Listing children of group nodes
            children = cmds.listRelatives(group_nodes[name], c=True)
            # group_nodes is arranged in hierarchical order i.e. the next node should be the child of previous
            if children and (group_nodes[name + 1] in children):
                if name == 'SET_TO_WORLD' and 'CAM' in children:
                    continue
            else:
                hierarchy = "WORLDSCALE\n|__SET_TO_WORLD\n" + "    " + "|__TRACK_GEO\n" + "    " + "|__CAM"
                self.logger.error("Incorrect hierarchy.",
                                  extra={
                                      "action_show_more_info": {
                                          "label": "Show Info",
                                          "tooltip": "Show the required hierarchy",
                                          "text": "Required hierarchy:\n\n{}".format(hierarchy)
                                      }
                                  }
                                  )
                return False
        return True


    def _connected_image_plane(self):
        camshape = cmds.listRelatives(CAMERA_NAME, s=True, c=True)[0]
        connections = cmds.listConnections(camshape + '.imagePlane', source=True, type='imagePlane')
        if not connections:
            self.logger.error("Image plane not attached to CAM.")
            return False
        return True


    def _camera_naming(self):
        """Checks the naming of the camera.
            :param:
                group_nodes: The list of nodes that should be in the scene. This will be
                used to check node hierarchy once camera naming is validated.
            :return: True if yes false otherwise
        """
        # Look for all the cameras present in the scene
        all_cameras = cmds.listCameras()
        # Remove the default_cameras from the list
        main_cam = list(set(all_cameras) - set(DEFAULT_CAMERAS))
        if main_cam:
            if len(main_cam) > 1:
                # Checking if more than one CAM present
                self.logger.error("More the one camera detected. Only CAM should be present.")
                return False
            elif main_cam[0] != CAMERA_NAME:
                # Validating camera name
                self.logger.error("Incorrect camera name! Should be CAM.")
                return False
        else:
            self.logger.error("Camera (CAM) not present in the scene.")
            return False
        return True


    def _node_naming(self, groups):
        """Checking if the established group node names have not been tampered with.
            :param:
                group_nodes: group nodes to be present in the scene
                groups: group nodes that are actually present
            :return: True if yes false otherwise
        """
        # Check for extra group nodes apart from the ones in group_nodes
        extras = list(set(groups) - set(GROUP_NODES))
        # check for any group nodes apart from the once mentioned
        if extras:
            self.logger.error("Incorrect naming or extra group nodes present in the scene.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Show the conflicting group nodes",
                                      "text": "Please check the group nodes:\n{}".format("\n".join(extras)) +
                                              "\n\nOnly following group nodes should be present:\n{}".format(
                                                  "\n".join(GROUP_NODES))
                                  }
                              }
                              )
            return False
        # check if any of the required group nodes are missing
        elif not set(GROUP_NODES).issubset(set(groups)):
            self.logger.error("Please ensure all the group nodes are present.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Group nodes",
                                      "text": "Following group nodes should be present:\n{}".format(
                                          "\n".join(GROUP_NODES))
                                  }
                              }
                              )
            return False
        return True


    @staticmethod
    def _is_group(node=None):
        """Check for all the group nodes present in the scene.
            :param:
                node: all the nodes in the scene
            :return: True if yes false otherwise
        """
        if cmds.nodeType(node) != "transform":
            return False

        children = cmds.listRelatives(node, c=True)
        if not children:
            return True

        for c in children:
            if cmds.nodeType(c) != 'transform':
                return False
        else:
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
        all_dag_nodes = cmds.ls(dag=True, sn=True)
        groups = [g for g in all_dag_nodes if self._is_group(g)]

        status = True
        # Checks for the scene file, i.e if the item is not a sequence or a cache file
        if item.type == "file.maya":
            nodes = self._node_naming(groups) and \
                    self._check_hierarchy(groups) and \
                    self._track_geo_child_naming() and \
                    self._track_geo_locked_channels()and \
                    self._extra_nodes_outside_track_geo() and \
                    self._sync_frame_range_with_shotgun(item)
            cam = self._camera_naming() and self._connected_image_plane()
            status = nodes and cam and status
        elif item.properties['is_sequence']:
            sequences = self._framerange_of_sequence(item)
            status = sequences and status

        if not status:
            return status

        return super(MayaPublishFilesDDIntegValidationPlugin, self).validate(task_settings, item)
