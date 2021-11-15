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
import json

# from software.nuke.nuke_python import submission_sanity_checks as ssc
# submission_tools = ssc.NukeSanityChecks()

try:
    ssvfx_script_path = ""#C:\\Users\\shotgunadmin\\Scripts\\Pipeline\\ssvfx_scripts"
    if "SSVFX_PIPELINE_DEV" in os.environ.keys():
        pipeline_root = os.environ["SSVFX_PIPELINE_DEV"]
        ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")
    else:
        if "SSVFX_PIPELINE" in os.environ.keys():
            pipeline_root =  os.environ["SSVFX_PIPELINE"]
            ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")
            if os.path.exists(ssvfx_script_path):
                pass
            else:
                print("!!!!!! Could not find %s" %(ssvfx_script_path,))
            print("Found env var path: %s" %(ssvfx_script_path,))
        else:
            print("SSVFX_PIPELINE not in env var keys. Using explicit")
            pipeline_root = "\\\\10.80.8.252\\VFX_Pipeline"
            ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")

    sys.path.append(ssvfx_script_path)
    from thinkbox.deadline import deadline_manager3
    from thinkbox.deadline import deadline_submission4
    from general.file_functions import file_strings
    from general.data_management import json_manager
    from software.nuke.nuke_command_line  import nuke_cmd_functions as ncmd
    from shotgun import shotgun_utilities
