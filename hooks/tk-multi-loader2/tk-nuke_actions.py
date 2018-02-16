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

from code.nuke_preferences import NukePreferences

HookBaseClass = sgtk.get_hook_baseclass()

class NukeActions(HookBaseClass):
    """
    Shotgun Panel Actions for Nuke
    """
    
    def generate_actions(self, sg_publish_data, actions, ui_area):
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
        - If it will be shown in the history area, "history" is passed.
                
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Shotgun Data: %s" % (ui_area, actions, sg_publish_data))
        
        action_instances = []

        if "read_node" in actions:
            action_instances.append( {"name": "read_node", 
                                      "params": None,
                                      "caption": "Create Read Node", 
                                      "description": "This will add a read node to the current scene."} )

        if "script_import" in actions:        
            action_instances.append( {"name": "script_import",
                                      "params": None, 
                                      "caption": "Import Contents", 
                                      "description": "This will import all the nodes into the current scene."} )

        if "open_project" in actions:
            action_instances.append( {"name": "open_project",
                                      "params": None,
                                      "caption": "Open Project",
                                      "description": "This will open the Nuke Studio project in the current session."} )

        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the ``execute_action``
            method for backward compatibility with hooks written for the previous
            version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an error
            is raised midway through.

        :param list actions: Action dictionaries.
        """
        for single_action in actions:
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]
            self.execute_action(name, params, sg_publish_data)

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.
        
        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """
        app = self.parent

        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Shotgun Data: %s" % (name, params, sg_publish_data))
        
        # resolve path - forward slashes on all platforms in Nuke
        path = self.get_publish_path(sg_publish_data).replace(os.path.sep, "/")
        
        if name == "read_node":
            self._create_read_node(path, sg_publish_data)
        
        if name == "script_import":
            self._import_script(path, sg_publish_data)

        if name == "open_project":
            self._open_project(path, sg_publish_data)

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behavior of things
    
    def _import_script(self, path, sg_publish_data):
        """
        Import contents of the given file into the scene.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        import nuke
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        nuke.nodePaste(path)

    def _open_project(self, path, sg_publish_data):
        """
        Open the nuke studio project.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        import nuke

        if not nuke.env.get("studio"):
            # can't import the project unless nuke studio is running
            raise Exception("Nuke Studio is required to open the project.")

        import hiero
        hiero.core.openProject(path)

    def _create_read_node(self, path, sg_publish_data):
        """
        Create a read node representing the publish.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.        
        """        
        import nuke
        
        (_, ext) = os.path.splitext(path)

        # If this is an Alembic cache, use a ReadGeo2 and we're done.
        if ext.lower() == '.abc' or ext.lower() == '.obj':
            read_geo = nuke.createNode('ReadGeo2')
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

        # `nuke.createNode()` will extract the format and frame range from the
        # file itself (if possible), whereas `nuke.nodes.Read()` won't. We'll
        # also check to see if there's a matching template and override the
        # frame range, but this should handle the zero config case. This will
        # also automatically extract the format and frame range for movie files.
        read_node = nuke.createNode("Read")
        read_node["file"].fromUserText(path)

        # find the sequence range if it has one:
        seq_range = self._find_sequence_range(path, sg_publish_data)

        # to fetch the nuke prefs from pipeline
        nuke_prefs = NukePreferences()

        for knob_name, knob_value in nuke_prefs.getKnobOverridesGenerator(self._find_pipe_step(path, sg_publish_data)):
            if read_node.Class() in knob_name:
                knob_name = knob_name.replace(read_node.Class(), read_node.name())
                nuke.knob(knob_name, knob_value)

        if seq_range:
            # override the detected frame range.
            read_node["first"].setValue(seq_range[0])
            read_node["last"].setValue(seq_range[1])

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

    def _find_sequence_range(self, path, sg_publish_data):
        """
        Helper method attempting to extract sequence information.
        
        Using the toolkit template system, the path will be probed to 
        check if it is a sequence, and if so, frame information is
        attempted to be extracted.
        
        :param path: Path to file on disk.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: None if no range could be determined, otherwise (min, max)
        """
        # find a template that matches the path:

        if sg_publish_data["entity"].get("type") == "Element":
            filters = [["id", "is", sg_publish_data["entity"].get("id")]]
            fields = ["cut_in", "cut_out"]
            item = self.sgtk.shotgun.find_one("Element", filters, fields)

            return (item.get("cut_in", 1001), item.get("cut_out", 1001))
        else:
            if sg_publish_data["version"]:
                entity_type = sg_publish_data["version"].get("type")
                filters = [["id", "is", sg_publish_data["version"].get("id")]]
                fields = ["sg_first_frame", "sg_last_frame"]
                item = self.sgtk.shotgun.find_one(entity_type, filters, fields)

                return (item.get("sg_first_frame", 1001), item.get("sg_last_frame", 1001))
            else:
                # last fallback method to read frames for a render
                # by getting the frame numbers from the template fields
                template = None
                try:
                    template = self.parent.sgtk.template_from_path(path)
                except sgtk.TankError:
                    pass
                
                if not template:
                    return None
                    
                # get the fields and find all matching files:
                fields = template.get_fields(path)

                # find frame numbers from these files:
                frames = []

                if "SEQ" in fields:
                    files = self.parent.sgtk.paths_from_template(template, fields, ["SEQ", "eye"])
                else:
                    return None
                
                for file in files:
                    fields = template.get_fields(file)
                    if "SEQ" in fields:
                        frame = fields.get("SEQ")
                    else:
                        frame = None
                    
                    if frame != None:
                        frames.append(frame)

                if not frames:
                    return None
                
                # return the range
                return (min(frames), max(frames))


