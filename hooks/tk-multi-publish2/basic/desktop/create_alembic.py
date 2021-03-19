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
import sys
import re
import pprint
import time
import datetime
import shutil
import sgtk
import traceback
from sgtk.util.filesystem import copy_file, ensure_folder_exists

# find SSVFX/Deadline plugins
log = sgtk.LogManager.get_logger(__name__)
eng = sgtk.platform.current_engine()

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
                log.debug("!!!!!! Could not find %s" %(ssvfx_script_path,))
            log.debug("Found env var path: %s" %(ssvfx_script_path,))
        else:
            log.debug("SSVFX_PIPELINE not in env var keys. Using explicit")
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

class CreateAlembicPlugin(HookBaseClass):
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
            "alembic.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Create Alembic with Deadline"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return """
        Send a job to create the alembic of a given 3D file.<br><br>

        An <b>Alembic</b> Published File entry will be created in Shotgun and linked to the given Task/Entity
        """ 

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
                "default": "mb, ma",
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
        return ["file.maya"]

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

        if 'fields' not in item.properties.keys():
            return accept

        if 'template' not in item.properties.keys():
            return accept

        file_info = item.properties['fields']
        extension = file_info["extension"].lower()

        valid_extensions = [ ext.strip().lstrip(".") for ext in settings["File Extensions"].value.split(",") ]

        if extension not in valid_extensions:
            self.logger.debug(
                "%s is not in the valid extensions list for Version creation" %
                (extension,)
            )
            return accept

        else:
            accept = {"accepted": True}

        # test for appropriate outsource_root template
        template = item.properties.get('template')

        if template:
            self.logger.debug("Associated template is: %s" %(template.name))
            if template.name == "maya_shot_outsource_work_file":
                accept = {"accepted": True}


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
        publisher = self.parent

        if not item.context.task:
            raise Exception("Need task info!")

        project_info = item.properties.get("project_info")
        if not project_info['local_storage']:
            self.logger.warning("No local storage defined - this may be required for future processes such as publishing files")
        else:
            self.logger.info("Local storage: %s" % (project_info['local_storage']))

        if not item.properties.get("step"):
            self.review_process = publisher.shotgun.find("Step", 
                [['id', 'is', item.context.step['id']]], 
                item.properties["step_fields"])
        else:
            self.review_process = item.properties.get("step")

        if item.properties.fields:
            maya_shot_cache_alembic_abc = publisher.engine.get_template_by_name('maya_shot_cache_alembic_abc').apply_fields(item.properties.fields)
            self.logger.info("Caching to: %s" % (maya_shot_cache_alembic_abc))
            item.properties['maya_shot_cache_alembic_abc'] = maya_shot_cache_alembic_abc

        # We allow the information to be pre-populated by the collector or a
        # base class plugin. They may have more information than is available
        # here such as custom type or template settings.
        publish_type = "Alembic Cache" #item.to_dict()['type_display'] 
        publish_path = maya_shot_cache_alembic_abc
        publish_code = os.path.split(maya_shot_cache_alembic_abc)[1]
        publish_name = re.sub(r".abc$", "", self.get_publish_name(settings, item, output_path=item.properties['maya_shot_cache_alembic_abc']))

        # Note the name, context, and path *must* match the values supplied to
        # register_publish in the publish phase in order for this to return an
        # accurate list of previous publishes of this file.

        publishes = self.test_conflicting_publishes( 
            publish_path,
            publish_name)


        if publishes:
            conflict_info = (
                "If you continue, these conflicting publishes will no "
                "longer be available to other users via the loader:<br>"
                "<pre>%s</pre>" % (pprint.pformat(publishes),)
            )
            self.logger.warning(
                "Found %s conflicting publishes in Shotgun" % (len(publishes),),
                extra={
                    "action_show_more_info": {
                        "label": "Show Conflicts",
                        "tooltip": "Show conflicting publishes in Shotgun",
                        "text": conflict_info
                    }
                }
            )
            return False

        self.logger.info("A Publish will be created in Shotgun and linked to:")
        self.logger.info("  %s" % (maya_shot_cache_alembic_abc,))


        temp_root_template = publisher.engine.get_template_by_name("temp_shot_root")
        temp_root = temp_root_template.apply_fields(item.properties.fields)
        self.test_template(item, temp_root, 'temp_root')

        item.properties['publish_name'] = publish_name
        item.properties['publish_type'] = publish_type      
        item.properties['publish_path'] =  publish_path
        try:
            item.properties['publish_task_id'] =  item.context.task['id']
            self.logger.warning(item.properties['publish_task_id'])
        except:
            pass

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

        # self.logger.debug(">>>>> item.properties at START Publish")
        # self.logger.debug(item.properties.to_dict())

        # publisher = self.parent
        self.dl_submission = deadline_submission4.DeadlineSubmission()

        # create deadline files
        self.create_dl_info_files( item )

        # create submission files
        job_info_file, plugin_info_file = self._create_submission_files( item )

        # send submission job to deadline
        self.send_to_dl( job_info_file, plugin_info_file )

        # project_info = item.properties.get("project_info")
        # entity_info = item.properties.get("entity_info")
        

        # item.properties["output_root"] = os.path.split(item.properties['publish_path'])[0]
        # item.properties["output_main"] = os.path.split(item.properties['publish_path'])[1]
        # item.properties["output_ext"] = os.path.splitext(item.properties['publish_path'])[1]
                        
        # content_info_dict = {}
        # item.properties["content_info"] = content_info_dict

        # process_info = self.set_process_info(self.dl_submission,
        #                 "MayaBatch",
        #                 "alembic-cache",
        #                 {},
        #                 project_info,
        #                 entity_info,
        #                 item)

        # if not os.path.exists(item.properties["output_root"]):
        #     os.makedirs(item.properties["output_root"])
        #     self.logger.debug("Making dir: %s" % (item.properties["output_root"]))

        # self.send_to_dl(self.dl_submission, process_info, item) 

        # handle copying of work to publish if templates are in play
        # self._copy_work_to_publish(settings, item)
        # if (item.properties['template'] and
        # item.properties.fields):
        #     if item.properties['template'].name == "incoming_outsource_shot_folder_root":
        #         maya_shot_work = publisher.engine.get_template_by_name('maya_shot_work')
        #         item.properties['work_template'] =  maya_shot_work
        #         self._copy_outsource_to_work(settings, item)

        maya_shot_work = publisher.engine.get_template_by_name('maya_shot_work')
        self._copy_outsource_to_work( settings, item, maya_shot_work )
    
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

    def get_publish_template(self, settings, item):
        """
        Get a publish template for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish template for

        :return: A template representing the publish path of the item or
            None if no template could be identified.
        """

        return item.get_property("publish_template")
  
    def get_publish_name(self, settings, item, output_path=None):
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
        if output_path:
            path = output_path
        
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

    def send_to_dl(self, dl_module, draft_info, item):
        """
        Runs cmd function to send image sequence to DL.
        Needs to be of type file.type.sequence.

        :param item: Item to process
        """   
        self.dm = deadline_manager3.DeadlineManager()

        try:
            deadline_submission = self.dm.get_dl_cmd("%s %s %s" % (draft_info['job_info_file'], draft_info['plugin_info_file'], item.properties['path']))
        except:
            raise Exception("Failed in the DL submission process.")          
        finally:
            self.logger.debug("Sucessfully Sent job to DL.")
            for line in deadline_submission.splitlines():
                if not line:
                    pass
                else:
                    self.logger.debug("--- %s "% (line,))
        
        # self.logger.info("Version Submission Complete!\nVersion has been sent to SG and the QT sent to DL")
    
    def replace_slashes(self, path):
        """
        Simple function to replace back with forward slashes
        """
        if not path:
            return
        else:
            return path.replace("\\","/")

    def set_process_info(self, dl_module, plugin_name, process_name, plugin_settings, project_info, entity_info, item, multiple_task_list=None):
        
        process_info = None
        # DL vairables
        batch_name = (item.properties['publish_name'] + "_submit") or ""
        job_name = (item.properties['publish_name']) or ""
        plate_type = ""        
        create_version = False
        project_root_name = None
        update_version = False
        update_client_version = False
        create_publish = True
        publish_file_type = "Alembic Cache"
        publish_file_name = item.properties['publish_name']
        publish_file_version = item.properties['version_data'].get('version_number')
        publish_file_task = None
        copy_to_location = False
        copy_location = None
        plugin_path = None
        zip_output = False
        plugin_version = None
        comment = ""
        title = "alembic_cache"        
        department = "VFX"
        group="artist"
        priority = 55
        primary_pool = "vfx_maya"
        secondary_pool = "vfx_maya"
        machine_limit = 1
        concurrent_task = 1
        chunk_size = 1000000

        # # Content variables
        content_info = item.properties.get('content_info') or ""
        content_output_file = item.properties.get('output_main') or ""
        content_output_file_total = item.properties.get('output_main') or ""
        content_output_file_ext = item.properties.get('output_ext') or ""
        content_output_root = item.properties.get('output_root') or ""
        content_output_file_total = os.path.join(content_output_root,content_output_file)
        job_dependencies = ""
        frame_range = item.properties.get("frame_range") or None
        slate_enabled = False
        burnin_enabled = False
        plugin_in_script = None
        plugin_out_script = None
        temp_root = self.replace_slashes(item.properties['temp_root'])
        script_file = None

        user_name = ""
        try:
            user_info = item.properties.get("user_info")    
            if( user_info and 
            len(user_info)==1):
                user_name = user_info[0]['login']
        except:
            self.logger.warning("Could not get user_name info")

        try:
            publish_file_task = item.properties.get('publish_task_id')
        except:
            self.logger.warning("Could not get publish_task_id info")

        if item.properties['project_info']['local_storage']:
            project_root_name = item.properties['project_info']['local_storage']['code']

        software_maya = next((soft for soft in item.properties['software_info'] if soft['products'] == "Maya"), None)
        if software_maya:
            plugin_version = software_maya['version_names']

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
            publish_file_task = publish_file_task,
            publish_file_name = publish_file_name,
            publish_file_version = publish_file_version,
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
            project_root_name = project_root_name,              
            sg_temp_root = temp_root
            )
        
        # for pk, in process_info.items():
            

        # if multiple_task_list != None:
        #     process_info.update({'info_json_count':len(multiple_task_list)})
        #     for index, i in enumerate(multiple_task_list):
        #         info_json_key = 'info_json_0%s'%str(index+1)
        #         process_info.update({info_json_key:i})

        # job_info_file,plugin_info_file = self.create_dl_info_files(dl_module, project_info, entity_info, process_info)
        job_info_file,plugin_info_file = self.create_dl_info_files(dl_module, item)
        process_info.update({'job_info_file':job_info_file})
        process_info.update({'plugin_info_file':plugin_info_file})

        return process_info

    # def create_dl_info_files(self, dl_module, project_info_dict, entity_info, process_info_dict):
    def create_dl_info_files(self, dl_module, item):
        
        job_info = None
        plugin_info = None

        # total_info = dict(
        # project_info = project_info_dict,
        # entity_info = entity_info,
        # process_info = process_info_dict
        # )

        total_info = item.to_dict().get('global_properties')
        process_plugin = item.properties['set_software'].get('code')

        job_info = self.create_job_info(dl_module,
                            total_info, 
                            process_plugin)
        plugin_info = self.create_plugin_info(dl_module,
                            total_info, 
                            process_plugin)

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
                self.logger.info("Template: %s - %s" % (property_key,template))
                return template            

    def test_conflicting_publishes(self, publish_path,publish_name):

        publisher = self.parent
        publish_match = None
        self.logger.warning("Testing for existing Alembics with same name/path")


        publish_filters = [
            ["published_file_type", "is", {"type": "PublishedFileType", "id": 5}],
            ["name", "is", publish_name]
        ]

        publish_fields = [
            "path",
            "code",
            "entity",
            "name",
        ]

        published_files = publisher.shotgun.find("PublishedFile", 
            publish_filters,
            publish_fields
            )

        if published_files:                   
            publish_match = next((pub for pub in published_files if (pub['name'] == publish_name and sgtk.util.ShotgunPath.normalize(pub['path']['local_path_windows']) == sgtk.util.ShotgunPath.normalize(publish_path))),None)
        
        return publish_match

    def _copy_outsource_to_work(self, settings, item, template):

        # work_template = item.properties.get("work_template")
        # if not work_template:
        if not template:
            self.logger.debug(
                "No workfiles template set on the item. "
                "Skipping copy file to publish location."
            )
            return

        if not item.properties.get('fields'):
            self.logger.debug(
                "No item fields supplied from collector."
                "Cannot resolve template paths."
            )
            return

        # copy the outsource files to the work location
        # by default, the path that was collected for publishing
        outsource_file = item.properties['path']
        work_file = template.apply_fields( item.properties['fields'] )

        # copy the file
        try:
            work_folder = os.path.dirname(work_file)
            ensure_folder_exists(work_folder)
            copy_file(outsource_file, work_file)
        except Exception:
            raise Exception(
                "Failed to copy outsource file from '%s' to '%s'.\n%s" %
                (outsource_file, work_file, traceback.format_exc())
            )

        self.logger.debug(
            "Copied work file '%s' to work file '%s'." %
            (outsource_file, work_file)
        )     

        # for outsource_file in outsource_files:

        #     # if not work_template.validate(outsource_file):
        #     #     self.logger.warning(
        #     #         "Work file '%s' did not match work template '%s'. "
        #     #         "Publishing in place." % (outsource_file, work_template)
        #     #     )
        #     #     return

        #     # work_fields = work_template.get_fields(outsource_file)

        #     # missing_keys = work_template.missing_keys(work_fields)

        #     # if missing_keys:
        #     #     self.logger.warning(
        #     #         "Work file '%s' missing keys required for the publish "
        #     #         "template: %s" % (outsource_file, missing_keys)
        #     #     )
        #     #     return

        #     work_file = work_template.apply_fields(item.properties.fields)
        #     self.logger.debug(">>>>> work_file: %s" % str(work_file))
        #     self.logger.debug(">>>>> outsource_file: %s" % str(outsource_file))

            # # copy the file
            # try:
            #     work_folder = os.path.dirname(work_file)
            #     ensure_folder_exists(work_folder)
            #     copy_file(outsource_file, work_file)
            # except Exception:
            #     raise Exception(
            #         "Failed to copy outsource file from '%s' to '%s'.\n%s" %
            #         (outsource_file, work_file, traceback.format_exc())
            #     )

            # self.logger.debug(
            #     "Copied work file '%s' to work file '%s'." %
            #     (outsource_file, work_file)
            # )                
