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
import json
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

        if not item.description:
            raise Exception("Need to fill in description detailing submitted work!")

        ### PUBLISH FILE VALIDATION ###
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

        # gather remaining publish data
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

        #### ALEMBIC-SPECIFIC VALIDATION/FILE GENERATION ###
        # refine JSON values and generate .job files for Deadline
        json_properties = item.properties.get('json_properties')

        process_type = item.properties['step'].get('sg_review_process_type').lower()        
        process_dict =  json_properties[process_type]
        json_path = json_properties['general_settings']['alembic_json_file']

        if not json_path:
            raise Exception( "Missing path to deadline json file" )

        # update values for alembic render
        plugin_info_file = None
        job_info_file = None
        for process in process_dict['processes']:
            alembic_process = process_dict['processes'][process]
            # process settings
            alembic_process['process_settings']['review_output'] = publish_path
            alembic_process['process_settings']['plugin_name'] = "MayaBatch"

            # deadline_settings
            alembic_process['deadline_settings']['output_file'] = publish_code
            alembic_process['deadline_settings']['content_output_file_total'] = publish_path
            alembic_process['deadline_settings']['output_root'] = os.path.dirname( publish_path )
            alembic_process['deadline_settings']['frame_range'] = "%s-%s" % ( item.properties['entity_info']['sg_head_in'], item.properties['entity_info']['sg_tail_out'] )

            plugin_info_file = alembic_process['deadline_settings']['plugin_info_file']
            job_info_file = alembic_process['deadline_settings']['job_info_file']

        item.properties['alembic_job_files'] = {
                                                "plugin_info_file": plugin_info_file,
                                                "job_info_file": job_info_file,
                                                }

        # create json storage dir
        if not os.path.exists( os.path.dirname( json_path ) ):
            os.makedirs( os.path.dirname( json_path ) )

        # create alembic output dir
        if not os.path.exists( os.path.dirname( publish_path ) ):
            os.makedirs( os.path.dirname( publish_path ) )


        self.logger.warning(">>>>> writing to json file: %s" % json_path)

        file_write = open( json_path, "w+" )
        json_data = json.dumps(process_dict, sort_keys=False,
                                indent=4, separators=(',', ': '), default=str)
        file_write.write(json_data)
        file_write.flush()
        file_write.close()

        self.gather_job_info( process_dict )
        self.gather_plugin_info( process_dict )

        if not ( job_info_file and plugin_info_file ):
            if not job_info_file:
                raise Exception( "Missing job info file" )
            else:
                raise Exception( "Missing plugin info file" )

        # for i in item.properties:
        #     self.logger.warning(">>>>> %s: %s" % ( i, item.properties[i] ) )

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

        info_files = item.properties['alembic_job_files']
        
        self.dm = deadline_manager3.DeadlineManager3()
        # deadline_submission = self.dm.get_dl_cmd("%s %s %s" % (draft_info['job_info_file'], draft_info['plugin_info_file'], item.properties['path']))
        self.dm.get_dl_cmd( "%s %s %s" % ( info_files.get('job_info_file'), info_files.get('plugin_info_file'), item.properties['path'] ) )

        maya_shot_work = publisher.engine.get_template_by_name('maya_shot_work')
        self._copy_outsource_to_work( item, maya_shot_work )

        self.publish_file_publish( item )


        self.logger.info( "Published Alembic Cache to SG" )
    
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

    def _copy_outsource_to_work(self, item, template):

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

    def gather_job_info(self, info_dict):
        """
        Sets up the deadline job info 

        :param info_dict: loaded data for the content that will inform all relevant requirements
        """

        # Collect basic JSON components to simplify organizing 
        project_info = info_dict['project_info']
        entity_info = info_dict['entity_info']
        processes_dict =  info_dict.get('processes')

        # loop through processes to set up appropriate values for job file
        for i in processes_dict:
            key = str(i)
            if not processes_dict[key]:
                continue

            process_settings = processes_dict[key]['process_settings']
            deadline_settings = processes_dict[key]['deadline_settings']

            job_info_file = deadline_settings.get('job_info_file')
            if not job_info_file:
                self.logger.warning("No job_info_file found!")
                break
            if not os.path.exists( os.path.dirname( job_info_file ) ):
                os.makedirs( os.path.dirname( job_info_file ) )

            # set output locations
            output_filename = deadline_settings['output_file']
            output_directory = deadline_settings['output_root']
            if deadline_settings.get('job_dependencies'):
                output_filename = deadline_settings['output_file']
                output_directory = deadline_settings['output_root']

            basic_job_info = dict(
                BatchName= deadline_settings['batch_name'],
                OnJobComplete= "Nothing",
                Plugin= process_settings['plugin_name'],
                MachineLimit= deadline_settings['machine_limit'],
                ConcurrentTasks= deadline_settings['concurrent_task'],
                ChunkSize= deadline_settings['chunk_size'],
                Department= deadline_settings.get('department'),
                Group= deadline_settings.get('group'),
                Priority= deadline_settings['priority'],
                Name= deadline_settings['job_name'],
                OutputFilename0= output_filename,
                OutputDirectory0= output_directory,
                Pool= deadline_settings['primary_pool'],
                SecondaryPool= deadline_settings['secondary_pool'],
                UserName= process_settings['user'],
                Frames= deadline_settings['frame_range'],
                ExtraInfo0= project_info['name'],
            )

            job_extra_info = dict(
                ProjectID= project_info['id'],
                ProjectName= project_info['name'],
                ContentType= info_dict['entity_info']['type'],                
                ContentID= entity_info['id'],
                PublishFileType= deadline_settings['publish_file_type'],
                ProcessType= key,
                CreateVersion= process_settings['create_version'],
                UpdateVersion= process_settings['update_version'],
                CreatePublish= process_settings['create_publish'],
                UpdateClientVersion= process_settings['update_client_version'],
                FileExtension=deadline_settings['output_file_ext']
            )

            if 'version_info' in info_dict.keys():
                version_info = info_dict['version_info']
                job_extra_info['VersionName']= version_info.get('code')
                job_extra_info['VersionID']= version_info.get('id')
                job_extra_info['PipelineStep']= version_info['sg_task']['name']
                job_extra_info['InFile']= version_info['sg_path_to_frames'],
                job_extra_info['TaskID']= version_info['sg_task']['id']
                job_extra_info['Description']= version_info.get('description')                          

            # write the actual job file to disk
            job_info_file = deadline_settings['job_info_file']
            writer = open( job_info_file, "w" )

            for i in basic_job_info:
                try:
                    writer.write( "%s=%s\n" % ( i, basic_job_info[i] ) )
                except:
                    writer.write( "%s=%s\n" % ( i, basic_job_info[i].encode('utf-8') ) )
            
            for i, j in enumerate(job_extra_info.keys()):
                ev_num = str(i)
                try:
                    writer.write( "ExtraInfoKeyValue%s=%s=%s\n" % ( ev_num, j, job_extra_info[j] ) )
                except:
                    writer.write( "ExtraInfoKeyValue%s=%s=%s\n" % ( ev_num, j, job_extra_info[j].encode('utf-8') ) )
            
            writer.close()
            self.logger.info("Created JOBINFO %s " % (job_info_file))
    
    def gather_plugin_info(self, info_dict):
        """
            Sets up the deadline job info 
            :param info_dict loaded data for the content that will inform all relevant requirements
        """

        if 'json_properties'in info_dict.keys():
            json_properties = info_dict['json_properties']
            process_type = info_dict['step'].get('sg_review_process_type').lower()        
            processes_dict =  json_properties[process_type].get('processes')
        else:
            processes_dict =  info_dict.get('processes')

        # Flatten the dictionary to prepare it for writing to plugin file
        # NOTE: DL files can't be nested dictionaries/lists
        def flatten_dict(my_dict, existing_dict, prev_key=None):
            for k, v in my_dict.items():
                safe_name = k
                if prev_key:
                    safe_name =  "%s_%s" % (prev_key.split("_")[0], k)

                if not isinstance(v, dict):
                    existing_dict[safe_name] = v
                else:
                    flatten_dict(v, existing_dict, prev_key=k)
            return existing_dict  

        # loop through processes to set up appropriate values for job file
        for i in processes_dict:
            key = str(i)

            if not processes_dict[key]:
                self.logger.warning("No data found for %s" %(key))
                continue            
            process_settings = processes_dict[key]['process_settings']
            deadline_settings = processes_dict[key]['deadline_settings']
            alembic_settings = processes_dict[key]['alembic_settings']

            plugin_info_file = deadline_settings.get('plugin_info_file')
            if not os.path.exists( os.path.dirname( plugin_info_file ) ):
                os.makedirs( os.path.dirname( plugin_info_file ) )

            set_string = "ScriptArg%s=%s=%s\n"
            root_list = []
            for j in processes_dict[key]:
                root_list.extend( flatten_dict( processes_dict[key][j], {} ).items() )

            # alembic-specific additions read from project's alembic setting json
            write_list = []
            write_list.append( "Version=%s\n" % process_settings['plugin_version'] )
            write_list.append( "AlembicAttributePrefix=%s\n" % alembic_settings['alembic_attribute_prefix'] )
            write_list.append( "AlembicAttributes=%s\n" % alembic_settings['alembic_attributes'] )
            write_list.append( "AlembicFormatOption=%s\n" % alembic_settings['alembic_format_option'] )
            write_list.append( "AlembicHighSubFrame=%s\n" % alembic_settings['alembic_high_subframe'] )
            write_list.append( "AlembicJob=%s\n" % alembic_settings['alembic_job'] )
            write_list.append( "AlembicLowSubFrame=%s\n" % alembic_settings['alembic_low_subframe'] )
            write_list.append( "AlembicSelection=%s\n" % alembic_settings['alembic_selection'] )
            write_list.append( "AlembicSubFrames=%s\n" % alembic_settings['alembic_subframes'] )
            write_list.append( "Animation=%s\n" % alembic_settings['animation'] )
            write_list.append( "Build=%s\n" % alembic_settings['build'] )
            write_list.append( "EnableOpenColorIO=%s\n" % alembic_settings['enable_open_colorIO'] )
            write_list.append( "IgnoreError211=%s\n" % alembic_settings['ignore_error_211'] )

            write_list.append( "OutputFile=%s\n" % deadline_settings['output_file'] )
            write_list.append( "OutputFilePath=%s\n" % deadline_settings['output_root'] )

            write_list.extend( [ set_string % (j,k,l) for j,(k,l) in enumerate(root_list) ] )
            
            # write the actual plugin file to disk
            writer = open(plugin_info_file, "w")

            for info_dict in write_list:
                writer.write(info_dict)

            writer.close()

            self.logger.info("Created PLUGININFO %s " % (plugin_info_file))

    def publish_file_publish(self, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        publisher = self.parent

        # ---- determine the information required to publish

        # We allow the information to be pre-populated by the collector or a
        # base class plugin. They may have more information than is available
        # here such as custom type or template settings.

        publish_name = item.properties['publish_name']
        publish_path = item.properties['publish_path']
        publish_type = item.properties['publish_type']
        publish_dependencies_paths = []
        publish_thumbnail = item.get_property("thumbnail_path")
        publish_user = item.get_property("publish_user", default_value=None)
        publish_version = self.get_publish_version( item )

        # Test if there is sufficient info for thumbnail
        if publish_thumbnail:
            self.logger.debug("Found first frame for thumbnail:")
            self.logger.debug(publish_thumbnail)
        else:
            self.logger.debug("No thumbnail file given.")

        self.logger.debug("Publish name: %s" % (publish_name,))

        # arguments for publish registration
        self.logger.info("Registering publish...")

        publish_data = {
            "tk": publisher.sgtk,
            "context": item.context,
            "path": publish_path,
            "name": publish_name,
            "comment": item.description,
            "version_number": publish_version,
        }
        item.properties.publish_fields = {
            "sg_fields": {"sg_status_list": "cmpt",}
            }

        item.properties.publish_kwargs = {
            "version_entity": None,
            "thumbnail_path": publish_thumbnail, 
            "created_by": publish_user,
            "published_file_type": publish_type,
            "dependency_paths": publish_dependencies_paths,
            "dependency_ids": [],
            }
            

        # catch-all for any extra kwargs that should be passed to register_publish.
        publish_kwargs = item.get_property("publish_kwargs", default_value={})
        publish_fields = item.get_property("publish_fields", default_value={})
        
        # add extra kwargs
        publish_data.update(publish_kwargs)
        publish_data.update(publish_fields)

        # log the publish data for debugging
        self.logger.debug(
            "Populated Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Publish Data",
                    "tooltip": "Show the complete Publish data dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(publish_data),)
                }
            }
        )

        # create the publish and stash it in the item properties for other
        # plugins to use.
        item.properties.sg_publish_data = sgtk.util.register_publish(**publish_data)
        self.logger.info("Publish registered!")
        self.logger.debug(
            "Shotgun Publish data...",
            extra={
                "action_show_more_info": {
                    "label": "Shotgun Publish Data",
                    "tooltip": "Show the complete Shotgun Publish Entity dictionary",
                    "text": "<pre>%s</pre>" % (pprint.pformat(item.properties.sg_publish_data),)
                }
            }
        )

    def get_publish_version(self, item):
        """
        Get the publish version for the supplied settings and item.

        :param settings: This plugin instance's configured settings
        :param item: The item to determine the publish version for

        Extracts the publish version via the configured work template if
        possible. Will fall back to using the path info hook.
        """

        # publish version explicitly set or defined on the item
        publish_version = item.get_property("publish_version")
        if publish_version:
            return publish_version

        # fall back to the template/path_info logic
        publisher = self.parent
        path = item.properties.path

        work_template = item.properties.get("work_template")
        work_fields = None
        publish_version = None

        if work_template:
            if work_template.validate(path):
                self.logger.debug(
                    "Work file template configured and matches file.")
                work_fields = work_template.get_fields(path)

        if work_fields:
            # if version number is one of the fields, use it to populate the
            # publish information
            if "version" in work_fields:
                publish_version = work_fields.get("version")
                self.logger.debug(
                    "Retrieved version number via work file template.")

        else:
            self.logger.debug(
                "Using path info hook to determine publish version.")
            publish_version = publisher.util.get_version_number(path)
            if publish_version is None:
                publish_version = 1

        return publish_version