except Exception as err:
    raise Exception("Could not load on of the studio modules: %s" % err)

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
        return self._icon
                                                             
    @icon.setter
    def icon(self, plugin_key=None):
        """
        Plugin path setter
        """
        pass

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return self._name

    @name.setter
    def name(self, plugin_key=None):
        """
        name setter
        """
        pass

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return self._description

    @description.setter
    def description(self, plugin_key=None):
        """
        description setter
        """
        pass


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
                "default": "jpeg, jpg, png, mov, mp4, dpx, exr, tif, tiff",
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

        # re set properties to correspond to upload_version or slap_comp configurations
        self.reset_properties(item)

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
            elif item.properties.get("sg_slap_comp"):
                accept.update({'checked': False})
                # log the accepted file and display a button to reveal it in the fs
                self.logger.info(
                    "Slap Comp plugin accepted: %s" % (file_path,),
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
        
        exclude_descriptors = [ "distort", "undistort", "persp", "cones" ]
        exclude_templates = [ "incoming_outsource_shot_nuke_render", 
                                "incoming_outsource_shot_matchmove_render", 
                                "incoming_outsource_shot_undistorted" 
                                ]
        # reject distort/undistort outsource items
        if item.properties.get('template'):
            if item.properties.get('template').name in exclude_templates:
                if 'descriptor' in item.properties["fields"].keys():
                    if item.properties.fields['descriptor'] in exclude_descriptors:
                        self.logger.debug(
                                        "Removing template %s : %s from Version for Review" % (
                                            item.properties.get('template').name,
                                            item.properties.fields['descriptor']
                                            )
                                        )
                        accept.update({'checked': False})
                        accept.update({'enabled': False})
                        accept.update({'visible': False})
                        accept = {"accepted": False}
                else:
                    self.logger.debug(
                                    "Removing template %s from Version for Review as Undistort" % (
                                        item.properties.get('template').name,
                                        )
                                    )
                    accept.update({'checked': False})
                    accept.update({'enabled': False})
                    accept.update({'visible': False})
                    accept = {"accepted": False}

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
        get_file_string = file_strings.FileStrings()

        now = datetime.datetime.now()
        ampm = self.get_ampm(now)

        if not item.context.task:
            raise Exception("Need task info!")

        if not item.description:
            raise Exception("Need to fill in description detailing submitted work!")

        if not item.properties.get("frame_range"):
            self.logger.warning("Could not get frame range from item. Needed for the creation of the QT. Sending as a single frame render.")

        if not item.properties.get("step"):
            self.logger.error("Missing step info")

        if not item.properties['entity_info'].get("main_plate") and item.properties.get("sg_slap_comp"):
            raise Exception("Missing Main Plate: Cannot complete Slap Comp")

        if not item.properties['template_paths'].get('job_file_dir'):
            self.logger.error("Missing directory info for writing job files")

        job_file_dir = item.properties['template_paths']['job_file_dir']
        if not os.path.exists( job_file_dir ):
            os.makedirs( job_file_dir )

        if not os.access(job_file_dir, os.W_OK):
            self.logger.error("User does not have permission to write files to this directory: %s" % job_file_dir )

        # TODO: add check for missing frames in render sequence
        # if [ frame for frame in item.properties['sequence_paths'] if os.path.exists( frame ) ]:
        #     self.logger.error("Missing frames in render sequence")

        # Check for a Version with same Version name   
        if item.properties['existing_version']['version']:
            existing_version = item.properties['existing_version']['version']
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

        # path = item.properties["path"]
        self.logger.debug("Type: %s" % (item.context.entity,))
        self.logger.debug("Task: %s" % (item.context.task,))
        self.logger.debug("Step: %s" % (item.context.step,))
        self.logger.debug("Description: %s" % (item.description,))
        self.logger.debug("Job File Directory: %s" % (job_file_dir,))

        # Nuke-specific sanity checks
        if publisher.engine.name == "tk-nuke":
            from software.nuke.nuke_python import submission_sanity_checks as ssc
            submission_tools = ssc.NukeSanityChecks()
            
            self.logger.debug("Running Nuke-specific Sanity Checks...")

            if not item.properties.get('sanity_checks'):
                submission_tools.sanity_checks(item)
            elif item.properties.get('failed_check'):
                item.properties['sanity_checks'] = False
                item.properties['failed_check'] = False
                raise Exception("A Sanity Check has failed. This item cannot be validated.")

        # self.logger.warning( ">>>>> properties: %s" % item.properties.keys() )

        review_process = item.properties.get("step")

        review_process_type = review_process['sg_review_process_type']
        review_process_entity_type = review_process['entity_type']
        item.properties['review_process_type'] = review_process_type.lower()
        self.logger.info("Review process info: %s - %s" %(review_process_entity_type,
                                                        item.properties.get("review_process_type")))

        # append discription to existing version_data
        item.properties['version_data'].update( { "description": item.description } )
        # self.logger.warning( ">>>>> image? %s" % item.properties['version_data']['image'] )
            
        item.properties['playlist_name'] = "%s%s%s_Resolve_Review_%s" %("%04d" % (now.year),
                                                                        "%02d" % (now.month),
                                                                        "%02d" % (now.day),
                                                                        str(ampm))
            
        self.logger.debug("Using review JSON: %s" % ( item.properties['template_paths'].get('review_process_json') ))

        entity_info = item.properties.get('entity_info')
        entity_type = item.properties['fields'].get('type')

        # attach any outstanding entity-type specific info to the entity info
        if entity_type == "Shot":
            camera = item.properties.get('camera')
            entity_info.update( { "main_plate_camera": camera } )
            self.logger.info("Main plate camera - %s" % ( camera.get('code')))
            
        elif entity_type == "Asset":
            pass

        if item.properties.get('version_data'):
            entity_info.update({"version":item.properties.get('version_data')})
            
        item.properties['entity_info'] = entity_info

        # Input
        item.properties['input_path'] = get_file_string.get_input_file_format(item.properties.get("path") )
        self.logger.debug("Input path: %s" % item.properties['input_path'])

        json_properties = item.properties.get('json_properties')

        # process_type = item.properties['step'].get('sg_review_process_type').lower()        
        process_dict =  item.properties.get('process_dict')
        process_dict['entity_info']['description'] = item.description

        for process in process_dict['processes']:
            nuke_settings = process_dict['processes'].get(process).get('nuke_settings')
            process_qt_codec = nuke_settings.get('quicktime_codec')
            if not process_qt_codec:
                raise Exception("JSON process %s has no Quicktime codec" % process)

            nuke_settings['content_notes_value'] = {
                                                    'message': item.description
                                                    }

            nuke_settings['SSVFX_SLATE'].update( {
                                                'notes': item.description
                                                } )

            if process_dict['processes'][process]['process_settings'].get('create_version'):
                item.properties['version_data'].update({
                    "sg_path_to_movie": process_dict['processes'][process]['process_settings'].get('review_output')
                })

        self._write_dl_json( json_properties['general_settings']['info_json_file'], process_dict )

        # for key in item.properties['process_dict']:
        #     self.logger.warning( ">>>>> %s: %s" % (key, item.properties['process_dict'][key]) )

        self.logger.debug( ">>>>> END UPLOAD_VERSION VALIDATION >>>>>")

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
        self.dl_submission = deadline_submission4.DeadlineSubmission()
        # jm = json_manager.JsonManager()
        # sg_writer = shotgun_utilities.ShotgunWriter(shotgun=publisher.shotgun)

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

        # dev switch for DL submission testing
        dev_switch = False
        if not dev_switch:
            # Create the version
            start_time = datetime.datetime.now()
            str_time = start_time.strftime("%H:%M")
            sg_version_data = {
                                "project": item.properties['version_data'].get('project'),
                                "code": item.properties['version_data'].get('code'),
                                "description": item.description,
                                "entity": item.properties['version_data'].get('entity'),
                                "sg_task": item.properties['version_data'].get('sg_task'),
                                "image": item.properties['version_data'].get('image'),
                                "frame_range": item.properties['version_data'].get('frame_range'),
                                "sg_path_to_frames": item.properties['version_data'].get('sg_path_to_frames'),
                                "sg_path_to_movie": item.properties['version_data'].get('sg_path_to_movie'),
                                "sg_version_number": item.properties['version_data'].get('version_number'),
                            }

            self.logger.info( "Creating Version : %s" % ( sg_version_data.get("code"), ) )
            # start_time = time.time()
            # self.logger.debug("--- Version creation took %s seconds ---" % (time.time() - str_time))
            try:
                version = publisher.shotgun.create("Version", sg_version_data)
                self.logger.info("Created version: %s" % version)
            except Exception as err:
                self.logger.error("Failed to create SG version. Check connection to Shotgun.")
                raise Exception( "Error: %s" % err )
            
            if version:
                self.logger.info("Version info:  %s" % (str(version.get('code') ) ) )
                item.properties["version_info"] = version
                if 'version_data' in item.properties.keys():
                    item.properties['version_data'].update({'id':version['id']})   
                else:
                    item.properties['version_data']['version'] = version

            self.logger.info("Version upload complete!")
        
        # create deadline files
        self.create_dl_info_files( item )

        # create submission files
        job_info_file, plugin_info_file = self._create_submission_files( item )

        # send submission job to deadline
        if not job_info_file:
            raise Exception( "Missing job info file" )
        elif not plugin_info_file:
            raise Exception( "Missing plugin info file" )

        self.dm = deadline_manager3.DeadlineManager3()
        item.properties['dl_result'] = self.dm.get_dl_cmd("%s %s" % ( job_info_file, plugin_info_file))

        # self.thumbnail_dependency(item)

        self.logger.warning(">>>>> FINISHED VERSION PUBLISH >>>>>")

        # self.send_to_dl( job_info_file, plugin_info_file )
    
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

    def get_publish_name(self, settings, item):
        """
        Get the publish name for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish name for

        Uses the path info hook to retrieve the publish name.
        """

        # publish name explicitly set or defined on the item
        publish_name = item.properties.get("publish_name")

        if publish_name:
            return publish_name

        # fall back to the path_info logic
        publisher = self.parent
        path = item.properties.get("path")
        
        if "sequence_paths" in item.properties:
            # generate the name from one of the actual files in the sequence
            name_path = item.properties.get("sequence_paths")[0]
            is_sequence = True
        else:
            name_path = path
            is_sequence = False

        return_name = publisher.util.get_publish_name(
                                                        name_path,
                                                        sequence=is_sequence
                                                    )

        return return_name

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

    def _create_submission_files(self, item):
        """
        Create job files for Deadline python job that will create the appropriate Quicktime jobs

        :param item: collector item with info needed to fill out the file variables
        """
        # create path/directories to the job file storage location
        job_file_dir = item.properties['template_paths']['job_file_dir']

        output_name = "%s_%s" % ( item.properties['version_data']['code'], "submission" )

        submission_job_file = os.path.join( job_file_dir, "%s_job_info.job" % output_name )
        submission_plugin_file = os.path.join( job_file_dir, "%s_plugin_info.job" % output_name )

        submission_job_info = [
                        "BatchName=%s" % item.properties['version_data']['code'] + "_submit",
                        "Name=%s" % output_name,
                        "Plugin=Python",
                        "Priority=55",
                        "MachineLimit=1",
                        "Pool=vfx_processing",
                        "SecondaryPool=vfx_processing",
                        "ExtraInfo0=%s" % item.properties['project_info']['name'],
                        ]

        # submission script switch for dev
        script_file = item.properties['json_properties']['general_settings']['script_file']
        # if "SSVFX_PIPELINE_DEV" in os.environ.keys():
        #     dev_root = os.environ["SSVFX_PIPELINE_DEV"]
        #     script_location = os.path.join( "Pipeline", "ssvfx_scripts", "thinkbox", "python", "submission_process_submit.py" )
        #     script_file = os.path.join( dev_root, script_location )

        submission_plugin_info = [
                            "ScriptFile=%s" % script_file,
                            "Arguments=%s" % item.properties['json_properties']['general_settings']['info_json_file'],
                            "Version=2.7",
                            ]

        submission_job_file, submission_plugin_file = self.create_dl_job_files( submission_job_file, submission_job_info, submission_plugin_file, submission_plugin_info )

        return submission_job_file, submission_plugin_file

    def create_dl_info_files(self, item):
        """
        Create the files for the individual Quicktime jobs Deadline will create

        :param item: item to submit for data collection
        """

        item_dict = item.to_dict().get('global_properties')

        if not item_dict:
            raise Exception( "Could not find global_properties in item dictionary" )
        
        try:
            self.dl_submission.gather_job_info( item_dict )
            self.dl_submission.gather_plugin_info( item_dict )  
        except Exception as err:
            raise Exception( "Unable to create job info file: %s" % err )

    def _write_dl_json(self, json_path, process_dict):
        """
        Create JSON file used for DL processing

        :param json_path: final JSON output file path
        :param process_dict: Info to be written to JSON file
        """

        file_path = json_path
        if not file_path:
            return

        if not os.path.exists( os.path.dirname( json_path ) ):
            os.makedirs( os.path.dirname( json_path ) )

        try:
            file_write = open( json_path, "w+" )
            json_data = json.dumps(process_dict, sort_keys=False,
                                    indent=4, separators=(',', ': '), default=str)
            file_write.write(json_data)
            file_write.flush()
            file_write.close()
        except:
            file_write.close()
            raise Exception( "Failed to write JSON to %s" % json_path )

    def reset_properties(self, item):
        '''
        Toggles between slap comp and version for review renders
        '''
        
        #TO DO: Get the plugin name to reflect the actual change in the Publisher

        publisher = self.parent

        shotgun_url = publisher.sgtk.shotgun_url

        media_page_url = "%s/page/media_center" % (shotgun_url,)
        review_url = "https://www.shotgunsoftware.com/features/#review"

        if item.properties.get("sg_version_for_review"):
            # icon 
            self._icon = os.path.join(
                                        self.disk_location,
                                        "icons",
                                        "review.png"
                                    )
            
            # name 
            self._name = "Upload for review"

            # description 
            self._description = """
            Upload the file to Shotgun for review.<br><br>

            A <b>Version</b> entry will be created in Shotgun and a transcoded
            copy of the file will be attached to it. The file can then be reviewed
            via the project's <a href='%s'>Media</a> page, <a href='%s'>RV</a>, or
            the <a href='%s'>Shotgun Review</a> mobile app.
            """ % (media_page_url, review_url, review_url)

        elif item.properties.get("sg_slap_comp"):
            # icon 
            self._icon = os.path.join(
                                        self.disk_location,
                                        "icons",
                                        "slap.png"
                                    )
            
            # name 
            self._name = "Slap Comp for review"

            # description 
            self._description = """
            A Slap Comp will be created using a predefined nuke script.<br><br>


            A <b>Version</b> entry will then be created in Shotgun and a transcoded
            copy of the file will be attached to it. The file can then be reviewed
            via the project's <a href='%s'>Media</a> page, <a href='%s'>RV</a>, or
            the <a href='%s'>Shotgun Review</a> mobile app.
            """ % (media_page_url, review_url, review_url)

    def create_dl_job_files(self, submission_job_file, submission_job_info, submission_plugin_file, submission_plugin_info):
        # job_dir, job_name = os.path.split(submission_job_file)
        # pugin_dir, pugin_name = os.path.split(submission_plugin_file)

        # if not os.path.exists( job_dir ):
        #     os.makedirs( job_dir )
        # if not os.path.exists( pugin_dir ):
        #     os.makedirs( pugin_dir )
        
        # write job files
        job_writer = open( submission_job_file, "w" )
        for i in submission_job_info:
            job_writer.write( "%s\n" % i )

        job_writer.close()

        # write plugin files
        plugin_writer = open( submission_plugin_file, "w" )
        for i in submission_plugin_info:
            plugin_writer.write( "%s\n" % i )

        plugin_writer.close()

        return submission_job_file, submission_plugin_file

    ### TODO: Add thumbnail dependency to replace Pump job on farm
    # def thumbnail_dependency(self, item):

    #     dl_result = item.properties.get('dl_result')
    #     if not dl_result:
    #         return
        
    #     process_dict = item.properties.get('process_dict')
    #     if not process_dict:
    #         return
        
    #     self.logger.warning(">>>>> process_dict >>>>>")
    #     thumbnail_dict = item.properties['json_properties'].get('thumbnail')
    #     if not thumbnail_dict:
    #         return

    #     self.logger.warning(">>>>> thumbnail_dict >>>>>")
    #     processes = process_dict.get('processes')
    #     if not processes:
    #         return

    #     self.logger.warning(">>>>> processes >>>>>")
    #     if "win" in sys.platform:
    #         path_root = "windows_path"
    #         sg_root = "local_path_windows"
    #     elif sys.platform == "linux":
    #         path_root = "linux_path"
    #         sg_root = "local_path_linux"

    #     for process in processes:
    #         # If you're not making a version you don't need a thumbnail
    #         if not processes[process]['process_settings']['create_version']:
    #             continue

    #         self.logger.warning(">>>>> Preparing thubnail info for %s" % process ) 
            
    #         temp_root = os.path.join(process_dict['project_info']['sg_root'][sg_root],"admin", "processing", "temp").replace("\\","/")

    #         thumb_job_id = None
    #         thumb_job_info_file = "%s/%s/%s/%s-thumb_job_info.job" % (temp_root,"deadline","thumbnails",item.properties['version_data'].get('code'))
    #         thumb_plugin_info_file = "%s/%s/%s/%s-thumb_plugin_info.job" % (temp_root,"deadline","thumbnails",item.properties['version_data'].get('code'))  

    #         find_id = re.search(r"JobID=(.+)\n", dl_result)
    #         if find_id:
    #             job_id = find_id.group(1)

    #         thumb_job_info = [
    #                     "BatchName=%s" % processes[process]['deadline_settings'].get('batch_name'),
    #                     "Name=%s-thumbnail" % (item.properties['version_data'].get('code')),
    #                     "Plugin=Python",
    #                     "Priority=55",
    #                     "MachineLimit=1",
    #                     "Pool=%s" % thumbnail_dict['job_info'].get('pool'),
    #                     "SecondaryPool=%s" % thumbnail_dict['job_info'].get('secondary_pool'),
    #                     "ExtraInfo0=%s" % process_dict['project_info']['name'],
    #                     "Frames=0-1",
    #                     "ChunkSize=1000000",
    #                     "JobDependencies=%s"%(job_id),
    #                     "UserName=%s" %( processes[process]['process_settings'].get('user') )
    #                     ]
    #         thumb_plugin_info = [
    #                     "ScriptFile=%s" % thumbnail_dict['plugin_info'].get('script_file'),
    #                     "Arguments=%s,%s" % (process, item.properties['json_properties']['general_settings']['info_json_file'] ),
    #                     "Version=2.7",
    #                     ]

    #         thumb_job_info, thumb_plugin_info = self.create_dl_job_files(thumb_job_info_file, thumb_job_info, thumb_plugin_info_file, thumb_plugin_info)

            
    #         if (thumb_job_info and thumb_plugin_info):
    #             self.logger.info("Both dependent job files found: %s and %s " %(thumb_job_info,thumb_plugin_info))
    #             start_time = time.time()
    #             deadline_submission = self.dm.get_dl_cmd("%s %s" % ( thumb_job_info, thumb_plugin_info))
    #             self.logger.info(deadline_submission)
    #             self.logger.info("--- Deadline Submission took %s seconds ---" % (str(time.time() - start_time)))
    #             for line in deadline_submission.splitlines():
    #                 if line.startswith("JobID="):
    #                     d_dl_job_id = line[6:]        
    #             self.logger.warning(">>>>> submitted job ID: %s" % d_dl_job_id)
    #         else:
    #             self.logger.error("Issue writing on of the DL .job files") 
