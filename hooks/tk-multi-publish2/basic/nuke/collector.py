﻿# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import sys
import re
import nuke
import sgtk
from nukepy.utils import nuke_utils as nutils

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

class NukeSessionCollector(HookBaseClass):
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

    @property
    def user_info(self):
        publisher = self.parent
        ctx = publisher.engine.context
        user_fields = [
            'name',
            'login',
            'sg_ip_address'
        ]
        user_filter = [
            ['id', 'is', ctx.user['id']],
        ]
        user_info = publisher.shotgun.find_one(
            'HumanUser',
            user_filter,
            user_fields
        )
        return user_info

    @property
    def software_info(self):
        """
        Test SG for all associated software
        :returns: The SG info of the given softwares
        """
        publisher = self.parent

        software_filters = [
            ['id', 'is_not', 0],
            ['version_names', 'is_not', None]
        ]
        software_fields = [
            'code',
            'products',
            system_path_variable,
            'version_names',
            'sg_pipeline_tools'
        ]
        software_info = publisher.shotgun.find(
            'Software',
            software_filters,
            software_fields
        )
        return software_info

    @property
    def codec_info(self):
        """
        Test SG for all associated codec

        :returns: The SG info of the given codecs
        """
        publisher = self.parent

        codec_filters = []

        codec_fields = ['id',
                        'code',
                        'name',
                        'sg_nuke_code',
                        'sg_output_folder']

        codec_info = publisher.shotgun.find(
            'CustomNonProjectEntity08',
            codec_filters,
            codec_fields
        )

        return codec_info

    @property
    def project_info(self):
        """
        A dictionary of relative Project info that is taken from SG Project page
        """
        publisher = self.parent
        ctx = publisher.engine.context
        proj_info = publisher.shotgun.find_one("Project",
                                               [['id', 'is', ctx.project['id']]],
                                               ['name',
                                                'id',
                                                'sg_root',
                                                'sg_status',
                                                'sg_date_format',
                                                'sg_short_name',
                                                'sg_frame_rate',
                                                'sg_vendor_id',
                                                'sg_frame_handles',
                                                'sg_data_type',
                                                'sg_format_width',
                                                'sg_format_height',
                                                'sg_delivery_slate_count',
                                                'sg_client_version_submission',
                                                'sg_incoming_plate_jpg_',
                                                'sg_delivery_default_process',
                                                'sg_incoming_fileset_padding',
                                                'sg_proxy_format_ratio',
                                                'sg_format_pixel_aspect_ratio',
                                                'sg_lut',
                                                'sg_version_zero_lut',
                                                'sg_version_zero_slate',
                                                'sg_version_zero_internal_burn_in',
                                                'sg_burnin_frames_format',
                                                'sg_delivery_qt_dual_lut',
                                                'sg_delivery_format_width',
                                                'sg_delivery_format_height',
                                                'sg_delivery_reformat_filter',
                                                'sg_delivery_fileset_padding',
                                                'sg_delivery_fileset_slate',
                                                'sg_zip_fileset_delivery',
                                                'sg_pixel_aspect_ratio',
                                                'sg_reformat_plates_to_deliverable',
                                                'sg_delivery_fileset',
                                                'sg_delivery_fileset_compression',
                                                'sg_delivery_qt_bitrate',
                                                'sg_delivery_qt_slate',
                                                'sg_delivery_burn_in',
                                                'sg_delivery_qt_codecs',
                                                'sg_delivery_qt_formats',
                                                'sg_delivery_folder_structure',
                                                'sg_color_space',
                                                'sg_project_color_management',
                                                'sg_project_color_management_config',
                                                'sg_timecode',
                                                'sg_upload_qt_formats',
                                                'sg_review_qt_codecs',
                                                'sg_review_burn_in',
                                                'sg_review_qt_slate',
                                                'sg_review_qt_formats',
                                                'sg_slate_frames_format',
                                                'sg_frame_leader',
                                                'sg_review_lut',
                                                'sg_type',
                                                'tank_name',
                                                'sg_3d_settings']
                                               )
        proj_info.update({'artist_name': ctx.user['name']})

        formats = publisher.shotgun.find("CustomNonProjectEntity01",
                                         [],
                                         ['code',
                                          'sg_format_height',
                                          'sg_format_width',
                                          ])
        proj_info.update({'formats': formats})

        local_storage = publisher.shotgun.find("LocalStorage",
                                               [],
                                               ["code",
                                                system_path_variable,
                                                "linux_path",
                                                "mac_path"])

        proj_sg_root = proj_info.get('sg_root')
        proj_info['local_storage'] = None
        if proj_sg_root:
            proj_info['local_storage'] = next(
                (ls for ls in local_storage if ls[system_path_variable] in proj_sg_root.get(system_root_variable)),
                None)

        if proj_info['sg_3d_settings']:
            sg_3d_settings = publisher.shotgun.find("CustomNonProjectEntity03",
                                                    [
                                                        ["id", "is", proj_info['sg_3d_settings'][0].get('id')]
                                                    ],
                                                    ['code',
                                                     'sg_primary_render_layer',
                                                     'sg_additional_render_layers',
                                                     'sg_render_engine',
                                                     ])

            proj_info.update({'sg_3d_settings': sg_3d_settings})

        return proj_info

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

        selected_nodes = nuke.selectedNodes()
        if not selected_nodes:
            nuke.message("<b style='color:salmon'>No Nodes Selected</b>")
            return

        selected_writes = [node for node in selected_nodes if node.Class() in ["WriteTank", "Write"]]
        if not selected_writes:
            nuke.message("<b style='color:salmon'>No Write Nodes Selected</b>")
            return 

        # filter selected_nodes for Version from both SsWrite and SGWrite types
        # To preserve compatibility
        selected_versions = []
        for node in selected_writes:
            knobs = {knob_name:node[knob_name].value() for knob_name in node.knobs()}
            if "Version" in [knobs.get('ssWriteType'),knobs.get('write_type')]:
                selected_versions.append(node)

        if not selected_versions:
            nuke.message("<b style='color:salmon'>No Version Write Nodes Selected.\nCan't locate render path.</b>")
            return 

        existing_paths = []
        for node in selected_versions:
            knobs = {knob_name:node[knob_name].value() for knob_name in node.knobs()}
            path = knobs.get('file') or knobs.get('cached_path')

            if path in existing_paths:
                continue
            else:
                self.process_write_node(node, parent_item)
                existing_paths.append(path)
                
    def process_write_node(self, node, parent_item):
        '''
        Processing for SG Write Nodes to prepare them for publishing

        :param node:  SG write node for processing
        :param parent_item:  The parent item for any sg write nodes collected
        '''

        publisher = self.parent
        engine = publisher.engine
        ctx = engine.context

        sg_writenode_app = engine.apps.get("tk-nuke-writenode")

        knobs = {knob_name:node[knob_name].value() for knob_name in node.knobs()}
        path = knobs.get('file') or knobs.get('cached_path')
        rendered_files = nutils.sequence_from_directory( path, split_seqs=True)
        if not rendered_files:
            self.logger.error("No rendered files for path %s" % path)
            return

        if isinstance(rendered_files, list):
            self.logger.error("Too many paths for %s\nplease check that render is not missing frames." % node.name())
            return 

        node_path,frame_range = rendered_files.split(" ")
        node_path = os.path.dirname(node_path)
        self.logger.info('Processing path: %s' % path)

        path_info = publisher.util.get_frame_sequence_path(
            {'path': node_path, 'ignore_folder_list': [], 'seek_folder_list': []})
        curr_fields = path_info.get('all_fields')

        # get project info
        project_info = self.project_info

        # get codec info
        codec_info = self.codec_info

        if curr_fields:

            # run one large shotgun search to collect entity, task, and step info
            search_fields = self._task_fields(curr_fields)

            # some renders don't have a task_name, we assign these to processing
            task_name = curr_fields.get('task_name') or "processing"
            filters = [
                ["project.Project.id", "is", ctx.project['id']],
                ["content", "is", task_name],
            ]

            entity_type = "entity.%s" % curr_fields['type']
            entity_code = "%s.code" % entity_type
            entity_name = curr_fields['Entity']
            filters.append([entity_code, "is", entity_name])

            entity_info = self.sgtk.shotgun.find_one("Task", filters, search_fields)

            entity = {}
            task = {}
            step = {}
            camera = {}

            # Parse search results into entity, task, step, and camera
            for key in entity_info:
                key_split = key.split(".")
                set_key = key_split[-1]

                if len(key_split) == 1:
                    task[key] = entity_info[key]

                if key_split[0] == 'step':
                    step[set_key] = entity_info[key]
                elif "sg_main_plate_camera" in key_split:
                    camera[set_key] = entity_info[key]
                else:
                    entity[set_key] = entity_info[key]

            # add task id to current fields (holdover from previous version of script)
            if task:
                self.logger.info("Task: %s" % (task))
                curr_fields['id'] = task['entity']['id']

            # define plugin visibility/enabled
            if step:
                step_bools = self._set_plugins_from_sg(step)

            # manual override for non-version renders
            if not curr_fields.get('task_name'):
                step_bools['sg_version_for_review'] = False
                step_bools['sg_publish_to_shotgun'] = True

            self.logger.info("Publish: %s | Version: %s" % (
                step_bools["sg_publish_to_shotgun"],
                step_bools["sg_version_for_review"]
            ))

        entity.update({
            'type': curr_fields['type'],
        })

        for info in path_info['path_info_returns']:

            if not info.get('fields'):
                self.logger.warning(">>>>> Unable to locate fields, bypassing...")
                continue

            properties = {
                # class properties to pass
                'user_info': self.user_info,
                'codec_info': self.codec_info,
                'project_info': self.project_info,
                'software_info': self.software_info,

                # assign properties from path_info values
                'fields': info['fields'],
                'folder_name': info['folder_name'],
                'frame_range': info['file_range'],
                'template': info['base_template'],

                # step and plugin booleons
                'step': step,
                'sg_publish_to_shotgun': step_bools.get('sg_publish_to_shotgun'),
                'sg_version_for_review': step_bools.get('sg_version_for_review'),
                # 'sg_slap_comp': layer_bools.get('sg_slap_comp'),

                # other shotgun dictionaries
                'entity_info': entity,
                'task': task,
                'camera': camera,

                # vendor info for outsource
                'vendor': curr_fields.get('vendor'),
                'workfile_dir': info.get('workfile_dir'),
                'publish_path': info.get('publish_path'),

                # templates and other quicktime info
                'extra_templates': self._get_extra_templates(info['fields']),
                'process_plugin_info': info['process_plugin_info'],
                'padded_file_name': info['padded_file_name']
            }

            for i in properties:
                self.logger.warning(">>>>> %s: %s" % (i, properties[i]))

        self.logger.warning(">>>>> entity: %s" % entity)

        # # get entity_info and split it 
        # entity_info = self.entity_info

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
        if entity.get("sg_head_in") and entity.get("sg_tail_out"):
            sg_range = "%s-%s" % (entity.get("sg_head_in"), entity.get("sg_tail_out") )

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
        item.properties["entity_info"] = entity

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

    #### IN DEVELOPMENT ####
    # def get_selected_reads(self, parent_item):
    #     """
    #     Process any selected read nodes
    #     """
    #     # selected_reads = nuke.selectedNodes()
    #     selected_reads = [node for node in nuke.selectedNodes() if node.Class() == 'Read']

    #     if not selected_reads:
    #         self.logger.debug("No Read Nodes Selected")
    #         return

    #     if len(selected_reads) > 2:
    #         self.logger.warning("Too Many Reads Selected")
    #         return

    #     self.logger.warning("Running: get_selected_reads")

    #     existing_paths = []
    #     for node in selected_reads:
    #         # some files rendered, use first frame to get a master path
    #         # which can be used for path-based operations
    #         folder = os.path.dirname(node['file'].value())

    #         # Prevent redundancies by checking for node file path in a list
    #         if folder in existing_paths:
    #             continue
    #         else:
    #             self.process_write_node(node, parent_item)
    #             existing_paths.append(folder)

    # def compare_context(self, node, engine):
    #     # check node type
    #     if node.Class() != "Read":
    #         self.logger.warning("Not a Read node")
    #         return (False, None)

    #     # check engine for writenode
    #     if "tk-nuke-writenode" not in engine.apps.keys():
    #         self.logger.warning("Cannot Generate Session Path: Please Save and Try Again")
    #         return
        
    #     # collect paths to compare and delete write
    #     new_sg_write = engine.apps["tk-nuke-writenode"].create_new_write_node("Exr", "Version")
    #     session_path = new_sg_write['cached_path'].value()
    #     nuke.delete(new_sg_write)

    #     node_path = node['file'].value()

    #     # create context items to compare
    #     session_context = sgtk.sgtk_from_path(session_path).context_from_path(session_path)

    #     try:
    #         node_context = sgtk.sgtk_from_path(node_path).context_from_path(node_path)
    #     except:
    #         self.logger.warning(">>>>> Failed to find node context")
    #         return

    #     self.logger.warning(">>>>> contexts")
    #     self.logger.warning(session_context)
    #     self.logger.warning(node_context.to_dict())

    #     result = node_context == session_context

    #     return (result, node_context)
    #### IN DEVELOPMENT ####

    def _set_plugins_from_sg(self, step):
        '''
        Assign correct plugins based on item step

        :param step: The item's task step from Shotgun
        '''

        # Set plugin defaults
        plugins_dict = {
            "sg_publish_to_shotgun": True,
            "sg_version_for_review": True,
            "sg_slap_comp": False
        }

        # Determine which plugins to load
        for key in plugins_dict:
            if step.get(key) != None:
                plugins_dict[key] = step.get(key)

            if key == "sg_version_for_review":
                if not step.get(key):
                    plugins_dict[key] = True
                else:
                    plugins_dict[key] = False

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

    def _get_extra_templates(self, item):
        '''
        Get assorted templates for assigning input/output locations

        :param item: the collector item for property assignment
        '''
        publisher = self.parent

        # find default templates
        nuke_review_template = publisher.engine.get_template_by_name("nuke_review_template2")
        review_process_json_template = publisher.engine.get_template_by_name("general_review_process_json")
        alembic_json_template = publisher.engine.get_template_by_name("alembic_review_process_json")
        alembic_output_template = publisher.engine.get_template_by_name('alembic_output_json')
        workfiles_template = None

        # find templates for the correct entity type
        if item['type'].lower() == "shot":
            review_process_json_template = publisher.engine.get_template_by_name("shot_review_process_json2")
            temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
            info_json_template = publisher.engine.get_template_by_name('shot_submission_json_file')
            qt_template = publisher.engine.get_template_by_name('resolve_shot_review_mov')
            qt_template_secondary = publisher.engine.get_template_by_name('resolve_shot_review_mov_secondary')
            workfiles_template = publisher.engine.get_template_by_name('nuke_shot_work')
        elif item['type'].lower() == "asset":
            review_process_json_template = publisher.engine.get_template_by_name("asset_review_process_json2")
            temp_root_template = publisher.engine.get_template_by_name("temp_asset_render_root")
            info_json_template = publisher.engine.get_template_by_name('asset_submission_json_file')
            qt_template = publisher.engine.get_template_by_name('resolve_asset_review_mov')
            qt_template_secondary = publisher.engine.get_template_by_name('resolve_asset_review_mov_secondary')
            workfiles_template = publisher.engine.get_template_by_name('nuke_asset_work')
        else:
            info_json_template = publisher.engine.get_template_by_name('info_json_file')
            temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
            # fixme defaults for qt_template and qt_template_secondary

        extra_templates = {
            'nuke_review_template': nuke_review_template,
            'temp_root_template': temp_root_template,
            'info_json_template': info_json_template,
            'review_process_json_template': review_process_json_template,
            'qt_template': qt_template,
            'qt_template_secondary': qt_template_secondary,
            'workfiles_template': workfiles_template,
            'alembic_template': alembic_json_template,
            'alembic_output_template': alembic_output_template,
        }

        return extra_templates

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
