# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
# ### OVERRIDDEN IN SSVFX_SG ###

from ss_config.hooks.tk_multi_publish2.desktop.collector import SsBasicSceneCollector

# class BasicSceneCollector(SsBasicSceneCollector):
#     """
#     A basic collector that handles files and general objects.
#     """
#     pass

import mimetypes
import os
import sys
import re
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# A look up of node types to parameters for finding outputs to publish
_NUKE_OUTPUTS = {
    "Write": "file",
    "WriteGeo": "file",
}

if "win" in sys.platform:
    system_path_variable = "windows_path"
    system_root_variable = "local_path_windows"
elif sys.platform == "linux":
    system_path_variable = "linux_path"
    system_root_variable = "local_path_linux"

class NukeSessionCollector(SsBasicSceneCollector):
    """
    Collector that operates on the current nuke/nukestudio session. Should
    inherit from the basic collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # grab any base class settings
        collector_settings = super(NukeSessionCollector, self).settings or {}

        # settings specific to this collector
        nuke_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                "correspond to a template defined in "
                "templates.yml. If configured, is made available"
                "to publish plugins via the collected item's "
                "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(nuke_session_settings)

        return collector_settings   
    
    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Nuke/NukeStudio and parents a
        subtree of items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        publisher = self.parent
        engine = publisher.engine

        if ((hasattr(engine, "studio_enabled") and engine.studio_enabled) or
            (hasattr(engine, "hiero_enabled") and engine.hiero_enabled)):

            # running nuke studio or hiero
            self.collect_current_nukestudio_session(settings, parent_item)

            # since we're in NS, any additional collected outputs will be
            # parented under the root item
            project_item = parent_item
        else:
            # running nuke. ensure additional collected outputs are parented
            # under the session
            project_item = self.collect_current_nuke_session(settings,
                parent_item)

        # run node collection if not in hiero
        if hasattr(engine, "hiero_enabled") and not engine.hiero_enabled:
            self.collect_sg_writenodes(project_item)
            # self.get_selected_reads(project_item)                                             #### PHASE 2 ####
            self.collect_node_outputs(project_item)

        self.logger.warning(">>>>> process_session complete >>>>>")

    def collect_current_nuke_session(self, settings, parent_item):
        """
        Analyzes the current session open in Nuke and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        publisher = self.parent

        # get the current path
        path = _session_path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Nuke Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "nuke.session",
            "Nuke Script",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "nuke.png"
        )
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        curr_fields = {}
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)
            
            # create path where script copy should end up
            curr_fields = work_template.get_fields(path)
            publish_template = publisher.engine.get_template_by_name("nuke_shot_publish")
            script_copy_output = publish_template.apply_fields(curr_fields)

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            session_item.properties["publish_template"] = work_template
            self.logger.debug("Work and Publish templates defined for Nuke collection.")

            # add script copy destination to item properties
            session_item.properties["path"] = path
            session_item.properties["work_fields"] = curr_fields
            session_item.properties["copy_destination"] = script_copy_output

        self.logger.info("Collected current Nuke script")
        return session_item

    def collect_current_nukestudio_session(self, settings, parent_item):
        """
        Analyzes the current session open in NukeStudio and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        # import here since the hooks are imported into nuke and nukestudio.
        # hiero module is only available in later versions of nuke
        import hiero.core

        publisher = self.parent

        # go ahead and build the path to the icon for use by any projects
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "nukestudio.png"
        )

        if hiero.ui.activeSequence():
            active_project = hiero.ui.activeSequence().project()
        else:
            active_project = None

        # attempt to retrive a configured work template. we can attach
        # it to the collected project items
        work_template_setting = settings.get("Work Template")
        work_template = None
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)

        # FIXME: begin temporary workaround
        # we use different logic here only because we don't have proper support
        # for multi context workflows when templates are in play. So if we have
        # a work template configured, for now we'll only collect the current,
        # active document. Once we have proper multi context support, we can
        # remove this.
        if work_template:
            # same logic as the loop below but only processing the active doc
            if not active_project:
                return
            project_item = parent_item.create_item(
                "nukestudio.project",
                "NukeStudio Project",
                active_project.name()
            )
            self.logger.info(
                "Collected Nuke Studio project: %s" % (active_project.name(),))
            project_item.set_icon_from_path(icon_path)
            project_item.properties["project"] = active_project
            project_item.properties["work_template"] = work_template
            self.logger.debug(
                "Work template defined for NukeStudio collection.")
            return
        # FIXME: end temporary workaround

        for project in hiero.core.projects():

            # create the session item for the publish hierarchy
            project_item = parent_item.create_item(
                "nukestudio.project",
                "NukeStudio Project",
                project.name()
            )
            project_item.set_icon_from_path(icon_path)

            # add the project object to the properties so that the publish
            # plugins know which open project to associate with this item
            project_item.properties["project"] = project

            self.logger.info(
                "Collected Nuke Studio project: %s" % (project.name(),))

            # enable the active project and expand it. other projects are
            # collapsed and disabled.
            if active_project and active_project.guid() == project.guid():
                project_item.expanded = True
                project_item.checked = True
            elif active_project:
                # there is an active project, but this isn't it. collapse and
                # disable this item
                project_item.expanded = False
                project_item.checked = False

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            if work_template:
                project_item.properties["work_template"] = work_template
                self.logger.debug(
                    "Work template defined for NukeStudio collection.")

    def collect_node_outputs(self, parent_item):
        """
        Scan known output node types in the session and see if they reference
        files that have been written to disk.

        :param parent_item: The parent item for any nodes collected
        """

        # iterate over all the known output types
        for node_type in _NUKE_OUTPUTS:

            # get all the instances of the node type
            all_nodes_of_type = [n for n in nuke.allNodes()
                if n.Class() == node_type]

            # iterate over each instance
            for node in all_nodes_of_type:

                param_name = _NUKE_OUTPUTS[node_type]

                # evaluate the output path parameter which may include frame
                # expressions/format
                file_path = node[param_name].evaluate()

                if not file_path or not os.path.exists(file_path):
                    # no file or file does not exist, nothing to do
                    continue

                self.logger.info(
                    "Processing %s node: %s" % (node_type, node.name()))

                # file exists, let the basic collector handle it
                item = super(NukeSessionCollector, self)._collect_file(
                    parent_item,
                    file_path,
                    frame_sequence=True
                )

                # the item has been created. update the display name to include
                # the nuke node to make it clear to the user how it was
                # collected within the current session.
                item.name = "%s (%s)" % (item.name, node.name())

    def collect_sg_writenodes(self, parent_item):
        """
        Collect any rendered sg write nodes in the session.

        :param parent_item:  The parent item for any sg write nodes collected
        """
        publisher = self.parent
        engine = publisher.engine

        sg_writenode_app = engine.apps.get("tk-nuke-writenode")      

        if not sg_writenode_app:
            self.logger.debug(
                "The tk-nuke-writenode app is not installed. "
                "Will not attempt to collect those nodes."
            )
            return

        # Search for write nodes in node selection
        # If no node is selected, display error message
        selected_nodes = nuke.selectedNodes()

        if not selected_nodes:
            return nuke.message("<b style='color:salmon'>No Nodes Selected</b>")

        selected_writes = [node for node in selected_nodes if node.Class() in ["WriteTank", "Write"]]
        if not selected_writes:
            return nuke.message("<b style='color:salmon'>No Write Nodes Selected</b>")

        # filter selected_nodes for Version from both SsWrite and SGWrite types
        # To preserve compatibility
        selected_versions = []
        for node in selected_writes:
            knobs = {knob_name:node[knob_name].value() for knob_name in node.knobs()}
            if "Version" in [knobs.get('ssWriteType'),knobs.get('write_type')]:
                selected_writes.append(node)

        if not selected_versions:
            return nuke.message("<b style='color:salmon'>No Version Write Nodes Selected.\n Can't locate render path.</b>")
        
        existing_paths = []
        # for node in selected_versions:
        for node in selected_versions:
            # see if any frames have been rendered for this write node
            rendered_files = sg_writenode_app.get_node_render_files(node)

            # some files rendered, use first frame to get a master path
            # which can be used for path-based operations
            folder = os.path.dirname(rendered_files[0][0])

            # Prevent redundancies by checking for node file path in a list
            if folder in existing_paths:
                continue
            else:
                self.process_write_node(node, parent_item)
                existing_paths.append(folder)

    def process_write_node(self, node, parent_item):
        '''
        Processing for SG Write Nodes to prepare them for publishing

        :param node:  SG write node for processing
        :param parent_item:  The parent item for any sg write nodes collected
        '''

        publisher = self.parent
        engine = publisher.engine

        sg_writenode_app = engine.apps.get("tk-nuke-writenode")

        # get project info
        project_info = self.project_info

        # get entity_info
        entity_info = self.entity_info

        # get codec info
        codec_info = self.codec_info

        # see if any frames have been rendered for this write node
        # the except is a fallback in case the shotgun-specific process fails
        try:
            rendered_files = sg_writenode_app.get_node_render_files(node)
        except:
            rendered_files = ([], None)
            directory = os.path.dirname(node['file'].value())
            files = os.listdir(directory)
            for filename in files:
                rendered_files[0].append(os.path.join(directory, filename).replace("/", "\\"))
        
        no_frames = "<b style='color:salmon'>There are no rendered frames associated with node %s.\nIt will not be queued for submission</b>"
        # Sometimes rendered_files has a return, but the list is empty
        # So it's important to check for both conditions
        if not rendered_files:
            self.logger.debug("rendered_files retruned no results: continuing")
            nuke.message(no_frames % node.name())
            return
        elif rendered_files[0] == []:
            self.logger.debug("rendered_files[0] returned empty list: continuing")
            nuke.message(no_frames % node.name())
            return

        # some files rendered, use first frame to get a master path
        # which can be used for path-based operations
        folder = os.path.dirname(rendered_files[0][0])
        contents = publisher.util.get_frame_sequences(folder, super(NukeSessionCollector, self)._get_image_extensions())
        path = contents[0][0]
        frames = sorted(contents[0][-1])
        frame_range = "1-1"

        # set initial range from file list
        first_frame_search = self._get_frame_number(frames[0])
        last_frame_search = self._get_frame_number(frames[-1])

        if (first_frame_search and last_frame_search):
            frame_range = "%s-%s" % ( first_frame_search.group(1), last_frame_search.group(1) )
            self.logger.info("Frame range from path: %s" % frame_range)
        
        if first_frame_search.group(1) == last_frame_search.group(1):
            frame_range = first_frame_search.group(1)
            self.logger.info("Frame range from single frame: %s" % frame_range)

        # compare initial frame range to Shotgun frame range (if there is one)
        # if they are different, prompt the user to select a range
        sg_range = None
        if entity_info.get("sg_head_in") and entity_info.get("sg_tail_out"):
            sg_range = "%s-%s" % (entity_info.get("sg_head_in"), entity_info.get("sg_tail_out") )

        first_frame = frame_range.split("-")[0]
        last_frame = frame_range.split("-")[-1]

        item_info = super(NukeSessionCollector, self)._get_item_info(path)

        # item_info will be for the single file. we'll update the type and
        # display to represent a sequence. This is the same pattern used by
        # the base collector for image sequences. We're not using the base
        # collector to create the publish item though since we already have
        # the sequence path, template knowledge provided by the
        # tk-nuke-writenode app. The base collector makes some "zero config"
        # assupmtions about the path that we don't need to make here.
        item_type = "%s.sequence" % (item_info["item_type"],)
        type_display = "%s Sequence" % (item_info["type_display"],)
        
        # we'll publish the path with the frame/eye spec (%V, %04d)
        # publish_path = sg_writenode_app.get_node_render_path(node)

        # construct publish name:
        # render_template = sg_writenode_app.get_node_render_template(node)
        template = sgtk.sgtk_from_path(path).template_from_path(path)
        render_path_fields = template.get_fields(path)
        node_context = sgtk.sgtk_from_path(path).context_from_path(path)

        rp_name = render_path_fields.get("name")
        rp_channel = render_path_fields.get("channel")

        if not rp_name and not rp_channel:
            publish_name = "%s_%s" % (render_path_fields['Shot'], render_path_fields['task_name'])
        elif not rp_name:
            publish_name = "Channel %s" % rp_channel
        elif not rp_channel:
            publish_name = rp_name
        else:
            publish_name = "%s, Channel %s" % (rp_name, rp_channel)

        # get the version number from the render path
        version_number = render_path_fields.get("version")

        # use the path basename and nuke writenode name for display
        # (_, filename) = os.path.split(publish_path)
        (_, filename) = os.path.split(path)
        display_name = "%s from Node:  %s" % (publish_name, node.name())

        # create and populate the item
        item = parent_item.create_item(
            item_type, type_display, display_name)

        item.set_icon_from_path(item_info["icon_path"])
        
        # if the supplied path is an image, use the path as # the thumbnail.
        item.set_thumbnail_from_path(path)

        # disable thumbnail creation since we get it for free
        item.thumbnail_enabled = False

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        # item.properties["path"] = publish_path
        item.properties["path"] = path

        # set template for upload_version
        item.properties["template"] = template

        # additional properties from the Desktop collector        
        item.properties["folder_name"] = os.path.dirname(folder)
        item.properties["content_version_name"] = os.path.dirname(folder)
        item.properties["user_info"] = self.user_info

        fields = {}
 
        if template:
            self.logger.debug("File template: %s" % (template.name))
            fields = template.get_fields(path)
        
        item.properties["fields"] = fields

        # set pipeline step
        item.properties["pipeline_step"] = engine.context.step['name']

        # include an indicator that this is an image sequence and the known
        # file that belongs to this sequence
        file_sequence = rendered_files[0]
        item.properties["sequence_paths"] = []
        item.properties["sequence_paths"] = sorted(file_sequence)

        # store publish info on the item so that the base publish plugin
        # doesn't fall back to zero config path parsing
        # item.properties["publish_name"] = publish_name
        item.properties["publish_version"] = version_number
        # item.properties["publish_template"] = render_template                   #### nuke_shot_render_exr ####
        # item.properties["work_template"] = render_template                      #### nuke_shot_render_exr ####
        item.properties["software_info"] = self.software_info
        item.properties["color_space"] = self._get_node_colorspace(node)
        item.properties["first_frame"] = first_frame
        item.properties["last_frame"] = last_frame
        item.properties["frame_range"] = frame_range
        item.properties["sg_range"] = sg_range
        item.properties['file_fields'] = render_path_fields

        # store the nuke writenode on the item as well. this can be used by
        # secondary publish plugins
        item.properties["sg_writenode"] = node

        # determine step settings for publish/upload plugins
        if node.Class() != "Read":
            filters = [
                    ["content", "is",  engine.context.task['name']],
                    ["entity.Shot.code", "is", engine.context.entity['name']],
                    ["project.Project.id", "is", engine.context.project['id']]  
                ]
        else:
            filters = [
                    ["content", "is",  render_path_fields['task_name']],
                    ["entity.Shot.code", "is", render_path_fields['Shot']],
                    ["project.Project.id", "is", node_context.to_dict()['project']['id']]  
                ]

        task_fields =[
                "step",
                "entity"
            ]       

        task = engine.shotgun.find_one("Task", filters, task_fields)

        step = next((i for i in self.step_info if i['id'] == task['step']['id']), None)
        item.properties['step'] = step

        if step:   
            for k,v in self._set_plugins_from_sg(step['id']).items():
                item.properties[k] = v
        else:
            for k,v in self._set_plugins_from_sg(None).items():
                item.properties[k] = v

        # set project info
        item.properties["project_info"] = project_info

        # set entity_info
        item.properties["entity_info"] = entity_info

        # set codec info
        item.properties["codec_info"] = codec_info

        # set standardized pipeline root 
        if os.environ.get('SSVFX_PIPELINE') == "//10.80.8.252/VFX_Pipeline/Pipeline".replace("/", "\\"):
            item.properties["pipeline_root"] = "//10.80.8.252/VFX_Pipeline".replace("/", "\\")
        else:
            item.properties["pipeline_root"] = os.environ.get('SSVFX_PIPELINE')

        # we have a publish template so disable context change. This
        # is a temporary measure until the publisher handles context
        # switching natively.
        item.context_change_allowed = False

        # self.logger.info("Collected file: %s" % (publish_path,))
        self.logger.info("Collected file: %s" % (path))

    def _get_node_colorspace(self, node):
        """
        Get the colorspace for the specified nuke node

        :param node:    The nuke node to find the colorspace for
        :returns:       The string representing the colorspace for the node
        """
        cs_knob = node.knob("colorspace")
        if not cs_knob:
            return
    
        cs = cs_knob.value()
        # handle default value where cs would be something like: 'default (linear)'
        if cs.startswith("default (") and cs.endswith(")"):
            cs = cs[9:-1]
        return cs

    def _set_plugins_from_sg(self, step_id):

        # Determine if there are plugin visibility settings in Shotgun
        publish_bool = next((i['sg_publish_to_shotgun'] for i in self.step_info if i['id'] == step_id), None)
        version_bool = next((i['sg_version_for_review'] for i in self.step_info if i['id'] == step_id), None)
        slap_bool = next((i['sg_slap_comp'] for i in self.step_info if i['id'] == step_id), None)
        
        plugins_dict = {}
        # Determine which plugins to load
        if step_id == None:
            self.logger.debug("No Step ID found. Loading defaults.")
            plugins_dict["publish_to_shotgun"] = True
            plugins_dict["sg_version_for_review"] = True
            plugins_dict["sg_slap_comp"] = False
        else:
            plugins_dict["publish_to_shotgun"] = publish_bool
            plugins_dict["sg_slap_comp"] = slap_bool
            if not version_bool:
                plugins_dict["sg_version_for_review"] = True
            else:
                plugins_dict["sg_version_for_review"] = False

        self.logger.info("Publish: %s | Version: %s | Slap: %s"%(plugins_dict["publish_to_shotgun"],
                                                plugins_dict["sg_version_for_review"],
                                                plugins_dict["sg_slap_comp"]))
        return plugins_dict

    def _get_frame_number(self, path):

        """
        Extract a SEQ frame number from the supplied path.

        This is used by plugins for populating frame range info.

        :param path: The path to a file.

        :return: An integer representing the frame number in the supplied
            path. If no version found, ``None`` will be returned.
        """
        
        frame_number = r"\.(\d{4,10})\."
                
        return re.search(frame_number, path)

    def _task_fields(self, curr_fields):
        '''
        Generate a list of fields to search for in SG

        :param curr_fields: info derived from the path and used for specificity
        '''
        # default field
        search_fields = [
            "entity",
        ]

        # step fields
        search_fields.extend([
            "step.Step.id",
            "step.Step.code",
            'step.Step.sg_department',
            'step.Step.sg_publish_to_shotgun',
            'step.Step.sg_version_for_review',
            'step.Step.sg_slap_comp',
            'step.Step.sg_review_process_type',
            'step.Step.entity_type',
        ])

        # entity fields
        entity_type = curr_fields['type']
        if entity_type == "Shot":
            search_fields.extend([
                "entity.Shot.code",
                "entity.Shot.id",
                "entity.Shot.type",
                "entity.Shot.description",
                "entity.Shot.created_by",
                "entity.Shot.sg_episode",
                "entity.Shot.sg_shot_lut",
                "entity.Shot.sg_shot_audio",
                "entity.Shot.sg_status_list",
                "entity.Shot.sg_project_name",
                "entity.Shot.sg_plates_processed_date",
                "entity.Shot.sg_shot_lut",
                "entity.Shot.sg_shot_ocio",
                "entity.Shot.sg_without_ocio",
                "entity.Shot.sg_head_in",
                "entity.Shot.sg_tail_out",
                "entity.Shot.sg_lens_info",
                "entity.Shot.sg_plate_proxy_scale",
                "entity.Shot.sg_frame_handles",
                "entity.Shot.sg_shot_ccc",
                "entity.Shot.sg_seq_ccc",
                "entity.Shot.sg_vfx_work",
                "entity.Shot.sg_scope_of_work",
                "entity.Shot.sg_editorial_notes",
                "entity.Shot.sg_sequence"
                "entity.Shot.sg_main_plate",
                "entity.Shot.sg_latest_version",
                "entity.Shot.sg_latest_client_version",
                "entity.Shot.sg_gamma",
                "entity.Shot.sg_target_age",
                "entity.Shot.sg_shot_transform",
                "entity.Shot.sg_main_plate_camera",
                "entity.Shot.sg_main_plate_camera.Camera.code",
                "entity.Shot.sg_main_plate_camera.Camera.sg_format_width",
                "entity.Shot.sg_main_plate_camera.Camera.sg_format_height",
                "entity.Shot.sg_main_plate_camera.Camera.sg_pixel_aspect_ratio",
                "entity.Shot.sg_main_plate_camera.Camera.sg_pump_incoming_transform_switch",
            ])

        elif entity_type == "Asset":
            search_fields.extend([
                "entity.Asset.code",
                "entity.Asset.id",
                "entity.Asset.type",
                "entity.Asset.description",
                "entity.Asset.created_by",
                "entity.Asset.sg_status_list",
                "entity.Asset.sg_head_in",
                "entity.Asset.sg_tail_out",
                "entity.Asset.sg_lens_info",
                "entity.Asset.sg_vfx_work",
                "entity.Asset.sg_scope_of_work",
                "entity.Asset.sg_editorial_notes",
                "entity.Asset.sg_latest_version",
                "entity.Asset.sg_latest_client_version"
            ])

        return search_fields


def _session_path():
    """
    Return the path to the current session
    :return:
    """
    root_name = nuke.root().name()
    return None if root_name == "Root" else root_name
