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
Hook that loads defines all the available actions, broken down by publish type. 
"""

import glob
import os
import re
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class MayaActions(HookBaseClass):
    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behaviour of things
            
    def _create_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """
        file_node = cmds.shadingNode('file', asTexture=True)

        has_frame_spec, path = self._find_first_frame(path)
        cmds.setAttr( "%s.fileTextureName" % file_node, path, type="string" )

        # TODO: check if there is a pre-2015 condition for this?
        if has_frame_spec:
            # setting the frame extension flag will create an expression to use
            # the current frame.
            cmds.setAttr("%s.useFrameExtension" % (file_node,), 1)
        return file_node

    def _create_udim_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a UDIM (Mari) texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """
        # create the normal file node:
        file_node = self._create_texture_node(path, sg_publish_data)
        if file_node:
            # path is a UDIM sequence so set the uv tiling mode to 3 ('UDIM (Mari)')
            cmds.setAttr("%s.uvTilingMode" % file_node, 3)
            # and generate a preview:
            mel.eval("generateUvTilePreview %s" % file_node)
        return file_node

    def _find_first_frame(self, path):
        has_frame_spec = False
        # replace any %0#d format string with a glob character. then just find
        # an existing frame to use. example %04d => *
        frame_pattern = re.compile("(%0\dd)")
        frame_match = re.search(frame_pattern, path)
        if frame_match:
            has_frame_spec = True
            frame_spec = frame_match.group(1)
            glob_path = path.replace(frame_spec, "*")
            frame_files = glob.glob(glob_path)
            if frame_files:
                return has_frame_spec, frame_files[0]
            else:
                return has_frame_spec, None
        return has_frame_spec, path

    def _create_image_plane(self, path, sg_publish_data):
        """
        Create a file texture node for a UDIM (Mari) texture

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard
            publish fields.
        :returns: The newly created file node
        """

        app = self.parent

        has_frame_spec, path = self._find_first_frame(path)
        if not path:
            self.parent.logger.error(
                "Could not find file on disk for published file path %s" %
                (path,)
            )
            return

        # create an image plane for the supplied path, visible in all views
        (img_plane, img_plane_shape) = cmds.imagePlane(
            fileName=path,
            showInAllViews=True
        )
        app.logger.debug(
            "Created image plane %s with path %s" %
            (img_plane, path)
        )

        if has_frame_spec:
            # setting the frame extension flag will create an expression to use
            # the current frame.
            cmds.setAttr("%s.useFrameExtension" % (img_plane_shape,), 1)
