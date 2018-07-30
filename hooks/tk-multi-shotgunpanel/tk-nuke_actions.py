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
Hook that defines all the available actions, broken down by publish type. 
"""
import sgtk
import os
import re
import glob

from code.nuke_preferences import NukePreferences

HookBaseClass = sgtk.get_hook_baseclass()

class CustomNukeActions(HookBaseClass):
    """
    Shotgun Panel Actions for Nuke
    """

    def generate_actions(self, sg_data, actions, ui_area):
        """
        Returns a list of action instances for a particular object.
        The data returned from this hook will be used to populate the
        actions menu.

        The mapping between Shotgun objects and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the app
        has already established *which* actions are appropriate for this object.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        The ui_area parameter is a string and indicates where the item is to be shown.

        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.

        :param sg_data: Shotgun data dictionary with all the standard shotgun fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent

        # get the existing action instances
        action_instances = super(CustomNukeActions, self).generate_actions(sg_data, actions, ui_area)

        if "deep_read_node" in actions:
            action_instances.append({"name": "deep_read_node",
                                     "params": None,
                                     "caption": "Create Deep Read Node",
                                     "description": "This will add a read node to the current scene."})

        return action_instances

    def execute_action(self, name, params, sg_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_data: Shotgun data dictionary
        :returns: No return value expected.
        """

        app = self.parent

        # call the actions from super
        super(CustomNukeActions, self).execute_action(name, params, sg_data)

        # resolve path
        # toolkit uses utf-8 encoded strings internally and Maya API expects unicode
        # so convert the path to ensure filenames containing complex characters are supported
        path = self.get_publish_path(sg_data).decode("utf-8")

        if name == "deep_read_node":
            self._create_deep_read_node(path, sg_data)

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behavior of things

    def _create_deep_read_node(self, path, sg_publish_data):
        """
        Create a read node representing the publish.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        import nuke

        (_, ext) = os.path.splitext(path)

        # deep files should only be EXRs
        valid_extensions = [".exr"]

        if ext.lower() not in valid_extensions:
            raise Exception("Unsupported file extension for '%s'!" % path)

        # `nuke.createNode()` will extract the format from the
        # file itself (if possible), whereas `nuke.nodes.Read()` won't. We'll
        # also check to see if there's a matching template and override the
        # frame range, but this should handle the zero config case. This will
        # also automatically extract the format and frame range for movie files.
        read_node = nuke.createNode("DeepRead")
        # this detects frame range automatically only if it is explicitly passed
        # (i.e. if the argument to fromUserText() is of the format
        # "<img_seq_path> <start>-<end>")
        read_node["file"].fromUserText(path)

        # find the sequence range if it has one:
        seq_range = self._find_sequence_range(path)

        # to fetch the nuke prefs from pipeline
        step = self._find_pipe_step(path, sg_publish_data)
        nuke_prefs = NukePreferences(step)

        for knob_name, knob_value in nuke_prefs.getKnobOverridesGenerator(step):
            if read_node.Class() in knob_name:
                knob_name = knob_name.replace(read_node.Class(), read_node.name())
                nuke.knob(knob_name, knob_value)

        if seq_range:
            # override the detected frame range.
            read_node["first"].setValue(seq_range[0])
            read_node["last"].setValue(seq_range[1])
        else:
            self.parent.logger.warning("{}: Not setting frame range.".format(read_node.name()))

        # try to fetch a proxy path using templates
        proxy_path = self._get_proxy_path(path)

        if proxy_path:
            read_node["proxy"].fromUserText(proxy_path)
        else:
            self.parent.logger.warning("{}: Not setting proxy path.".format(read_node.name()))

    def _create_read_node(self, path, sg_publish_data):
        """
        Create a read node representing the publish.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """        
        import nuke
        
        (_, ext) = os.path.splitext(path)

        valid_geo_extensions = [".abc", ".obj", ".fbx"]

        # If this is an Alembic cache, use a ReadGeo2 and we're done.
        if ext.lower() in valid_geo_extensions:
            read_geo = nuke.createNode('ReadGeo2')
            # TODO: check issue of alembic with multiple nodes
            # http://community.foundry.com/discuss/topic/103204
            read_geo.knob('file').setValue(path)
            return

        valid_extensions = [".png", 
                            ".jpg", 
                            ".jpeg", 
                            ".exr", 
                            ".cin", 
                            ".dpx", 
                            ".tiff", 
                            ".tif", 
                            ".mov", 
                            ".psd",
                            ".tga",
                            ".ari",
                            ".gif",
                            ".iff"]

        if ext.lower() not in valid_extensions:
            raise Exception("Unsupported file extension for '%s'!" % path)

        # `nuke.createNode()` will extract the format from the
        # file itself (if possible), whereas `nuke.nodes.Read()` won't. We'll
        # also check to see if there's a matching template and override the
        # frame range, but this should handle the zero config case. This will
        # also automatically extract the format and frame range for movie files.
        read_node = nuke.createNode("Read")
        # this detects frame range automatically only if it is explicitly passed
        # (i.e. if the argument to fromUserText() is of the format
        # "<img_seq_path> <start>-<end>")
        read_node["file"].fromUserText(path)

        # find the sequence range if it has one:
        seq_range = self._find_sequence_range(path)

        # to fetch the nuke prefs from pipeline
        step = self._find_pipe_step(path, sg_publish_data)
        nuke_prefs = NukePreferences(step)

        for knob_name, knob_value in nuke_prefs.getKnobOverridesGenerator(step):
            if read_node.Class() in knob_name:
                knob_name = knob_name.replace(read_node.Class(), read_node.name())
                nuke.knob(knob_name, knob_value)

        if seq_range:
            # override the detected frame range.
            read_node["first"].setValue(seq_range[0])
            read_node["last"].setValue(seq_range[1])
        else:
            self.parent.logger.warning("{}: Not setting frame range.".format(read_node.name()))

        # try to fetch a proxy path using templates
        proxy_path = self._get_proxy_path(path)

        if proxy_path:
            read_node["proxy"].fromUserText(proxy_path)
        else:
            self.parent.logger.warning("{}: Not setting proxy path.".format(read_node.name()))

    def _get_proxy_path(self, path):
        # TODO: use sg_publish_data to find associated file tagged as "proxy" instead
        # find a template that matches the path:
        template = None
        try:
            template = self.parent.sgtk.template_from_path(path)
        except sgtk.TankError:
            pass
        if not template:
            return None

        # get the fields
        fields = template.get_fields(path)

        # get proxy template
        proxy_template_exp = "{env_name}_proxy_image"
        proxy_template_name = self.parent.resolve_setting_expression(proxy_template_exp)
        proxy_template = self.parent.sgtk.templates.get(proxy_template_name)

        if not proxy_template:
            self.parent.logger.warning("Unable to find proxy template: {}".format(proxy_template_name))
            return None

        try:
            proxy_path = proxy_template.apply_fields(fields)
            return proxy_path
        except sgtk.TankError:
            self.parent.logger.warning("Unable to apply fields: {}"
                                       "\nto proxy template: {}".format(fields, proxy_template_name))
            return None

    def _find_pipe_step(self, path, sg_publish_data):
        """Helper method to extract pipeline step from renders.

        By extracting fields from the template path.
        
        Args:
            path (str): File path
            sg_publish_data (dict): Shotgun data dictionary with all the standard publish fields.
        
        Returns:
            str: pipeline step in case of a render, "asset" in case of a plate. None if neither could be found.
        """

        if sg_publish_data["entity"].get("type") == "Element":
            return "asset"
        else:
            if sg_publish_data["task"]:
                entity_type = sg_publish_data["task"].get("type")
                filters = [["id", "is", sg_publish_data["task"].get("id")]]
                fields = ["step"]
                item = self.sgtk.shotgun.find_one(entity_type, filters, fields)

                step = item.get("step", None)

                # fetch the short_name of the task
                entity_type = step.get("type")
                filters = [["id", "is", step.get("id")]]
                fields = ["short_name"]

                step_info = self.sgtk.shotgun.find_one(entity_type, filters, fields)

                if step_info:
                    return step_info.get("short_name")
                else:
                    return None

    def _find_sequence_range(self, path):
        """
        Helper method attempting to extract sequence information.
        
        Using the toolkit template system, the path will be probed to 
        check if it is a sequence, and if so, frame information is
        attempted to be extracted.
        
        :param path: Path to file on disk.
        :returns: None if no range could be determined, otherwise (min, max)
        """
        # find a template that matches the path:
        template = None
        try:
            template = self.parent.sgtk.template_from_path(path)
        except sgtk.TankError:
            pass

        if not template:
            # If we don't have a template to take advantage of, then
            # we are forced to do some rough parsing ourself to try
            # to determine the frame range.
            return self._sequence_range_from_path(path)

        # get the fields and find all matching files:
        fields = template.get_fields(path)
        if not "SEQ" in fields:
            # Ticket #655: older paths match wrong templates,
            # so fall back on path parsing
            return self._sequence_range_from_path(path)

        files = self.parent.sgtk.paths_from_template(template, fields, ["SEQ", "eye"])

        # find frame numbers from these files:
        frames = []
        for file in files:
            fields = template.get_fields(file)
            frame = fields.get("SEQ")
            if frame != None:
                frames.append(frame)
        if not frames:
            return None

        # return the range
        return (min(frames), max(frames))


