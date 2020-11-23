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
import pprint
import sys
import re
import sgtk
import datetime
import time

# find SSVFX/Deadline plugins
log = sgtk.LogManager.get_logger(__name__)

try:
    ssvfx_script_path = ""#C:\\Users\\shotgunadmin\\Scripts\\Pipeline\\ssvfx_scripts"
    if os.path.exists(ssvfx_script_path):
        pipeline_root = "C:\\Users\\shotgunadmin\\Scripts"
    else:
        if "SSVFX_PIPELINE" in os.environ.keys():
            pipeline_root =  os.environ["SSVFX_PIPELINE"]
            ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")
            if os.path.exists(ssvfx_script_path):
                pass
            else:
                log.debug("!!!!!! Could not find %s" %(ssvfx_script_path,))
            log.debug("Found env var path: %s" %(ssvfx_script_path,))
        else:
            log.debug("SSVFX_PIPELINE not in env var keys. Using explicit")
            pipeline_root = "\\\\10.80.8.252\\VFX_Pipeline"
            ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")

    sys.path.append(ssvfx_script_path)
    from thinkbox.deadline import deadline_manager
    from thinkbox.deadline import deadline_submission3
    from general.file_functions import file_strings
    from general.data_management import json_manager
    from software.nuke.nuke_command_line  import nuke_cmd_functions as ncmd
    from shotgun import shotgun_utilities
except:
    raise Exception("Could not load on of the studio modules!")

HookBaseClass = sgtk.get_hook_baseclass()

