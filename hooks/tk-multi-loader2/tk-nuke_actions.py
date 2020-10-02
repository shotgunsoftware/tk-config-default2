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
import os
import re
import glob
import sys

import sgtk

import nuke
import random

HookBaseClass = sgtk.get_hook_baseclass()

# Set global studio scripts dirs
if "SSVFX_PIPELINE" in os.environ.keys():
    sys.path.append(os.environ["SSVFX_PIPELINE"])
    nuke.tprint("Appended %s to sys path" % (os.environ["SSVFX_PIPELINE"]))
else:
    nuke.tprint("Failed to append path")

# Collects nodes in a dictionary to arrange them by type
# If the base list is empty, returns nothing
from software.nuke.nuke_python import nuke_tools as nt

imp_nuke_tools = nt.NukeTools()
nuke.tprint("NukeTools loaded from %s " %(nt.__file__))
publish_file_types = {}
old_reads =[]
node_groups = {}


class NukeActions(HookBaseClass):
    
    ##############################################################################################################
    # public interface - to be overridden by deriving classes 
        
    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.
    
        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.
        
        The hook should return at least one action for each item passed in via the 
        actions parameter.
        
        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.
        
        Because you are operating on a particular publish, you may tailor the output 
        (caption, tooltip etc) to contain custom information suitable for this publish.
        
        The ui_area parameter is a string and indicates where the publish is to be shown. 
        - If it will be shown in the main browsing area, "main" is passed. 
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed. 
        
        Please note that it is perfectly possible to create more than one action "instance" for 
        an action! You can for example do scene introspection - if the action passed in 
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than 
        one object is returned for an action, use the params key to pass additional 
        data into the run_action hook.
        
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        # Creates dictionary of dictionaries containing publish information for plate types
        global publish_file_types
        app = self.parent
        if publish_file_types == {}:

            eng = app.engine
            sg = eng.shotgun

            publish_file_types = sg.find("PublishedFileType", 
                    [["sg_nuke_backdrop_color", "is_not", None]], 
                    ["code","sg_nuke_backdrop_color"])


        global old_reads, node_groups
        old_reads = []
        node_groups ={}

        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))
        
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

        if "clip_import" in actions:
            action_instances.append( {"name": "clip_import",
                                      "params": None, 
                                      "caption": "Import Clip", 
                                      "description": "This will import a publish as clip in Hiero or Nuke Studio."} ) 

        if "import_camera" in actions:
            action_instances.append( {"name": "import_camera",
                                      "params": None, 
                                      "caption": "Import Alembic Camera", 
                                      "description": "This will import a published alembic camera created in Maya as a Nuke Camera node."} ) 

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
        read_node_list = []
        for single_action in actions:
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]
                        
            if name == 'read_node':
                read_node_list.append(self.execute_action(name, params, sg_publish_data))
            else:
                self.execute_action(name, params, sg_publish_data)

        '''
        This method has been modified to handle the positioning of newly created notes
        And to create backdrops for groups of nodes
        Any Main Plate will always be placed at 0x,0y on the node grid
        '''

        # Creates a list (old_reads) of all nodes, including newly created ones.
        # Then removes newly created nodes from the list.
        # Then creates a list of y values to check in the creation of new node rows/backdrops

        global old_reads
        for node in read_node_list:
            if node in old_reads:
                old_reads.remove(node)
            else:
                pass

        old_ys = []
        for y_value in old_reads:
            old_ys.append(y_value['ypos'].value())

        # Removes any non-nodes returned by create_read_node
        cleaning_list = []
        for node in read_node_list:
            if node == '':
                pass
            else:
                cleaning_list.append(node)
        read_node_list = cleaning_list
        
        global node_groups
        if read_node_list != []:
            node_groups = imp_nuke_tools.node_sorting_dictionary(read_node_list)
            exist_dict = imp_nuke_tools.node_sorting_dictionary(old_reads)
            ng_copy = node_groups.copy()
        else:
            return

        # Creates Main and BG Plates first
        if 'Main Plate' in ng_copy:
            ng_copy['Main Plate'][0]['xpos'].setValue(0)
            ng_copy['Main Plate'][0]['ypos'].setValue(0)
            del ng_copy['Main Plate']
        else:
            pass

        # Instances Shotgun Engine to create task tag
        app = self.parent
        eng = app.engine #tk-nuke
        task = '_' + str(eng.context.step['name'])

        # Positions remaining nodes
        # If the node is NOT in an exisiting category it is positioned in a new row starting at 860x
        # If the node IS in an existing group, it is added to the appropriate row
        x_increment = 180
        y_increment = 250
        yVal = 360
        for elm in ng_copy:
            if elm not in exist_dict:
                xVal = 430
                yVal -= y_increment
                for item in ng_copy[elm]:
                    while yVal in old_ys:
                        yVal -= y_increment
                    else:
                        item['ypos'].setValue(yVal)
                        item['xpos'].setValue(xVal)
                        xVal += x_increment
            
            else:
                exist_xvals = []
                exist_yval = 0
                backdrop = nuke.toNode(elm + task)
                for i in exist_dict[elm]:
                    exist_xvals.append(i['xpos'].value())
                    exist_yval = i['ypos'].value()
                for j in ng_copy[elm]:
                    j['xpos'].setValue(max(exist_xvals) + x_increment)
                    j['ypos'].setValue(exist_yval)
                    exist_xvals.append(j['xpos'].value())

        # Applies a backdrop on newly created nodes
        # Determines whether or not a group color value has been assigned in Shotgun
        for i in node_groups:
            if i not in exist_dict:
                get_plate_color = next((pf for pf in publish_file_types if pf['code'] == i), 'other')
                if type(get_plate_color) == type({}):
                    passed_color = get_plate_color['sg_nuke_backdrop_color']
                else:
                    passed_color = get_plate_color

                # Applies customized label for the Main Plate, containing dimensions and version number
                if i != 'Main Plate':
                    setBackdrop = node_groups[i]
                    imp_nuke_tools.auto_backdrop_2(setBackdrop, i, passed_color, task)
                else:
                    setBackdrop = node_groups[i]
                    temp = imp_nuke_tools.auto_backdrop_2(setBackdrop, i, passed_color, task)
                    set_label = node_groups[i][0]['label'].value()
                    temp['label'].setValue(
                        i + '\n' + set_label.split(' ')[0] 
                    )
            # Extends the borders of existing backdrops with new nodes added to them
            else:
                x = nuke.toNode(str(i + task))
                if 'Main Plate' in i:
                    pass
                elif len(exist_dict[i]) >= 2:
                    x['bdwidth'].setValue(x['bdwidth'].value() + (180 * len(node_groups[i])))
                else:
                    pass

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
                      "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))
        
        # resolve path - forward slashes on all platforms in Nuke
        path = self.get_publish_path(sg_publish_data).replace(os.path.sep, "/")
        
        if name == "read_node":
            read_node = self._create_read_node(path, sg_publish_data)
            return read_node
        
        if name == "script_import":
            self._import_script(path, sg_publish_data)

        if name == "open_project":
            self._open_project(path, sg_publish_data)
            
        if name == "clip_import":
            self._import_clip(path, sg_publish_data)
            
        if name == "import_camera":
            self._import_camera(path, sg_publish_data)

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behavior of things


    def _import_clip(self, path, sg_publish_data):
        """
        Imports the given publish data into Nuke Studio or Hiero as a clip.

        :param str path: Path to the file(s) to import.
        :param dict sg_publish_data: Shotgun data dictionary with all of the standard publish
            fields.
        """
        if not self.parent.engine.studio_enabled and not self.parent.engine.hiero_enabled:
            raise Exception("Importing shot clips is only supported in Hiero and Nuke Studio.")

        import hiero
        from hiero.core import (
            BinItem,
            MediaSource,
            Clip,
        )

        if not hiero.core.projects():
            raise Exception("An active project must exist to import clips into.")

        project = hiero.core.projects()[-1]
        bins = project.clipsBin().bins()
        media_source = MediaSource(path)
        clip = Clip(media_source)
        project.clipsBin().addItem(BinItem(clip))
    
    def _import_script(self, path, sg_publish_data):
        """
        Import contents of the given file into the scene.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        import nuke

        # must use unicode otherwise path won't be found
        if not os.path.exists(path.decode('utf-8')):
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
    
    def _import_camera(self, path, sg_publish_data):
        '''
        Import Alembic Camera from Maya as a Nuke Camera.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        '''

        import nuke

        # Special Notes:
        # The node has to be created with a path and the read_from_file box checked.
        # This allows the hideControlPanel command to disable a popup dialog
        # that would otherwise get stuck behind the Shotgun Loader window and freeze Nuke.
        node = nuke.createNode('Camera2', 'read_from_file True file %s' % path)
        node.hideControlPanel()

    def _create_read_node(self, path, sg_publish_data):
        """
        Create a read node representing the publish.
        
        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.        
        """        

        import nuke
        (_, ext) = os.path.splitext(path)

        # setup shotgun engine
        eng = sgtk.platform.current_engine()

        # shotgun searches
        proj_info = eng.shotgun.find_one("Project", 
                                        [['id', 'is', eng.context.project['id']]], 
                                        ['sg_read_color_space'])

        # If this is an Alembic cache, use a ReadGeo2 and we're done.
        if ext.lower() == ".abc":
            nuke.createNode("ReadGeo2", "file {%s}" % path)
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
                            ".mp4",
                            ".psd",
                            ".tga",
                            ".ari",
                            ".gif",
                            ".iff"]

        if ext.lower() not in valid_extensions:
            raise Exception("Unsupported file extension for '%s'!" % path)

        # Creates node if there are no filepath matches, otherwise returns an empty string

        # `nuke.createNode()` will extract the format and frame range from the
        # file itself (if possible), whereas `nuke.nodes.Read()` won't. We'll
        # also check to see if there's a matching template and override the
        # frame range, but this should handle the zero config case. This will
        # also automatically extract the format and frame range for movie files.
        imp_nuke_tools = nt.NukeTools()
        global old_reads
        old_reads = nuke.allNodes('Read')

        if imp_nuke_tools.path_check(path, old_reads):
            return ''
        else:
            read_node = nuke.createNode("Read")
            read_node["file"].fromUserText(path)
            
        # Set temporary node name to prevent name conflicts
        # and applies a special label/bookmarking to Main Plates
        read_node['name'].setValue(sg_publish_data['published_file_type']['name'] + '_' + str(random.randint(1000000000000000,9999999999999999)))

        # Find the sequence range if it has one:
        seq_range = self._find_sequence_range(path)

        if seq_range:
            # override the detected frame range.
            read_node["first"].setValue(seq_range[0])
            read_node["last"].setValue(seq_range[1])
        
        if 'Main Plate' in sg_publish_data['published_file_type']['name']:

            res_width = read_node.metadata().get('input/width')
            res_height = read_node.metadata().get('input/height')
            label_value = ''

            if res_width:
                label_value = str(read_node.metadata().get('input/width'))
            
            if res_height:
                label_value += 'x' + str(read_node.metadata().get('input/height'))

            label_value += '\nv.' + str(sg_publish_data['version_number'])

            read_node['label'].setValue(label_value)
            read_node['bookmark'].setValue(True)

            # set proxy main path
            read_path = read_node["file"].value()

            proj_proxies = eng.shotgun.find("PublishedFile", 
                                            [['project.Project.id', 'is', eng.context.project['id']],
                                            ['published_file_type', 'is', {'type': 'PublishedFileType', 'id': 12}]], 
                                            ['code', 'path'])

            filename = os.path.basename(read_path)
            stripped_name = os.path.splitext(filename)

            while stripped_name[-1] != '':
                stripped_name = os.path.splitext(stripped_name[0])

            stripped_name = stripped_name[0]

            proxy_path = next((i['path']['local_path_windows'] for i in proj_proxies if stripped_name in i['code']), None)

            if proxy_path:
                read_node['proxy'].setValue(proxy_path)
            else:
                pass

        else:
            read_node['label'].setValue('v.' + str(sg_publish_data['version_number']))


        # Collects all Read nodes and sorts them by plate type
        reads_asof_now = nuke.allNodes('Read')
        node_groups = imp_nuke_tools.node_sorting_dictionary(reads_asof_now)
        existing_node_names = [n.name() for n in reads_asof_now]

        # Assigns a name to read_node based on plate type
        # Plus how many plates of that type are in the current node graph
        rn_name = read_node['name'].value().split('_')[0]
        renumerator = 0
        rn_number = len(node_groups[rn_name])
        
        while str(rn_name + '_' + str(rn_number)) in existing_node_names:
            renumerator += 1
            rn_number += renumerator
        else:
            read_node['name'].setValue(rn_name + '_' + str(rn_number))    

        if proj_info['sg_read_color_space'] != None:
            if proj_info['sg_read_color_space'] in ['premultiplied', 'raw', 'auto_alpha']:
                read_node[proj_info['sg_read_color_space']].setValue(True)
            else:
                read_node['colorspace'].setValue(proj_info['sg_read_color_space'])
        else:
            pass

        return read_node

    def _sequence_range_from_path(self, path):
        """
        Parses the file name in an attempt to determine the first and last
        frame number of a sequence. This assumes some sort of common convention
        for the file names, where the frame number is an integer at the end of
        the basename, just ahead of the file extension, such as
        file.0001.jpg, or file_001.jpg. We also check for input file names with
        abstracted frame number tokens, such as file.####.jpg, or file.%04d.jpg.

        :param str path: The file path to parse.

        :returns: None if no range could be determined, otherwise (min, max)
        :rtype: tuple or None
        """
        # This pattern will match the following at the end of a string and
        # retain the frame number or frame token as group(1) in the resulting
        # match object:
        #
        # 0001
        # ####
        # %04d
        #
        # The number of digits or hashes does not matter; we match as many as
        # exist.
        frame_pattern = re.compile(r"([0-9#]+|[%]0\dd)$")
        root, ext = os.path.splitext(path)
        match = re.search(frame_pattern, root)

        # If we did not match, we don't know how to parse the file name, or there
        # is no frame number to extract.
        if not match:
            return None

        # We need to get all files that match the pattern from disk so that we
        # can determine what the min and max frame number is.
        glob_path = "%s%s" % (
            re.sub(frame_pattern, "*", root),
            ext,
        )
        files = glob.glob(glob_path)

        # Our pattern from above matches against the file root, so we need
        # to chop off the extension at the end.
        file_roots = [os.path.splitext(f)[0] for f in files]

        # We know that the search will result in a match at this point, otherwise
        # the glob wouldn't have found the file. We can search and pull group 1
        # to get the integer frame number from the file root name.
        frames = [int(re.search(frame_pattern, f).group(1)) for f in file_roots]
        return (min(frames), max(frames))

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
            return None
        
        files = self.parent.sgtk.paths_from_template(template, fields)

        # Somthing has gone wrong
        # despite having valid templates, no files were returned
        # so we'll pretend no template was found
        if files == []:
            try:
                sequence_range = self._sequence_range_from_path(path)
                return sequence_range
            except:
                nuke.tprint(">>>>> SOMETHING WENT WRONG")
        
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


