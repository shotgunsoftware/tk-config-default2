    # Copyright (c) 2017 Shotgun Software Inc.
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
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.

    This collector hook is used to collect individual files that are browsed or
    dragged and dropped into the Publish2 UI. It can also be subclassed by other
    collectors responsible for creating items for a file to be published such as
    the current Maya session file.

    This plugin centralizes the logic for collecting a file, including
    determining how to display the file for publishing (based on the file
    extension).

    In addition to creating an item to publish, this hook will set the following
    properties on the item::

        path - The path to the file to publish. This could be a path
            representing a sequence of files (including a frame specifier).

        sequence_paths - If the item represents a collection of files, the
            plugin will populate this property with a list of files matching
            "path".

    """

    @property
    def user_info(self):

        publisher = self.parent
        ctx = publisher.engine.context 
        user_fields =[
            'login',
            'sg_ip_address'
        ]
        user_filter =[
            ['id', 'is', ctx.user['id']],
        ]
        user_info = publisher.shotgun.find(
            'HumanUser',
            user_filter,
            user_fields
            )    

        return user_info

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
        proj_info.update({'artist_name' : ctx.user['name']})

        formats = publisher.shotgun.find("CustomNonProjectEntity01",
        [],
        ['code',
        'sg_format_height',
        'sg_format_width',
        ])
        proj_info.update({'formats' : formats})

        local_storage = publisher.shotgun.find("LocalStorage",
        [],
        ["code",
        "windows_path",
        "linux_path",
        "mac_path"])
        
        if "win" in sys.platform:
            path_root = "windows_path"
            sg_root = "local_path_windows"
        elif sys.platform == "linux":
            path_root = "linux_path"
            sg_root = "local_path_linux"

        local_storage_match = next((ls for ls in local_storage if ls[path_root] in proj_info['sg_root'][sg_root]), None)
        proj_info['local_storage'] = local_storage_match

        if proj_info['sg_3d_settings']:
            sg_3d_settings = publisher.shotgun.find("CustomNonProjectEntity03",
            [],
            ['code',
            'sg_primary_render_layer',
            'sg_additional_render_layers',
            'sg_render_engine',
            ])

            proj_info.update({'sg_3d_settings' : sg_3d_settings})

        return proj_info         
  
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
        # ['sg_pipeline_tools', 'is', True]
        ]
        
        software_fields = [
        'code',
        'products',
        'windows_path',
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
    def common_file_info(self):
        """
        A dictionary of file type info that allows the basic collector to
        identify common production file types and associate them with a display
        name, item type, and config icon.

        The dictionary returned is of the form::

            {
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                <Publish Type>: {
                    "extensions": [<ext>, <ext>, ...],
                    "icon": <icon path>,
                    "item_type": <item type>
                },
                ...
            }

        See the collector source to see the default values returned.

        Subclasses can override this property, get the default values via
        ``super``, then update the dictionary as necessary by
        adding/removing/modifying values.
        """

        if not hasattr(self, "_common_file_info"):

            # do this once to avoid unnecessary processing
            self._common_file_info = {
                "Alembic Cache": {
                    "extensions": ["abc"],
                    "icon": self._get_icon_path("alembic.png"),
                    "item_type": "file.alembic",
                },
                "3dsmax Scene": {
                    "extensions": ["max"],
                    "icon": self._get_icon_path("3dsmax.png"),
                    "item_type": "file.3dsmax",
                },
                "Hiero Project": {
                    "extensions": ["hrox"],
                    "icon": self._get_icon_path("hiero.png"),
                    "item_type": "file.hiero",
                },
                "Houdini Scene": {
                    "extensions": ["hip", "hipnc"],
                    "icon": self._get_icon_path("houdini.png"),
                    "item_type": "file.houdini",
                },
                "Maya Scene": {
                    "extensions": ["ma", "mb"],
                    "icon": self._get_icon_path("maya.png"),
                    "item_type": "file.maya",
                },
                "Motion Builder FBX": {
                    "extensions": ["fbx"],
                    "icon": self._get_icon_path("fbx.png"),
                    "item_type": "file.motionbuilder",
                },
                "Nuke Script": {
                    "extensions": ["nk"],
                    "icon": self._get_icon_path("nuke.png"),
                    "item_type": "file.nuke",
                },
                "Photoshop Image": {
                    "extensions": ["psd", "psb"],
                    "icon": self._get_icon_path("photoshop.png"),
                    "item_type": "file.photoshop",
                },
                "Rendered Image": {
                    "extensions": ["dpx", "exr", "png", "jpg", "jpeg"],
                    "icon": self._get_icon_path("image_sequence.png"),
                    "item_type": "file.image",
                },
                "Texture Image": {
                    "extensions": ["tx", "tga", "dds", "rat"],
                    "icon": self._get_icon_path("texture.png"),
                    "item_type": "file.texture",
                },
                "DMP": {
                    "extensions": ["tif", "tiff"],
                    "icon": self._get_icon_path("dmp.png"),
                    "item_type": "file.image",
                },                
                "3D Equalizer": {
                    "extensions": ["3de"],
                    "icon": self._get_icon_path("lens.png"),
                    "item_type": "file.3de",
                },                
            }

        return self._common_file_info

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
        return {}

    @property
    def step_fields(self):

        search_fields = [
            'id', 
            'code', 
            'sg_department',
            'sg_publish_to_shotgun', 
            'sg_version_for_review', 
            'sg_slap_comp', 
            'sg_review_process_type', 
            'entity_type',
            ]
        return search_fields

    @property
    def step_info(self):
        '''
        A collector that gathers all existing pipeline steps to build 2 lists:
        1) publish_codes: the names of all steps that should be published to Shotgun*
        2) version_codes: the names of all steps that should publish review versions
        3) sg_slap_comp: option to create a slap comp Version for review

        *publish_codes also includes all SSVFX Shotgun WriteNode render types
        ** This needs to be hand-coded at the moment. Sorry...
        '''

        publisher = self.parent
        search_fields = self.step_fields
        steps_info = publisher.shotgun.find("Step", [], search_fields)

        return steps_info
    
    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        # default implementation does not do anything
        pass

    def process_file(self, settings, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """
        entity = None
        curr_fields = None
        step = None    
        task = None
        primary_render_folder = []
        additional_render_folder = []
        path = re.sub(r"^[/\\]{2}pix[a-zA-Z0-9_\.]+", r"//pix_artist", path)

        publisher = self.parent
        ctx = publisher.engine.context

        # Path string for manipulation
        path = str(sgtk.util.ShotgunPath.normalize(path)).replace('\\','/')
        self.logger.info('Submission path is: ' + path)

        path_info = publisher.util.get_frame_sequence_path( {'path': path, 'ignore_folder_list': [], 'seek_folder_list': []} )
        # for i in path_info:
            # self.logger.warning( ">>>>> path_info template path %s" % i['tmp_path'] )
            # self.logger.warning( ">>>>> path_info template info %s" % i['work_template'] )
            # self.logger.warning( ">>>>> path_info current fields %s" % i['fields'] )
            # for j in i.keys():
            #     self.logger.warning( ">>>>> %s: %s" % ( j, i[j] ) )

        # self.logger.warning( ">>>>> Context Info: %s" % ctx.to_dict() )


        # Attempt to get entity elements from Templates
        # Default to manual entry if there is no Template
        tk = sgtk.sgtk_from_path(path)
        if tk:
            work_template = tk.template_from_path(path)
            if work_template:
                curr_fields = work_template.get_fields(path)
                # self.logger.warning("collector work_template %s" %(work_template))
                # self.logger.warning("collector curr_fields %s" %(curr_fields))
            else:
                self.logger.debug("Could not get work_template from: %s" %(path))
        else:
            self.logger.debug("Could not get TK from path!") 

        entity = {
            'name': '',
            'output': '',
            'version_number': curr_fields.get( 'version' ) or '',
            'task_name': curr_fields.get( 'task_name' ) or '',
            'vendor': curr_fields.get( 'vendor' ) or ''
            }

        task_fields =[
            "step",
            "entity"
            ]

        filters = [
            ["content", "is", entity['task_name']],
            ["project.Project.id", "is", ctx.project['id']]  
            ]

        if curr_fields:

            if "Shot" in curr_fields.keys():
                entity.update( {
                        'Shot': curr_fields['Shot'],
                        'type': "Shot"
                    })

                filters.append( ["entity.Shot.code", "is", entity['Shot']] )

            elif "Asset" in curr_fields.keys():
                entity.update({
                        'Asset': curr_fields['Asset'],
                        'type': "Asset"                        
                    })

                filters.append( ["entity.Asset.code", "is", entity['Asset']] )

            else:
                self.logger.info("Not an Asset or Shot entity.")
            
            task = self.sgtk.shotgun.find_one("Task", filters, task_fields)

            if task:
                self.logger.info("Task: %s" %(task))
                entity['id'] = task['entity']['id']
                step = next((i for i in self.step_info if i['id'] == task['step']['id']), None)
                if step:
                    self.logger.info("Step: %s" %(step))
                    if step['sg_department'] == "3D":
                        if self.project_info['sg_3d_settings']:
                            if self.project_info['sg_3d_settings'][0]['sg_primary_render_layer']:
                                primary_render_folder = self.project_info['sg_3d_settings'][0]['sg_primary_render_layer'].split(",")
                            if self.project_info['sg_3d_settings'][0]['sg_additional_render_layers']:
                                for additional in self.project_info['sg_3d_settings'][0]['sg_additional_render_layers'].split(","):
                                    additional_render_folder.append(additional)
                                self.logger.debug("Collected additionals %s. Will publish separately." % (additional_render_folder))

                
        # handle files and folders differently
        if os.path.isdir(path):
            self.logger.info("Collecting folder %s" %(path,))
            self._collect_folder(tk, self.user_info, parent_item, path, entity, step, task, primary_render_folder, additional_render_folder)
        else:
            self.logger.info("Collecting file  %s" %(path,))
            return self._collect_file(tk, self.user_info, parent_item, path, entity, step, task, primary_render_folder, additional_render_folder)
    
    def _collect_file(self, tk, user_info, parent_item, path, entity, step, task, primary_render_folder, additional_render_folder, frame_sequence=False):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :param frame_sequence: Treat the path as a part of a sequence
        :returns: The item that was created
        """
        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        publisher = self.parent
        evaluated_path = sgtk.util.ShotgunPath.normalize(path)

        # get info for the extension
        item_info = self._get_item_info(evaluated_path)
        item_type = item_info["item_type"]
        type_display = item_info["type_display"]
        thumbnail_path = None
        is_sequence = False

        if frame_sequence:
            # replace the frame number with frame spec
            seq_path = publisher.util.get_frame_sequence_path(evaluated_path)
            if seq_path:
                evaluated_path = seq_path
                type_display = "%s Sequence" % (type_display,)
                item_type = "%s.%s" % (item_type, "sequence")
                is_sequence = True

        display_name = publisher.util.get_publish_name(evaluated_path, sequence=is_sequence)
        self.logger.debug("Collect file display name is %s obtained from path" % (display_name,))
        # create and populate the item
        file_item = parent_item.create_item(item_type, type_display, display_name)
        file_item.set_icon_from_path(item_info["icon_path"])

        # if the supplied path is an image, use the path as # the thumbnail.
        if item_type.startswith("file.image") or item_type.startswith("file.texture"):
            file_item.set_thumbnail_from_path(evaluated_path)
            thumbnail_path = evaluated_path
            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False
        else:
            self.logger.debug("Using icon as thumbnail: %s" %(item_info["icon_path"],))
            file_item.set_thumbnail_from_path(item_info["icon_path"])
            thumbnail_path = item_info["icon_path"]
        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        file_item.properties["path"] = evaluated_path
        # Get version info
        content_version_name = os.path.basename(os.path.split(evaluated_path)[0])

        first_frame_search = self._get_frame_number(evaluated_path)
        frame_range = "1-1"
        if first_frame_search:
            frame_range = first_frame_search.group(1) 
        if is_sequence:
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            file_item.properties["sequence_paths"] = [evaluated_path]
        self.logger.debug("Frame range: %s" % (frame_range))
        folder_name = os.path.basename(evaluated_path)

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        file_item.properties['entity_info']={}
        file_item.properties['entity_info']['id']=None
        if entity:
            file_item.properties['entity_info'] = entity
            file_item.properties["pipeline_step"] = entity['task_name']
        else:
            self.logger.debug("No entity given.")
            file_item.properties["pipeline_step"] = None

        file_item.properties["process_info"] = {}
        file_item.properties["project_info"] = self.project_info
        file_item.properties["software_info"] = self.software_info
        file_item.properties["codec_info"] = self.codec_info
        file_item.properties["user_info"] = user_info
        file_item.properties["vendor"] = entity['vendor']

        file_item.properties["path"] = evaluated_path
        # file_item.properties["sequence_paths"] = img_seq_files
        file_item.properties["thumbnail_path"] = thumbnail_path
        file_item.properties["content_version_name"] = content_version_name
        file_item.properties["frame_range"] = frame_range        
        file_item.properties["folder_name"] = folder_name      
        file_item.properties['step_fields'] = self.step_fields
        file_item.properties['step'] = step
        file_item.properties['template'] = None
        file_item.properties['workfile_template'] = None
        file_item.properties['fields'] = None

        if step:   
            for k,v in self._set_plugins_from_sg(step['id']).items():
                file_item.properties[k] = v
        else:
            for k,v in self._set_plugins_from_sg(None).items():
                file_item.properties[k] = v    

        # Template set
        template = tk.template_from_path(evaluated_path)
        if template:
            self.logger.debug("File template: %s" % (template.name))
            file_item.properties['template'] = template
            file_item.properties['fields'] = template.get_fields(evaluated_path)
            if template.name == "incoming_outsource_shot_version_psd":
                file_item.properties['fields']['task_name'] = file_item.properties['fields']['task_name'].lower()
                file_item.properties['workfile_template'] = publisher.engine.get_template_by_name('psd_shot_work').apply_fields(file_item.properties['fields'])
            
            if template.name == "incoming_outsource_shot_version_tif":
                file_item.properties['fields']['task_name'] = file_item.properties['fields']['task_name'].lower()
                file_item.properties['workfile_template'] = publisher.engine.get_template_by_name('psd_shot_version_tif').apply_fields(file_item.properties['fields'])           

            if file_item.properties['workfile_template']:
                file_item.properties['publish_path'] = file_item.properties['workfile_template']
                self.logger.info("Publish will copy file to here and publish: %s" % (file_item.properties['workfile_template']))
        else:
            self.logger.warning("Could not get template from %s" %(evaluated_path))

        # self.logger.warning(">>>>> _collect_file path: %s" % evaluated_path)
        # self.logger.warning(">>>>> _collect_file template: %s" % template)

        # Set Context
        try:
            self.logger.info('Context (Task, Link) is ' + str(self.sgtk.context_from_entity("Task", task["id"])))
            file_item.context = self.sgtk.context_from_entity("Task", task["id"])
        except:
            self.logger.warning('Could not auto-set the context for this item. Not a recognised template patern/naming convention. Please set Task/Link manually')
            file_item.context = None

        # for i in file_item.properties.to_dict():
        #     self.logger.warning( ">>>>> %s: %s" % ( i, file_item.properties.to_dict()[i] ) )
        
        return file_item

    def _collect_folder(self, tk, user_info, parent_item, folder, entity, step, task, primary_render_folder, additional_render_folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """
        ignore_files = ["Thumbs.db"]
        ignore_folders = [".mayaSwatches"]
        folder_items = []
            
        def get_seq_item(folder, sub_folders = False):

            self.logger.debug("Attempting to get seq items in %s" %(folder))
            img_sequences = publisher.util.get_frame_sequences(
                os.path.normpath(folder),
                self._get_image_extensions()
            )
            
            if not img_sequences:
                self.logger.debug("Could not find frame sequences.")
                return None
            else:
                self.logger.debug("Image sequence count: %s" % str(len(img_sequences)))
                for (image_seq_path, img_seq_files) in img_sequences:
                    # folder_name = ""
                    folder_name = os.path.basename(folder)
                    # get info for the extension
                    item_info = self._get_item_info(image_seq_path)
                    item_type = item_info["item_type"]
                    type_display = item_info["type_display"]

                    # the supplied image path is part of a sequence. alter the
                    # type info to account for this.
                    type_display = "%s Sequence" % (type_display,)
                    item_type = "%s.%s" % (item_type, "sequence")
                    icon_name = "image_sequence.png"
                    frame_range = "1-1"

                    # Get version info
                    content_version_name = os.path.basename(os.path.split(image_seq_path)[0])
                    version_number = publisher.util.get_version_number(image_seq_path)

                    # Get frame range from first/last file path string
                    # from sorted SEQ list of
                    img_seq_files.sort()
                    first_frame_file = img_seq_files[0]
                    last_frame_file = img_seq_files[-1]

                    first_frame_search = self._get_frame_number(first_frame_file)
                    last_frame_search = self._get_frame_number(last_frame_file)
                    if (first_frame_search and 
                    last_frame_search):
                        frame_range = (first_frame_search.group(1) +  
                                        "-" +
                                        last_frame_search.group(1))
                        self.logger.debug("Frame range from path: %s" % frame_range)
                    else:
                        self.logger.debug("Could not find frame numbers.")

                    display_name = "%s - %s" % (publisher.util.get_publish_name(first_frame_file, sequence=True),folder_name)
                    self.logger.debug("Collect folder display name: %s" % (display_name))
                    if version_number:
                        display_name += "- v%s" % (str(version_number).zfill(3))
                    
                    # self.logger.warning(">>>>> item_type: %s" % item_type)
                    # self.logger.warning(">>>>> type_display: %s" % type_display)
                    # self.logger.warning(">>>>> display_name: %s" % display_name )
                    # create and populate the item
                    file_item = parent_item.create_item(
                        item_type,
                        type_display,
                        display_name 
                    )
                    icon_path = self._get_icon_path(icon_name)
                    file_item.set_icon_from_path(icon_path)
                    # get the first frame of the sequence. we'll use this for the
                    # thumbnail and to generate the display name
                    file_item.set_thumbnail_from_path(first_frame_file)
                    if os.path.exists(first_frame_file):
                        thumbnail_path = first_frame_file
                    else:
                        thumbnail_path = None   
                    
                    # Get additional info from templates
                    # error suppression for rare cases where the template search faults
                    try:
                       template = tk.template_from_path(image_seq_path)
                       fields = {}
                    except:
                        self.logger.warning("Error retrieving template.")
                        template = None
                        fields = {}
 
                    if template:
                        self.logger.debug("File template: %s" % (template.name))
                        fields = template.get_fields(image_seq_path)
                    
                        if template.name == 'shot_plate_main_undistorted':
                            file_item.properties['publish_type'] = "Undistorted Main Plate"
                    else:
                        template =  tk.template_from_path(folder)
                        if template:
                            self.logger.debug("Folder template: %s" % (template.name))                            
                            fields = template.get_fields(folder)

                    self.logger.debug("fields %s" %(fields))

                    # disable thumbnail creation since we get it for free
                    file_item.thumbnail_enabled = False
                    # all we know about the file is its path. set the path in its
                    # properties for the plugins to use for processing.
                    file_item.properties['entity_info']={}
                    file_item.properties['entity_info']['id']=None

                    if entity:
                        file_item.properties['entity_info'] = entity                        
                        file_item.properties["pipeline_step"] = entity['task_name']
                    else:
                        file_item.properties["pipeline_step"] = None

                    file_item.properties["project_info"] = self.project_info
                    file_item.properties["software_info"] = self.software_info
                    file_item.properties["codec_info"] = self.codec_info

                    file_item.properties["process_info"] = {}
                    file_item.properties["user_info"] = user_info
                    file_item.properties["vendor"] = entity['vendor']                    
                    
                    file_item.properties["path"] = image_seq_path
                    file_item.properties["sequence_paths"] = img_seq_files
                    file_item.properties["thumbnail_path"] = thumbnail_path
                    file_item.properties["content_version_name"] = content_version_name
                    file_item.properties["frame_range"] = frame_range        
                    file_item.properties["folder_name"] = folder_name
                    file_item.properties['step_fields'] = self.step_fields                    
                    file_item.properties['step'] = step
                    file_item.properties['fields'] = fields                    
                    file_item.properties['template'] = template

                    # self.logger.warning(">>>>> get_seq_item path: %s" % folder)
                    # self.logger.warning(">>>>> get_seq_item template: %s" % template)


                    # create task context to replace project-level context
                    if step:   
                        for k,v in self._set_plugins_from_sg(step['id']).items():
                            file_item.properties[k] = v
                    else:
                        for k,v in self._set_plugins_from_sg(None).items():
                            file_item.properties[k] = v   
                                                 
                    # Set Context
                    try:
                        self.logger.info('Context (Task, Link) is ' + str(self.sgtk.context_from_entity("Task", task["id"])))
                        file_item.context = self.sgtk.context_from_entity("Task", task["id"])
                    except:
                        self.logger.warning('Could not auto-set the context for this item. Not a recognised template patern/naming convention. Please set Task/Link manually')
                        file_item.context = None

                    self.logger.info("Collected file: %s" % (image_seq_path,))

                    # for i in file_item.properties.to_dict():
                    #     self.logger.warning( ">>>>> %s: %s" % ( i, file_item.properties.to_dict()[i] ) )

                    return file_item

        def get_single_item(file_item, path, display_name, entity, step, frame_range):

            self.logger.debug("Getting single item: %s" %(path,))

            tk = sgtk.sgtk_from_path(path)

            new_item = parent_item.create_item(
                file_item["item_type"],
                file_item["type_display"],
                display_name 
            )
            
            new_item.properties['path'] = path
            new_item.properties["publish_to_shotgun"] = True
            new_item.properties["sg_version_for_review"] = False
            new_item.set_icon_from_path(file_item['icon_path'])
            new_item.properties['step'] = step
            new_item.properties['frame_range'] = frame_range
            
            # Attempt to find a frame range for items without one
            # Default to None if no range can be established
            if not frame_range:
                # Set range for single item
                if not os.path.isdir(path):
                    first_frame_file = path

                    first_frame_search = self._get_frame_number(first_frame_file)

                    if first_frame_search:
                        frame_range = first_frame_search.group(1)
                        self.logger.debug("Frame range from path: %s" % frame_range)

                else:
                    # set range for a sequence
                    frame_list = sorted( os.listdir( path ) )
                    first_frame_file = frame_list[0]
                    last_frame_file = frame_list[-1]

                    first_frame_search = self._get_frame_number(first_frame_file)
                    last_frame_search = self._get_frame_number(last_frame_file)

                    if (first_frame_search and last_frame_search):
                        frame_range = (first_frame_search.group(1) +  
                                        "-" +
                                        last_frame_search.group(1))
                        self.logger.debug("Frame range from directory paths: %s" % frame_range)

            # verify and apply frame range amendments
            new_item.properties['frame_range'] = frame_range
            
            new_item.properties['file_info'] = publisher.util.get_file_path_components(path)
            new_item.properties["software_info"] = self.software_info      

            # Error handling to deal with rare instances where template searches break the collection process
            try:
                new_item_file_template = tk.template_from_path(path)
                new_item_folder_template = tk.template_from_path(new_item.properties['file_info']['folder'])
            except:
                new_item_file_template = None
                new_item_folder_template = None

            # self.logger.warning(">>>>> get_single_item path: %s" % path)
            # self.logger.warning(">>>>> get_single_item new_item_folder_template: %s" % new_item_folder_template)
            

            new_item.properties['template'] = None
            new_item.properties['template_file'] = None
            new_item.properties['fields'] = None

            if new_item_folder_template:
                new_item.properties['template'] = new_item_folder_template
                new_item.properties['fields'] = new_item_folder_template.get_fields(new_item.properties['file_info']['folder'])

            if new_item_file_template:
                new_item.properties['template_file'] = new_item_file_template                

            new_item.properties["project_info"] = self.project_info
            new_item.properties["user_info"] = user_info
            
            new_item.properties['entity_info']={}
            new_item.properties['entity_info']['id']=None
            
            new_item.properties['codec_info'] = self.codec_info
            new_item.properties['step_fields'] = self.step_fields   

            if entity:
                new_item.properties['entity_info'] = entity
                                    # create task context to replace project-level context
            if step:   
                for k,v in self._set_plugins_from_sg(step['id']).items():
                    new_item.properties[k] = v
            else:
                for k,v in self._set_plugins_from_sg(None).items():
                    new_item.properties[k] = v

            # Set Context
            try:
                self.logger.debug('Context is %s. Display name: %s' % (str(self.sgtk.context_from_entity("Task", task["id"])), display_name))
                new_item.context = self.sgtk.context_from_entity("Task", task["id"])
            except:
                self.logger.warning('Could not auto-set the context for this item. Not a recognised template patern/naming convention. Please set Task/Link manually')
                new_item.context = None

            self.logger.warning(">>>>> NEW ITEM PROPERTIES")
            for i in new_item.properties.to_dict():
                self.logger.warning( ">>>>> %s: %s" % ( i, new_item.properties.to_dict()[i] ) )
            self.logger.warning(">>>>> NEW ITEM PROPERTIES END")

            return new_item

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        publisher = self.parent   
        folder = sgtk.util.ShotgunPath.normalize(folder)

        # Get frame range
        frame_range = None

        # frame range for single items in folders
        if len(os.listdir(folder) ) == 1:
            frame_range_path = os.path.join(folder, os.listdir(folder)[0] )
            evaluated_path = sgtk.util.ShotgunPath.normalize(frame_range_path)

            first_frame_search = self._get_frame_number(evaluated_path)
            
            frame_range = "1-1"
            if first_frame_search:
                frame_range = first_frame_search.group(1) 

            self.logger.debug("Frame range: %s" % (frame_range))

        # frame range for matchmoves
        if step != None:
            if step['id'] == 4:
                sg_frame_range = publisher.shotgun.find_one("Shot", 
                                                        [["id", "is", task['entity']['id']]],
                                                        ['sg_head_in', 'sg_tail_out'])
                
                if sg_frame_range['sg_head_in'] and sg_frame_range['sg_tail_out']:
                    frame_range = "%s-%s" % (sg_frame_range['sg_head_in'], sg_frame_range['sg_tail_out'])

        if primary_render_folder:
            self.logger.info("Searching for primary renders in:")
            for search_folder in primary_render_folder:
                self.logger.info(" - %s" % (search_folder))
        else:
            self.logger.debug("No primary folder set. Search all..")
        
        for root, sub_folder ,files in os.walk(folder):

            # Continue if certain ignore folders are met
            if(os.path.basename(root) in ignore_folders):
                continue

            # Main walk area
            if (root != folder):
                self.logger.debug("Sub folder(s):")
                self.logger.debug(sub_folder)
                files = list(set(files) - set(ignore_files))
                if len(files)>0:
                    if len(files) == 1:
                        self.logger.debug("Found ONE file in: %s" % (root,))
                        file_item = self._get_item_info(os.path.join(root,files[0]))
                        if primary_render_folder:
                            if os.path.basename(root) not in primary_render_folder:
                                file_item.properties["sg_slap_comp"] = False                              
                        single_item = get_single_item(file_item, os.path.join(root,files[0]), "%s" %(files[0],) , entity, step, frame_range)
                        folder_items.append(single_item)
                    elif len(files)>1:
                        self.logger.debug("Found %s files in: %s" % (len(files),root))
                        # display_name += "- %s" % (root)
                        seq_file_items = get_seq_item(root, sub_folders=True)
                        if primary_render_folder:
                            if os.path.basename(root) not in primary_render_folder:
                                seq_file_items.properties["sg_slap_comp"] = False                        
                        if seq_file_items:
                            folder_items.append(seq_file_items)
               
            else:
                # check for files that are in the root folder
                if len(files)==1:
                    # self.logger.warning(files)
                    file_item = self._get_item_info(os.path.join(root,files[0]))
                    single_item = get_single_item(file_item, os.path.join(root,files[0]), "%s" %(files[0],) , entity, step, frame_range)
                    folder_items.append(single_item)
                elif len(files)>1:
                    self.logger.debug("Found %s files in: %s" % (len(files),root))
                    seq_file_items = get_seq_item(sgtk.util.ShotgunPath.normalize(root))
                    if not seq_file_items:
                        for index, file in enumerate(files):
                            file_item = self._get_item_info(os.path.join(root,file))
                            single_item = get_single_item(file_item, os.path.join(root,files[index]), "%s" %(file,) , entity, step, frame_range)
                            folder_items.append(single_item)
                else:
                    self.logger.warn("Found %s files in: %s" % (len(files),root))

        return folder_items
    
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

    def _get_item_info(self, path):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param path: The file path to identify type info for

        :return: A dictionary of information about the item to create::

            # path = "/path/to/some/file.0001.exr"

            {
                "item_type": "file.image.sequence",
                "type_display": "Rendered Image Sequence",
                "icon_path": "/path/to/some/icons/folder/image_sequence.png",
                "path": "/path/to/some/file.%04d.exr"
            }

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """

        publisher = self.parent

        # extract the components of the supplied path
        file_info = publisher.util.get_file_path_components(path)
        extension = file_info["extension"]
        filename = file_info["filename"]

        # default values used if no specific type can be determined
        type_display = "File"
        item_type = "file.unknown"

        # keep track if a common type was identified for the extension
        common_type_found = False

        icon_path = None

        # look for the extension in the common file type info dict
        for display in self.common_file_info:
            type_info = self.common_file_info[display]

            if extension in type_info["extensions"]:
                # found the extension in the common types lookup. extract the
                # item type, icon name.
                type_display = display
                item_type = type_info["item_type"]
                icon_path = type_info["icon"]
                common_type_found = True
                break

        if not common_type_found:
            # no common type match. try to use the mimetype category. this will
            # be a value like "image/jpeg" or "video/mp4". we'll extract the
            # portion before the "/" and use that for display.
            (category_type, _) = mimetypes.guess_type(filename)

            if category_type:

                # mimetypes.guess_type can return unicode strings depending on
                # the system's default encoding. If a unicode string is
                # returned, we simply ensure it's utf-8 encoded to avoid issues
                # with toolkit, which expects utf-8
                if isinstance(category_type, unicode):
                    category_type = category_type.encode("utf-8")

                # the category portion of the mimetype
                category = category_type.split("/")[0]

                type_display = "%s File" % (category.title(),)
                item_type = "file.%s" % (category,)
                icon_path = self._get_icon_path("%s.png" % (category,))

        # fall back to a simple file icon
        if not icon_path:
            icon_path = self._get_icon_path("file.png")

        # everything should be populated. return the dictionary
        return dict(
            item_type=item_type,
            type_display=type_display,
            icon_path=icon_path,
        )

    def _get_icon_path(self, icon_name, icons_folders=None):
        """
        Helper to get the full path to an icon.

        By default, the app's ``hooks/icons`` folder will be searched.
        Additional search paths can be provided via the ``icons_folders`` arg.

        :param icon_name: The file name of the icon. ex: "alembic.png"
        :param icons_folders: A list of icons folders to find the supplied icon
            name.

        :returns: The full path to the icon of the supplied name, or a default
            icon if the name could not be found.
        """
        # ensure the publisher's icons folder is included in the search
        app_icon_folder = os.path.join(self.disk_location, "icons")

        # build the list of folders to search
        if icons_folders:
            icons_folders.append(app_icon_folder)
        else:
            icons_folders = [app_icon_folder]

        # keep track of whether we've found the icon path
        found_icon_path = None

        # iterate over all the folders to find the icon. first match wins
        for icons_folder in icons_folders:
            icon_path = os.path.join(icons_folder, icon_name)
            if os.path.exists(icon_path):
                found_icon_path = icon_path
                break
            
        # supplied file name doesn't exist. return the default file.png image
        if not found_icon_path:
            found_icon_path = os.path.join(app_icon_folder, "file.png")


        return found_icon_path

    def _get_image_extensions(self):

        if not hasattr(self, "_image_extensions"):

            image_file_types = [
                "Photoshop Image",
                "Rendered Image",
                "Texture Image"
            ]
            image_extensions = set()

            for image_file_type in image_file_types:
                image_extensions.update(
                    self.common_file_info[image_file_type]["extensions"])

            # get all the image mime type image extensions as well
            mimetypes.init()
            types_map = mimetypes.types_map
            for (ext, mimetype) in types_map.iteritems():
                if mimetype.startswith("image/"):
                    image_extensions.add(ext.lstrip("."))

            self._image_extensions = list(image_extensions)

        return self._image_extensions

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
