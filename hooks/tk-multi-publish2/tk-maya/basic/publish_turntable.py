# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license 
# file included in this repository.

import os
import maya.cmds as cmds
import maya.mel as mel
import pprint
import re
import sgtk
import subprocess
import sys
import shutil
import datetime

HookBaseClass = sgtk.get_hook_baseclass()

# Environment variables for turntable script
OUTPUT_PATH_ENVVAR = 'UNREAL_SG_FBX_OUTPUT_PATH'
CONTENT_BROWSER_PATH_ENVVAR = 'UNREAL_SG_CONTENT_BROWSER_PATH'
MAP_PATH_ENVVAR = 'UNREAL_SG_MAP_PATH'

class MayaUnrealTurntablePublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open maya session as an exported FBX.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.
    temp_folder = "C:/temp_unreal_shotgun/"
    
    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        <p>This plugin renders a turntable of the asset for the current session
        in Unreal Engine.  The asset will be exported to FBX and imported into
        an Unreal Project for rendering turntables.  A command line Unreal render
        will then be initiated and output to a templated location on disk.  Then,
        the turntable render will be published to Shotgun and submitted for review
        as a Version.</p>
        """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
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

        # inherit the settings from the base publish plugin
        base_settings = super(MayaUnrealTurntablePublishPlugin, self).settings or {}

        # settings specific to this class
        maya_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            }
        }

        work_template_setting = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for exported FBX files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            }
        }

        unreal_engine_version_setting = {
            "Unreal Engine Version": {
                "type": "string",
                "default": None,
                "description": "Version of the Unreal Engine exectuable to use."
            }
        }
        
        unreal_project_path_setting = {
            "Unreal Project Path": {
                "type": "string",
                "default": None,
                "description": "Path to the Unreal project to load."
            }
        }

        turntable_map_path_setting = {
            "Turntable Map Path": {
                "type": "string",
                "default": None,
                "description": "Unreal path to the turntable map to use to render the turntable."
            }
        }
        
        sequence_path_setting = {
            "Sequence Path": {
                "type": "string",
                "default": None,
                "description": "Unreal path to the level sequence to use to render the turntable."
            }
        }

        assets_output_path_setting = {
            "Turntable Assets Path": {
                "type": "string",
                "default": None,
                "description": "Unreal output path where the turntable assets will be imported."
            }
        }

        # update the base settings
        base_settings.update(maya_publish_settings)
        base_settings.update(work_template_setting)
        base_settings.update(unreal_engine_version_setting)
        base_settings.update(unreal_project_path_setting)
        base_settings.update(turntable_map_path_setting)
        base_settings.update(sequence_path_setting)
        base_settings.update(assets_output_path_setting)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["maya.turntable"]

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

        accepted = True
        publisher = self.parent
        template_name = settings["Publish Template"].value

        # ensure a work file template is available on the parent item
        work_template = item.parent.properties.get("work_template")
        if not work_template:
            self.logger.debug(
                "A work template is required for the session item in order to "
                "publish a turntable.  Not accepting the item."
            )
            accepted = False

        # ensure the publish template is defined and valid and that we also have
        publish_template = publisher.get_template_by_name(template_name)
        if not publish_template:
            self.logger.debug(
                "The valid publish template could not be determined for the "
                "turntable.  Not accepting the item."
            )
            accepted = False

        # we've validated the publish template. add it to the item properties
        # for use in subsequent methods
        item.properties["publish_template"] = publish_template

        # because a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        item.context_change_allowed = False

        return {
            "accepted": accepted,
            "checked": True
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        path = _session_path()

        # ---- ensure the session has been saved

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The Maya session has not been saved."
            self.logger.error(
                error_msg,
                extra=_get_save_as_action()
            )
            raise Exception(error_msg)

        # get the normalized path
        path = sgtk.util.ShotgunPath.normalize(path)

        # get the configured work file template
        work_template = item.parent.properties.get("work_template")
        publish_template = item.properties.get("publish_template")

        # get the current scene path and extract fields from it using the work
        # template:
        work_fields = work_template.get_fields(path)

        # stash the current scene path in properties for use later
        item.properties["work_path"] = path

        # ensure the fields work for the publish template
        missing_keys = publish_template.missing_keys(work_fields)
        if missing_keys:
            error_msg = "Work file '%s' missing keys required for the " \
                        "publish template: %s" % (path, missing_keys)
            self.logger.error(error_msg)
            raise Exception(error_msg)

        # Validate the Unreal executable and project, stash in properties
        unreal_exec_path = self.get_unreal_project_path() or self._get_unreal_exec_path(settings)
        if not unreal_exec_path or not os.path.isfile(unreal_exec_path):
            self.logger.error("Unreal executable not found at {}".format(unreal_exec_path))
            return False
        item.properties["unreal_exec_path"] = unreal_exec_path

        # Use the Unreal project path override if it's defined, otherwise use the path from the settings
        # stash in properties
        unreal_project_path = self.get_unreal_project_path() or self._get_unreal_project_path(settings)
        if not unreal_project_path or not os.path.isfile(unreal_project_path):
            self.logger.error("Unreal project not found at {}".format(unreal_project_path))
            return False
        item.properties["unreal_project_path"] = unreal_project_path

        # Validate the Unreal data settings, stash in properties
        turntable_map_path_setting = settings.get("Turntable Map Path")
        turntable_map_path = turntable_map_path_setting.value if turntable_map_path_setting else None
        if not turntable_map_path:
            self.logger.debug("No Unreal turntable map configured.")
            return False
        item.properties["turntable_map_path"] = turntable_map_path

        # Validate the Unreal level sequence path, stash in properties
        sequence_path_setting = settings.get("Sequence Path")
        sequence_path = sequence_path_setting.value if sequence_path_setting else None
        if not sequence_path:
            self.logger.debug("No Unreal turntable sequence configured.")
            return False
        item.properties["sequence_path"] = sequence_path

        # Validate the Unreal content browser path, stash in properties
        unreal_content_browser_path_setting = settings.get("Turntable Assets Path")
        unreal_content_browser_path = unreal_content_browser_path_setting.value if unreal_content_browser_path_setting else None
        if not unreal_content_browser_path:
            self.logger.debug("No Unreal turntable assets output path configured.")
            return False
        item.properties["unreal_content_browser_path"] = unreal_content_browser_path

        # create the publish path by applying the fields. store it in the item's
        # properties. This is the path we'll create and then publish in the base
        # publish plugin. Also set the publish_path to be explicit.
        item.properties["path"] = publish_template.apply_fields(work_fields)
        item.properties["publish_path"] = item.properties["path"]
        item.properties["publish_type"] = "Unreal Turntable Render"

        # use the work file's version number when publishing
        if "version" in work_fields:
            item.properties["publish_version"] = work_fields["version"]
        
        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # Get the Unreal settings again
        unreal_exec_path = item.properties["unreal_exec_path"]
        unreal_project_path = item.properties["unreal_project_path"]
        turntable_map_path = item.properties["turntable_map_path"]
        sequence_path = item.properties["sequence_path"]
        unreal_content_browser_path = item.properties["unreal_content_browser_path"]

        # This plugin publishes a turntable movie to Shotgun
        # These are the steps needed to do that

        # =======================
        # 1. Export the Maya scene to FBX
        # The FBX will be exported to a temp folder
        # Another folder can be specified as long as the name has no spaces
        # Spaces are not allowed in command line Unreal Python args
        self.parent.ensure_folder_exists(self.temp_folder)
        fbx_folder = self.temp_folder

        # Get the filename from the work file
        work_path = item.properties.get("work_path")
        work_path = os.path.normpath(work_path)
        work_name = os.path.split(work_path)[1]
        work_name = os.path.splitext(work_name)[0]        

        # Replace non-word characters in filename, Unreal doesn't like those
        # Substitute '_' instead
        exp = re.compile(u"\W", re.UNICODE)
        work_name = exp.sub("_", work_name)

        # Use current time as string as a unique identifier
        now = datetime.datetime.now()
        timestamp = str(now.hour) + str(now.minute) + str(now.second)

        # Replace file extension with .fbx and suffix it with "_turntable"
        fbx_name = work_name + "_" + timestamp + "_turntable.fbx"
        fbx_output_path = os.path.join(fbx_folder, fbx_name)
        
        # Export the FBX to the given output path
        if not self._maya_export_fbx(fbx_output_path):
            return False

        # Keep the fbx path for cleanup at finalize
        item.properties["temp_fbx_path"] = fbx_output_path
        
        # =======================
        # 2. Import the FBX into Unreal.
        # 3. Instantiate the imported asset into a duplicate of the turntable map.
        # Use the unreal_setup_turntable to do this in Unreal

        current_folder = os.path.dirname( __file__ )
        script_name = "../unreal/unreal_setup_turntable.py"
        script_path = os.path.join(current_folder, script_name)
        script_path = os.path.abspath(script_path)

        # Workaround for script path with spaces in it
        if " " in script_path:
            # Make temporary copies of the scripts to a path without spaces
            script_destination = self.temp_folder + "unreal_setup_turntable.py"
            shutil.copy(script_path, script_destination)
            script_path = script_destination

            importer_path = os.path.join(current_folder, "../unreal/unreal_importer.py")
            importer_path = os.path.abspath(importer_path)
            importer_destination = self.temp_folder + "unreal_importer.py"
            shutil.copy(importer_path, importer_destination)

            do_temp_folder_cleanup = True

        if " " in unreal_project_path:
            unreal_project_path = '"{}"'.format(unreal_project_path)
            
        # Set the script arguments in the environment variables            
        # The FBX to import into Unreal
        os.environ[OUTPUT_PATH_ENVVAR] = fbx_output_path
        self.logger.info("Setting environment variable {} to {}".format(OUTPUT_PATH_ENVVAR, fbx_output_path))

        # The Unreal content browser folder where the asset will be imported into
        os.environ[CONTENT_BROWSER_PATH_ENVVAR] = unreal_content_browser_path
        self.logger.info("Setting environment variable {} to {}".format(CONTENT_BROWSER_PATH_ENVVAR, unreal_content_browser_path))

        # The Unreal turntable map to duplicate where the asset will be instantiated into
        os.environ[MAP_PATH_ENVVAR] = turntable_map_path
        self.logger.info("Setting environment variable {} to {}".format(MAP_PATH_ENVVAR, turntable_map_path))

        self._unreal_execute_script(unreal_exec_path, unreal_project_path, script_path)

        del os.environ[OUTPUT_PATH_ENVVAR]
        del os.environ[CONTENT_BROWSER_PATH_ENVVAR]
        del os.environ[MAP_PATH_ENVVAR]

        # =======================
        # 4. Render the turntable to movie.
        # Output the movie to the publish path
        publish_path = item.properties.get("path")
        publish_path = os.path.normpath(publish_path)

        # Split the destination path into folder and filename
        destination_folder = os.path.split(publish_path)[0]
        movie_name = os.path.split(publish_path)[1]
        movie_name = os.path.splitext(movie_name)[0]

        # Ensure that the destination path exists before rendering the sequence
        self.parent.ensure_folder_exists(destination_folder)

        # Render the turntable
        self._unreal_render_sequence_to_movie(unreal_exec_path, unreal_project_path, turntable_map_path, sequence_path, destination_folder, movie_name)
        
        # Publish the movie file to Shotgun
        super(MayaUnrealTurntablePublishPlugin, self).publish(settings, item)
        
        # Create a Version entry linked with the new publish
        publish_name = item.properties.get("publish_name")
        
        # Populate the version data to send to SG
        self.logger.info("Creating Version...")
        version_data = {
            "project": item.context.project,
            "code": movie_name,
            "description": item.description,
            "entity": self._get_version_entity(item),
            "sg_path_to_movie": publish_path,
            "sg_task": item.context.task
        }

        publish_data = item.properties.get("sg_publish_data")

        # If the file was published, add the publish data to the version
        if publish_data:
            version_data["published_files"] = [publish_data]

        # Log the version data for debugging
        self.logger.debug(
            "Populated Version data...",
            extra={
                "action_show_more_info": {
                    "label": "Version Data",
                    "tooltip": "Show the complete Version data dictionary",
                    "text": "<pre>%s</pre>" % (
                    pprint.pformat(version_data),)
                }
            }
        )

        # Create the version
        self.logger.info("Creating version for review...")
        version = self.parent.shotgun.create("Version", version_data)

        # Stash the version info in the item just in case
        item.properties["sg_version_data"] = version

        # On windows, ensure the path is utf-8 encoded to avoid issues with
        # the shotgun api
        upload_path = item.properties.get("path")
        if sys.platform.startswith("win"):
            upload_path = upload_path.decode("utf-8")

        # Upload the file to SG
        self.logger.info("Uploading content...")
        self.parent.shotgun.upload(
            "Version",
            version["id"],
            upload_path,
            "sg_uploaded_movie"
        )
        self.logger.info("Upload complete!")
        
    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # do the base class finalization
        super(MayaUnrealTurntablePublishPlugin, self).finalize(settings, item)

        # bump the session file to the next version
        # self._save_to_next_version(item.properties["maya_path"], item, _save_session)
        
        # Delete the exported FBX and scripts from the temp folder
        shutil.rmtree(self.temp_folder)

        # Revive this when Unreal supports spaces in command line Python args
        # fbx_path = item.properties.get("temp_fbx_path")
        # if fbx_path:
        #     try:
        #         os.remove(fbx_path)
        #     except:
        #         pass

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
        
    def _maya_export_fbx(self, fbx_output_path):
        # Export scene to FBX
        try:
            self.logger.info("Exporting scene to FBX {}".format(fbx_output_path))
            cmds.FBXResetExport()
            cmds.FBXExportSmoothingGroups('-v', True)
            # Mel script equivalent: mel.eval('FBXExport -f "fbx_output_path"')
            cmds.FBXExport('-f', fbx_output_path)
        except:
            self.logger.error("Could not export scene to FBX")
            return False
            
        return True
        
    def _unreal_execute_script(self, unreal_exec_path, unreal_project_path, script_path):
        command_args = []
        command_args.append(unreal_exec_path)       # Unreal executable path
        command_args.append(unreal_project_path)    # Unreal project
        
        command_args.append('-ExecutePythonScript="{}"'.format(script_path))
        self.logger.info("Executing script in Unreal with arguments: {}".format(command_args))
        
        print "COMMAND ARGS: %s" % (command_args)

        subprocess.call(" ".join(command_args))

    def _unreal_render_sequence_to_movie(self, unreal_exec_path, unreal_project_path, unreal_map_path, sequence_path, destination_path, movie_name):
        """
        Renders a given sequence in a given level to a movie file
        
        :param destination_path: Destionation folder where to generate the movie file
        :param unreal_map_path: Path of the Unreal map in which to run the sequence
        :param sequence_path: Content Browser path of sequence to render
        :param movie_name: Filename of the movie that will be generated
        :returns: True if a movie file was generated, False otherwise
                  string representing the path of the generated movie file
        """
        # First, check if there's a file that will interfere with the output of the Sequencer
        # Sequencer can only render to avi file format
        output_filename = "{}.avi".format(movie_name)
        output_filepath = os.path.join(destination_path, output_filename)

        if os.path.isfile(output_filepath):
            # Must delete it first, otherwise the Sequencer will add a number in the filename
            try:
                os.remove(output_filepath)
            except OSError, e:
                self.logger.debug("Couldn't delete {}. The Sequencer won't be able to output the movie to that file.".format(output_filepath))
                return False, None

        # Render the sequence to a movie file using the following command-line arguments
        cmdline_args = []
        
        # Note that any command-line arguments (usually paths) that could contain spaces must be enclosed between quotes

        # Important to keep the order for these arguments
        cmdline_args.append(unreal_exec_path)       # Unreal executable path
        cmdline_args.append(unreal_project_path)    # Unreal project
        cmdline_args.append(unreal_map_path)        # Level to load for rendering the sequence
        
        # Command-line arguments for Sequencer Render to Movie
        # See: https://docs.unrealengine.com/en-us/Engine/Sequencer/Workflow/RenderingCmdLine
        sequence_path = "-LevelSequence={}".format(sequence_path)
        cmdline_args.append(sequence_path)          # The sequence to render
        
        output_path = '-MovieFolder="{}"'.format(destination_path)
        cmdline_args.append(output_path)            # output folder, must match the work template

        movie_name_arg = "-MovieName={}".format(movie_name)
        cmdline_args.append(movie_name_arg)         # output filename
        
        cmdline_args.append("-game")
        cmdline_args.append("-MovieSceneCaptureType=/Script/MovieSceneCapture.AutomatedLevelSequenceCapture")
        cmdline_args.append("-ResX=1280")
        cmdline_args.append("-ResY=720")
        cmdline_args.append("-ForceRes")
        cmdline_args.append("-Windowed")
        cmdline_args.append("-MovieCinematicMode=yes")
        cmdline_args.append("-MovieFormat=Video")
        cmdline_args.append("-MovieFrameRate=24")
        cmdline_args.append("-MovieQuality=75")
        cmdline_args.append("-MovieWarmUpFrames=30")
        cmdline_args.append("-NoTextureStreaming")
        cmdline_args.append("-NoLoadingScreen")
        cmdline_args.append("-NoScreenMessages")

        self.logger.info("Sequencer command-line arguments: {}".format(cmdline_args))
        
        # Send the arguments as a single string because some arguments could contain spaces and we don't want those to be quoted
        subprocess.call(" ".join(cmdline_args))

        return os.path.isfile(output_filepath), output_filepath

    def _get_unreal_exec_path(self, settings):
        """
        Return the path to the Unreal Engine executable to use
        Uses the Engine Launcher logic to scan for Unreal executables and selects the one that
        matches the version defined in the settings, prioritizing non-development builds
        :returns an absolute path to the Unreal Engine executable to use:
        """
        unreal_engine_version_setting = settings.get("Unreal Engine Version")
        unreal_engine_version = unreal_engine_version_setting.value if unreal_engine_version_setting else None
        
        if not unreal_engine_version:
            return None

        # Create a launcher for the current context
        engine = sgtk.platform.current_engine()
        software_launcher = sgtk.platform.create_engine_launcher(engine.sgtk, engine.context, "tk-unreal")

        # Discover which versions of Unreal are available
        software_versions = software_launcher.scan_software()
        valid_versions = []
        for software_version in software_versions:
            if software_version.version.startswith(unreal_engine_version):
                # Insert non-dev builds at the start of the list
                if "(Dev Build)" not in software_version.display_name:
                    valid_versions.insert(0, software_version)
                else:
                    valid_versions.append(software_version)

        # Take the first valid version
        if valid_versions:
            return valid_versions[0].path
            
        return None

    def _get_unreal_project_path(self, settings):
        """
        Return the path to the Unreal project to use based on the "Unreal Project Path" and
        "Unreal Engine Version" settings. It uses the same path resolution as for hook paths
        to expand {config} and {engine} to their absolute path equivalent.
        :returns an absolute path to the Unreal project to use:
        """
        unreal_project_path_setting = settings.get("Unreal Project Path")
        unreal_project_path = unreal_project_path_setting.value if unreal_project_path_setting else None
        if not unreal_project_path:
            return None

        unreal_engine_version_setting = settings.get("Unreal Engine Version")
        unreal_engine_version = unreal_engine_version_setting.value if unreal_engine_version_setting else None
        if unreal_engine_version:
            unreal_project_path = unreal_project_path.replace("{unreal_engine_version}", unreal_engine_version)
        
        if unreal_project_path.startswith("{config}"):
            hooks_folder = self.sgtk.pipeline_configuration.get_hooks_location()
            unreal_project_path = unreal_project_path.replace("{config}", hooks_folder)
        elif unreal_project_path.startswith("{engine}"):
            engine = sgtk.platform.current_engine()
            engine_hooks_path = os.path.join(engine.disk_location, "hooks")
            unreal_project_path = unreal_project_path.replace("{engine}", engine_hooks_path)

        return os.path.normpath(unreal_project_path)
        
    def get_unreal_exec_path(self):
        """
        Return the path to the Unreal Engine executable to use
        Override this function in a custom hook derived from this class to implement your own logic
        or override the path from the settings
        :returns an absolute path to the Unreal Engine executable to use; None to use the path from the settings:
        """
        return None
        
    def get_unreal_project_path(self):
        """
        Return the path to the Unreal project to use
        Override this function in a custom hook derived from this class to implement your own logic
        or override the path from the settings
        :returns an absolute path to the Unreal project to use; None to use the path from the settings:
        """
        return None
        
def _get_work_path(path, work_template):
    """
    Return the equivalent work path with the filename from path applied to the work template
    :param path: An absulote path with a filename
    :param work_template: A template to use to get the work path
    :returns a work path:
    """
    # Get the filename from the path
    filename = os.path.split(path)[1]
    
    # Retrieve the name field from the filename excluding the extension
    work_path_fields = {"name" : os.path.splitext(filename)[0]}
    
    # Apply the name to the work template
    work_path = work_template.apply_fields(work_path_fields)
    work_path = os.path.normpath(work_path)

    return work_path

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = cmds.file(query=True, sn=True)

    if isinstance(path, unicode):
        path = path.encode("utf-8")

    return path


def _save_session(path):
    """
    Save the current session to the supplied path.
    """

    # Maya can choose the wrong file type so we should set it here
    # explicitly based on the extension
    maya_file_type = None
    if path.lower().endswith(".ma"):
        maya_file_type = "mayaAscii"
    elif path.lower().endswith(".mb"):
        maya_file_type = "mayaBinary"

    cmds.file(rename=path)

    # save the scene:
    if maya_file_type:
        cmds.file(save=True, force=True, type=maya_file_type)
    else:
        cmds.file(save=True, force=True)


# TODO: method duplicated in all the maya hooks
def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    # default save callback
    callback = cmds.SaveScene

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current session",
            "callback": callback
        }
    }
