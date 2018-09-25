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

MAYA_TIME_UNITS = {15: 'game',
                   24: 'film',
                   25: 'pal',
                   30: 'ntsc',
                   48: 'show',
                   50: 'palf',
                   60: 'ntscf'}
LAYER_PLACEHOLDER = "LAYERPLACEHOLDER"
ARNOLD_DISPLAY_DRIVER = "defaultArnoldDisplayDriver"

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

            self.set_show_preferences(file_path, context)

        elif operation == "save":
            # save the current scene:
            cmds.file(save=True)
        elif operation == "save_as":
            # first rename the scene as file_path:
            cmds.file(rename=file_path)
            self.set_show_preferences(file_path, context)

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

    def set_show_preferences(self, file_path, context):
        fields = context.as_template_fields()

        # getting fields from file path because
        # context.as_template_fields() doesn't contain {name}, {version}
        file_template = context.sgtk.template_from_path(file_path)
        if not file_template:
            warning_message = "Current file path doesn't conform to Shotgun template. " \
                              "Not setting show default settings."
            self.parent.logger.warning(warning_message)
            QtGui.QMessageBox.warning(None, "Show defaults not set", warning_message)
            return

        fields.update(file_template.get_fields(file_path))
        render_temp = self.get_render_template(context)
        frame_sq_key = context.sgtk.template_keys['SEQ']  # Can 'SEQ' change?

        show_prefs = preferences.Preferences(pref_file_name="show_preferences.yaml",
                                             role=fields.get("Step"),
                                             seq_override=fields.get("Sequence"),
                                             shot_override=fields.get("Shot"))
        # set fps
        try:
            fps = show_prefs["show_settings"]["fps"]
        except KeyError as ke:
            warning_message = "Unable to find {} in show preferences. " \
                              "Not setting fps.".format(ke)
            self.parent.logger.warning(warning_message)
            QtGui.QMessageBox.warning(None, "FPS not set", warning_message)
        else:
            try:
                try:
                    cmds.currentUnit(time=MAYA_TIME_UNITS[fps])
                except KeyError:
                    # unable to find the fps value in our lookup dict.
                    # try setting the actual value itself, in case Maya version is >=2017
                    cmds.currentUnit(time="{}fps".format(fps))
            except RuntimeError as runtime_error:
                self.parent.logger.error(runtime_error)
                QtGui.QMessageBox.warning(None,
                                          "FPS not set",
                                          "RuntimeError: {}.\n"
                                          "See script editor for details.".format(runtime_error))

        # get resolution and set render defaults
        try:
            fields.update({"width": show_prefs["show_settings"]["resolution"]["width"],
                           "height": show_prefs["show_settings"]["resolution"]["height"],
                           "output": LAYER_PLACEHOLDER})    # output is alphanumeric
                                                            # replace with token <Layer>
        except KeyError as ke:
            warning_message = "Unable to find {} in show preferences. " \
                              "Not setting render defaults.".format(ke)
            self.parent.logger.warning(warning_message)
            QtGui.QMessageBox.warning(None, "Render defaults not set", warning_message)
        else:
            fields.pop("extension")  # remove ma as extension to apply default img ext
            render_path = render_temp.apply_fields(fields)
            maya_prefs = preferences.Preferences(pref_file_name="maya_preferences.yaml",
                                                 role=fields.get("Step"),
                                                 seq_override=fields.get("Sequence"),
                                                 shot_override=fields.get("Shot"))
            self.set_render_settings(fields=fields,
                                     placeholder_render_path=render_path,
                                     frame_sq_key=frame_sq_key,
                                     prefs=maya_prefs)

    def set_render_settings(self, **kwargs):
        renderers = ['default', 'vray', 'arnold']
        for renderer in renderers:
            setter_func = getattr(self, "set_{}_render_settings".format(renderer))
            setter_func(**kwargs)

    def get_render_template(self, context):
        """
        Get template for path where the render should be saved.

        :param context: Context
                        The context of current operation.

        :return:        Template
                        Shotgun template for render path according to current context.
        """
        templates = context.sgtk.templates

        template_exp = "{engine_name}_{env_name}_work_render"
        template_name = self.parent.resolve_setting_expression(template_exp)
        render_temp = templates.get(template_name)

        return render_temp

    def apply_overrides(self, node, enum_overrides, other_overrides):
        """
        Helper function to set attribute overrides for a maya node.

        :param node:            String
                                Name of maya node
        :param enum_overrides:  dict
                                Should contain items of the form
                                    <attribute_name>: <value>
                                for only enum attributes
        :param other_overrides: dict
                                Should contain items of the form
                                    <attribute_name>: {"value": <value>,
                                                       "type": <type_recognised_by_maya>}
                                for any non-enum attributes
        """
        for key, value in enum_overrides.items():
            self.set_enum_attr("{}.{}".format(node, key), value, lock=True)
        for attr_name, value_dict in other_overrides.items():
            self.unlock_and_set_attr("{}.{}".format(node, attr_name), value_dict.get("value"),
                                     attribute_type=value_dict.get("type"), lock=True)

    def set_default_render_settings(self, fields, placeholder_render_path, frame_sq_key, prefs):
        """
        Set render file name and path, image format and image resolution for default Maya renderers.
        Also, apply any overrides passed in prefs.

        :param fields:          dict
                                Template fields used to create the final render path
        :param render_path:     String
                                Complete path to the rendered image
        :param frame_sq_key:    SequenceKey
                                Object containing the number format for the frame sequence
        :param prefs:           Preferences
                                Object containing configurable overrides for any attribute

        :returns:               None
        """
        render_path = placeholder_render_path.replace(LAYER_PLACEHOLDER, "<RenderLayer>")
        # set resolution
        self.unlock_and_set_attr("defaultResolution.aspectLock", False, lock=True)
        self.unlock_and_set_attr("defaultResolution.width", fields["width"], lock=True)
        self.unlock_and_set_attr("defaultResolution.height", fields["height"], lock=True)

        prefix, ext = self.split_prefix_ext(render_path, frame_sq_key)

        # setMayaSoftwareImageFormat: mel script that ships with Maya (used internally)
        # sets image format for software/hardware renderers using extension string safely
        mel.eval("setMayaSoftwareImageFormat {}".format(ext))

        # set file prefix
        self.unlock_and_set_attr("defaultRenderGlobals.imageFilePrefix", prefix,
                                 attribute_type="string", lock=True)

        # ensure frame/animation ext = name.#.ext
        self.set_enum_attr("defaultRenderGlobals.outFormatControl", "As Output Format", lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.animation", True, lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.putFrameBeforeExt", True, lock=True)
        self.unlock_and_set_attr("defaultRenderGlobals.extensionPadding",
                                 int(frame_sq_key.format_spec), lock=True)
        self.set_enum_attr("defaultRenderGlobals.periodInExt", "Period in Extension", lock=True)

        # set overrides from preferences, if any exist
        enum_overrides = prefs.get("sgtk_render_settings", {}).get("default", {}).get("enum_attr", {})
        other_overrides = prefs.get("sgtk_render_settings", {}).get("default", {}).get("other", {})
        self.apply_overrides("defaultRenderGlobals", enum_overrides, other_overrides)

    def set_vray_render_settings(self, fields, placeholder_render_path, frame_sq_key, prefs):
        """
        Set render file name and path, image format and image resolution
        and some other default settings for any vray nodes in the maya file.
        Also, apply any overrides passed in prefs.

        :param fields:          dict
                                Template fields used to create the final render path
        :param render_path:     String
                                Complete path to the rendered image
        :param frame_sq_key:    SequenceKey
                                Object containing the number format for the frame sequence
        :param prefs:           Preferences
                                Object containing configurable overrides for any attribute

        :returns:               None
        """
        if not cmds.pluginInfo("vrayformaya", query=True, loaded=True):
            return
        vray_nodes = cmds.ls(type="VRaySettingsNode")
        if not vray_nodes:
            return

        render_path = placeholder_render_path.replace(LAYER_PLACEHOLDER, "<Layer>")
        # get overrides from preferences, if any exist
        enum_overrides = prefs.get("sgtk_render_settings", {}).get("vray", {}).get("enum_attr", {})
        other_overrides = prefs.get("sgtk_render_settings", {}).get("vray", {}).get("other", {})

        for node in vray_nodes:
            # set resolution
            self.unlock_and_set_attr("{}.aspectLock".format(node), False, lock=True)
            self.unlock_and_set_attr("{}.width".format(node), fields["width"], lock=True)
            self.unlock_and_set_attr("{}.height".format(node), fields["height"], lock=True)

            prefix, ext = self.split_prefix_ext(render_path, frame_sq_key)

            self.unlock_and_set_attr("{}.imageFormatStr".format(node), ext,
                                     attribute_type="string", lock=True)
            self.unlock_and_set_attr("{}.fileNamePrefix".format(node), prefix,
                                     attribute_type="string", lock=True)

            # ensure frame/animation ext = name.#.ext
            self.set_enum_attr("{}.animType".format(node), "Standard", lock=True)
            self.unlock_and_set_attr("{}.fileNamePadding".format(node),
                                     int(frame_sq_key.format_spec), lock=True)

            # set prefs overrides
            self.apply_overrides(node, enum_overrides, other_overrides)

    def set_arnold_render_settings(self, fields, placeholder_render_path, frame_sq_key, prefs):
        """
        Set render file name and path, image resolution, format and compression,
        and some other default settings for any arnold driver nodes in the maya file.

        Also, apply any overrides passed in prefs.
        """
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            return
        arnold_aov_driver_nodes = cmds.ls(type="aiAOVDriver")
        if not arnold_aov_driver_nodes:
            return
        if ARNOLD_DISPLAY_DRIVER in arnold_aov_driver_nodes:
            arnold_aov_driver_nodes.remove(ARNOLD_DISPLAY_DRIVER)

        # get overrides from preferences, if any exist
        enum_overrides = prefs.get("sgtk_render_settings", {}).get("arnold", {}).get("enum_attr", {})
        other_overrides = prefs.get("sgtk_render_settings", {}).get("arnold", {}).get("other", {})

        for node in arnold_aov_driver_nodes:
            current_ext = cmds.getAttr("{}.ai_translator".format(node))
            prefix, ext = self.split_prefix_ext(placeholder_render_path, frame_sq_key)

            if current_ext != "deepexr":
                # forcefully inherit file path from render globals
                self.unlock_and_set_attr("{}.prefix".format(node), '',
                                         attribute_type="string", lock=True)
                # apply default settings
                self.unlock_and_set_attr("{}.ai_translator".format(node), ext,
                                         attribute_type="string", lock=True)
                if ext == "exr":
                    # if not exr, assume other settings are specified as overrides
                    self.set_enum_attr("{}.exrCompression".format(node), "zips", lock=True)
            else:
                self.unlock_and_set_attr("{}.prefix".format(node),
                                         prefix.replace(LAYER_PLACEHOLDER, "<RenderLayer>Deep"),
                                         attribute_type="string", lock=True)
            self.unlock_and_set_attr("{}.mergeAOVs".format(node), True, lock=True)
            self.unlock_and_set_attr("{}.tiled".format(node), False, lock=True)

            # apply overrides from prefs
            self.apply_overrides(node, enum_overrides, other_overrides)

    # move to a maya utils location?
    @staticmethod
    def set_enum_attr(attribute_full, value, lock=False):
        """
        Set enum value for a maya node attribute using its string representation.

        :param attribute_full:  String
                                Full name of the attribute of format <node_name>.<attribute_name>
        :param value:           String
                                Value that should be assigned to the attribute passed
        :param lock:            Boolean
                                Whether the attribute should be locked after it is set.

        :return:                None
        """
        node, attribute_short = attribute_full.split('.', 1)
        enum_string = cmds.attributeQuery(attribute_short, node=node, listEnum=True)[0]
        enum_list = enum_string.split(':')
        enum_dict = {}; index = 0
        for enum_item in enum_list:
            if '=' in enum_item:
                index = enum_item.split('=')[1]
                enum_dict[enum_item.split('=')[0]] = index
            else:
                enum_dict[enum_item] = index
            index += 1

        SceneOperation.unlock_and_set_attr(attribute_full, enum_dict[value], lock=lock)

    @staticmethod
    def unlock_and_set_attr(attribute, value, attribute_type=None, lock=False):
        """
        Utility maya method to unlock a node attribute and set its value.

        :param attribute:       String
                                Full name of the attribute of format <node_name>.<attribute_name>
        :param value:           Value that should be assigned to the attribute passed
        :param attribute_type:  String
                                Type of passed value (according to Maya)
                                Needs to be specified if non-numeric
        :param lock:            Boolean
                                Whether the attribute should be locked after it is set.

        :return:                None
        """
        cmds.setAttr(attribute, lock=False)
        if attribute_type:
            cmds.setAttr(attribute, value, type=attribute_type, lock=lock)
        else:
            cmds.setAttr(attribute, value, lock=lock)

    @staticmethod
    def split_prefix_ext(render_path, frame_sq_key):
        """
        Utility method to split the render path into a prefix
        that can be passed to maya render settings and image extension.

        :param render_path:     String
                                Path where the renders should be saved.
        :param frame_sq_key:    SequenceKey
                                Object containing the number format for the frame sequence

        :return:                Tuple (String, String)
                                File name prefix and extension.
        """
        prefix, ext = os.path.splitext(render_path)
        ext = ext.lstrip('.')
        prefix = prefix.replace("." + frame_sq_key.default, "")

        return prefix, ext
