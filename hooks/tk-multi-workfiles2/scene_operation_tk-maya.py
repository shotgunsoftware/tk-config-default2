# Copyright (c) 2015 Shotgun Software Inc.
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

HookClass = sgtk.get_hook_baseclass()

from dd.runtime import api
api.load("preferences")
import preferences

class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """

        if operation == "current_path":
            # return the current scene path
            return cmds.file(query=True, sceneName=True)
        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            cmds.file(new=True, force=True)
            cmds.file(file_path, open=True, force=True)

            # getting fields from file path because context.as_template_fields() doesn't contain {name}, {version}
            file_template = context.sgtk.template_from_path(file_path)
            fields = file_template.get_fields(file_path)

            render_temp = self.get_render_template(context)
            frame_sq_key = context.sgtk.template_keys['SEQ']    # Can 'SEQ' change?

            # get show resolution
            indiapipeline_prefs = preferences.Preferences(package="indiapipeline")
            try:
                fields.update({"width": indiapipeline_prefs["show_resolution"]["width"],
                               "height": indiapipeline_prefs["show_resolution"]["height"],
                               "output": "LAYERPLACEHOLDER"})   # output is alphanumeric; replace with token <Layer>
            except KeyError as ke:
                # logging?
                print "Unable to find {} in indiapipeline preferences. Not setting render defaults.".format(ke)
            else:
                fields.pop("extension")                         # remove ma as extension to apply default img ext
                render_path = render_temp.apply_fields(fields).replace("LAYERPLACEHOLDER", "<Layer>")
                self.set_render_defaults(fields, render_path, frame_sq_key)
                self.set_vray_settings(fields, render_path, frame_sq_key)

        elif operation == "save":
            # save the current scene:
            cmds.file(save=True)
        elif operation == "save_as":
            # first rename the scene as file_path:
            cmds.file(rename=file_path)

            # Maya can choose the wrong file type so
            # we should set it here explicitly based
            # on the extension
            maya_file_type = None
            if file_path.lower().endswith(".ma"):
                maya_file_type = "mayaAscii"
            elif file_path.lower().endswith(".mb"):
                maya_file_type = "mayaBinary"

            # save the scene:
            if maya_file_type:
                cmds.file(save=True, force=True, type=maya_file_type)
            else:
                cmds.file(save=True, force=True)

        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while cmds.file(query=True, modified=True):
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your scene?",
                                                 "Your scene has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes|QtGui.QMessageBox.No|QtGui.QMessageBox.Cancel)

                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    scene_name = cmds.file(query=True, sn=True)
                    if not scene_name:
                        cmds.SaveSceneAs()
                    else:
                        cmds.file(save=True)

            # do new file:
            cmds.file(newFile=True, force=True)
            return True

    def get_render_template(self, context):
        fields = context.as_template_fields()
        templates = context.sgtk.templates
        entity_type = context.entity["type"]

        if entity_type == "Asset":
            if "Shot" in fields:
                render_temp = templates["tk-maya_shot_asset_work_render"]
            elif "Sequence" in fields:
                render_temp = templates["tk-maya_sequence_asset_work_render"]
            else:
                render_temp = templates["tk-maya_project_asset_work_render"]
        elif entity_type == "Shot":
            render_temp = templates["tk-maya_shot_work_render"]
        elif entity_type == "Sequence":
            render_temp = templates["tk-maya_sequence_work_render"]
        else:  # elif type == "Project": (?)
            render_temp = templates["tk-maya_project_work_render"]

        return render_temp

    def set_render_defaults(self, fields, render_path, frame_sq_key):
        # set resolution
        self.unlock_and_set_attr("defaultResolution.aspectLock", False, lock=True)
        self.unlock_and_set_attr("defaultResolution.width", fields["width"], lock=True)
        self.unlock_and_set_attr("defaultResolution.height", fields["height"], lock=True)

        prefix, ext = self.split_prefix_ext(render_path, frame_sq_key)

        # setMayaSoftwareImageFormat: mel script that ships with Maya (used internally)
        # sets image format for software/hardware renderers using extension string safely
        mel.eval("setMayaSoftwareImageFormat {}".format(ext))

        # set file prefix
        self.unlock_and_set_attr("defaultRenderGlobals.imageFilePrefix", prefix, type="string", lock=True)

        # ensure frame/animation ext = name.#.ext
        self.set_enum_attr("defaultRenderGlobals.outFormatControl", "As Output Format", lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.animation", True, lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.putFrameBeforeExt", True, lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.extensionPadding", int(frame_sq_key.format_spec), lock=True)
        self.set_enum_attr("defaultRenderGlobals.periodInExt", "Period in Extension", lock=True)

    def set_vray_settings(self, fields, render_path, frame_sq_key):
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            return
        vray_nodes = cmds.ls(type="VRaySettingsNode")
        if not vray_nodes:
            return
        for node in vray_nodes:
            # set resolution
            self.unlock_and_set_attr("{}.aspectLock".format(node), False, lock=True)
            self.unlock_and_set_attr("{}.width".format(node), fields["width"], lock=True)
            self.unlock_and_set_attr("{}.height".format(node), fields["height"], lock=True)

            prefix, ext = self.split_prefix_ext(render_path, frame_sq_key)

            self.unlock_and_set_attr("{}.imageFormatStr".format(node), ext, type="string", lock=True)
            self.unlock_and_set_attr("{}.fileNamePrefix".format(node), prefix, type="string", lock=True)

            # ensure frame/animation ext = name.#.ext
            self.set_enum_attr("{}.animType".format(node), "Standard", lock=True)
            self.unlock_and_set_attr("{}.fileNamePadding".format(node), int(frame_sq_key.format_spec), lock=True)

    # move to a maya utils location?
    def set_enum_attr(self, attribute_full, value, lock=False):
        node, attribute_short = attribute_full.split('.', 1)
        enum_string = cmds.attributeQuery(attribute_short, node=node, listEnum=True)[0]
        enum_list = enum_string.split(':')
        enum_dict = {}; index=0
        for enum_item in enum_list:
            if '=' in enum_item:
                index = enum_item.split('=')[1]
                enum_dict[enum_item.split('=')[0]] = index
            else:
                enum_dict[enum_item] = index
            index += 1

        self.unlock_and_set_attr(attribute_full, enum_dict[value], lock=lock)

    def unlock_and_set_attr(self, attribute, value, type=None, lock=False):
        cmds.setAttr(attribute, lock=False)
        if type:
            cmds.setAttr(attribute, value, type=type, lock=lock)
        else:
            cmds.setAttr(attribute, value, lock=lock)

    def split_prefix_ext(self, render_path, frame_sq_key):
        prefix, ext = os.path.splitext(render_path)
        ext = ext.lstrip('.')
        prefix = prefix.replace("." + frame_sq_key.default, "")

        return prefix, ext