class UploadVersionPlugin(HookBaseClass):
    """
    Plugin for sending quicktimes and images to shotgun for review.
    """
                                                             
    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            "icons",
            "review.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Upload for review"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        publisher = self.parent

        shotgun_url = publisher.sgtk.shotgun_url

        media_page_url = "%s/page/media_center" % (shotgun_url,)
        review_url = "https://www.shotgunsoftware.com/features/#review"

        return """
        Upload the file to Shotgun for review.<br><br>

        A <b>Version</b> entry will be created in Shotgun and a transcoded
        copy of the file will be attached to it. The file can then be reviewed
        via the project's <a href='%s'>Media</a> page, <a href='%s'>RV</a>, or
        the <a href='%s'>Shotgun Review</a> mobile app.
        """ % (media_page_url, review_url, review_url)


    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

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
        return {
            "File Extensions": {
                "type": "str",
                "default": "jpeg, jpg, png, mov, mp4, dpx, exr",
                "description": "File Extensions of files to include"
            },
            "Upload": {
                "type": "bool",
                "default": True,
                "description": "Upload content to Shotgun?"
            },
            "Link Local File": {
                "type": "bool",
                "default": True,
                "description": "Should the local file be referenced by Shotgun"
            },

        }

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """

        # we use "video" since that's the mimetype category.
        return ["file.image", "file.video", "file.image.sequence"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """
        accept = {"accepted": False}
        publisher = self.parent
        file_path = item.properties["path"]

        file_info = publisher.util.get_file_path_components(file_path)
        extension = file_info["extension"].lower()

        valid_extensions = []

        for ext in settings["File Extensions"].value.split(","):
            ext = ext.strip().lstrip(".")
            valid_extensions.append(ext)

        if extension in valid_extensions:
            # return the accepted info
            accept = {"accepted": True}
            if item.properties.get("sg_version_for_review"):
                accept.update({'checked': True})
                # log the accepted file and display a button to reveal it in the fs
                self.logger.info(
                    "Version upload plugin accepted: %s" % (file_path,),
                    extra={
                        "action_show_folder": {
                            "path": file_path
                        }
                    }
                )
            else:
                accept.update({'checked': False})
                accept.update({'enabled': False})
                accept.update({'visible': False})   
                accept = {"accepted": False}        
                                 
        else:
            self.logger.debug(
                "%s is not in the valid extensions list for Version creation" %
                (extension,)
            )
        

        return accept

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """ 
        # publish_thumbnail = self.get_publish_thumbnail(settings, item)
        publisher = self.parent
        sg_reader = shotgun_utilities.ShotgunReader(shotgun=publisher.shotgun)
        get_file_string = file_strings.FileStrings()

        temp_root = None
        now = datetime.datetime.now()
        ampm = self.get_ampm(now)

        if not item.context.task:
            raise Exception("Need task info!")

        if not item.description:
            raise Exception("Need to fill in description detailing submitted work!")

        if not item.properties.get("frame_range"):
            self.logger.warning("Could not get frame range from item. Needed for the creation of the QT. Sending as a single frame render.")

        self.logger.debug("Type: %s" % (item.context.entity,))
        self.logger.debug("Task: %s" % (item.context.task,))
        self.logger.debug("Step: %s" % (item.context.step,))
        self.logger.debug("Description: %s" % (item.description,))

        if not item.properties.get("step"):
            review_process = publisher.shotgun.find_one("Step", 
                [['id', 'is', item.context.step['id']]], 
                item.properties["step_fields"])
        else:
            review_process = item.properties.get("step")

        review_process_type = review_process['sg_review_process_type']
        review_process_entity_type = review_process['entity_type']
        item.properties['review_process_type']=review_process_type.lower()
        self.logger.info("Review process info: %s - %s" %(review_process_entity_type,
                                                        item.properties.get("review_process_type")))
        # Check for a Version with same Version name   
        version_name = ""
        publish_name = item.properties.get("publish_name")
        path = item.properties["path"]
        
        version_number = item.properties.get("publish_version")
        version_number = "_v" + str(version_number).zfill(3)
        
        if not publish_name:
            self.logger.debug("Using path info hook to determine publish name.")
            publish_name = self.get_publish_name(settings, item)
        else:
            pass
        
        version_name = publish_name + version_number

        existing_version_data = [
            ['project', 'is', {'type': 'Project','id': item.context.project['id']}],
            ["code", "is", version_name]
        ]
        
        existing_version = publisher.shotgun.find_one("Version", 
                                                    existing_version_data,
                                                    ["code"])
        
        if existing_version:
            self.logger.warning(
                "Version already exists with the same name!",
                extra={
                    "action_show_in_shotgun": {
                        "label": "Conflict Version",
                        "tooltip": "Reveal the conflicting version in Shotgun.",
                        "entity": existing_version
                    }
                })                                                                                                      
            raise Exception("Version exists with same name: %s " % (existing_version['code'],))
        else:
            version_thumbnail = self.get_version_thumbnail(item)
            version_data = {
                "project": item.context.project,
                "code": version_name,
                "description": item.description,
                "entity": self._get_version_entity(item),
                "sg_task": item.context.task,
                "image": version_thumbnail,
                "frame_range": item.properties.get("frame_range"),
                "sg_path_to_frames": path
            }
            item.properties['version_data'] = version_data

        # Get the output paths based on context 
        nuke_review_template = publisher.engine.get_template_by_name("nuke_review_template2")
        review_process_json_template = publisher.engine.get_template_by_name("review_process_json")
        temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
        info_json_template = publisher.engine.get_template_by_name('info_json_file')

        resolve_fields = {
            'Shot': item.context.entity['name'],
            'task_name': item.context.task['name'],
            'name': None,
            'version': item.properties.get("publish_version"),
            'ampm': ampm,
            'YYYY': now.year,
            'MM': now.month,
            'DD': now.day
        }        
        fields = {}
        item.properties['info_json_template'] = info_json_template
        item.properties['resolve_fields'] = resolve_fields
        item.properties['fields'] = fields
        item.properties['playlist_name'] = "%s%s%s_Resolve_Review_%s" %("%04d" % (now.year),
                                                                        "%02d" % (now.month),
                                                                        "%02d" % (now.day),
                                                                        str(ampm))
        temp_root = temp_root_template.apply_fields(resolve_fields)
        nuke_review_file = nuke_review_template.apply_fields(fields)
        review_process_json = review_process_json_template.apply_fields(fields)
        self.logger.debug("Using review JSON: %s" % (review_process_json))
        self.test_template(item, temp_root, 'temp_root')
        self.test_template(item, review_process_json, 'review_process_json')
        self.test_template(item, nuke_review_file, 'nuke_review_script')

        # Get entity info from SG
        entity_filter = [
            ['project', 'is', {'type': 'Project','id': item.context.project['id']}],
            ["code", "is", item.context.entity['name']]
        ]
           
        if item.context.entity['type'] == "Shot":
            shot_info = publisher.shotgun.find_one("Shot",
                                                    entity_filter,
                                                    [
                                                    "code",
                                                    "id",
                                                    "description",
                                                    "created_by",
                                                    "sg_episode",
                                                    "sg_shot_lut",
                                                    "sg_shot_audio",
                                                    "sg_status_list",
                                                    "sg_project_name",
                                                    "sg_plates_processed_date",
                                                    "sg_shot_lut",
                                                    "sg_shot_ocio",
                                                    "sg_without_ocio",
                                                    "sg_head_in",
                                                    "sg_tail_out",
                                                    "sg_lens_info",
                                                    "sg_plate_proxy_scale",
                                                    "sg_frame_handles",
                                                    "sg_shot_ccc",
                                                    "sg_seq_ccc",
                                                    "sg_vfx_work",
                                                    "sg_scope_of_work",
                                                    "sg_editorial_notes",
                                                    "sg_sequence"
                                                    "sg_main_plate",
                                                    "sg_latest_version",
                                                    "sg_latest_client_version",
                                                    "sg_gamma",
                                                    "sg_target_age",
                                                    "sg_shot_transform"
                                                    ])
            shot_info_dict = {}
            shot_info.update({"type": "Shot"})
            shot_info.update({"main_plate":self._get_published_main_plate(sg_reader, item)})
            if item.properties.get('version_data'):
                shot_info.update({"version":item.properties.get('version_data')})
            for i in shot_info.keys():
                shot_info_dict.update({i:shot_info[i]})
            item.properties['entity_info'] = shot_info_dict

        elif item.context.entity['type'] == "Asset":
            asset_info = publisher.shotgun.find_one("Asset",
                                                    entity_filter,
                                                    [
                                                    "code",
                                                    "id",
                                                    "description",
                                                    "created_by",
                                                    "sg_status_list",
                                                    "sg_head_in",
                                                    "sg_tail_out",
                                                    "sg_lens_info",
                                                    "sg_vfx_work",
                                                    "sg_scope_of_work",
                                                    "sg_editorial_notes",
                                                    "sg_latest_version",
                                                    "sg_latest_client_version"
                                                    ])
            asset_info_dict = {}
            asset_info.update({"type": "Asset"})
            if item.properties.get('version_data'):
                asset_info.update({"version":item.properties.get('version_data')})            
            for i in asset_info.keys():
                asset_info_dict.update({i:asset_info[i]})
            item.properties['entity_info'] = asset_info_dict
        else:
            # Set shot specifics to None
            item.properties['shot'] = {}
            item.properties['content_info'] = None
            item.properties['shot'].update({'sg_lens_info' : None})
            item.properties['shot'].update({'sg_gamma' : None})
            item.properties['shot_lut'] = None
            item.properties['lut_pick'] = "None-(Log)"
            item.properties['shot'].update({'sg_frame_handles' : None})

        # Aux files
        draft_py = os.path.join(pipeline_root,"ssvfx_scripts\\thinkbox\\draft\\draft_process_submit.py")
        # draft_py=os.path.join("C:\\Users\\shotgunadmin\\Scripts\\Pipeline\\ssvfx_scripts\\thinkbox\\draft\\draft_process_submit.py")
        item.properties["script_file"] = draft_py

        codecs = item.properties.get("codec_info")
        if (len(item.properties.get("project_info")['sg_review_qt_codecs'])>0 and codecs): 
            review_codecs = item.properties.get("project_info")['sg_review_qt_codecs']  
            if review_codecs:
                for i in review_codecs:
                    codec_match = next((codec for codec in codecs if codec['code'] == i['name']), None) 
                    review_codec = codec_match['sg_nuke_code']
                    self.logger.debug("Nuke codec name: %s" % (review_codec,))
            item.properties['review_codec'] = review_codec
        else:
            raise Exception("Not enough info for submission. Needs review codec info from SG.")                            

        # Input
        item.properties['input_path'] = get_file_string.get_input_file_format(item.properties.path)
        self.logger.debug("Input path: %s" % item.properties['input_path'])

        # At this stage we have gathered all the required Project info needed for the
        # submission and creation of the QTs. Now we need to loop through the alternative jobs

        return True
        
    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        publisher = self.parent
        self.dl_submission = deadline_submission3.DeadlineSubmission()
        jm = json_manager.JsonManager()
        sg_writer = shotgun_utilities.ShotgunWriter(shotgun=publisher.shotgun)

        self.logger.debug(
            "Populated Version data...",
            extra={
                "action_show_more_info": {
                    "label": "Version Data",
                    "tooltip": "Show the complete Version data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat( item.properties.get("version_data")),)
                }
            }
        )

        # Create the version
        try:
            self.logger.info("Creating Version : %s" % (item.properties.get("version_data")['code'],))
            start_time = time.time()
            version = publisher.shotgun.create("Version", item.properties.get("version_data"))
            self.logger.debug("--- Version creation took %s seconds ---" % (time.time() - start_time))
            if version:
                self.logger.info("Version info:  %s" % (str(version)))
                item.properties.sg_version_data = version
                if 'version' in item.properties['entity_info'].keys():
                    item.properties['entity_info']['version'].update({'id':version['id']})   
                else:
                    item.properties['entity_info']['version']=version
        except:
            raise Exception("Failed to upload Version to SG ")
        finally:
            self.logger.info("Version upload complete!")

        total_info_dict = dict(
        project_info = item.properties.get("project_info"),
        entity_info = item.properties.get("entity_info"),
        )
        # Create the json file
        review_output = None
        process_info_list = []
        review_process_json = item.properties.get('review_process_json')
        review_process_json_dict = self.read_json_file(jm,total_info_dict,review_process_json)

        process_dict =  review_process_json_dict[item.properties.get('review_process_type')]
        
        for i in process_dict.keys():
            self.logger.info("Creating process files for %s" % (i))            
            resolve_fields = item.properties.get('resolve_fields')
            resolve_fields.update({'name': str(i)})

            if resolve_fields['version'] == None:
                self.logger.warning("No version number find from path. Setting to version Zero")
                resolve_fields['version'] = 000
            if 'plugin_in_script_alt' in process_dict[str(i)].keys():
                item.properties['nuke_review_script'] = os.path.join(total_info_dict['project_info']['sg_root']['local_path_windows'], 
                                                process_dict[str(i)]['plugin_in_script_alt'])
            self.logger.info("Update nuke script: %s" % (item.properties['nuke_review_script']))

            info_json_file = item.properties['info_json_template'].apply_fields(resolve_fields)
            info_json_file = re.sub("(\s+)", "-", info_json_file) 
            info_json_file = self.test_template(item, info_json_file, 'info_json_file')                
            process_info_list.append(info_json_file)  

            review_template = publisher.engine.get_template_by_name(process_dict[str(i)]['qt_template_secondary'])
            review_output = review_template.apply_fields(resolve_fields)
            review_output = self.test_template(item, review_output, str(i))

            item.properties["output_root"] = os.path.split(review_output)[0]
            item.properties["output_main"] = os.path.split(review_output)[1]
            item.properties["output_ext"] = os.path.splitext(review_output)[1]
                        
            item.properties['nuke_out_script'] = os.path.join(item.properties.get('temp_root'),
                                                                "deadline", 
                                                                "%s_%s.nk" % (item.properties.get('version_data')['code'], 
                                                                            str(i)))

            item.properties['entity_info'].update({'create_version':process_dict[str(i)]['create_version']})
            item.properties['entity_info'].update({'update_version':process_dict[str(i)]['update_version']})

            content_info_dict = {}
            if (process_dict[str(i)]['content_info'] and 
            isinstance(process_dict[str(i)]['content_info'], dict)):
                for k,v in process_dict[str(i)]['content_info'].items():
                    try:
                        content_info_dict[str(k)] = item.properties.get("entity_info")[str(v)]
                    except:
                        self.logger.debug("!!! Issue getting content info for %s" % (str(v)))

      
            item.properties["content_info"] = content_info_dict

            process_info = self.set_process_info(self.dl_submission,
                            "Nuke",
                            str(i),
                            process_dict[str(i)],
                            item.properties.get("project_info"),
                            item.properties.get("software_info"),
                            item.properties.get("entity_info"),
                            item)

            total_info_dict.update({'process_info': process_info})
            if process_dict[str(i)]['add_to_review_playlist']:
                added_verions = sg_writer.add_version_to_playlist(
                    item.context.project['id'],
                    item.properties.get('playlist_name'),
                    'rsv',
                    version['code'],
                    version['id']
                )
                if not added_verions:
                    self.logger.debug("Playlist %s already has Verion %s" %(item.properties.get('playlist_name'),version['code']))
                else:
                    self.logger.debug("Updated Playlist %s with Verion %s" %(item.properties.get('playlist_name'),version['code']))
            info_json_file = self.write_json_file(jm,
                        total_info_dict, 
                        info_json_file)  

            # log results  
            self.logger.debug("Review template: %s" %(str(process_dict[str(i)])))
            self.logger.debug("Review output: %s" %(str(review_output)))
            self.logger.debug("JSON file: %s" %(str(info_json_file)))

        item.properties['process_info_list']=process_info_list

        # Send the QT creation job to the farm
        try:
            draft_info = self.set_process_info(self.dl_submission,
                            "DraftPlugin",
                            'draft-update',
                            {"create_version": False,"update_version": False, "update_client_version": False},
                            item.properties.get("project_info"),
                            item.properties.get("software_info"),
                            item.properties.get("entity_info"),
                            item,
                            multiple_task_list = item.properties.get("process_info_list"))

            self.send_to_dl(self.dl_submission, draft_info, item) 
        except:
            raise Exception("Failed to send QT job to DL")
        finally:            
            self.logger.info("Version upload complete!")
    
    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        pass

    def _get_version_entity(self, item):
        """
        Returns the best entity to link the version to.
        """

        if item.context.entity:
            return item.context.entity
        elif item.context.project:
            return item.context.project
        else:
            return None
    
    def _get_published_main_plate(self, sg_reader, item):
   
        published_main_plate = sg_reader.get_pushlished_file(item.context.project['id'], 
                                                                        "Main Plate", 
                                                                        "Shot", 
                                                                        entity_id=item.context.entity['id'], 
                                                                        get_latest=True)
        
        self.logger.info("Got main plate of entity %s - %s" %(str(item.context.entity['id']),published_main_plate))

        return published_main_plate       

    def get_publish_name(self, settings, item):
        """
        Get the publish name for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish name for

        Uses the path info hook to retrieve the publish name.
        """

        # publish name explicitly set or defined on the item
        publish_name = item.get_property("publish_name")
        if publish_name:
            return publish_name

        # fall back to the path_info logic
        publisher = self.parent
        path = item.properties.path
        
        if "sequence_paths" in item.properties:
            # generate the name from one of the actual files in the sequence
            name_path = item.properties.sequence_paths[0]
            is_sequence = True
        else:
            name_path = path
            is_sequence = False

        return publisher.util.get_publish_name(
            name_path,
            sequence=is_sequence
        )

    def get_version_thumbnail(self, item):
         
         thumbnail_path = None

         thumbnail_path = item.get_property("thumbnail_path")

         return thumbnail_path

    def get_ampm(self, now):
        """
        Get the AM or PM string value for further use
        :param time: now datetime based function
        """
        ampm =""
        if int(now.strftime("%H")) < 11:
            ampm = "AM"
        elif int(now.strftime("%H")) < 16:
            ampm = "PM"            
        else:   
            ampm = "LATE"
        
        return ampm

    def send_to_dl(self, dl_module, draft_info, item):
        """
        Runs cmd function to send image sequence to DL.
        Needs to be of type file.type.sequence.

        :param item: Item to process
        """   
        self.dm = deadline_manager.DeadlineManager()

        try:
            deadline_submission = self.dm.get_dl_cmd("%s %s" %(draft_info['job_info_file'], draft_info['plugin_info_file']))
        except:
            raise Exception("Failed in the DL submission process.")          
        finally:
            self.logger.debug("Sucessfully Sent job to DL.")
            for line in deadline_submission.splitlines():
                if not line:
                    pass
                else:
                    self.logger.debug("--- %s "% (line,))
        
        self.logger.info("Version Submission Complete!\nVersion has been sent to SG and the QT sent to DL")
    
    def replace_slashes(self, path):
        """
        Simple function to replace back with forward slashes
        """
        if not path:
            return
        else:
            return path.replace("\\","/")

    def set_process_info(self, dl_module, plugin_name, process_name, plugin_settings, project_info, software_info, entity_info, item, multiple_task_list=None):
        
        process_info = None
        # DL vairables
        batch_name = (entity_info['version']['code']+"_submit") or ""
        job_name = entity_info['version']['code']+ "_" + process_name or ""
        plate_type = entity_info['version']['code'] or ""        
        create_version = entity_info['create_version'] or False
        update_version = entity_info['update_version'] or False
        update_client_version = False
        create_publish = False
        publish_file_type = None
        copy_to_location = False
        copy_location = None
        plugin_version = None
        plugin_path = None
        zip_output = False
        # user = project_info['artist_name'] or ""
        comment = ""
        title = "artist_submit"        
        department = "VFX"
        group="artist"
        priority = 55
        if process_name == "shotgun-version":
            priority = 50        
        primary_pool = "draft_submission"
        secondary_pool = "draft_submission"
        if plugin_name == "DraftPlugin":
            primary_pool = "vfx_processing"
            secondary_pool = "vfx_processing"            
        machine_limit = 1
        concurrent_task = 1
        chunk_size = 1000000

        # Content variables
        content_info = item.properties.get('content_info') or ""
        content_output_file = item.properties.get('output_main') or ""
        content_output_file_total = item.properties.get('output_main') or ""
        content_output_file_ext = item.properties.get('output_ext') or ""
        content_output_root = item.properties.get('output_root') or ""
        content_output_file_total = os.path.join(content_output_root,content_output_file)
        job_dependencies = ""
        frame_range = item.properties.get("frame_range") or "1-1"
        if 'slate' in  plugin_settings.keys():
            if not plugin_settings['slate']:
                pass
            else:
                if len(frame_range.split("-")) == 1:
                    frame_range = "%s-%s" % (frame_range, frame_range)
                else:
                    first_frame= frame_range.split("-")[0]
                    last_frame= frame_range.split("-")[1]
                    frame_range = "%s-%s" % (first_frame, last_frame)
            
        # Software Variables
        software_nuke = next((soft for soft in software_info if soft['products'] == plugin_name), None)
        try:
            plugin_version = software_nuke['version_names']
            plugin_path = software_nuke['windows_path']
        except:
            pass

        slate_enabled = project_info['sg_review_qt_slate']
        burnin_enabled = project_info['sg_review_burn_in']
        plugin_in_script = self.replace_slashes(item.properties['nuke_review_script'])
        plugin_out_script = item.properties['nuke_out_script']
        temp_root = self.replace_slashes(item.properties['temp_root'])
        script_file = self.replace_slashes(item.properties['script_file']) or None

        user_name = ""
        try:
            user_info = item.properties.get("user_info")    
            if( user_info and 
            len(user_info)==1):
                user_name = user_info[0]['login']
        except:
            self.logger.warning("Could not get user_name info")

        process_info = dict(
            batch_name = batch_name,
            job_name = job_name, 
            process_name = process_name, 
            content_info = content_info,
            plate_type = plate_type,
            create_version = create_version,
            update_version = update_version,
            update_client_version = update_client_version,
            create_publish = create_publish,
            publish_file_type = publish_file_type,
            copy_to_location = copy_to_location,
            copy_location = copy_location,
            zip_output = zip_output,
            user = user_name,      
            title = title,
            comment = comment,
            department = department,
            group= group,
            priority = priority,
            primary_pool = primary_pool,
            secondary_pool = secondary_pool,
            machine_limit = machine_limit,
            concurrent_task = concurrent_task,
            chunk_size = chunk_size,                
            frame_range =frame_range,
            content_output_file = content_output_file,
            content_output_file_ext =content_output_file_ext,  
            content_output_file_total = content_output_file_total,          
            content_output_root = content_output_root,
            job_dependencies = job_dependencies,
            plugin_name = plugin_name,
            plugin_path = plugin_path,
            plugin_version = plugin_version,
            plugin_settings = plugin_settings,
            plugin_in_script = plugin_in_script,
            plugin_out_script = plugin_out_script,
            slate_enabled = slate_enabled,
            burnin_enabled = burnin_enabled,
            script_file = script_file,
            sg_temp_root = temp_root
            )
        
        if multiple_task_list != None:
            process_info.update({'info_json_count':len(multiple_task_list)})
            for index, i in enumerate(multiple_task_list):
                info_json_key = 'info_json_0%s'%str(index+1)
                process_info.update({info_json_key:i})

        job_info_file,plugin_info_file = self.create_dl_info_files(dl_module, project_info, entity_info, process_info)
        process_info.update({'job_info_file':job_info_file})
        process_info.update({'plugin_info_file':plugin_info_file})

        return process_info

    def create_dl_info_files(self, dl_module, project_info_dict, entity_info, process_info_dict):
        
        job_info = None
        plugin_info = None

        total_info = dict(
        project_info = project_info_dict,
        entity_info = entity_info,
        process_info = process_info_dict
        )

        job_info = self.create_job_info(dl_module,
                            total_info, 
                            process_info_dict['plugin_name'])
        plugin_info = self.create_plugin_info(dl_module,
                            total_info, 
                            process_info_dict['plugin_name'])  

        return(job_info, plugin_info)

    def create_job_info(self, dl_module, total_info, plugin_name):

        job_info = None
        try:
            job_info = self.dl_submission.gather_job_info(
                total_info,
                )
        except Exception as err:
            raise Exception("Unable to create %s job info file %s" % (plugin_name, err))
        finally:
            job_info = job_info.replace("/","\\")
            self.logger.debug("Created %s job info file for %s." % (plugin_name,total_info['process_info']['process_name']),
                    extra={
                    "action_show_folder": {
                        "path": job_info
                    }
            })
        return job_info

    def create_plugin_info(self, dl_module, total_info, plugin_name):

        plugin_info = None
        try:
            plugin_info = self.dl_submission.gather_plugin_info(
                total_info,
                )
        except Exception as err:
            raise Exception("Unable to create %s plugin info file %s" % (plugin_name, err))
        finally:
            plugin_info = plugin_info.replace("/","\\")
            self.logger.debug("Created %s plugin info file for %s" % (plugin_name,total_info['process_info']['process_name']),
                    extra={
                    "action_show_folder": {
                        "path": plugin_info
                    }
                    })
            return plugin_info

    def write_json_file(self, json_module, info_dict, json_filename):

        json_file = None
        try:
            json_file = json_module.create_JsonFile(
                info_dict,
                filename=json_filename
            )
        except:
            raise Exception("Issue creating JSON file - needed for DL submission!")
        finally:
            self.logger.debug("Created info JSON file.",
                    extra={
                    "action_show_folder": {
                        "path": json_filename
                    }
                    })

            return json_file

    def read_json_file(self, json_module, info_dict, json_filename):

        json_file = None
        try:
            json_file = json_module.read_JsonDataFile(filename=json_filename)
        except:
            raise Exception("Issue reading JSON file - needed for DL submission!")
        finally:
            self.logger.debug("Read info JSON file.",
                    extra={
                    "action_show_folder": {
                        "path": json_filename
                    }
                    })

        return json_file

    def test_template(self, item, template, property_key, exists=False):
        """
        Test to see if the template was found and raise error if not
        :param: property_key (str) Template name from project
        :param: exists (bool) T/F to see if path exists
        """
        if not template:
            raise Exception("Could not resolve the ouput path for %s!" %(property_key,))
        else:
            if exists:
                if not os.path.exists(template):
                    raise Exception("Path doesn't exist %s!" %(property_key,))
            if property_key:                 
                item.properties[property_key] = template
                self.logger.debug("Template: %s - %s" % (property_key,template))
                return template            